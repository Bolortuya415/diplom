"""
Retrieval quality evaluation script.

Evaluates the RAG pipeline's retrieval performance using a benchmark
question set with known relevant documents.

Metrics:
    - Precision@k: What fraction of retrieved chunks are relevant?
    - Recall@k: What fraction of relevant chunks were retrieved?
    - Hit@k: Was at least one relevant chunk retrieved?
    - MRR (Mean Reciprocal Rank): How high is the first relevant chunk ranked?

Thesis note:
    These are standard information retrieval metrics used to evaluate
    the quality of the vector search component independently from the
    LLM generation quality. This separation allows us to diagnose whether
    poor answers stem from retrieval failure or generation failure.

Usage:
    python scripts/evaluate_retrieval.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.pipeline import RAGPipeline
from rag.config import RAGConfig

# Benchmark question set with expected relevant source files and keywords
# In a real evaluation, you would have human-annotated relevance judgments
BENCHMARK_QUESTIONS = [
    {
        "query": "Хүйсийн тэгш байдлын тухай хуулиар юу хамгаалагддаг вэ?",
        "relevant_keywords": ["тэгш байдал", "хууль", "хамгаалалт", "эрх"],
        "relevant_sources": [],  # Fill after ingesting real documents
        "category": "law",
    },
    {
        "query": "Ажлын байранд бэлгийн дарамтаас хэрхэн хамгаалах вэ?",
        "relevant_keywords": ["бэлгийн дарамт", "ажлын байр", "хамгаалалт"],
        "relevant_sources": [],
        "category": "workplace",
    },
    {
        "query": "Хүүхдийн эрхийн тухай хуулинд юу бичигдсэн бэ?",
        "relevant_keywords": ["хүүхэд", "эрх", "хууль"],
        "relevant_sources": [],
        "category": "children",
    },
    {
        "query": "Хөгжлийн бэрхшээлтэй хүмүүсийн эрхийн тухай хууль юу вэ?",
        "relevant_keywords": ["хөгжлийн бэрхшээл", "эрх", "хууль"],
        "relevant_sources": [],
        "category": "disability",
    },
    {
        "query": "Гэр бүлийн хүчирхийллийн тухай хууль юу хэлдэг вэ?",
        "relevant_keywords": ["гэр бүл", "хүчирхийлэл", "хууль"],
        "relevant_sources": [],
        "category": "domestic_violence",
    },
    {
        "query": "Ялгаварлан гадуурхалтын эсрэг хууль Монголд байдаг уу?",
        "relevant_keywords": ["ялгаварлан гадуурхалт", "хууль", "Монгол"],
        "relevant_sources": [],
        "category": "discrimination",
    },
    {
        "query": "Жендерийн мэдрэмж гэж юу вэ?",
        "relevant_keywords": ["жендер", "мэдрэмж", "ойлголт"],
        "relevant_sources": [],
        "category": "education",
    },
    {
        "query": "Тэгш хамруулах боловсрол гэж юу вэ?",
        "relevant_keywords": ["тэгш", "хамруулах", "боловсрол", "инклюзив"],
        "relevant_sources": [],
        "category": "education",
    },
    {
        "query": "Сургуулийн дарамтыг хэрхэн зогсоох вэ?",
        "relevant_keywords": ["сургууль", "дарамт", "зогсоох", "арга"],
        "relevant_sources": [],
        "category": "bullying",
    },
    {
        "query": "Эрэгтэй, эмэгтэй хүмүүсийн цалингийн зөрүүг хэрхэн арилгах вэ?",
        "relevant_keywords": ["цалин", "зөрүү", "эрэгтэй", "эмэгтэй", "тэгш"],
        "relevant_sources": [],
        "category": "pay_gap",
    },
]


def keyword_relevance(chunk_text: str, keywords: list[str]) -> bool:
    """Check if a chunk contains at least one relevant keyword."""
    text_lower = chunk_text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def evaluate_retrieval(pipeline: RAGPipeline, questions: list[dict], k_values: list[int] = None):
    """
    Evaluate retrieval quality across benchmark questions.

    Uses keyword-based relevance as a proxy when human annotations
    are not available.
    """
    if k_values is None:
        k_values = [1, 3, 5]

    results = {k: {"precision": [], "recall": [], "hit": [], "mrr": []} for k in k_values}

    for q in questions:
        query = q["query"]
        keywords = q["relevant_keywords"]

        for k in k_values:
            retrieved = pipeline.embedding_manager.search(query, top_k=k)

            if not retrieved:
                results[k]["precision"].append(0.0)
                results[k]["recall"].append(0.0)
                results[k]["hit"].append(0.0)
                results[k]["mrr"].append(0.0)
                continue

            # Check relevance of each retrieved chunk
            relevance = [keyword_relevance(r["text"], keywords) for r in retrieved]
            num_relevant = sum(relevance)

            # Precision@k
            precision = num_relevant / len(retrieved)
            results[k]["precision"].append(precision)

            # Hit@k (at least one relevant)
            hit = 1.0 if num_relevant > 0 else 0.0
            results[k]["hit"].append(hit)

            # MRR (reciprocal rank of first relevant)
            mrr = 0.0
            for rank, is_rel in enumerate(relevance, 1):
                if is_rel:
                    mrr = 1.0 / rank
                    break
            results[k]["mrr"].append(mrr)

            # Recall@k (approximate — we don't know total relevant)
            # Using hit as a proxy for recall in this simplified evaluation
            results[k]["recall"].append(hit)

    # Aggregate
    summary = {}
    for k in k_values:
        summary[f"k={k}"] = {
            "Precision@k": round(sum(results[k]["precision"]) / max(len(results[k]["precision"]), 1), 4),
            "Hit@k": round(sum(results[k]["hit"]) / max(len(results[k]["hit"]), 1), 4),
            "MRR": round(sum(results[k]["mrr"]) / max(len(results[k]["mrr"]), 1), 4),
            "num_queries": len(results[k]["precision"]),
        }

    return summary


def main():
    config = RAGConfig()
    pipeline = RAGPipeline(config=config)

    if not pipeline.initialize():
        print("No index found. Ingest documents first, then run evaluation.")
        print("\nBenchmark questions saved for future use.")

        # Save benchmark for later
        output_path = Path("scripts/benchmark_questions.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(BENCHMARK_QUESTIONS, f, ensure_ascii=False, indent=2)
        print(f"Saved to: {output_path}")
        return

    print("=" * 60)
    print("  RETRIEVAL QUALITY EVALUATION")
    print("=" * 60)

    summary = evaluate_retrieval(pipeline, BENCHMARK_QUESTIONS)

    for k_label, metrics in summary.items():
        print(f"\n  {k_label}:")
        for metric, value in metrics.items():
            print(f"    {metric}: {value}")

    # Save results
    output_path = Path("scripts/retrieval_evaluation_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
