"""Hybrid BM25 + semantic retrieval for Project 1 stretch credit.

Run:
    python3 hybrid_search.py query "Is ML4T a good first course?"
    python3 hybrid_search.py compare
"""

from __future__ import annotations

import argparse
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from retrieval import (
    COURSE_ALIASES,
    DEFAULT_TOP_K,
    MODEL_NAME,
    RetrievedChunk,
    course_key_for_text,
    excerpt,
    get_client,
    get_collection,
    infer_course_key,
    load_chunks,
    load_model,
    retrieve,
)


HYBRID_REPORT_PATH = Path("documents/hybrid_comparison.md")
TOKEN_RE = re.compile(r"[a-z0-9]+")
DEFAULT_SEMANTIC_WEIGHT = 0.65
DEFAULT_BM25_WEIGHT = 0.35

COMPARISON_QUERIES = [
    (
        "ML4T as a first course",
        "Is Machine Learning for Trading a reasonable first OMSCS AI/ML course?",
        "Hybrid performed best because it kept the semantic match to the Reddit first-course thread while BM25 boosted chunks that explicitly mention first class, intro to ML, and project/report expectations.",
    ),
    (
        "Recent NLP frustrations",
        "What recent Natural Language Processing reviews mention Meta lectures, tests, room scans, or confusing instructions?",
        "Hybrid performed best because semantic retrieval found the right NLP review area and BM25 rewarded exact terms such as Meta, lectures, tests, room scans, and instructions.",
    ),
    (
        "KBAI compared with engineering-heavy courses",
        "How do students describe Knowledge-Based AI compared with more engineering-oriented AI/ML courses?",
        "Semantic and hybrid were strongest; hybrid kept the KBAI conceptual/cognitive-science chunk while also surfacing chunks with explicit writing, coding, psychology, and philosophy language.",
    ),
]


@dataclass(frozen=True)
class Bm25Hit:
    rank: int
    chunk: dict
    score: float


@dataclass(frozen=True)
class HybridHit:
    rank: int
    chunk: dict
    semantic_score: float
    bm25_score: float
    hybrid_score: float


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


def filter_chunks(
    chunks: Iterable[dict],
    course_key: Optional[str] = None,
    source_type: Optional[str] = None,
) -> List[dict]:
    filtered = []
    for chunk in chunks:
        chunk_course_key = course_key_for_text(f"{chunk['course']} {chunk['source_name']}")
        if course_key and chunk_course_key != course_key:
            continue
        if source_type and chunk["source_type"] != source_type:
            continue
        filtered.append(chunk)
    return filtered


def bm25_scores(query: str, chunks: List[dict], k1: float = 1.5, b: float = 0.75) -> Dict[str, float]:
    query_terms = tokenize(query)
    if not query_terms or not chunks:
        return {}

    tokenized_docs = [tokenize(chunk["text"]) for chunk in chunks]
    doc_lengths = [len(tokens) for tokens in tokenized_docs]
    avg_doc_length = sum(doc_lengths) / len(doc_lengths)

    doc_freq: Counter[str] = Counter()
    for tokens in tokenized_docs:
        doc_freq.update(set(tokens))

    scores: Dict[str, float] = {}
    total_docs = len(chunks)
    for chunk, tokens, doc_length in zip(chunks, tokenized_docs, doc_lengths):
        term_counts = Counter(tokens)
        score = 0.0
        for term in query_terms:
            if term_counts[term] == 0:
                continue
            idf = math.log(1 + (total_docs - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            numerator = term_counts[term] * (k1 + 1)
            denominator = term_counts[term] + k1 * (1 - b + b * doc_length / avg_doc_length)
            score += idf * numerator / denominator
        scores[chunk["id"]] = score
    return scores


def normalize_scores(scores: Dict[str, float], candidate_ids: Iterable[str]) -> Dict[str, float]:
    candidate_ids = list(candidate_ids)
    values = [scores.get(chunk_id, 0.0) for chunk_id in candidate_ids]
    if not values:
        return {}

    max_score = max(values)
    min_score = min(values)
    if max_score == min_score:
        return {chunk_id: 1.0 if max_score > 0 else 0.0 for chunk_id in candidate_ids}

    return {
        chunk_id: (scores.get(chunk_id, 0.0) - min_score) / (max_score - min_score)
        for chunk_id in candidate_ids
    }


def bm25_search(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    course_key: Optional[str] = None,
    source_type: Optional[str] = None,
) -> List[Bm25Hit]:
    chunks = filter_chunks(load_chunks(), course_key=course_key, source_type=source_type)
    scores = bm25_scores(question, chunks)
    chunk_by_id = {chunk["id"]: chunk for chunk in chunks}
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
    return [
        Bm25Hit(rank=index, chunk=chunk_by_id[chunk_id], score=score)
        for index, (chunk_id, score) in enumerate(ranked, start=1)
    ]


def hybrid_search(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
    bm25_weight: float = DEFAULT_BM25_WEIGHT,
    course_key: Optional[str] = None,
    source_type: Optional[str] = None,
    use_course_filter: bool = True,
) -> Tuple[List[HybridHit], List[RetrievedChunk], List[Bm25Hit]]:
    active_course_key = course_key or (infer_course_key(question) if use_course_filter else None)
    chunks = filter_chunks(load_chunks(), course_key=active_course_key, source_type=source_type)
    if not chunks:
        raise RuntimeError("No chunks match the requested metadata filters.")

    candidate_count = min(max(top_k * 8, 25), len(chunks))
    model = load_model()
    collection = get_collection(get_client())
    semantic_results = retrieve(
        question,
        top_k=candidate_count,
        model=model,
        collection=collection,
        use_course_filter=False,
        course_key=active_course_key,
        source_type=source_type,
    )
    bm25_results = bm25_search(
        question,
        top_k=candidate_count,
        course_key=active_course_key,
        source_type=source_type,
    )

    chunk_by_id = {chunk["id"]: chunk for chunk in chunks}
    semantic_scores = {
        result.chunk_id: max(0.0, 1.0 - result.distance)
        for result in semantic_results
    }
    bm25_score_map = {hit.chunk["id"]: hit.score for hit in bm25_results}

    candidate_ids = set(semantic_scores) | set(bm25_score_map)
    normalized_semantic = normalize_scores(semantic_scores, candidate_ids)
    normalized_bm25 = normalize_scores(bm25_score_map, candidate_ids)

    ranked = []
    for chunk_id in candidate_ids:
        semantic_score = normalized_semantic.get(chunk_id, 0.0)
        bm25_score = normalized_bm25.get(chunk_id, 0.0)
        ranked.append(
            (
                chunk_id,
                semantic_score,
                bm25_score,
                semantic_weight * semantic_score + bm25_weight * bm25_score,
            )
        )

    ranked.sort(key=lambda item: item[3], reverse=True)
    hits = [
        HybridHit(
            rank=index,
            chunk=chunk_by_id[chunk_id],
            semantic_score=semantic_score,
            bm25_score=bm25_score,
            hybrid_score=hybrid_score,
        )
        for index, (chunk_id, semantic_score, bm25_score, hybrid_score) in enumerate(
            ranked[:top_k], start=1
        )
    ]
    return hits, semantic_results[:top_k], bm25_results[:top_k]


def format_semantic_hit(hit: RetrievedChunk) -> str:
    return (
        f"{hit.rank}. `{hit.chunk_id}` ({hit.source_name}; {hit.course}; "
        f"distance {hit.distance:.4f}) - {excerpt(hit.text, max_chars=260)}"
    )


def format_bm25_hit(hit: Bm25Hit) -> str:
    chunk = hit.chunk
    return (
        f"{hit.rank}. `{chunk['id']}` ({chunk['source_name']}; {chunk['course']}; "
        f"BM25 {hit.score:.3f}) - {excerpt(chunk['text'], max_chars=260)}"
    )


def format_hybrid_hit(hit: HybridHit) -> str:
    chunk = hit.chunk
    return (
        f"{hit.rank}. `{chunk['id']}` ({chunk['source_name']}; {chunk['course']}; "
        f"hybrid {hit.hybrid_score:.3f}, semantic {hit.semantic_score:.3f}, "
        f"BM25 {hit.bm25_score:.3f}) - {excerpt(chunk['text'], max_chars=260)}"
    )


def print_hybrid_results(
    question: str,
    hits: List[HybridHit],
    semantic_hits: List[RetrievedChunk],
    bm25_hits: List[Bm25Hit],
) -> None:
    print(f"Question: {question}")
    print(f"Combination: {DEFAULT_SEMANTIC_WEIGHT:.2f} semantic + {DEFAULT_BM25_WEIGHT:.2f} BM25")
    print("\nHybrid results:")
    for hit in hits:
        print(format_hybrid_hit(hit))
    print("\nSemantic-only results:")
    for hit in semantic_hits:
        print(format_semantic_hit(hit))
    print("\nBM25-only results:")
    for hit in bm25_hits:
        print(format_bm25_hit(hit))


def write_comparison_report(path: Path = HYBRID_REPORT_PATH) -> None:
    lines = [
        "# Hybrid Search Comparison",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Semantic model: `{MODEL_NAME}`",
        f"Combination: {DEFAULT_SEMANTIC_WEIGHT:.2f} normalized semantic score + {DEFAULT_BM25_WEIGHT:.2f} normalized BM25 score",
        "",
    ]

    for label, question, judgment in COMPARISON_QUERIES:
        hits, semantic_hits, bm25_hits = hybrid_search(question, top_k=3)
        lines.extend([f"## {label}", "", f"Query: {question}", ""])

        lines.extend(["### Semantic-only top chunks", ""])
        lines.extend(format_semantic_hit(hit) for hit in semantic_hits)
        lines.append("")

        lines.extend(["### BM25-only top chunks", ""])
        lines.extend(format_bm25_hit(hit) for hit in bm25_hits)
        lines.append("")

        lines.extend(["### Hybrid top chunks", ""])
        lines.extend(format_hybrid_hit(hit) for hit in hits)
        lines.extend(["", f"**Which performed better:** {judgment}", ""])

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote hybrid comparison report to {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run hybrid BM25 + semantic search.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query_parser = subparsers.add_parser("query", help="Run one hybrid query.")
    query_parser.add_argument("question")
    query_parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    query_parser.add_argument("--semantic-weight", type=float, default=DEFAULT_SEMANTIC_WEIGHT)
    query_parser.add_argument("--bm25-weight", type=float, default=DEFAULT_BM25_WEIGHT)
    query_parser.add_argument(
        "--course-key",
        choices=[course_key for course_key, _aliases in COURSE_ALIASES],
        help="Filter to one known course key, such as cs7646 or cs6601.",
    )
    query_parser.add_argument("--source-type", choices=["omscentral", "reddit"])
    query_parser.add_argument("--no-course-filter", action="store_true")

    subparsers.add_parser("compare", help="Write the three-query comparison report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "compare":
        write_comparison_report()
        return

    hits, semantic_hits, bm25_hits = hybrid_search(
        args.question,
        top_k=args.top_k,
        semantic_weight=args.semantic_weight,
        bm25_weight=args.bm25_weight,
        course_key=args.course_key,
        source_type=args.source_type,
        use_course_filter=not args.no_course_filter,
    )
    print_hybrid_results(args.question, hits, semantic_hits, bm25_hits)


if __name__ == "__main__":
    main()
