import json
import re
from collections.abc import Iterator

import httpx

from app.core.config import settings
from app.services.retrieval_service import tokenize


SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？；;.!?])")


def _sentence_score(question_tokens: set[str], sentence: str) -> int:
    sentence_tokens = set(tokenize(sentence))
    return len(question_tokens & sentence_tokens)


def _local_chat_completion(messages: list[dict], context: list[dict]) -> str:
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
    best_matches = [item for item in candidate_sentences if item[0] > 0][:2]

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
    parts = []
    for index, item in enumerate(context, start=1):
        page_suffix = f"\n页码：{item['page_no']}" if item.get("page_no") else ""
        section_suffix = f"\n章节：{item['section_title']}" if item.get("section_title") else ""
        parts.append(f"[{index}] 文档：{item['document_title']}{page_suffix}{section_suffix}\n片段：{item['snippet']}")
    return "\n\n".join(parts)


def _system_prompt() -> str:
    return (
        "你是企业知识检索系统中的问答助手。"
        "你必须严格依据提供的文档片段回答，使用简洁中文。"
        "如果文档中没有足够信息，请明确说明无法确认，不要编造。"
        "回答时先直接给结论，再用一句话说明依据。"
        "引用依据时优先使用文档标题或文档编号，不要虚构来源。"
    )


def _stream_remote_chat_completion(provider: str, messages: list[dict], context: list[dict]) -> tuple[Iterator[str], str]:
    config = _provider_config(provider)
    if not config:
        answer = _local_chat_completion(messages, context)
        return iter([answer]), "local"

    api_key, base_url, model = config
    question = messages[-1]["content"] if messages else ""
    context_text = _build_context_text(context)
    payload = {
        "model": model,
        "temperature": 0.2,
        "stream": True,
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": f"问题：{question}\n\n可用文档片段：\n{context_text}"},
        ],
    }

    def generate() -> Iterator[str]:
        try:
            with httpx.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60.0,
            ) as response:
                response.raise_for_status()
                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if not line.startswith("data:"):
                        continue
                    body = line[5:].strip()
                    if body == "[DONE]":
                        break

                    try:
                        data = json.loads(body)
                    except json.JSONDecodeError:
                        continue

                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if isinstance(content, str) and content:
                        yield content
                    elif isinstance(content, list):
                        for item in content:
                            text = item.get("text") if isinstance(item, dict) else None
                            if text:
                                yield text
        except Exception:
            yield _local_chat_completion(messages, context)

    return generate(), provider


def _remote_chat_completion(provider: str, messages: list[dict], context: list[dict]) -> tuple[str, str]:
    stream, provider_used = _stream_remote_chat_completion(provider, messages, context)
    return "".join(stream).strip(), provider_used


def chat_completion(messages: list[dict], context: list[dict], provider: str | None = None) -> tuple[str, str]:
    resolved_provider = _resolve_provider(provider)
    if resolved_provider == "local":
        return _local_chat_completion(messages, context), "local"
    return _remote_chat_completion(resolved_provider, messages, context)


def stream_chat_completion(messages: list[dict], context: list[dict], provider: str | None = None) -> tuple[Iterator[str], str]:
    resolved_provider = _resolve_provider(provider)
    if resolved_provider == "local":
        return iter([_local_chat_completion(messages, context)]), "local"
    return _stream_remote_chat_completion(resolved_provider, messages, context)


def answer_with_rag(question: str, chunks: list[dict], provider: str | None = None) -> dict:
    answer, provider_used = chat_completion([{"role": "user", "content": question}], chunks, provider)
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
