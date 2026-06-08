# Chunking Strategy Comparison

Generated: 2026-06-08T04:43:42.492272+00:00
Embedding model for comparison: `all-MiniLM-L6-v2`
Strategy A: review/comment-boundary chunks from `documents/chunks.jsonl` (984 chunks)
Strategy B: fixed 450-token windows with 75-token overlap over cleaned documents (769 chunks)

## ML4T first-course advice

Query: Is Machine Learning for Trading a reasonable first OMSCS AI/ML course?

Course-aware comparison filter: `cs7646`

### Strategy A: review/comment-boundary chunks

1. `r-omscs-machine-learning-for-trading-first-omscs-course-0001` (r/OMSCS - Machine Learning for Trading First OMSCS Course?; CS 7646 first-course discussion; cosine 0.808) - Course/topic: CS 7646 first-course discussion. Source: r/OMSCS - Machine Learning for Trading First OMSCS Course?. Hi guys, I’m about to begin my first semester in the OMSCS program. I was thinking of taking Machine Learning for Trading (CS7646) as my first class as it hits th...
2. `omscentral-machine-learning-for-trading-reviews-0091` (OMSCentral - Machine Learning for Trading reviews; CS 7646 Machine Learning for Trading; cosine 0.768) - Course/topic: CS 7646 Machine Learning for Trading. Source: OMSCentral - Machine Learning for Trading reviews. April 30, 2023 fall 2022 This is one of the best courses in the OMS program and I would consider it a "must take" if you are in OMSCS or OMSA. The projects are pretty...
3. `omscentral-machine-learning-for-trading-reviews-0111` (OMSCentral - Machine Learning for Trading reviews; CS 7646 Machine Learning for Trading; cosine 0.764) - Course/topic: CS 7646 Machine Learning for Trading. Source: OMSCentral - Machine Learning for Trading reviews. October 24, 2022 fall 2022 This is my first OMSCS course with a non-CS background. Overall, this is a great class for an introduction to ML and a first class. However...

### Strategy B: fixed windows

1. `fixed-omscentral-machine-learning-for-trading-reviews-0081` (OMSCentral - Machine Learning for Trading reviews; CS 7646 Machine Learning for Trading; cosine 0.718) - Course/topic: CS 7646 Machine Learning for Trading. Source: OMSCentral - Machine Learning for Trading reviews. August 15, 2022 summer 2022 Machine Learning for Trading was a decent class. It was about the experience I expected, but there's room for improvement. For some backgr...
2. `fixed-omscentral-machine-learning-for-trading-reviews-0040` (OMSCentral - Machine Learning for Trading reviews; CS 7646 Machine Learning for Trading; cosine 0.711) - Course/topic: CS 7646 Machine Learning for Trading. Source: OMSCentral - Machine Learning for Trading reviews. of the course. People were angry about the tardiness since a lot of the code we used in Project 8 came from earlier projects where we didn't know if it was correct. I...
3. `fixed-r-omscs-machine-learning-for-trading-first-omscs-course-0001` (r/OMSCS - Machine Learning for Trading First OMSCS Course?; CS 7646 first-course discussion; cosine 0.708) - Course/topic: CS 7646 first-course discussion. Source: r/OMSCS - Machine Learning for Trading First OMSCS Course?. --- Item 1 --- Hi guys, I’m about to begin my first semester in the OMSCS program. I was thinking of taking Machine Learning for Trading (CS7646) as my first clas...

**Which performed better:** The review/comment-boundary strategy performed better because its top results were complete Reddit comments and complete OMSCentral reviews about ML4T as a first class. The fixed-window baseline found related text, but some windows started or ended mid-comment.

## AI prerequisite background

Query: What background do students recommend before taking Artificial Intelligence?

Course-aware comparison filter: `cs6601`

### Strategy A: review/comment-boundary chunks

1. `omscentral-artificial-intelligence-reviews-0073` (OMSCentral - Artificial Intelligence reviews; CS 6601 Artificial Intelligence; cosine 0.594) - Course/topic: CS 6601 Artificial Intelligence. Source: OMSCentral - Artificial Intelligence reviews. May 10, 2023 spring 2023 The course has challenging concepts with assignments and exam questions that test your understanding well. It was very satisfying to submit the assignm...
2. `omscentral-artificial-intelligence-reviews-0050` (OMSCentral - Artificial Intelligence reviews; CS 6601 Artificial Intelligence; cosine 0.591) - Course/topic: CS 6601 Artificial Intelligence. Source: OMSCentral - Artificial Intelligence reviews. June 19, 2024 spring 2024 Background: minor in CS in undergrad, working as a dev for a decade. Second OMS class, first AI-related class ever. The class material and assignments...
3. `omscentral-artificial-intelligence-reviews-0021` (OMSCentral - Artificial Intelligence reviews; CS 6601 Artificial Intelligence; cosine 0.581) - Course/topic: CS 6601 Artificial Intelligence. Source: OMSCentral - Artificial Intelligence reviews. August 11, 2025 spring 2025 Great course. If you're looking to get enough pre-req info for all other AI/ML courses at GT, this is where to start. It goes moderately in-depth on...

### Strategy B: fixed windows

1. `fixed-omscentral-artificial-intelligence-reviews-0005` (OMSCentral - Artificial Intelligence reviews; CS 6601 Artificial Intelligence; cosine 0.556) - Course/topic: CS 6601 Artificial Intelligence. Source: OMSCentral - Artificial Intelligence reviews. is dropped, and lowest challenge question dropped. The exams were tough but were take-home, so you have a lot of time to re-read the books and materials and apply them. If like...
2. `fixed-omscentral-artificial-intelligence-reviews-0069` (OMSCentral - Artificial Intelligence reviews; CS 6601 Artificial Intelligence; cosine 0.550) - Course/topic: CS 6601 Artificial Intelligence. Source: OMSCentral - Artificial Intelligence reviews. like a graduate level class from an underfunded state university. It’s a shame that the professor of this course didn’t take more responsibility in running this course. Rating:...
3. `fixed-omscentral-artificial-intelligence-reviews-0051` (OMSCentral - Artificial Intelligence reviews; CS 6601 Artificial Intelligence; cosine 0.549) - Course/topic: CS 6601 Artificial Intelligence. Source: OMSCentral - Artificial Intelligence reviews. AI but I do professionally and work with very experienced professionals in the fields. This is a very good class, but some things hold it back from being an excellent class. Th...

**Which performed better:** The boundary strategy performed better because each top result kept one student's background, prerequisite list, and workload caveat together. Fixed windows sometimes blended adjacent reviews or cut off the reason a prerequisite mattered.

## KBAI conceptual vs engineering-heavy

Query: How do students describe Knowledge-Based AI compared with more engineering-oriented AI/ML courses?

Course-aware comparison filter: `cs7637`

### Strategy A: review/comment-boundary chunks

1. `omscentral-knowledge-based-ai-reviews-0064` (OMSCentral - Knowledge-Based AI reviews; CS 7637 Knowledge-Based AI; cosine 0.652) - Course/topic: CS 7637 Knowledge-Based AI. Source: OMSCentral - Knowledge-Based AI reviews. May 17, 2023 spring 2023 Background: BS degree in civil engineering with ~2 years of development experience. KBAI was my second course in the program after HCI. As mentioned in this cour...
2. `omscentral-knowledge-based-ai-reviews-0074` (OMSCentral - Knowledge-Based AI reviews; CS 7637 Knowledge-Based AI; cosine 0.643) - Course/topic: CS 7637 Knowledge-Based AI. Source: OMSCentral - Knowledge-Based AI reviews. December 15, 2022 fall 2022 KBAI was one of the best courses I've ever taken, and I highly recommend it for anyone who REALLY wants to learn how to think differently about complex proble...
3. `omscentral-knowledge-based-ai-reviews-0012` (OMSCentral - Knowledge-Based AI reviews; CS 7637 Knowledge-Based AI; cosine 0.643) - Course/topic: CS 7637 Knowledge-Based AI. Source: OMSCentral - Knowledge-Based AI reviews. August 23, 2025 summer 2025 I enjoyed this course. It helped me frame my perspective about AI Agents. The foundations on how an AI Agent need to be built is interesting. Newly introduced...

### Strategy B: fixed windows

1. `fixed-omscentral-knowledge-based-ai-reviews-0055` (OMSCentral - Knowledge-Based AI reviews; CS 7637 Knowledge-Based AI; cosine 0.630) - Course/topic: CS 7637 Knowledge-Based AI. Source: OMSCentral - Knowledge-Based AI reviews. a rewarding experience. Rating: 3 / 5 Difficulty: 3 / 5 Workload: 20 hours / week --- Item 74 --- December 15, 2022 fall 2022 KBAI was one of the best courses I've ever taken, and I high...
2. `fixed-omscentral-knowledge-based-ai-reviews-0003` (OMSCentral - Knowledge-Based AI reviews; CS 7637 Knowledge-Based AI; cosine 0.608) - Course/topic: CS 7637 Knowledge-Based AI. Source: OMSCentral - Knowledge-Based AI reviews. to design their AI agents through writing, similar to the homework assignments. Then with pseudocode included, they can take their design docs and apply them into code to ensure that the...
3. `fixed-omscentral-knowledge-based-ai-reviews-0078` (OMSCentral - Knowledge-Based AI reviews; CS 7637 Knowledge-Based AI; cosine 0.608) - Course/topic: CS 7637 Knowledge-Based AI. Source: OMSCentral - Knowledge-Based AI reviews. and you can follow along with other student's approaches using slack or Piazza to help you with mini projects and the RPM project. If you make connections the course isn't difficult and...

**Which performed better:** The boundary strategy performed better because KBAI comparisons depend on a full opinion unit: writing, coding, cognitive science, philosophy, and project style are usually explained in one review. Fixed windows retrieved many of the same documents but were less self-contained.
