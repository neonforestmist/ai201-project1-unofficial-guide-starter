"""Collect, clean, and chunk Project 1 source documents.

Run:
    python3 ingest.py

Outputs:
    documents/clean/*.txt
    documents/chunks.jsonl
    documents/manifest.json
    documents/sample_chunks.md
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("documents")
RAW_DIR = OUTPUT_DIR / "raw"
CLEAN_DIR = OUTPUT_DIR / "clean"
CHUNKS_PATH = OUTPUT_DIR / "chunks.jsonl"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
SAMPLE_PATH = OUTPUT_DIR / "sample_chunks.md"

MAX_ITEMS_PER_SOURCE = 120
MAX_TOKENS = 900
CONTEXT_TOKEN_BUFFER = 40
CONTENT_MAX_TOKENS = MAX_TOKENS - CONTEXT_TOKEN_BUFFER
TARGET_TOKENS = 760
OVERLAP_TOKENS = 100
MIN_WORDS = 35
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X) "
    "CodePath AI201 Project 1 student document collector"
)


@dataclass(frozen=True)
class Source:
    name: str
    source_type: str
    url: str
    course: str

    @property
    def fetch_url(self) -> str:
        if self.source_type == "reddit":
            parsed = urlparse(self.url)
            return self.url.replace(f"{parsed.scheme}://{parsed.netloc}", "https://old.reddit.com")
        return self.url

    @property
    def slug(self) -> str:
        text = re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
        return text[:80]


SOURCES = [
    Source(
        "OMSCentral - Machine Learning reviews",
        "omscentral",
        "https://www.omscentral.com/courses/machine-learning/reviews",
        "CS 7641 Machine Learning",
    ),
    Source(
        "OMSCentral - Artificial Intelligence reviews",
        "omscentral",
        "https://www.omscentral.com/courses/artificial-intelligence/reviews",
        "CS 6601 Artificial Intelligence",
    ),
    Source(
        "OMSCentral - Deep Learning reviews",
        "omscentral",
        "https://www.omscentral.com/courses/deep-learning/reviews",
        "CS 7643 Deep Learning",
    ),
    Source(
        "OMSCentral - Reinforcement Learning and Decision Making reviews",
        "omscentral",
        "https://www.omscentral.com/courses/reinforcement-learning-and-decision-making/reviews",
        "CS 7642 Reinforcement Learning and Decision Making",
    ),
    Source(
        "OMSCentral - Natural Language Processing reviews",
        "omscentral",
        "https://www.omscentral.com/courses/natural-language-processing/reviews",
        "CS 7650 Natural Language Processing",
    ),
    Source(
        "OMSCentral - Knowledge-Based AI reviews",
        "omscentral",
        "https://www.omscentral.com/courses/knowledge-based-ai/reviews",
        "CS 7637 Knowledge-Based AI",
    ),
    Source(
        "OMSCentral - Machine Learning for Trading reviews",
        "omscentral",
        "https://www.omscentral.com/courses/machine-learning-for-trading/reviews",
        "CS 7646 Machine Learning for Trading",
    ),
    Source(
        "OMSCentral - AI, Ethics, and Society reviews",
        "omscentral",
        "https://www.omscentral.com/courses/ai-ethics-and-society/reviews",
        "CS 6603 AI, Ethics, and Society",
    ),
    Source(
        "r/OMSCS - Has anyone actually had a good experience with OMSCS's workload?",
        "reddit",
        "https://www.reddit.com/r/OMSCS/comments/1rk9zh9/has_anyone_actually_had_a_good_experience_with/",
        "OMSCS workload discussion",
    ),
    Source(
        "r/OMSCS - Machine Learning for Trading First OMSCS Course?",
        "reddit",
        "https://www.reddit.com/r/OMSCS/comments/1mkkwfh/machine_learning_for_trading_first_omscs_course/",
        "CS 7646 first-course discussion",
    ),
]


def fetch_html(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=45)
    response.raise_for_status()
    return response.text


def write_raw_document(source: Source, html: str) -> Path:
    path = RAW_DIR / f"{source.slug}.html"
    path.write_text(html, encoding="utf-8")
    return path


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def count_tokens(text: str) -> int:
    return len(text.split())


def strip_omscentral_hashes(text: str) -> str:
    text = re.sub(r"\b[A-Za-z0-9+/]{16,}={0,2}\b", "", text)
    return re.sub(r"^[+=/\s]+", "", text).strip()


def looks_substantive(text: str) -> bool:
    if count_tokens(text) < MIN_WORDS:
        return False
    boilerplate_markers = [
        "Updated Fall 2024 Please read the RULES",
        "permalink embed save report",
        "Want to add to the discussion",
        "This thread is archived",
    ]
    return not any(marker in text for marker in boilerplate_markers)


def extract_omscentral_units(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    units: List[str] = []
    seen = set()

    for article in soup.select("article"):
        text = normalize_text(article.get_text(" ", strip=True))
        text = strip_omscentral_hashes(text)
        if "Rating:" not in text or "Difficulty:" not in text or "Workload:" not in text:
            continue
        if not looks_substantive(text):
            continue
        if text in seen:
            continue
        seen.add(text)
        units.append(text)
        if len(units) >= MAX_ITEMS_PER_SOURCE:
            break

    return units


def extract_reddit_units(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    units: List[str] = []
    seen = set()

    for body in soup.select("div.usertext-body div.md"):
        text = normalize_text(body.get_text(" ", strip=True))
        if not looks_substantive(text):
            continue
        if text in seen:
            continue
        seen.add(text)
        units.append(text)
        if len(units) >= MAX_ITEMS_PER_SOURCE:
            break

    return units


def split_words(words: List[str], target_tokens: int = TARGET_TOKENS) -> List[str]:
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + target_tokens, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(end - OVERLAP_TOKENS, start + 1)
    return chunks


def split_long_text(text: str) -> List[str]:
    words = text.split()
    if len(words) <= CONTENT_MAX_TOKENS:
        return [text]

    chunks = []
    current_sentences: List[str] = []
    current_tokens = 0

    for sentence in SENTENCE_SPLIT_PATTERN.split(text):
        sentence = sentence.strip()
        if not sentence:
            continue
        sentence_tokens = count_tokens(sentence)

        if sentence_tokens > CONTENT_MAX_TOKENS:
            if current_sentences:
                chunks.append(" ".join(current_sentences))
                current_sentences = []
                current_tokens = 0
            chunks.extend(split_words(sentence.split()))
            continue

        should_flush = current_sentences and current_tokens + sentence_tokens > TARGET_TOKENS
        if should_flush:
            chunks.append(" ".join(current_sentences))
            overlap_words = chunks[-1].split()[-OVERLAP_TOKENS:]
            current_sentences = [" ".join(overlap_words)] if overlap_words else []
            current_tokens = len(overlap_words)

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks


def add_chunk_context(source: Source, text: str) -> str:
    return f"Course/topic: {source.course}. Source: {source.name}. {text}"


def chunk_units(source: Source, units: Iterable[str]) -> List[dict]:
    chunks = []
    chunk_index = 0

    for unit_index, unit in enumerate(units, start=1):
        for piece_index, text in enumerate(split_long_text(unit), start=1):
            chunk_index += 1
            contextual_text = add_chunk_context(source, text)
            chunks.append(
                {
                    "id": f"{source.slug}-{chunk_index:04d}",
                    "source_name": source.name,
                    "source_type": source.source_type,
                    "course": source.course,
                    "url": source.url,
                    "fetch_url": source.fetch_url,
                    "chunk_index": chunk_index,
                    "unit_index": unit_index,
                    "piece_index": piece_index,
                    "token_count": count_tokens(contextual_text),
                    "text": contextual_text,
                }
            )

    return chunks


def write_clean_document(source: Source, units: List[str]) -> Path:
    path = CLEAN_DIR / f"{source.slug}.txt"
    lines = [
        f"Source: {source.name}",
        f"Course/topic: {source.course}",
        f"Type: {source.source_type}",
        f"URL: {source.url}",
        f"Fetched items: {len(units)}",
        "",
    ]

    for index, unit in enumerate(units, start=1):
        lines.append(f"--- Item {index} ---")
        lines.append(unit)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_chunks(chunks: List[dict]) -> None:
    with CHUNKS_PATH.open("w", encoding="utf-8") as outfile:
        for chunk in chunks:
            outfile.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def sample_chunks(chunks: List[dict], sample_size: int = 5) -> List[dict]:
    if len(chunks) <= sample_size:
        return chunks
    random.seed(201)
    return random.sample(chunks, sample_size)


def write_sample_file(samples: List[dict]) -> None:
    lines = ["# Sample Chunks", ""]
    for sample in samples:
        lines.extend(
            [
                f"## {sample['id']}",
                "",
                f"- Source: {sample['source_name']}",
                f"- Course/topic: {sample['course']}",
                f"- Tokens: {sample['token_count']}",
                "",
                sample["text"],
                "",
            ]
        )
    SAMPLE_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_manifest(source_summaries: List[dict], total_chunks: int) -> None:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(source_summaries),
        "total_chunks": total_chunks,
        "chunking": {
            "strategy": "Review/comment boundary first; long items split by sentence-aware token windows.",
            "max_tokens": MAX_TOKENS,
            "content_max_tokens_before_context": CONTENT_MAX_TOKENS,
            "target_tokens_for_long_splits": TARGET_TOKENS,
            "overlap_tokens_for_long_splits": OVERLAP_TOKENS,
            "max_items_per_source": MAX_ITEMS_PER_SOURCE,
        },
        "sources": source_summaries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def collect_source(source: Source) -> tuple[List[str], List[dict], dict]:
    html = fetch_html(source.fetch_url)
    raw_path = write_raw_document(source, html)
    if source.source_type == "omscentral":
        units = extract_omscentral_units(html)
    elif source.source_type == "reddit":
        units = extract_reddit_units(html)
    else:
        raise ValueError(f"Unknown source type: {source.source_type}")

    if not units:
        raise RuntimeError(f"No substantive text extracted from {source.name}")

    clean_path = write_clean_document(source, units)
    chunks = chunk_units(source, units)
    summary = {
        "name": source.name,
        "course": source.course,
        "type": source.source_type,
        "url": source.url,
        "fetch_url": source.fetch_url,
        "raw_path": str(raw_path),
        "clean_path": str(clean_path),
        "items": len(units),
        "chunks": len(chunks),
    }
    return units, chunks, summary


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks: List[dict] = []
    source_summaries: List[dict] = []

    for source in SOURCES:
        print(f"Collecting {source.name}...")
        _, chunks, summary = collect_source(source)
        all_chunks.extend(chunks)
        source_summaries.append(summary)
        print(f"  items={summary['items']} chunks={summary['chunks']}")

    write_chunks(all_chunks)
    write_manifest(source_summaries, len(all_chunks))
    samples = sample_chunks(all_chunks)
    write_sample_file(samples)

    print("")
    print(f"Wrote {len(all_chunks)} chunks to {CHUNKS_PATH}")
    print(f"Wrote manifest to {MANIFEST_PATH}")
    print(f"Wrote sample chunks to {SAMPLE_PATH}")
    print("")
    print("Sample chunks:")
    for sample in samples:
        preview = sample["text"][:500].replace("\n", " ")
        print(f"- {sample['id']} | {sample['source_name']} | {sample['token_count']} tokens")
        print(f"  {preview}...")


if __name__ == "__main__":
    main()
