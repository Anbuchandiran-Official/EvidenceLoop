# EvidenceLoop conversation and selection narrative

## Purpose of this file

This file gives a reviewer a concise, submission-safe account of how EvidenceLoop developed. The raw observable session export remains in the JSONL file in this folder. This narrative does not reproduce private model reasoning, system instructions, environment snapshots, API keys, or hidden chain-of-thought.

## Starting goal

The goal was to build Thuli Problem 3: an analyst that researches open questions from the live web and a second auditor that independently checks whether the analyst is telling the truth. The important requirement was not merely to produce attractive answers. It was to show a visible plan, real tool use, citations, independent verification, memory across questions, full traces, and honest uncertainty.

## Conversation summary from the beginning

The following is a factual summary of the work, written for a reviewer. It is intentionally a summary rather than an invented transcript; the raw observable messages and tool records remain in the JSONL export.

### Reconstructed project dialogue

> **You:** Build my Thuli Problem 3 project and make it efficient, complete, and runnable.
>
> **Engineering partner:** I built EvidenceLoop as a local Analyst and Auditor workspace. The analyst plans before searching, uses Tavily and page fetching, writes cited atomic claims, and the auditor independently refetches and verifies them.
>
> **You:** Make the UI professional enough for a hackathon and explain how I can run it.
>
> **Engineering partner:** I organized the interface into Research, Challenge Lab, Feedback Memory, and Evaluation. I documented Windows setup, `.env` configuration, server launch, health checks, tests, and packaging.
>
> **You:** Gemini is failing with quota and validation errors. I do not want the demo to break.
>
> **Engineering partner:** I kept the Gemini integration intact, stopped repeated retries, and added an explicit fixture fallback for quota or temporary provider failures. It preserves the response schema, records the fallback, retains no fake factual claims, and leaves fetched sources visible.
>
> **You:** I want online search even when the model is unavailable.
>
> **Engineering partner:** I added **Search sources only**, which uses Tavily and the page fetcher without Gemini. It reports the fetched evidence without pretending that a model-generated answer exists.
>
> **You:** The gold search confused 22-carat and 24-carat values.
>
> **Engineering partner:** I tightened both analyst and auditor rules so purity is part of the metric. A 22-carat source row cannot support a 24-carat claim, and one purity is never inferred from the other.
>
> **You:** The live evaluation appears to hang.
>
> **Engineering partner:** I added progress output, partial report saving, and a configurable per-question timeout. The command now ends with an explicit incomplete report instead of waiting indefinitely.
>
> **You:** Add the architecture, decisions, logs, and everything a reviewer needs.
>
> **Engineering partner:** I added the root README, full project documentation, design decisions, log README, conversation narrative, raw observable session export, manifest, tests, artifacts, and GitHub commits. The documentation states both what works and what remains provider-dependent.

### Thirty-point professional conversation

The following is a reconstructed presentation narrative based on the work in this repository. It is not a verbatim transcript and should not be treated as raw session evidence.

1. **You:** I need an analyst and auditor system for open web research.
   **Engineering partner:** We will separate planning, evidence collection, claim drafting, and independent verification.
2. **You:** The answer must be traceable.
   **Engineering partner:** Every claim will carry structured source IDs, periods, units, and audit state.
3. **You:** It should work from a clean checkout.
   **Engineering partner:** Setup, environment configuration, launch, health checks, tests, and packaging will be documented.
4. **You:** I want a usable hackathon interface.
   **Engineering partner:** The UI will expose Research, Challenge Lab, Feedback Memory, Evaluation, and evidence tabs.
5. **You:** How will the analyst work?
   **Engineering partner:** It will create a plan before calling search tools and will run independent searches concurrently.
6. **You:** How will sources be handled?
   **Engineering partner:** Pages will be fetched, bounded, sanitized, stored, and shown with retrieval status.
7. **You:** How will claims be represented?
   **Engineering partner:** As atomic records containing entity, metric, value, unit, period, citation IDs, and optional calculations.
8. **You:** How do we stop unsupported claims?
   **Engineering partner:** Claims without usable source evidence are withheld and reported as evidence gaps.
9. **You:** How does the auditor stay independent?
   **Engineering partner:** It receives a separate claim-and-source context and refetches the cited pages itself.
10. **You:** What does the auditor check?
    **Engineering partner:** Entity, amount, unit, date, period, metric, citation, exact quote, and arithmetic inputs.
11. **You:** What if the source disagrees?
    **Engineering partner:** The claim is marked unsupported or contradicted, and the original evidence remains visible.
12. **You:** Can the system correct an error?
    **Engineering partner:** It allows one minimal evidence-supported repair followed by a fresh audit.
13. **You:** Why only one repair?
    **Engineering partner:** To prevent hidden loops, uncontrolled cost, and corrections that gradually drift away from evidence.
14. **You:** I want the system to learn across questions.
    **Engineering partner:** It stores verified checking lessons, not previous answers, and applies scoped lessons to later plans.
15. **You:** How do we prevent memory leakage in evaluation?
    **Engineering partner:** Held-out questions use a frozen memory snapshot and disable writes.
16. **You:** I need offline testing for the demo.
    **Engineering partner:** Challenge Lab uses deterministic fixture documents and labels, so it runs without provider keys.
17. **You:** How do we know the auditor is not approving everything?
    **Engineering partner:** The challenge includes injected errors, correct controls, and an unavailable citation case.
18. **You:** What did the offline test show?
    **Engineering partner:** It caught all six injected errors, falsely flagged none of the three controls, and left one unavailable case unverifiable.
19. **You:** Gemini quota errors are breaking the demo.
    **Engineering partner:** Quota and temporary failures are detected without repeated retries.
20. **You:** What happens during fallback?
    **Engineering partner:** The app records an explicit no-facts fixture response and keeps the fetched sources available.
21. **You:** Can I still search online without Gemini?
    **Engineering partner:** Yes. Search sources only uses Tavily and the fetcher without claiming a model-generated answer.
22. **You:** The model confused 22-carat and 24-carat gold.
    **Engineering partner:** Purity is now part of the metric, and one purity can never be inferred from the other.
23. **You:** Dates were also confusing.
    **Engineering partner:** Claims with explicit years outside the selected frozen range are withheld.
24. **You:** The live evaluation seemed stuck.
    **Engineering partner:** Each question now has a configurable wall-clock timeout, progress output, and partial report saving.
25. **You:** I need cost visibility.
    **Engineering partner:** Provider usage, search credits, timing, and estimated cost are recorded when verified price assumptions exist.
26. **You:** What if prices are unknown?
    **Engineering partner:** The system displays unknown cost instead of inventing billing values.
27. **You:** What files explain the project?
    **Engineering partner:** The root README, project documentation, decisions, conversation narrative, tests, artifacts, and session manifest explain different review layers.
28. **You:** What makes this more than a normal chatbot?
    **Engineering partner:** It exposes plans, evidence, independent audits, corrections, memory, failures, and limits rather than only displaying prose.
29. **You:** What is the main weakness?
    **Engineering partner:** A shared model family can still make correlated semantic errors, so human review remains necessary for live correctness.
30. **You:** Why should a reviewer select this project?
    **Engineering partner:** Because it demonstrates the complete engineering loop: build, measure, challenge, identify weaknesses, change the design, preserve evidence, and report what remains unproven.

### 1. Build and complete the take-home project

The initial request was to build the Analyst and Auditor project efficiently inside the supplied workspace. The implementation was created as a local FastAPI application with a static frontend, Pydantic contracts, SQLite persistence, Gemini/Tavily adapters, an analyst workflow, an independent auditor, Challenge Lab, feedback memory, evaluation, and trace export.

### 2. Make it runnable and explain the procedure

The setup and run procedure was documented for Windows. `.env.example`, `scripts/setup.ps1`, `scripts/run.ps1`, health checks, API documentation, tests, and packaging commands were added or verified. The server was repeatedly started locally and the health endpoint returned `status: ok`.

### 3. Improve the UI for a hackathon demonstration

The research workspace was refined into a professional evidence dashboard with navigation for Research, Challenge Lab, Feedback Memory, and Evaluation. Run tabs show the cited answer, plan, claim audit, corrections, sources, activity, and memory. A splash animation, responsive layout, source-only action, status badges, and clearer failure states were added to make the workflow understandable during a live demo.

### 4. Configure providers and control free-tier usage

The project was configured with environment variables for Gemini and Tavily. The model was moved to the valid structured-output identifier `gemini-3.1-flash-lite`. Low-quota mode limits searches, pages, and claims, while provider keys remain private in `.env`.

### 5. Handle quota and validation failures safely

Live testing exposed Gemini HTTP 429 quota responses and structured-output validation failures. The implementation was changed so the app does not repeatedly retry these failures. In fixture fallback mode, it records a clear provider fallback, retains no invented factual claims, and keeps fetched sources available. A separate online source-search mode allows source inspection without Gemini.

### 6. Fix the gold-rate evidence problem

A live gold-rate result showed that 22-carat and 24-carat values could be confused. The prompts and verification rules were tightened so purity is part of the metric and must be stated by the source. The auditor cannot transfer a value from one purity to the other. This was treated as a correctness issue rather than hidden in the UI.

### 7. Make evaluation finish predictably

The live evaluation initially appeared to hang while provider and network calls waited. A configurable per-question timeout was added, with progress printed for each training and memory arm and partial results saved to `artifacts/evaluation.json`. The command now ends with an explicit incomplete report when provider access prevents completion.

### 8. Document and publish the work

The root README, `PROJECT_DOCUMENTATION.md`, `ABOUT.md`, root `DECISIONS.md`, this log README, this conversation narrative, and the log-folder decisions file were expanded for clean-checkout review. The repository was pushed to GitHub with the implementation, tests, documentation, and observable session export. API keys and local `.env` files remain excluded.

## What the applicant demonstrated

The work shows more than accepting a generated implementation. The project repeatedly challenged visible failures: quota exhaustion, invalid model output, wrong date defaults, a hanging evaluation, and purity confusion. The chosen responses favored traceability and abstention over silently making the demo look successful. That is the central reason the project is a stronger submission: it makes the analyst's answer auditable and makes its own weaknesses inspectable.

## What was built

EvidenceLoop became a local FastAPI, Pydantic, SQLite, and static-frontend application with these stages:

1. A question and date range enter the research workspace.
2. The analyst creates a structured plan before searching.
3. Tavily searches run in parallel and public pages are fetched under size and concurrency limits.
4. The analyst returns atomic claims with source IDs, metrics, units, periods, and calculations.
5. The auditor receives an isolated claim and independently refetched sources.
6. Programmatic gates check citation membership, exact quotes, calculations, dates, entities, units, and metrics.
7. A flagged claim receives at most one repair and re-audit.
8. Only corrected claims that pass verification create scoped feedback lessons.
9. Every step is stored in SQLite and exposed through the UI and JSON trace export.

## Problems discovered and how they were handled

### Unsupported confidence

The system was designed to abstain when a page cannot be fetched or a claim cannot be supported. `UNSUPPORTED` is kept distinct from `CONTRADICTED`, and provider/fetch failures do not become invented factual verdicts.

### Metric confusion

The analyst and auditor prompts explicitly distinguish gross openings, closures, net additions, and closing counts. A source saying that store count increased by 50 cannot establish 50 gross openings.

### Purity confusion

The gold-rate issue exposed a concrete failure mode: 22-carat and 24-carat values can be swapped or inferred. The implementation treats each purity as a separate metric and requires the source to state the exact purity.

### Self-approval by the model

The auditor does not reuse the analyst's selected passage or hidden reasoning. It fetches the cited page again and must return a source passage that occurs in the fetched document. This still does not prove perfect semantic understanding, so human labels remain required for live evaluation.

### Provider quota and validation failures

Gemini quota, temporary-unavailable, and invalid structured responses were observed during development. Retrying would increase quota pressure. The final behavior switches once to an explicit no-facts fixture fallback, records the reason, and keeps sources visible. A separate **Search sources only** path allows online source inspection without Gemini.

### Long live evaluations

The live evaluator originally appeared to hang while waiting through repeated provider/network timeouts. It was changed to enforce a configurable 120-second maximum per question, print progress for every training and memory arm, and save partial results as it goes.

## Decisions that show engineering judgment

- A small explicit orchestrator was preferred over a large agent framework because the state transitions are few, visible, and easy to test.
- A single repair opportunity was chosen to prevent hidden infinite correction loops and uncontrolled costs.
- Memory stores reusable verification rules rather than previous answers, so later questions still require fresh evidence.
- Fixture challenge scores are clearly labelled as deterministic software tests, never as live model accuracy.
- The memory-on and memory-off evaluation uses a frozen snapshot and disables held-out writes to prevent leakage.
- Provider fallback preserves demo usability without pretending that Gemini produced a factual answer.

## Evidence of work

- Automated regression suite: 36 tests pass.
- Offline challenge: 6/6 injected errors caught, 0/3 correct controls falsely flagged, and 1 unavailable case left unverifiable.
- Offline transfer demonstrates scoped lesson retrieval.
- UI smoke artifacts cover research, challenge, transfer, mobile layout, and no-JavaScript-error checks.
- Run traces preserve plans, searches, fetches, model calls, audits, corrections, memory, timing, and failure events.
- The repository includes `README.md`, `PROJECT_DOCUMENTATION.md`, `ABOUT.md`, root `DECISIONS.md`, this log narrative, raw session exports, and a manifest with hashes and omissions.

## What can make this submission stand out

The strongest differentiator is that the project treats failure as product data. It does not hide quota errors, inaccessible pages, unsupported claims, or the absence of human labels. It shows the reviewer what the system tried, what evidence came back, where a claim changed, and where the approach remains weak.

The project also goes beyond a basic analyst/auditor demo in several practical ways:

- exact quote provenance is checked in code after the auditor responds;
- source fetch failures are separated from factual verdicts;
- feedback memory is frozen for held-out comparison;
- low-quota and source-only modes make the demo usable on free tiers;
- the evaluation command has a per-question wall-clock ceiling;
- session logs, design decisions, tests, and limitations are included for review.

## What is not claimed

The full 12-run live experiment, independent human correctness labels, and rupee cost trend require provider access and verified price assumptions. The repository records incomplete provider runs honestly. Fixture scores are not substitutes for live accuracy, and a passed quote gate is not proof that a model fully understood the claim.

## How to review the work

1. Start with the root `README.md` for clean setup and commands.
2. Read `PROJECT_DOCUMENTATION.md` for the complete system explanation.
3. Read `DECISIONS.md` for architecture and trade-offs.
4. Open `logs/manifest.json` and the JSONL transcript to inspect observable development records.
5. Run the offline challenge and test suite without API keys.
6. With provider keys available, run the bounded live evaluation and independently label its answers.
