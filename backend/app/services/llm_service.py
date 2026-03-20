import math
import re
from collections import Counter

import httpx

from app.core.config import settings


TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？；;.!?])")
EMBEDDING_DIM = 8


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def generate_embedding(text: str) -> list[float]:
    # 当前 V1 的 embedding 是轻量本地实现，
    # 目标是先打通“向量检索链路”。
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * EMBEDDING_DIM

    counter = Counter(tokens)
    vector = [0.0] * EMBEDDING_DIM
    for token, count in counter.items():
        vector[hash(token) % EMBEDDING_DIM] += float(count)

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _sentence_score(question_tokens: set[str], sentence: str) -> int:
    sentence_tokens = set(_tokenize(sentence))
    return len(question_tokens & sentence_tokens)


def _local_chat_completion(messages: list[dict], context: list[dict]) -> str:
    # 本地回退回答逻辑：
    # 没配云模型，或云模型失败时，会从引用片段里抽取句子回答。
    question = messages[-1]["content"] if messages else ""
    question_tokens = set(_tokenize(question))
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
    # 按 provider 取模型连接配置。
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
    # 把检索片段拼成大模型更容易消费的上下文文本。
    parts = []
    for index, item in enumerate(context, start=1):
        parts.append(f"[{index}] 文档：{item['document_title']}\n片段：{item['snippet']}")
    return "\n\n".join(parts)


def _remote_chat_completion(provider: str, messages: list[dict], context: list[dict]) -> tuple[str, str]:
    # 真正调用云端模型的地方。
    config = _provider_config(provider)
    if not config:
        return _local_chat_completion(messages, context), "local"

    api_key, base_url, model = config
    question = messages[-1]["content"] if messages else ""
    context_text = _build_context_text(context)
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是企业知识检索系统中的问答助手。"
                    "你必须严格根据提供的文档片段回答，使用简洁中文。"
                    "如果文档中没有足够信息，请明确说无法确认，不要编造。"
                    "回答时优先直接给出结论，再补一句依据。"
                ),
            },
            {
                "role": "user",
                "content": f"问题：{question}\n\n可用文档片段：\n{context_text}",
            },
        ],
    }

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        if not content:
            raise ValueError("Empty model response")
        return content, provider
    except Exception:
        return _local_chat_completion(messages, context), "local"


def chat_completion(messages: list[dict], context: list[dict], provider: str | None = None) -> tuple[str, str]:
    # 统一的回答入口，屏蔽前端对 provider 的感知差异。
    resolved_provider = _resolve_provider(provider)
    if resolved_provider == "local":
        return _local_chat_completion(messages, context), "local"
    return _remote_chat_completion(resolved_provider, messages, context)


def answer_with_rag(question: str, chunks: list[dict], provider: str | None = None) -> dict:
    # RAG 封装：输入问题 + 检索片段，输出答案 + 引用。
    answer, provider_used = chat_completion([{"role": "user", "content": question}], chunks, provider)
    citations = [
        {
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "document_title": item["document_title"],
            "snippet": item["snippet"],
        }
        for item in chunks[:3]
    ]
    return {"answer": answer, "citations": citations, "provider_used": provider_used}
