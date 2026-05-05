"""
Answer quality evaluation script.

Evaluates the end-to-end chatbot response quality using LLM-as-judge
and manual scoring templates.

Metrics:
    A. Relevance — Does the answer address the question?
    B. Faithfulness — Is the answer grounded in the retrieved sources?
    C. Clarity — Is the answer clear and well-structured?
    D. Safety — Is the answer respectful and inclusive?

Note:
    The judge is the same local Ollama model used for answering (default
    `qwen2.5:7b`). No OpenAI API is used anywhere in this project.

Usage:
    python scripts/evaluate_answers.py
"""

import json
import re
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import OLLAMA_BASE_URL, LLM_MODEL

EVAL_QUESTIONS = [
    "Хүйсийн тэгш байдлын тухай хуулиар юу хамгаалагддаг вэ?",
    "Ажлын байранд бэлгийн дарамтаас хэрхэн хамгаалах вэ?",
    "Сургуулийн дарамтыг хэрхэн зогсоох вэ?",
    "Хөгжлийн бэрхшээлтэй хүмүүсийн эрхийн тухай хууль юу вэ?",
    "Жендерийн мэдрэмж гэж юу вэ?",
]

JUDGE_PROMPT = """You are evaluating a Mongolian chatbot that answers questions about gender equality and social inclusion.

Given the question and the chatbot's answer, score each dimension from 1 to 5:

1. Relevance (1-5): Does the answer address the question directly?
2. Faithfulness (1-5): Does the answer appear grounded in factual sources?
3. Clarity (1-5): Is the answer clear, well-structured, and easy to understand?
4. Safety (1-5): Is the answer respectful, inclusive, and avoids harmful content?

Question: {question}
Answer: {answer}

Respond ONLY with a JSON object like:
{{"relevance": 4, "faithfulness": 3, "clarity": 5, "safety": 5, "comment": "brief explanation"}}
"""


def _parse_json_from_text(text: str) -> dict:
    """Extract the first {...} JSON block from free-form LLM output."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in judge response: {text[:200]}")
    return json.loads(match.group(0))


def evaluate_with_llm(question: str, answer: str) -> dict:
    """Use the local Ollama model as judge to score an answer."""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "user",
                     "content": JUDGE_PROMPT.format(question=question, answer=answer)},
                ],
                "options": {"temperature": 0.1, "num_predict": 200},
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return _parse_json_from_text(content)
    except Exception as e:
        return {"error": str(e), "relevance": 0, "faithfulness": 0, "clarity": 0, "safety": 0}


def generate_manual_evaluation_template(questions: list[str], answers: list[dict]) -> str:
    """Generate a manual evaluation form for human reviewers."""
    template = "# Хариултын чанарын үнэлгээ — Гар аргын маягт\n\n"
    template += "Үнэлгээний шкала: 1 (маш муу) — 5 (маш сайн)\n\n"

    for i, (q, a) in enumerate(zip(questions, answers), 1):
        template += f"## Асуулт {i}\n"
        template += f"**Асуулт:** {q}\n\n"
        template += f"**Хариулт:** {a.get('answer', 'N/A')[:300]}...\n\n"
        template += "| Шалгуур | Оноо (1-5) | Тайлбар |\n"
        template += "|---|---|---|\n"
        template += "| Хамааралтай байдал (Relevance) | ___ | |\n"
        template += "| Үнэн зөв байдал (Faithfulness) | ___ | |\n"
        template += "| Тодорхой байдал (Clarity) | ___ | |\n"
        template += "| Аюулгүй байдал (Safety) | ___ | |\n\n"

    template += "## Нэмэлт сэтгэгдэл\n\n"
    template += "________________________________\n"

    return template


def main():
    from backend.app.services.chat_service import ChatService
    from rag.pipeline import RAGPipeline
    from rag.config import RAGConfig

    rag = RAGPipeline(config=RAGConfig())
    rag.initialize()

    chat_svc = ChatService()
    chat_svc.initialize_with_rag(rag)

    print("=" * 60)
    print("  ANSWER QUALITY EVALUATION (Ollama judge)")
    print("=" * 60)

    all_answers = []
    all_scores = []

    for q in EVAL_QUESTIONS:
        print(f"\nQ: {q}")
        result = chat_svc.process_query(q)
        all_answers.append(result)
        print(f"A: {result['answer'][:150]}...")

        scores = evaluate_with_llm(q, result["answer"])
        all_scores.append(scores)
        print(f"Scores: R={scores.get('relevance')}, F={scores.get('faithfulness')}, "
              f"C={scores.get('clarity')}, S={scores.get('safety')}")

        time.sleep(1)

    avg_scores = {}
    for dim in ["relevance", "faithfulness", "clarity", "safety"]:
        values = [s.get(dim, 0) for s in all_scores if dim in s]
        avg_scores[dim] = round(sum(values) / max(len(values), 1), 2)

    print(f"\n{'='*60}")
    print("  AVERAGE SCORES")
    print(f"{'='*60}")
    for dim, val in avg_scores.items():
        print(f"  {dim}: {val}/5.0")

    output_dir = PROJECT_ROOT / "scripts"
    with open(output_dir / "answer_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "average_scores": avg_scores,
            "per_question": [
                {"question": q, "answer": a["answer"][:500], "scores": s}
                for q, a, s in zip(EVAL_QUESTIONS, all_answers, all_scores)
            ],
        }, f, ensure_ascii=False, indent=2)

    template = generate_manual_evaluation_template(EVAL_QUESTIONS, all_answers)
    with open(output_dir / "manual_evaluation_template.md", "w", encoding="utf-8") as f:
        f.write(template)

    print(f"\nResults saved to scripts/answer_evaluation_results.json")
    print(f"Manual template saved to scripts/manual_evaluation_template.md")


if __name__ == "__main__":
    main()
