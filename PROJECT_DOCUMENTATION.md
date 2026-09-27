# EvidenceLoop — Project Documentation

## 1. Project overview

EvidenceLoop is a local research workspace built for Thuli’s Problem 3: Analyst and Auditor. It answers open web research questions through a visible, evidence-first workflow. An analyst plans the investigation and gathers sources. A separate auditor independently checks each claim against freshly fetched source text. The system keeps the plan, searches, fetched pages, claims, audits, corrections, memory events, timings, and errors in an exportable trace.

The central design principle is simple: a fluent answer is not enough. Every retained fact must have a source, an exact supporting passage, a defined metric, a date or period, and an audit result. When evidence is missing, the system says so.

## 2. Problem being solved

Ordinary language-model research can:

- answer before it has a search plan;
- confuse similar metrics, such as gross store openings and net store additions;
- cite a source that does not support the claim;
- mix publication dates with event dates;
- confuse units, currencies, periods, or entities;
- infer 24-carat gold from a 22-carat rate;
- hide uncertainty behind a confident paragraph;
- repeat expensive calls after a provider quota error; and
- learn answers instead of learning how to check them.

EvidenceLoop addresses these failures with explicit orchestration, structured claims, independent auditing, abstention, one-step correction, and scoped feedback memory.

## 3. Main workflow

1. The user enters a question and a frozen date range.
2. The analyst reads relevant feedback lessons and creates a structured plan.
3. Planned web searches run through Tavily.
4. Public source pages are fetched and sanitized by the fetcher.
5. The analyst drafts atomic claims using only successfully fetched sources.
6. Claims outside the requested date range are withheld.
7. Important claims can trigger a bounded corroboration search.
8. The auditor receives an isolated claim and freshly fetched citations.
9. It checks entity, amount, unit, date, period, metric, citation, quote, and calculations.
10. Each claim is marked `SUPPORTED`, `UNSUPPORTED`, or `CONTRADICTED`, or kept without a factual verdict when the source/model cannot be evaluated.
11. A challenged claim receives at most one evidence-based repair attempt.
12. A changed claim creates a feedback lesson only after a fresh supported audit with a verified quote.
13. The complete trace is stored in SQLite and can be exported as JSON.

## 4. Architecture

```text
Browser
  → FastAPI routes
  → Engine orchestration
  → Analyst plan
  → Parallel Tavily searches
  → Bounded source fetching
  → Atomic claim draft
  → Independent auditor and refetch
  → Quote/calculation gates
  → One repair and re-audit
  → Verified lesson memory
  → SQLite run and trace storage
```

Important files:

- `evidenceloop/models.py` — Pydantic contracts for requests, plans, sources, claims, calculations, audits, and repairs.
- `evidenceloop/providers.py` — Gemini, Tavily, HTML/PDF fetching, schema conversion, usage tracking, and safe provider errors.
- `evidenceloop/engine.py` — planning, searches, fetching, claim filtering, budgets, audits, repairs, and memory writes.
- `evidenceloop/auditor.py` — independent prompt, refetching, exact quote membership, calculation validation, and verdict gates.
- `evidenceloop/storage.py` — SQLite runs, lessons, and interrupted-run handling.
- `evidenceloop/challenge.py` — deterministic offline challenge cases.
- `evidenceloop/transfer.py` — challenge-to-memory transfer demonstration.
- `evidenceloop/evaluation.py` — eight frozen-date questions and the paired memory-on/memory-off experiment.
- `evidenceloop/static/` — frontend UI, tabs, run status, evidence display, and demo controls.

## 5. Solutions to the evaluation requirements

### Analyst agent

The analyst plans before searching, uses real Tavily search and page fetch tools, runs independent search/fetch operations concurrently, preserves source snapshots, and produces atomic cited claims. It reports evidence gaps instead of filling them with plausible guesses.

### Auditor agent

The auditor does not receive the analyst’s hidden reasoning, selected excerpts, memory, or expected labels. It independently fetches the cited page and checks whether the source directly supports the complete claim. Missing citations are flagged. Exact quote membership is verified programmatically after the model judgment.

### Metric and purity protection

The prompts explicitly distinguish gross openings, closures, net additions, and closing counts. For commodities, 22-carat and 24-carat are separate metrics. The system requires the exact purity in the source and never derives one rate from the other.

### Corrections and memory

Only one repair is allowed per challenged claim. Original claim, first verdict, revision, final verdict, and explanations remain visible. Lessons store the checking rule, scope, source evidence, and later uses. Held-out evaluation uses a frozen memory snapshot and disables writes to prevent leakage.

### Provider failure and quota handling

Gemini remains the normal model path. When `GEMINI_FALLBACK_MODE=fixture`, a recognized quota or temporary-unavailable error switches once to an explicit no-facts fixture response. It does not retry the failed request and does not pretend a factual answer was generated. The **Search sources only** action can search and fetch online sources without Gemini.

### Cost control

`RESEARCH_QUOTA_MODE=low` limits live research to two searches, four source pages, and three claims, and skips corroboration and repairs. Usage metadata records input, output, thinking tokens, search credits, timing, and estimated cost when verified price assumptions are configured.

## 6. Challenge and evaluation evidence

The deterministic offline challenge contains six injected errors, three correct controls, and one unavailable source case. The latest fixture run caught all six injected errors, falsely flagged zero correct controls, and correctly left one case unverifiable. This is a software regression result, not a claim about general LLM accuracy.

The evaluation suite contains eight increasing-difficulty questions. Q1–Q4 train memory. Q5–Q8 reuse earlier entities as held-out paired questions with memory disabled and enabled. Live results require available Gemini/Tavily access and independent human labels. Auditor judgments are not treated as ground truth.

## 7. Setup and operation

Requirements: Python 3.10+, network access for live research, a Gemini API key, and a Tavily API key.

```powershell
Set-Location 'C:\Users\Anbu\OneDrive\Desktop\thuli project'
.\scripts\setup.ps1
Copy-Item .env.example .env
notepad .env
.\scripts\run.ps1 -OpenBrowser
```

Set `GEMINI_API_KEY`, `TAVILY_API_KEY`, and optionally `GEMINI_MODEL`. The current model is `gemini-3.1-flash-lite`. Never commit `.env`.

Run checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evidenceloop.evaluation --mode fixture
.\.venv\Scripts\python.exe -m evidenceloop.evaluation --mode live --question-timeout 120
```

The live evaluation has 12 runs. Each question is bounded by the `--question-timeout` value and writes progress and partial results to `artifacts/`. After live runs, independently review claims and fill `artifacts/human-review.csv` using `scripts/review_evaluation.py`.

## 8. User-facing demo procedure

1. Start the server with `scripts/run.ps1 -OpenBrowser`.
2. Open **Research** and enter a question.
3. Keep the low quota mode for a free-tier demonstration.
4. Select the date range and click **Begin research**.
5. Inspect **Cited answer**, **Claim audit**, **Sources**, **Activity**, and **Memory**.
6. If Gemini is unavailable, use **Search sources only** to inspect fetched web evidence.
7. Use **Challenge Lab** to demonstrate a deterministic offline audit without API calls.
8. Export the run trace for review.

## 9. Limitations and honest status

The application is a local, single-user prototype. Static HTML, text, and PDF extraction can fail on JavaScript-only pages, paywalls, scanned PDFs, and large documents. A quote proves provenance, not complete semantic entailment. The analyst and auditor use separate contexts but may share a model family, so correlated model errors can survive. Keyword lesson retrieval can miss paraphrases. A bounded corroboration search cannot establish exhaustive web coverage.

The full live evaluation, human correctness labels, and rupee cost trend must be completed when provider quota is available and verified prices are supplied. The project records blocked or incomplete runs instead of presenting fixture outputs as live accuracy.

## 10. Submission contents

- `README.md` — setup, commands, design, solutions, assessment notes, and limitations.
- `ABOUT.md` — short project overview.
- `DECISIONS.md` — engineering decisions and trade-offs.
- `PROJECT_DOCUMENTATION.md` — this full project explanation.
- `tests/` — automated workflow, provider, verifier, and review tests.
- `scripts/` — setup, launch, provider check, evaluation, review, export, and packaging commands.
- `artifacts/` — generated local verification and evaluation outputs; regenerate after new runs.

## 11. Final summary

EvidenceLoop is designed to make research inspectable. Its strongest feature is the separation between generating a claim and checking that claim against independently fetched evidence. Its most important limitation is also explicit: provider access and human review are required before live accuracy or cost improvement can be claimed.
