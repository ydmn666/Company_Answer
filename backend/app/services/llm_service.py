import json
import logging
import re
import time
from collections.abc import Iterator

import httpx

from app.core.config import settings
from app.core.logging_utils import log_event
from app.services.retrieval_service import tokenize


logger = logging.getLogger(__name__)

SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？；;.!?])")
STREAM_TOTAL_TIMEOUT_SECONDS = 75.0
STREAM_IDLE_TIMEOUT_SECONDS = 12.0
STREAM_READ_TIMEOUT_SECONDS = 15.0
STREAM_EMPTY_LINE_LIMIT = 24
STREAM_EMPTY_DATA_LIMIT = 12
STREAM_RAW_LINE_LOG_LIMIT = 5


def _trace(event: str, **payload) -> None:
    log_event(logger, event, **payload)


def _sentence_score(question_tokens: set[str], sentence: str) -> int:
    sentence_tokens = set(tokenize(sentence))
    return len(question_tokens & sentence_tokens)


def _history_text(messages: list[dict], limit: int = 6) -> str:
    if not messages:
        return "无"

    lines = []
    for item in messages[-limit:]:
        content = (item.get("content") or "").strip()
        if not content:
            continue
        role = "用户" if item.get("role") == "user" else "助手"
        lines.append(f"{role}: {content}")
    return "\n".join(lines) or "无"


def _empty_context_answer() -> str:
    return "当前问题没有命中可直接支撑回答的文档片段，请补充更具体的问题或先查看右侧引用。"


def _local_chat_completion(messages: list[dict], context: list[dict]) -> str:
    if not context:
        return _empty_context_answer()

    question = messages[-1]["content"] if messages else ""
    question_tokens = set(tokenize(question))
    candidate_sentences: list[tuple[int, str, str]] = []

    for item in context:
        for sentence in SENTENCE_SPLIT_PATTERN.split(item["snippet"]):
            cleaned_sentence = sentence.strip()
            if not cleaned_sentence:
                continue
            score = _sentence_score(question_tokens, cleaned_sentence)
            candidate_sentences.append((score, cleaned_sentence, item["document_title"]))

    candidate_sentences.sort(key=lambda value: value[0], reverse=True)
    best_matches = [item for item in candidate_sentences if item[0] > 0][:3]

    if not best_matches:
        titles = "、".join(dict.fromkeys(item["document_title"] for item in context)) or "当前知识库"
        return f"已检索到相关资料，但暂时无法从现有片段中提炼出明确答案。建议优先查看：{titles}。"

    answer_sentences = []
    used_titles = []
    for _, sentence, document_title in best_matches:
        answer_sentences.append(sentence)
        if document_title not in used_titles:
            used_titles.append(document_title)

    joined_titles = "、".join(used_titles)
    history_hint = _history_text(messages[:-1], limit=2)
    if history_hint != "无":
        return f"结合前文对话和 {joined_titles} 的内容，{''.join(answer_sentences)}"
    return f"根据 {joined_titles} 的内容，{''.join(answer_sentences)}"


def _resolve_provider(provider: str | None) -> str:
    requested = (provider or settings.llm_default_provider or "local").lower()
    if requested in {"deepseek", "kimi", "local"}:
        return requested
    return "local"


def _provider_config(provider: str) -> tuple[str, str, str] | None:
    if provider == "deepseek":
        if not settings.deepseek_api_key:
            return None
        return settings.deepseek_api_key, settings.deepseek_base_url.rstrip("/"), settings.deepseek_chat_model

    if provider == "kimi":
        if not settings.kimi_api_key:
            return None
        return settings.kimi_api_key, settings.kimi_base_url.rstrip("/"), settings.kimi_chat_model

    return None


def _build_context_text(context: list[dict]) -> str:
    if not context:
        return "无"

    parts = []
    for index, item in enumerate(context, start=1):
        page_suffix = f"\n页码：{item['page_no']}" if item.get("page_no") else ""
        section_suffix = f"\n章节：{item['section_title']}" if item.get("section_title") else ""
        parts.append(f"[{index}] 文档：{item['document_title']}{page_suffix}{section_suffix}\n片段：{item['snippet']}")
    return "\n\n".join(parts)


def _system_prompt() -> str:
    return (
        "你是企业知识检索系统中的问答助手。"
        "必须严格依据提供的文档片段回答，使用简洁中文。"
        "如果文档中没有足够信息，请明确说明无法确认，不要编造。"
        "如果当前问题是追问，需要结合最近几轮对话去理解指代。"
        "回答时尽量简短，先给结论。"
    )


def _build_remote_payload(messages: list[dict], context: list[dict], model: str, stream: bool) -> dict:
    question = messages[-1]["content"] if messages else ""
    history_text = _history_text(messages[:-1])
    context_text = _build_context_text(context)
    return {
        "model": model,
        "temperature": 0.2,
        "stream": stream,
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {
                "role": "user",
                "content": f"当前问题：{question}\n\n最近多轮上下文：\n{history_text}\n\n可用文档片段：\n{context_text}",
            },
        ],
    }


def _extract_delta_text(delta_content) -> list[str]:
    if isinstance(delta_content, str):
        return [delta_content] if delta_content else []
    if isinstance(delta_content, list):
        texts = []
        for item in delta_content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    texts.append(text)
        return texts
    return []


def _stream_remote_chat_completion(provider: str, messages: list[dict], context: list[dict]) -> tuple[Iterator[str], str]:
    if not context:
        _trace("stream.skip_empty_context", provider=provider)
        return iter([_empty_context_answer()]), "local"

    config = _provider_config(provider)
    if not config:
        _trace("stream.fallback_no_provider_config", provider=provider)
        answer = _local_chat_completion(messages, context)
        return iter([answer]), "local"

    api_key, base_url, model = config
    payload = _build_remote_payload(messages, context, model, stream=True)

    def generate() -> Iterator[str]:
        start_time = time.monotonic()
        last_token_at = start_time
        token_count = 0
        done_received = False
        finish_reason: str | None = None
        empty_line_count = 0
        empty_data_count = 0
        raw_line_samples: list[str] = []
        status_code: int | None = None
        timeout = httpx.Timeout(30.0, connect=10.0, read=STREAM_READ_TIMEOUT_SECONDS)

        _trace("stream.start", provider=provider, model=model, context_size=len(context))

        try:
            with httpx.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            ) as response:
                status_code = response.status_code
                _trace("stream.connected", provider=provider, status_code=status_code)
                response.raise_for_status()

                for raw_line in response.iter_lines():
                    now = time.monotonic()
                    if now - start_time > STREAM_TOTAL_TIMEOUT_SECONDS:
                        _trace("stream.total_timeout", provider=provider, status_code=status_code, tokens=token_count)
                        break

                    if token_count == 0 and now - last_token_at > STREAM_IDLE_TIMEOUT_SECONDS:
                        _trace("stream.idle_timeout_before_first_token", provider=provider, status_code=status_code)
                        break

                    if raw_line is None:
                        empty_line_count += 1
                        if empty_line_count >= STREAM_EMPTY_LINE_LIMIT:
                            _trace("stream.too_many_empty_lines", provider=provider, status_code=status_code)
                            break
                        continue

                    line = raw_line.strip()
                    if len(raw_line_samples) < STREAM_RAW_LINE_LOG_LIMIT and line:
                        raw_line_samples.append(line[:240])
                        _trace("stream.raw_line", provider=provider, index=len(raw_line_samples), line=line[:180])

                    if not line:
                        empty_line_count += 1
                        if empty_line_count >= STREAM_EMPTY_LINE_LIMIT:
                            _trace("stream.too_many_blank_lines", provider=provider, status_code=status_code)
                            break
                        continue

                    empty_line_count = 0

                    if not line.startswith("data:"):
                        continue

                    body = line[5:].strip()
                    if not body:
                        empty_data_count += 1
                        if empty_data_count >= STREAM_EMPTY_DATA_LIMIT:
                            _trace("stream.too_many_empty_data", provider=provider, status_code=status_code)
                            break
                        continue

                    empty_data_count = 0

                    if body == "[DONE]":
                        done_received = True
                        _trace("stream.done_marker", provider=provider, status_code=status_code, tokens=token_count)
                        break

                    try:
                        data = json.loads(body)
                    except json.JSONDecodeError:
                        _trace("stream.invalid_json", provider=provider, body=body[:120])
                        continue

                    choice = (data.get("choices") or [{}])[0]
                    finish_reason = choice.get("finish_reason") or finish_reason
                    delta = choice.get("delta") or {}
                    emitted = False

                    for text in _extract_delta_text(delta.get("content")):
                        if text:
                            emitted = True
                            token_count += 1
                            last_token_at = time.monotonic()
                            _trace("stream.token", provider=provider, token_count=token_count, size=len(text))
                            yield text

                    if finish_reason in {"stop", "length"}:
                        _trace(
                            "stream.finish_reason",
                            provider=provider,
                            finish_reason=finish_reason,
                            tokens=token_count,
                            status_code=status_code,
                        )
                        break

                    if not emitted and token_count == 0 and time.monotonic() - last_token_at > STREAM_IDLE_TIMEOUT_SECONDS:
                        _trace("stream.no_token_timeout", provider=provider, status_code=status_code)
                        break

        except Exception as exc:
            _trace("stream.exception", provider=provider, status_code=status_code, error=repr(exc))
            fallback = _local_chat_completion(messages, context)
            if fallback:
                _trace("stream.exception_fallback_local", provider=provider)
                yield fallback
            return

        _trace(
            "stream.closed",
            provider=provider,
            status_code=status_code,
            done=done_received,
            finish_reason=finish_reason,
            tokens=token_count,
            raw_samples=raw_line_samples,
        )

        if token_count == 0:
            fallback = _local_chat_completion(messages, context)
            if fallback:
                _trace("stream.empty_output_fallback_local", provider=provider, status_code=status_code)
                yield fallback

    return generate(), provider


def _remote_chat_completion(provider: str, messages: list[dict], context: list[dict]) -> tuple[str, str]:
    if not context:
        _trace("remote.skip_empty_context", provider=provider)
        return _empty_context_answer(), "local"

    config = _provider_config(provider)
    if not config:
        _trace("remote.fallback_no_provider_config", provider=provider)
        return _local_chat_completion(messages, context), "local"

    api_key, base_url, model = config
    payload = _build_remote_payload(messages, context, model, stream=False)
    timeout = httpx.Timeout(45.0, connect=10.0, read=20.0)

    try:
        _trace("remote.start", provider=provider, model=model, context_size=len(context))
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        _trace("remote.connected", provider=provider, status_code=response.status_code)
        response.raise_for_status()
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip(), provider
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(text)
            if parts:
                _trace("remote.content_list", provider=provider, parts=len(parts))
                return "".join(parts).strip(), provider
        _trace("remote.empty_content", provider=provider)
    except Exception as exc:
        _trace("remote.exception", provider=provider, error=repr(exc))

    _trace("remote.fallback_local", provider=provider)
    return _local_chat_completion(messages, context), "local"


def chat_completion(messages: list[dict], context: list[dict], provider: str | None = None) -> tuple[str, str]:
    if not context:
        return _empty_context_answer(), "local"

    resolved_provider = _resolve_provider(provider)
    if resolved_provider == "local":
        return _local_chat_completion(messages, context), "local"
    return _remote_chat_completion(resolved_provider, messages, context)


def stream_chat_completion(messages: list[dict], context: list[dict], provider: str | None = None) -> tuple[Iterator[str], str]:
    if not context:
        return iter([_empty_context_answer()]), "local"

    resolved_provider = _resolve_provider(provider)
    if resolved_provider == "local":
        return iter([_local_chat_completion(messages, context)]), "local"
    return _stream_remote_chat_completion(resolved_provider, messages, context)


def answer_with_rag(messages: list[dict], chunks: list[dict], provider: str | None = None) -> dict:
    answer, provider_used = chat_completion(messages, chunks, provider)
    citations = [
        {
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "document_title": item["document_title"],
            "snippet": item["snippet"],
            "page_no": item.get("page_no"),
        }
        for item in chunks[:3]
    ]
    return {"answer": answer, "citations": citations, "provider_used": provider_used}
