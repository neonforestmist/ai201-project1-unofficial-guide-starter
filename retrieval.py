"""Build and query the Project 1 vector store.

Run:
    python3 retrieval.py index
    python3 retrieval.py query "Is ML4T a good first OMSCS course?"
    python3 retrieval.py query "Is ML4T a good first OMSCS course?" --source-type reddit
    python3 retrieval.py evaluate

The ChromaDB store is written to chroma_db/, which is intentionally ignored by
git because it can be regenerated from documents/chunks.jsonl.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import chromadb
from sentence_transformers import SentenceTransformer


CHUNKS_PATH = Path("documents/chunks.jsonl")
VECTOR_STORE_DIR = Path("chroma_db")
RETRIEVAL_RESULTS_PATH = Path("documents/retrieval_results.md")

COLLECTION_NAME = "omscs_ai_ml_course_advice"
MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 64
DEFAULT_TOP_K = 5

EVALUATION_QUESTIONS = [
    "What do student reviews say about taking CS 7641 Machine Learning while working full-time?",
    "Is Machine Learning for Trading a reasonable first OMSCS AI/ML course, and what should a new student watch out for?",
    "What background do students recommend before taking Artificial Intelligence?",
    "How do students describe Knowledge-Based AI compared with more engineering-oriented AI/ML courses?",
    "What changed or frustrated students in recent Natural Language Processing reviews?",
]

COURSE_ALIASES = [
    (
        "cs7646",
        [
            "cs 7646",
            "cs7646",
            "machine learning for trading",
            "ml4t",
        ],
    ),
    (
        "cs7641",
        [
            "cs 7641",
            "cs7641",
            "machine learning",
        ],
    ),
    (
        "cs6601",
        [
            "cs 6601",
            "cs6601",
            "artificial intelligence",
        ],
    ),
    (
        "cs7643",
        [
            "cs 7643",
            "cs7643",
            "deep learning",
        ],
    ),
    (
        "cs7642",
        [
            "cs 7642",
            "cs7642",
            "reinforcement learning",
        ],
    ),
    (
        "cs7650",
        [
            "cs 7650",
            "cs7650",
            "natural language processing",
            "nlp",
        ],
    ),
    (
        "cs7637",
        [
            "cs 7637",
            "cs7637",
            "knowledge-based ai",
            "knowledge based ai",
            "kbai",
        ],
    ),
    (
        "cs6603",
        [
            "cs 6603",
            "cs6603",
            "ai, ethics, and society",
            "ai ethics and society",
        ],
    ),
]


@dataclass(frozen=True)
class RetrievedChunk:
    rank: int
    chunk_id: str
    distance: float
    source_name: str
    source_type: str
    course: str
    course_key: str
    url: str
    text: str


def load_chunks(path: Path = CHUNKS_PATH) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run `python3 ingest.py` before building the index."
        )

    chunks = []
    with path.open(encoding="utf-8") as infile:
        for line in infile:
            if line.strip():
                chunks.append(json.loads(line))

    if not chunks:
        raise RuntimeError(f"No chunks found in {path}")
    return chunks


def get_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))


def get_collection(client: chromadb.PersistentClient):
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def batched(items: List[dict], batch_size: int) -> Iterable[List[dict]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def chunk_metadata(chunk: dict) -> dict:
    return {
        "course_key": course_key_for_text(f"{chunk['course']} {chunk['source_name']}"),
        "source_name": chunk["source_name"],
        "source_type": chunk["source_type"],
        "course": chunk["course"],
        "url": chunk["url"],
        "fetch_url": chunk["fetch_url"],
        "chunk_index": chunk["chunk_index"],
        "unit_index": chunk["unit_index"],
        "piece_index": chunk["piece_index"],
        "token_count": chunk["token_count"],
    }


def course_key_for_text(text: str) -> str:
    normalized = text.lower().replace("-", " ")
    for course_key, aliases in COURSE_ALIASES:
        if any(alias in normalized for alias in aliases):
            return course_key
    return "general"


def infer_course_key(question: str) -> Optional[str]:
    normalized = question.lower().replace("-", " ")
    for course_key, aliases in COURSE_ALIASES:
        if any(alias in normalized for alias in aliases):
            return course_key
    return None


def build_where_filter(
    course_key: Optional[str] = None, source_type: Optional[str] = None
) -> Optional[dict]:
    filters = []
    if course_key:
        filters.append({"course_key": course_key})
    if source_type:
        filters.append({"source_type": source_type})

    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


def rebuild_index(chunks_path: Path = CHUNKS_PATH) -> int:
    chunks = load_chunks(chunks_path)
    model = load_model()
    client = get_client()

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = get_collection(client)

    for batch_number, batch in enumerate(batched(chunks, BATCH_SIZE), start=1):
        texts = [chunk["text"] for chunk in batch]
        embeddings = model.encode(
            texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).tolist()
        collection.add(
            ids=[chunk["id"] for chunk in batch],
            documents=texts,
            metadatas=[chunk_metadata(chunk) for chunk in batch],
            embeddings=embeddings,
        )
        print(f"Indexed batch {batch_number}: {len(batch)} chunks")

    return collection.count()


def retrieve(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    model: Optional[SentenceTransformer] = None,
    collection=None,
    use_course_filter: bool = True,
    course_key: Optional[str] = None,
    source_type: Optional[str] = None,
) -> List[RetrievedChunk]:
    model = model or load_model()
    if collection is None:
        client = get_client()
        collection = get_collection(client)

    if collection.count() == 0:
        raise RuntimeError("Vector store is empty. Run `python3 retrieval.py index` first.")

    query_embedding = model.encode(
        [question],
        show_progress_bar=False,
        normalize_embeddings=True,
    ).tolist()[0]

    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }

    active_course_key = course_key
    if not active_course_key and use_course_filter:
        active_course_key = infer_course_key(question)

    where_filter = build_where_filter(
        course_key=active_course_key,
        source_type=source_type,
    )
    if where_filter:
        query_kwargs["where"] = where_filter

    results = collection.query(**query_kwargs)

    retrieved = []
    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for rank, (chunk_id, text, metadata, distance) in enumerate(
        zip(ids, documents, metadatas, distances), start=1
    ):
        retrieved.append(
            RetrievedChunk(
                rank=rank,
                chunk_id=chunk_id,
                distance=distance,
                source_name=metadata["source_name"],
                source_type=metadata["source_type"],
                course=metadata["course"],
                course_key=metadata["course_key"],
                url=metadata["url"],
                text=text,
            )
        )
    return retrieved


def excerpt(text: str, max_chars: int = 550) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def print_results(
    question: str,
    results: List[RetrievedChunk],
    use_course_filter: bool = True,
    course_key: Optional[str] = None,
    source_type: Optional[str] = None,
) -> None:
    print(f"Question: {question}")
    active_course_key = course_key or (infer_course_key(question) if use_course_filter else None)
    if active_course_key:
        print(f"Course filter: {active_course_key}")
    if source_type:
        print(f"Source type filter: {source_type}")
    for result in results:
        print(
            f"\n{result.rank}. {result.chunk_id} | distance={result.distance:.4f}"
            f"\n   {result.source_name} | {result.source_type} | {result.course}"
            f"\n   {result.url}"
            f"\n   {excerpt(result.text)}"
        )


def write_evaluation_report(
    questions: List[str],
    all_results: List[List[RetrievedChunk]],
    top_k: int,
    use_course_filter: bool,
    path: Path = RETRIEVAL_RESULTS_PATH,
) -> None:
    lines = [
        "# Milestone 4 Retrieval Results",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Embedding model: `{MODEL_NAME}`",
        f"Vector store: `{VECTOR_STORE_DIR}/`",
        f"Collection: `{COLLECTION_NAME}`",
        f"Top-k: {top_k}",
        f"Course-aware filtering: {use_course_filter}",
        "",
    ]

    for index, (question, results) in enumerate(zip(questions, all_results), start=1):
        lines.extend([f"## Question {index}", "", question, ""])
        course_key = infer_course_key(question) if use_course_filter else None
        if course_key:
            lines.extend([f"Inferred course filter: `{course_key}`", ""])
        for result in results:
            lines.extend(
                [
                    f"### {result.rank}. `{result.chunk_id}`",
                    "",
                    f"- Distance: {result.distance:.4f}",
                    f"- Source: {result.source_name}",
                    f"- Course/topic: {result.course}",
                    f"- URL: {result.url}",
                    "",
                    excerpt(result.text, max_chars=750),
                    "",
                ]
            )

    path.write_text("\n".join(lines), encoding="utf-8")


def run_evaluation(
    top_k: int = DEFAULT_TOP_K, use_course_filter: bool = True
) -> None:
    model = load_model()
    collection = get_collection(get_client())
    all_results = []
    for question in EVALUATION_QUESTIONS:
        results = retrieve(
            question,
            top_k=top_k,
            model=model,
            collection=collection,
            use_course_filter=use_course_filter,
        )
        all_results.append(results)
        print_results(question, results, use_course_filter=use_course_filter)
        print("\n" + "-" * 80 + "\n")

    write_evaluation_report(
        EVALUATION_QUESTIONS,
        all_results,
        top_k=top_k,
        use_course_filter=use_course_filter,
    )
    print(f"Wrote retrieval report to {RETRIEVAL_RESULTS_PATH}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index and query the Project 1 chunks.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("index", help="Rebuild the ChromaDB vector store.")

    query_parser = subparsers.add_parser("query", help="Retrieve chunks for one question.")
    query_parser.add_argument("question", help="Question to retrieve evidence for.")
    query_parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    query_parser.add_argument(
        "--course-key",
        choices=[course_key for course_key, _aliases in COURSE_ALIASES],
        help="Filter to one known course key, such as cs7646 or cs6601.",
    )
    query_parser.add_argument(
        "--source-type",
        choices=["omscentral", "reddit"],
        help="Filter to one source type so the effect of metadata filtering is visible.",
    )
    query_parser.add_argument(
        "--no-course-filter",
        action="store_true",
        help="Disable metadata filtering when the question names a course.",
    )

    eval_parser = subparsers.add_parser(
        "evaluate", help="Run the five planning.md evaluation questions."
    )
    eval_parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    eval_parser.add_argument(
        "--no-course-filter",
        action="store_true",
        help="Disable metadata filtering when a question names a course.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "index":
        total = rebuild_index()
        print(f"Indexed {total} chunks into {VECTOR_STORE_DIR}/{COLLECTION_NAME}")
    elif args.command == "query":
        use_course_filter = not args.no_course_filter
        print_results(
            args.question,
            retrieve(
                args.question,
                top_k=args.top_k,
                use_course_filter=use_course_filter,
                course_key=args.course_key,
                source_type=args.source_type,
            ),
            use_course_filter=use_course_filter,
            course_key=args.course_key,
            source_type=args.source_type,
        )
    elif args.command == "evaluate":
        run_evaluation(top_k=args.top_k, use_course_filter=not args.no_course_filter)


if __name__ == "__main__":
    main()
