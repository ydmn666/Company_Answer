import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.llm_service import answer_with_rag
from app.services.retrieval_service import retrieve_top_chunks


def load_dataset() -> list[dict]:
    path = Path(settings.eval_dataset_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return json.loads(path.read_text(encoding="utf-8"))


def reciprocal_rank(results: list[str], relevant: set[str]) -> float:
    for index, item in enumerate(results, start=1):
        if item in relevant:
            return 1.0 / index
    return 0.0


def dcg(results: list[str], relevant: set[str]) -> float:
    score = 0.0
    for index, item in enumerate(results, start=1):
        gain = 1.0 if item in relevant else 0.0
        score += gain / math.log2(index + 1)
    return score


def ndcg(results: list[str], relevant: set[str]) -> float:
    ideal = dcg(list(relevant), relevant)
    if ideal == 0:
        return 0.0
    return dcg(results, relevant) / ideal


def answer_hit(answer: str, keywords: list[str]) -> bool:
    normalized = answer.lower()
    return all(keyword.lower() in normalized for keyword in keywords)


def format_answer_preview(answer: str, limit: int = 120) -> str:
    cleaned = " ".join(answer.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


def evaluate() -> None:
    dataset = load_dataset()
    if not dataset:
        print("评测集为空，未执行评测。")
        return

    db = SessionLocal()
    try:
        recall_scores = {k: [] for k in settings.eval_recall_k}
        mrr_scores = []
        ndcg_scores = []
        answer_scores = []

        print(f"Loaded {len(dataset)} evaluation samples from {settings.eval_dataset_path}")
        print("-" * 72)

        for index, item in enumerate(dataset, start=1):
            question = item["question"]
            relevant = set(item["relevant_documents"])
            chunks = retrieve_top_chunks(db, question, top_k=max(settings.eval_recall_k))
            ranked_docs = []
            for chunk in chunks:
                if chunk["document_title"] not in ranked_docs:
                    ranked_docs.append(chunk["document_title"])

            sample_recall = {}
            for k in settings.eval_recall_k:
                hit = 1.0 if any(doc in relevant for doc in ranked_docs[:k]) else 0.0
                recall_scores[k].append(hit)
                sample_recall[k] = hit

            sample_mrr = reciprocal_rank(ranked_docs, relevant)
            sample_ndcg = ndcg(ranked_docs, relevant)
            mrr_scores.append(sample_mrr)
            ndcg_scores.append(sample_ndcg)

            rag_result = answer_with_rag(question, chunks, provider="local")
            sample_answer_hit = 1.0 if answer_hit(rag_result["answer"], item["expected_answer_keywords"]) else 0.0
            answer_scores.append(sample_answer_hit)

            print(f"[{index}/{len(dataset)}] {question}")
            print(f"  Expected docs: {', '.join(item['relevant_documents'])}")
            print(f"  Retrieved docs: {', '.join(ranked_docs) if ranked_docs else 'None'}")
            print(
                "  Metrics: "
                + ", ".join([f"Recall@{k}={sample_recall[k]:.0f}" for k in settings.eval_recall_k])
                + f", MRR={sample_mrr:.4f}, nDCG={sample_ndcg:.4f}, AnswerHit={sample_answer_hit:.0f}"
            )
            print(f"  Expected keywords: {', '.join(item['expected_answer_keywords'])}")
            print(f"  Answer preview: {format_answer_preview(rag_result['answer'])}")
            print("-" * 72)

        print("Evaluation Summary")
        for k in settings.eval_recall_k:
            print(f"Recall@{k}: {sum(recall_scores[k]) / len(recall_scores[k]):.4f}")
        print(f"MRR: {sum(mrr_scores) / len(mrr_scores):.4f}")
        print(f"nDCG: {sum(ndcg_scores) / len(ndcg_scores):.4f}")
        print(f"Answer Hit Rate: {sum(answer_scores) / len(answer_scores):.4f}")
    finally:
        db.close()


if __name__ == "__main__":
    evaluate()
