# EvidenceLoop

A small research system for Thuli's **Problem 3: Analyst and Auditor**. It plans before searching, fetches actual source pages, answers in atomic cited claims, independently re-fetches citations, makes one repair attempt per flagged claim, and carries verified checking lessons into later plans.

The distinctive experiment is **Challenge → Correct → Transfer**. The interface separates real research from synthetic fixtures. It never presents fixture outcomes as model accuracy.

## Run on this Windows machine

Python 3.10.11 was detected at the path below. The `.venv` is already installed in this workspace.

```powershell
Set-Location 'C:\Users\Anbu\OneDrive\Desktop\thuli project'
.\.venv\Scripts\python.exe -m uvicorn evidenceloop.app:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Health: http://127.0.0.1:8000/health. API reference: http://127.0.0.1:8000/docs. Use one server process; run state is persisted but jobs are intentionally local to one process.

For a one-command Windows launch after setup:

```powershell
.\scripts\run.ps1 -OpenBrowser
```

This starts the server in the background, checks `/health`, records its PID and logs under `artifacts/`, and opens the browser. Stop it with `Stop-Process -Id (Get-Content artifacts\server.pid)`.

If port 8000 is already serving EvidenceLoop, use that running instance. Stop a foreground server with Ctrl+C. The build-session background server PID is recorded in `artifacts/server.pid`.

## Clean setup

Requires Python 3.10+ and network access to install packages. No Node build, database service, or browser API key is required.

```powershell
# This is the working interpreter detected on the author's machine.
& 'C:\Users\Anbu\AppData\Local\Programs\Python\Python310\python.exe' -m venv .venv
# On another Windows machine with Python installed, use: py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.lock.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe -m uvicorn evidenceloop.app:app --host 127.0.0.1 --port 8000
```

`--no-cache-dir` avoids a sandbox-specific Windows pip cache permission stall observed during setup. `requirements.lock.txt` contains the exact dependency versions actually tested; `pyproject.toml` defines supported ranges.

Set `GEMINI_API_KEY` and `TAVILY_API_KEY` in the local environment or `.env`. `GOOGLE_API_KEY` is an alternative model credential. Keep `GEMINI_MODEL` configurable to a model your account can access; the adapter defaults to `gemini-3.1-flash-lite`. Restart the app after changing `.env`. **Never paste keys into chat or commit `.env`.** Credentials are sent only in provider request headers. The browser receives readiness flags and missing-variable names, never values.

`GEMINI_SCHEMA_STYLE=legacy` uses `responseMimeType`/`responseJsonSchema`; `format` uses the newer `responseFormat` schema. Both paths are covered with mocked transport tests. Model availability and actual API compatibility still require a successful provider run.

When `GEMINI_FALLBACK_MODE=fixture` (the default in `.env.example`), a Gemini HTTP 429, quota, or temporary-unavailable response switches the current run once to the existing explicit fixture-style fallback. It records a `fallback` activity event, returns the normal plan/draft schema, retains no factual claims, and does not retry Gemini. Set `GEMINI_FALLBACK_MODE=off` for strict production behavior that surfaces provider failures instead.

## What to try

1. Open **Challenge lab**, select **Offline fixture rules**, and run the challenge.
2. Inspect **Claim audit**, including the exact net-versus-gross case. It is **UNSUPPORTED**, not contradicted.
3. Open **Corrections** to compare the original, first verdict, revision, source passage, and final verdict.
4. Select **Test lesson transfer**. A different synthetic company and period is checked with memory off and on. Both fixture arms are already correct: retrieval works, but no quality improvement is claimed.
5. Inspect **Feedback memory** and export a trace. Fixture lessons never enter live research.
6. Once both providers work, ask a question in **Research** and inspect its plan, cited answer, source snapshots, activities, repairs, lessons, and metrics.

## Tests and evaluation commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evidenceloop.evaluation --mode fixture
.\.venv\Scripts\python.exe scripts\provider_check.py
# Real model judgments on synthetic documents; needs Gemini but not Tavily:
.\.venv\Scripts\python.exe -m evidenceloop.evaluation --mode challenge-model
# Real web research: 4 training runs + 4 held-out questions x 2 arms = 12 runs:
.\.venv\Scripts\python.exe -m evidenceloop.evaluation --mode live
# With the server running; uses installed Google Chrome, headlessly:
.\.venv\Scripts\python.exe scripts\ui_smoke.py
# Refresh actual coding-session transcripts after the final response:
.\.venv\Scripts\python.exe scripts\export_session.py
# Create a clean submission archive (excludes .env, .venv and local SQLite data):
.\scripts\package.ps1
```

If Chrome is unavailable, install it or change the smoke script to a Playwright-managed Chromium after running `python -m playwright install chromium`.

The eight frozen-date questions are in `evidenceloop/evaluation.py`. Q5–Q8 reuse earlier entities. Each live experiment uses a fresh SQLite database, trains on Q1–Q4, freezes the resulting lessons, and disables writes in both held-out arms. Arm order alternates; model, temperature, source budgets, and search budgets remain equal. Both arms perform fresh research. Live-web drift remains a confound; one run per arm cannot establish statistical significance.

Correctness is **not** the auditor grading itself. Challenge labels are fixed separately and never appear in auditor inputs. Live correctness starts as `null`; independently review the held-out answers:

```powershell
.\.venv\Scripts\python.exe scripts\review_evaluation.py
# Fill artifacts/human-review.csv using the sources, independent of the auditor.
.\.venv\Scripts\python.exe scripts\review_evaluation.py --import-labels artifacts\human-review.csv
```

The blinded sheet includes question-level completeness/abstention and claim-level accuracy. Use `1`, `0`, or `unknown`, identify the reviewer, and include evidence. The importer validates completeness and produces a descriptive paired comparison. Auditor-flagged repeated mistake types remain labelled as model judgments, not human truth.

## Measured results and blockers

See `artifacts/RESULTS.md` and the actual JSON/test/browser artifacts. The offline challenge has **10 cases: 6 injected errors, 3 correct controls, 1 unavailable page**. The fixture verifier caught **6/6**, wrongly flagged **0/3**, and returned **1/10 unverifiable**. This is a deterministic software regression result.

The real Gemini preflight returned **HTTP 503**. `TAVILY_API_KEY` was missing. Consequently, no live research quality, live memory improvement, measured provider token usage, or rupee savings are claimed. The live evaluation artifact records the blocker rather than invented results.

Rupee cost stays unknown unless `INPUT_INR_PER_MILLION`, `OUTPUT_INR_PER_MILLION`, and `SEARCH_INR_PER_CREDIT` are supplied from verified billing assumptions. Output cost includes provider-reported thinking tokens, without requesting or logging thought content. Model tokens and Tavily credits come from API responses. Errors/incomplete usage prevent a complete cost estimate. Estimates are not invoices.

## Architecture and bounds

```text
Browser → FastAPI → Engine → plan → parallel Tavily searches → bounded page fetches
                            ↓
                    atomic claim draft → reserved corroboration search
                            ↓
                  isolated auditor → independently fetched citations
                            ↓
                 quote and calculation gates → one repair → re-audit
                            ↓
                     verified scoped lesson → later plan
All observable events and source snapshots → SQLite → JSON trace export
```

- `models.py`: Pydantic contracts for plans, claims, calculations, sources and verdicts.
- `providers.py`: configurable Gemini/Tavily adapters, bounded HTML/PDF fetches and safe failure messages.
- `auditor.py`: separate context, source refetching, quote membership and arithmetic gates.
- `engine.py`: budgets, orchestration, one repair opportunity, evidence-backed lesson creation.
- `challenge.py`, `transfer.py`, `evaluation.py`: distinct synthetic challenge and paired evaluation paths.
- `storage.py`: SQLite runs and lessons, interrupted-run recovery.

Default research budget: 4 searches (3 planned, 1 reserved for corroboration), 8 analyst pages, 8 claims, 4 concurrent fetches, 2 concurrent model calls, 600-second whole-run timeout. Auditor refetches are additional and explicitly counted. Important claims without multi-domain corroboration are labelled as gaps. Domain diversity is only a heuristic, not proof of editorial independence. Missing and incompatible data limit rankings to an observed sample.

The UI renders claims only from structured claim records; there is no separate uncited answer paragraph. Fetched sources are untrusted model data. Plans and concise verdict explanations are observable outputs; hidden chain-of-thought is neither requested nor stored.

## Limits and submission

This is a local, single-user take-home application. There is no authentication, queue service, or durable job resume. Run it on loopback, not as an Internet-facing service. The fetcher rejects private addresses and validates redirects, but DNS checks are not socket-pinned against rebinding. It handles static HTML, text and text PDFs; not JavaScript rendering, paywalls, scanned-PDF OCR, or exhaustive web coverage. Documents are bounded at 5 MB, 60 PDF pages and 45,000 extracted characters, with truncation recorded.

The analyst and auditor use independent contexts, but share a configurable model family. Correlated semantic errors can survive; exact quote membership proves text provenance, not entailment. Gross/net classification and exhaustive rankings still depend on model judgment. A single reserved corroboration query cannot exhaustively cross-check every claim. Memory retrieval uses scoped keywords; lessons only arise from corrected and re-supported claims, so some runs will learn nothing.

The assignment PDF was found at `C:\Users\Anbu\Downloads\dyla_take_home_problems.md.pdf` and read before completing implementation; a text extraction is retained under `artifacts/assignment-extracted.txt`. The workspace initially had no application or `AGENTS.md`. `DECISIONS.md` explains the five key decisions and next steps. Real observable coding-session exports are in `/logs`; refresh them before submission as documented there. This project has not been published, emailed, or submitted to Thuli.

Provider documentation checked during implementation: [Gemini structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output?hl=en), [Gemini API structured output overview](https://ai.google.dev/gemini-api/docs/structured-output), and [Tavily Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search).

For demos or limited free-tier accounts, set RESEARCH_QUOTA_MODE=low. This caps live research to two searches, four source pages, three claims, skips corroboration, and skips repair calls. Set RESEARCH_QUOTA_MODE=standard for the full workflow.
