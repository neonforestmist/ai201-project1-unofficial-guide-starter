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

The Milestone 5 query interface lives in `ask.py`. It retrieves the top 5 chunks with `retrieval.py`, formats each chunk as a numbered source label such as `[S1]`, sends those labeled excerpts to Groq's `llama-3.3-70b-versatile`, and prints the generated answer plus the retrieved source list.

```bash
python3 retrieval.py index
python3 ask.py "Is ML4T a good first OMSCS course?"
python3 ask.py evaluate
```

Use `--dry-run` to inspect the retrieved context and prompt without making a Groq API call:

```bash
python3 ask.py --dry-run "Is ML4T a good first OMSCS course?"
```

**System prompt grounding instruction:** The system prompt includes these grounding rules:

```text
- Answer only from the retrieved source excerpts in the user message.
- Do not use outside knowledge, guesses, or unstated assumptions.
- If the excerpts do not contain enough evidence, say that the retrieved documents do not contain enough information.
- Summarize patterns across sources instead of treating one student's review as universal truth.
- Cite every factual claim about courses with source labels like [S1] or [S2].
- End with a short "Sources" section listing the source labels you used.
```

**How source attribution is surfaced in the response:** `ask.py` passes each retrieved chunk to the model with its label, chunk ID, distance, source name, course/topic, URL, and excerpt. The generated answer is required to cite those labels inline. After the answer, the CLI prints the full retrieved source list so a reader can map `[S1]` back to the original source URL and chunk ID.

**Live generation status:** I ran `python3 ask.py evaluate` with a Groq API key stored in the ignored local `.env` file. Full generated answers and retrieved sources are saved in `documents/generation_results.md`.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What do student reviews say about taking CS 7641 Machine Learning while working full-time? | The answer should say ML is high workload and stressful, especially because of assignments and grading uncertainty, while noting reviews vary. | The system said ML can be challenging while working full-time, cited 14-20 hour/week retrieved workloads, mentioned heavy reports/quizzes, mixed rewarding vs. frustrating experiences, and recommended planning time/start early. | Relevant | Partially accurate |
| 2 | Is Machine Learning for Trading a reasonable first OMSCS AI/ML course, and what should a new student watch out for? | The answer should say ML4T can be a gentler first AI/ML course, but students warn about reports, project cadence, hidden tests/rubrics, and delayed feedback. | The system said ML4T can be reasonable as a first course, cited the Reddit first-course thread and OMSCentral reviews, and warned that workload varies by project and exams can be difficult. | Relevant | Partially accurate |
| 3 | What background do students recommend before taking Artificial Intelligence? | The answer should mention Python/numpy, probability/statistics, linear algebra, algorithms/search, starting early, and time-consuming exams/projects. | The system emphasized Bayesian probability, linear algebra, programming, data structures, algorithms, discrete math, multivariable calculus, and data science. It did not clearly mention starting early or the time burden. | Relevant | Partially accurate |
| 4 | How do students describe Knowledge-Based AI compared with more engineering-oriented AI/ML courses? | The answer should describe KBAI as more conceptual, writing-heavy, cognitive-science/human-reasoning oriented, with projects and participation rather than pure engineering. | The system described KBAI as focused on AI agents that think like humans, overlapping with cognitive science/philosophy, and balancing coding projects, writing, psychology, and philosophy. | Relevant | Accurate |
| 5 | What changed or frustrated students in recent Natural Language Processing reviews? | The answer should mention proctored/closed-book assessments, mixed reactions to Meta lectures, TA/course-policy changes, and praise for the main professor's lectures. | The system cited poor homework instructions, room scans for weekly quizzes, weak Meta lectures, difficult tests, and still noted praise for Dr. Reidl's lectures and course material. | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** What background do students recommend before taking Artificial Intelligence?

**What the system returned:** The answer was useful but incomplete. It correctly mentioned probability, Bayesian probability, linear algebra, programming, data structures, algorithms, discrete math, multivariable calculus, and data science. It did not mention some expected practical advice from the evaluation plan, especially starting early and the time-consuming exam/project workload.

**Root cause (tied to a specific pipeline stage):** Retrieval was relevant, but the top chunks leaned toward prerequisite/background descriptions rather than study-strategy details. The generation prompt asked for a concise answer, so the model compressed the evidence into prerequisite topics and dropped some workflow advice that appeared in the retrieved context, such as starting early and exams taking significant time.

**What you would change to fix it:** I would add a second retrieval pass for practical workload/study-advice terms when a question asks about "background" or "before taking" a course. I would also make the generation prompt explicitly ask for both prerequisite knowledge and preparation/workload advice when the retrieved context contains both.

---

## Spec Reflection

**One way the spec helped you during implementation:** `planning.md` made the implementation much more direct because the document choices, chunk metadata, embedding model, top-k value, and evaluation questions were already decided before coding. That meant each milestone could be built as a small piece of the planned architecture instead of changing direction mid-project. The five evaluation questions were especially helpful because they revealed concrete retrieval behavior, like the need for course-aware filtering when the phrase "Artificial Intelligence" could otherwise overlap with KBAI.

**One way your implementation diverged from the spec, and why:** The chunking plan originally expected paragraph-aware splitting for long reviews, but the OMSCentral HTML often collapsed review bodies into dense text without reliable paragraph boundaries. I changed the fallback splitter to sentence-aware token windows so long reviews still stayed readable and below the token cap. I also added course-aware metadata filtering during retrieval, which was not in the original plan, because the first retrieval tests showed that similar course names could otherwise pull adjacent but wrong courses.

---

## AI Usage

**Instance 1**

- *What I gave the AI:* The Domain, Document Sources, and Chunking Strategy sections from `planning.md`.
- *What it produced:* Python code for fetching OMSCentral and Reddit sources, extracting review/comment text, saving raw and cleaned documents, and writing chunk metadata to `documents/chunks.jsonl`.
- *What I changed or overrode:* I changed the long-review splitting from paragraph-aware to sentence-aware because the scraped HTML did not preserve paragraph boundaries reliably. I also added course/source text directly into each chunk so retrieval would have that context inside the embedding text.

**Instance 2**

- *What I gave the AI:* The Embedding Model, Retrieval Approach, Architecture, and Evaluation Plan sections from `planning.md`.
- *What it produced:* ChromaDB indexing and retrieval code using `all-MiniLM-L6-v2`, plus a Groq-based answer generation script with source citations.
- *What I changed or overrode:* I added course-aware metadata filtering so questions about `CS 6601 Artificial Intelligence` would not drift into `Knowledge-Based AI` chunks. I also added `--dry-run` and a stricter grounding prompt so the retrieved context and source labels could be inspected before live API calls.
