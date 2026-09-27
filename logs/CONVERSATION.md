# EvidenceLoop conversation and selection narrative

## Purpose of this file

This file gives a reviewer a concise, submission-safe account of how EvidenceLoop developed. The raw observable session export remains in the JSONL file in this folder. This narrative does not reproduce private model reasoning, system instructions, environment snapshots, API keys, or hidden chain-of-thought.

## Starting goal

The goal was to build Thuli Problem 3: an analyst that researches open questions from the live web and a second auditor that independently checks whether the analyst is telling the truth. The important requirement was not merely to produce attractive answers. It was to show a visible plan, real tool use, citations, independent verification, memory across questions, full traces, and honest uncertainty.

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
