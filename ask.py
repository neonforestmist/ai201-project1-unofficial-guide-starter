"""Ask grounded questions against the Project 1 RAG pipeline.

Run:
    python3 retrieval.py index
    python3 ask.py "Is ML4T a good first OMSCS course?"
    python3 ask.py evaluate

Use --dry-run to inspect retrieved context and prompts without a Groq API key.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from groq import Groq

from retrieval import (
    DEFAULT_TOP_K,
    EVALUATION_QUESTIONS,
    RetrievedChunk,
    excerpt,
    retrieve,
)


GENERATION_RESULTS_PATH = Path("documents/generation_results.md")
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_CONTEXT_CHARS_PER_SOURCE = 1200
MAX_RELEVANT_DISTANCE = 0.62

SYSTEM_PROMPT = """You are The Unofficial Guide, a careful RAG assistant for Georgia Tech OMSCS AI/ML course planning.

Grounding rules:
- Answer only from the retrieved source excerpts in the user message.
- Do not use outside knowledge, guesses, or unstated assumptions.
- Use conversation history only to understand follow-up references, not as evidence.
- If the excerpts do not contain enough evidence, say that the retrieved documents do not contain enough information.
- Summarize patterns across sources instead of treating one student's review as universal truth.
- Cite every factual claim about courses with source labels like [S1] or [S2].
- End with a short "Sources" section listing the source labels you used.
"""


@dataclass(frozen=True)
class SourceForPrompt:
    label: str
    chunk: RetrievedChunk
    excerpt: str


@dataclass(frozen=True)
class ChatTurn:
    question: str
    answer: str


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    sources: List[SourceForPrompt]
    used_llm: bool


def load_api_client() -> Groq:
    load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env, add your Groq key, "
            "then rerun this command. Use --dry-run to inspect retrieved context "
            "without making an LLM call."
        )
    return Groq()


def sources_for_prompt(chunks: List[RetrievedChunk]) -> List[SourceForPrompt]:
    sources = []
    for index, chunk in enumerate(chunks, start=1):
        sources.append(
            SourceForPrompt(
                label=f"S{index}",
                chunk=chunk,
                excerpt=excerpt(chunk.text, max_chars=MAX_CONTEXT_CHARS_PER_SOURCE),
            )
        )
    return sources


def format_context(sources: List[SourceForPrompt]) -> str:
    blocks = []
    for source in sources:
        chunk = source.chunk
        blocks.append(
            "\n".join(
                [
                    f"[{source.label}]",
                    f"Chunk ID: {chunk.chunk_id}",
                    f"Distance: {chunk.distance:.4f}",
                    f"Source: {chunk.source_name}",
                    f"Course/topic: {chunk.course}",
                    f"URL: {chunk.url}",
                    f"Excerpt: {source.excerpt}",
                ]
            )
        )
    return "\n\n".join(blocks)


def format_history(history: Optional[List[ChatTurn]]) -> str:
    if not history:
        return ""

    lines = []
    for turn in history[-3:]:
        lines.append(f"User: {turn.question}")
        lines.append(f"Assistant: {excerpt(turn.answer, max_chars=500)}")
    return "\n".join(lines)


def build_user_prompt(
    question: str,
    sources: List[SourceForPrompt],
    history: Optional[List[ChatTurn]] = None,
) -> str:
    parts = []
    history_text = format_history(history)
    if history_text:
        parts.extend(
            [
                "Conversation history for follow-up resolution only:",
                history_text,
                "",
            ]
        )

    parts.extend(
        [
            f"Question: {question}",
            "Retrieved source excerpts:",
            format_context(sources),
            "Write a concise, grounded answer with citations.",
        ]
    )
    return "\n\n".join(parts)


def source_list(sources: List[SourceForPrompt]) -> str:
    lines = []
    for source in sources:
        chunk = source.chunk
        lines.append(
            f"[{source.label}] {chunk.source_name} | {chunk.course} | "
            f"{chunk.chunk_id} | {chunk.url}"
        )
    return "\n".join(lines)


def retrieval_query_for(question: str, history: Optional[List[ChatTurn]]) -> str:
    if not history:
        return question
    prior_questions = [turn.question for turn in history[-2:]]
    return " ".join(prior_questions + [question])


def should_refuse(chunks: List[RetrievedChunk]) -> bool:
    return not chunks or chunks[0].distance > MAX_RELEVANT_DISTANCE


def refusal_answer() -> str:
    return (
        "I don't have enough information in the retrieved documents to answer that "
        "question. The closest retrieved chunks are outside the supported OMSCS "
        "AI/ML course-advice scope, so I will not guess."
    )


def ask(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    dry_run: bool = False,
    history: Optional[List[ChatTurn]] = None,
) -> AnswerResult:
    retrieval_question = retrieval_query_for(question, history)
    chunks = retrieve(retrieval_question, top_k=top_k)
    sources = sources_for_prompt(chunks)

    if should_refuse(chunks):
        return AnswerResult(question, refusal_answer(), sources, used_llm=False)

    if dry_run:
        answer = "\n\n".join(
            [
                "DRY RUN: no LLM call was made.",
                "System prompt:",
                SYSTEM_PROMPT,
                "User prompt:",
                build_user_prompt(question, sources, history=history),
                "Sources:",
                source_list(sources),
            ]
        )
        return AnswerResult(question, answer, sources, used_llm=False)

    client = load_api_client()
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(question, sources, history=history)},
        ],
        temperature=0.2,
        max_tokens=900,
    )
    answer = completion.choices[0].message.content.strip()
    return AnswerResult(question, answer, sources, used_llm=True)


def print_answer(result: AnswerResult) -> None:
    print(f"Question: {result.question}\n")
    print(result.answer)
    if result.used_llm:
        print("\nRetrieved sources:")
        print(source_list(result.sources))


def summarize_answer(answer: str, max_chars: int = 550) -> str:
    return excerpt(answer, max_chars=max_chars)


def write_generation_report(results: List[AnswerResult]) -> None:
    lines = [
        "# Milestone 5 Generation Results",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Model: `{GROQ_MODEL}`",
        f"Top-k retrieval: {DEFAULT_TOP_K}",
        "",
    ]

    for index, result in enumerate(results, start=1):
        lines.extend(
            [
                f"## Question {index}",
                "",
                result.question,
                "",
                "### Answer",
                "",
                result.answer,
                "",
                "### Retrieved Sources",
                "",
                source_list(result.sources),
                "",
            ]
        )

    GENERATION_RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")


def run_evaluation(top_k: int = DEFAULT_TOP_K, dry_run: bool = False) -> None:
    results = []
    for question in EVALUATION_QUESTIONS:
        result = ask(question, top_k=top_k, dry_run=dry_run)
        results.append(result)
        print_answer(result)
        print("\n" + "-" * 80 + "\n")

    if dry_run:
        print("Dry run complete; generation report was not written.")
        return

    write_generation_report(results)
    print(f"Wrote generation report to {GENERATION_RESULTS_PATH}")


def run_chat(top_k: int = DEFAULT_TOP_K, dry_run: bool = False) -> None:
    history: List[ChatTurn] = []
    print('Start chatting. Type "exit" or "quit" to stop.')
    while True:
        question = input("You: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        result = ask(question, top_k=top_k, dry_run=dry_run, history=history)
        print_answer(result)
        print()
        history.append(ChatTurn(question=question, answer=result.answer))
        history = history[-4:]


def run_memory_demo(top_k: int = DEFAULT_TOP_K, dry_run: bool = False) -> None:
    history: List[ChatTurn] = []
    demo_questions = [
        "Is Machine Learning for Trading a reasonable first OMSCS AI/ML course?",
        "What should I watch out for if I take it first?",
    ]

    for question in demo_questions:
        print(f"You: {question}\n")
        result = ask(question, top_k=top_k, dry_run=dry_run, history=history)
        print_answer(result)
        print("\n" + "-" * 80 + "\n")
        history.append(ChatTurn(question=question, answer=result.answer))
        history = history[-4:]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask grounded RAG questions.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Number of chunks to retrieve before generation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print retrieved context and prompts without calling Groq.",
    )

    parser.add_argument(
        "args",
        nargs="*",
        help='Question text, or "evaluate" to run the five planning.md questions.',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        if args.args and args.args[0] == "evaluate":
            run_evaluation(top_k=args.top_k, dry_run=args.dry_run)
            return
        if args.args and args.args[0] == "chat":
            run_chat(top_k=args.top_k, dry_run=args.dry_run)
            return
        if args.args and args.args[0] == "memory-demo":
            run_memory_demo(top_k=args.top_k, dry_run=args.dry_run)
            return

        question_args = args.args[1:] if args.args and args.args[0] == "ask" else args.args
        question = " ".join(question_args).strip()

        if not question:
            raise SystemExit('Provide a question or use "evaluate".')

        print_answer(ask(question, top_k=args.top_k, dry_run=args.dry_run))
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
