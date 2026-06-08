# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

This project covers student-generated advice for choosing Georgia Tech OMSCS AI/ML-related courses. It is useful because official course pages describe topics and credit hours, but they do not explain the lived student experience: realistic weekly workload, grading friction, TA support, prerequisite gaps, whether a course is good early in the program, or whether it can be paired with another class. The best answers live across long OMSCentral review pages and r/OMSCS threads, so a RAG system can make that scattered advice easier to search with grounded citations.

---

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | OMSCentral - Machine Learning reviews | Course review page | https://www.omscentral.com/courses/machine-learning/reviews |
| 2 | OMSCentral - Artificial Intelligence reviews | Course review page | https://www.omscentral.com/courses/artificial-intelligence/reviews |
| 3 | OMSCentral - Deep Learning reviews | Course review page | https://www.omscentral.com/courses/deep-learning/reviews |
| 4 | OMSCentral - Reinforcement Learning and Decision Making reviews | Course review page | https://www.omscentral.com/courses/reinforcement-learning-and-decision-making/reviews |
| 5 | OMSCentral - Natural Language Processing reviews | Course review page | https://www.omscentral.com/courses/natural-language-processing/reviews |
| 6 | OMSCentral - Knowledge-Based AI reviews | Course review page | https://www.omscentral.com/courses/knowledge-based-ai/reviews |
| 7 | OMSCentral - Machine Learning for Trading reviews | Course review page | https://www.omscentral.com/courses/machine-learning-for-trading/reviews |
| 8 | OMSCentral - AI, Ethics, and Society reviews | Course review page | https://www.omscentral.com/courses/ai-ethics-and-society/reviews |
| 9 | r/OMSCS - Has anyone actually had a good experience with OMSCS's workload? | Reddit discussion thread | https://www.reddit.com/r/OMSCS/comments/1rk9zh9/has_anyone_actually_had_a_good_experience_with/ |
| 10 | r/OMSCS - Machine Learning for Trading First OMSCS Course? | Reddit discussion thread | https://www.reddit.com/r/OMSCS/comments/1mkkwfh/machine_learning_for_trading_first_omscs_course/ |

---

## Document Ingestion

The Milestone 3 pipeline lives in `ingest.py`. It fetches all 10 sources from the source table, saves the raw fetched HTML under `documents/raw/`, extracts only the course review or Reddit comment bodies, and writes cleaned text files under `documents/clean/`.

For OMSCentral, the script extracts substantive `article` review blocks that include rating, difficulty, and workload metadata. For Reddit, it fetches the old Reddit version of each thread because it exposes comment text in server-rendered HTML, then filters out subreddit boilerplate and very short/non-substantive bodies. The cleaning step removes HTML, navigation, repeated page chrome, base64-looking author hash artifacts, empty bodies, and common Reddit boilerplate while preserving course context, dates/terms, student opinions, ratings, difficulty, and workload estimates.

The pipeline limits each large OMSCentral source to the first 120 substantive reviews so one very large page does not dominate the corpus. Natural Language Processing and the two Reddit threads had fewer available substantive items, so all extracted items were kept.

---

## Chunking Strategy

**Chunk size:** Each OMSCentral review or Reddit comment is treated as one candidate chunk when it is at most 900 whitespace-estimated tokens. Longer reviews/comments are split into sentence-aware windows targeting about 760 tokens, with a hard maximum of 900 tokens after adding course/source context.

**Overlap:** Short review/comment chunks use no overlap because each one is already a complete opinion unit. Long split chunks use a 100-token overlap so important context near a boundary, such as the course name, assignment, grade, or recommendation, is not lost.

**Why these choices fit your documents:** The documents are mostly standalone student reviews and Reddit comments, not long textbook chapters. Keeping each review/comment intact preserves a student's background, workload estimate, complaint, and recommendation in one retrievable unit. For long reviews, sentence-aware splitting keeps chunks readable while preventing one very long review from crowding out other evidence in retrieval.

**Preprocessing:** Raw HTML is saved before cleaning. Cleaned documents remove HTML tags, navigation, repeated page chrome, short boilerplate, Reddit subreddit-rule text, and OMSCentral author hash artifacts. Every chunk also receives metadata for `source_name`, `source_type`, `url`, `fetch_url`, `course`, `chunk_index`, `unit_index`, and `piece_index`, and the chunk text itself begins with the course/topic and source name.

**Final chunk count:** 984 chunks across 10 sources.

### Sample Chunks

Full sample chunks are saved in `documents/sample_chunks.md`. Five representative generated chunks:

| Chunk ID | Source | Tokens | Excerpt |
|---|---|---:|---|
| `omscentral-machine-learning-reviews-0069` | OMSCentral - Machine Learning reviews | 311 | CS 7641 review describing the course as challenging, recommending starting projects immediately, and emphasizing that reports and plots consume the most time. |
| `omscentral-machine-learning-for-trading-reviews-0041` | OMSCentral - Machine Learning for Trading reviews | 775 | CS 7646 review saying ML4T is a strong first-course option, while discussing project briefs, lectures, readings, reports, and hidden details to watch for. |
| `omscentral-deep-learning-reviews-0074` | OMSCentral - Deep Learning reviews | 161 | CS 7643 review praising the professor and assignments while criticizing difficult quizzes, the final project fit, and weaker guest lecture material. |
| `omscentral-reinforcement-learning-and-decision-making-reviews-0046` | OMSCentral - Reinforcement Learning and Decision Making reviews | 776 | CS 7642 review praising TA engagement, warning about hard Assignment 1 and Project 3, and describing infrastructure friction around RLlib and cloud setup. |
| `omscentral-machine-learning-reviews-0004` | OMSCentral - Machine Learning reviews | 668 | CS 7641 review discussing report grading uncertainty, hidden-rubric frustration, overlap with AI, and a heavy time commitment despite liking the material. |

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` through `sentence-transformers`. The retrieval pipeline in `retrieval.py` embeds the 984 chunks from `documents/chunks.jsonl`, stores them in a persistent ChromaDB collection named `omscs_ai_ml_course_advice`, and retrieves the top 5 chunks for each question. The ChromaDB files are stored locally in `chroma_db/`, which is ignored by git because it can be regenerated with:

```bash
python3 retrieval.py index
```

I chose `all-MiniLM-L6-v2` because it is fast, local, free to run, and strong enough for a small English corpus of course reviews and Reddit comments. It also keeps the project simple: no paid embedding API is required, and the same laptop can rebuild the index from the saved chunks.

The retrieval layer also applies a lightweight course-aware metadata filter when a question explicitly names a course code or course title. For example, a question about `CS 6601` or `Artificial Intelligence` filters to Artificial Intelligence chunks, which prevents the word "AI" from pulling in Knowledge-Based AI results too aggressively.

**Retrieval check:** I ran the 5 evaluation questions from `planning.md` with top-k set to 5. The results are saved in `documents/retrieval_results.md`.

| # | Question focus | Inferred filter | Retrieval quality |
|---|----------------|-----------------|-------------------|
| 1 | CS 7641 Machine Learning while working full-time | `cs7641` | Relevant ML workload/reports/grading chunks |
| 2 | ML4T as a first OMSCS AI/ML course | `cs7646` | Relevant Reddit thread plus ML4T review chunks |
| 3 | Background before Artificial Intelligence | `cs6601` | Relevant AI background/prerequisite chunks |
| 4 | Knowledge-Based AI compared with engineering-heavy courses | `cs7637` | Relevant KBAI conceptual/writing/project chunks |
| 5 | Recent NLP frustrations/changes | `cs7650` | Relevant NLP lecture, Meta lecture, assignment, and course-change chunks |

**Production tradeoff reflection:** If this were deployed for real users and cost was not a constraint, I would compare this local MiniLM model against a larger hosted embedding model. The tradeoffs would be retrieval accuracy on messy student writing, longer context handling for very detailed reviews, latency, privacy, operational complexity, and cost. Multilingual support is not essential for this mostly English corpus, but it would matter if the guide expanded to international student forums or non-English program discussions.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

**How source attribution is surfaced in the response:**

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

**What the system returned:**

**Root cause (tied to a specific pipeline stage):**

**What you would change to fix it:**

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

**One way your implementation diverged from the spec, and why:**

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*

**Instance 2**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
