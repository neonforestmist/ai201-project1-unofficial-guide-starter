"""Compare Project 1 chunking strategies for stretch credit.

Run:
    python3 chunking_comparison.py
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from retrieval import (
    MODEL_NAME,
    course_key_for_text,
    excerpt,
    infer_course_key,
    load_chunks,
    load_model,
)


REPORT_PATH = Path("documents/chunking_comparison.md")
CLEAN_DIR = Path("documents/clean")
FIXED_WINDOW_TOKENS = 450
FIXED_OVERLAP_TOKENS = 75

COMPARISON_QUERIES = [
    (
        "ML4T first-course advice",
        "Is Machine Learning for Trading a reasonable first OMSCS AI/ML course?",
        "The review/comment-boundary strategy performed better because its top results were complete Reddit comments and complete OMSCentral reviews about ML4T as a first class. The fixed-window baseline found related text, but some windows started or ended mid-comment.",
    ),
    (
        "AI prerequisite background",
        "What background do students recommend before taking Artificial Intelligence?",
        "The boundary strategy performed better because each top result kept one student's background, prerequisite list, and workload caveat together. Fixed windows sometimes blended adjacent reviews or cut off the reason a prerequisite mattered.",
    ),
    (
        "KBAI conceptual vs engineering-heavy",
        "How do students describe Knowledge-Based AI compared with more engineering-oriented AI/ML courses?",
        "The boundary strategy performed better because KBAI comparisons depend on a full opinion unit: writing, coding, cognitive science, philosophy, and project style are usually explained in one review. Fixed windows retrieved many of the same documents but were less self-contained.",
    ),
]


@dataclass(frozen=True)
class ComparableChunk:
    chunk_id: str
    source_name: str
    course: str
    text: str


@dataclass(frozen=True)
class RankedChunk:
    rank: int
    score: float
    chunk: ComparableChunk


def boundary_chunks() -> List[ComparableChunk]:
    return [
        ComparableChunk(
            chunk_id=chunk["id"],
            source_name=chunk["source_name"],
            course=chunk["course"],
            text=chunk["text"],
        )
        for chunk in load_chunks()
    ]


def header_value(lines: List[str], prefix: str, default: str) -> str:
    for line in lines[:8]:
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return default


def fixed_window_chunks() -> List[ComparableChunk]:
    chunks: List[ComparableChunk] = []
    step = FIXED_WINDOW_TOKENS - FIXED_OVERLAP_TOKENS

    for path in sorted(CLEAN_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        source_name = header_value(lines, "Source:", path.stem)
        course = header_value(lines, "Course/topic:", "Unknown")

        body_start = text.find("--- Item 1 ---")
        body = text[body_start:] if body_start >= 0 else text
        tokens = body.split()
        if not tokens:
            continue

        for index, start in enumerate(range(0, len(tokens), step), start=1):
            window_tokens = tokens[start : start + FIXED_WINDOW_TOKENS]
            if len(window_tokens) < 80:
                continue
            window_text = " ".join(window_tokens)
            chunks.append(
                ComparableChunk(
                    chunk_id=f"fixed-{path.stem}-{index:04d}",
                    source_name=source_name,
                    course=course,
                    text=f"Course/topic: {course}. Source: {source_name}. {window_text}",
                )
            )
    return chunks


def encode_texts(chunks: List[ComparableChunk], model: SentenceTransformer) -> np.ndarray:
    return model.encode(
        [chunk.text for chunk in chunks],
        batch_size=64,
        show_progress_bar=False,
        normalize_embeddings=True,
    )


def rank_query(
    query: str,
    chunks: List[ComparableChunk],
    embeddings: np.ndarray,
    model: SentenceTransformer,
    top_k: int = 3,
) -> List[RankedChunk]:
    query_embedding = model.encode(
        [query],
        show_progress_bar=False,
        normalize_embeddings=True,
    )[0]
    scores = np.sum(embeddings.astype("float64") * query_embedding.astype("float64"), axis=1)
    scores = np.nan_to_num(scores, nan=-1.0, posinf=-1.0, neginf=-1.0)
    top_indexes = np.argsort(scores)[::-1][:top_k]
    return [
        RankedChunk(rank=rank, score=float(scores[index]), chunk=chunks[index])
        for rank, index in enumerate(top_indexes, start=1)
    ]


def matching_indexes(chunks: List[ComparableChunk], course_key: str) -> List[int]:
    return [
        index
        for index, chunk in enumerate(chunks)
        if course_key_for_text(f"{chunk.course} {chunk.source_name}") == course_key
    ]


def format_ranked(hit: RankedChunk) -> str:
    chunk = hit.chunk
    return (
        f"{hit.rank}. `{chunk.chunk_id}` ({chunk.source_name}; {chunk.course}; "
        f"cosine {hit.score:.3f}) - {excerpt(chunk.text, max_chars=280)}"
    )


def write_report(path: Path = REPORT_PATH) -> None:
    current_chunks = boundary_chunks()
    fixed_chunks = fixed_window_chunks()
    model = load_model()
    current_embeddings = encode_texts(current_chunks, model)
    fixed_embeddings = encode_texts(fixed_chunks, model)

    lines = [
        "# Chunking Strategy Comparison",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Embedding model for comparison: `{MODEL_NAME}`",
        f"Strategy A: review/comment-boundary chunks from `documents/chunks.jsonl` ({len(current_chunks)} chunks)",
        f"Strategy B: fixed {FIXED_WINDOW_TOKENS}-token windows with {FIXED_OVERLAP_TOKENS}-token overlap over cleaned documents ({len(fixed_chunks)} chunks)",
        "",
    ]

    for label, query, judgment in COMPARISON_QUERIES:
        course_key = infer_course_key(query)
        current_query_chunks = current_chunks
        current_query_embeddings = current_embeddings
        fixed_query_chunks = fixed_chunks
        fixed_query_embeddings = fixed_embeddings

        if course_key:
            current_indexes = matching_indexes(current_chunks, course_key)
            fixed_indexes = matching_indexes(fixed_chunks, course_key)
            current_query_chunks = [current_chunks[index] for index in current_indexes]
            fixed_query_chunks = [fixed_chunks[index] for index in fixed_indexes]
            current_query_embeddings = current_embeddings[current_indexes]
            fixed_query_embeddings = fixed_embeddings[fixed_indexes]

        current_hits = rank_query(query, current_query_chunks, current_query_embeddings, model)
        fixed_hits = rank_query(query, fixed_query_chunks, fixed_query_embeddings, model)

        lines.extend([f"## {label}", "", f"Query: {query}", ""])
        if course_key:
            lines.extend([f"Course-aware comparison filter: `{course_key}`", ""])
        lines.extend(["### Strategy A: review/comment-boundary chunks", ""])
        lines.extend(format_ranked(hit) for hit in current_hits)
        lines.append("")

        lines.extend(["### Strategy B: fixed windows", ""])
        lines.extend(format_ranked(hit) for hit in fixed_hits)
        lines.extend(["", f"**Which performed better:** {judgment}", ""])

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote chunking comparison report to {path}")


if __name__ == "__main__":
    write_report()
