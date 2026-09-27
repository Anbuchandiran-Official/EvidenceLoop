# Real coding-session transcripts

## EvidenceLoop at a glance

EvidenceLoop is a local research application for Thuli Problem 3: **Analyst and Auditor**. It answers open web questions with a visible evidence trail instead of trusting one model-generated paragraph.

The **analyst** plans the research, searches the live web, fetches pages, and writes atomic cited claims. The **auditor** independently refetches cited pages and decides whether each claim is supported, unsupported, or contradicted. The UI exposes plans, searches, source snapshots, claims, audits, corrections, feedback memory, activity, timing, token usage, and failures.

## Complete workflow

```text
Question and date range → analyst plan → parallel Tavily searches
→ bounded HTML/PDF fetching → atomic claims with source IDs
→ independent auditor refetch → quote/date/metric/calculation gates
→ one repair and re-audit → verified checking lesson
→ SQLite run and JSON trace
```

The project protects against unsupported confidence, irrelevant citations, date and unit confusion, gross-versus-net metric errors, and 22-carat versus 24-carat gold mistakes. Missing evidence becomes an evidence gap rather than a guess.

## Architecture and design principles

FastAPI routes call the engine. The engine coordinates Pydantic contracts, Gemini, Tavily, the bounded page fetcher, the auditor, repairs, and SQLite storage. Async tasks parallelize independent searches and fetches. JSON export makes every state transition reviewable.

The design principles are evidence before fluency, separate generation and verification contexts, abstention over unsupported certainty, memory of checking rules rather than cached answers, and explicit budgets for tools, claims, repairs, and runtime. The full rationale is in [`DECISIONS.md`](DECISIONS.md), and the full project guide is [`../PROJECT_DOCUMENTATION.md`](../PROJECT_DOCUMENTATION.md).

## Main application areas

- **Research:** live source-backed questions with date controls.
- **Challenge Lab:** offline injected errors, correct controls, and unavailable evidence; no API key required.
- **Feedback memory:** verified checking lessons and later uses.
- **Evaluation:** eight increasing-difficulty questions with training and held-out memory comparisons.
- **Run tabs:** answer, plan, audit, corrections, sources, activity, and memory.

## Run it

From the project root:

```powershell
Set-Location 'C:\Users\Anbu\OneDrive\Desktop\thuli project'
.\.venv\Scripts\python.exe -m uvicorn evidenceloop.app:app --host 127.0.0.1 --port 8000
```

Or use `.\scripts\run.ps1 -OpenBrowser`. Open `http://127.0.0.1:8000`.

For a clean setup, run `.\scripts\setup.ps1`, copy `.env.example` to `.env`, and add `GEMINI_API_KEY` and `TAVILY_API_KEY`. The current model is `gemini-3.1-flash-lite`. Never commit `.env`.

## Demo, tests, and evaluation

Use `RESEARCH_QUOTA_MODE=low` for free-tier demos. `GEMINI_FALLBACK_MODE=fixture` handles quota errors once with an explicit no-facts response. **Search sources only** uses Tavily without Gemini. Challenge Lab fixture mode is fully offline.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evidenceloop.evaluation --mode fixture
.\.venv\Scripts\python.exe -m evidenceloop.evaluation --mode live --question-timeout 120
```

The offline challenge currently catches 6/6 injected errors, falsely flags 0/3 correct controls, and leaves one unavailable case unverifiable. Live accuracy, human labels, and rupee costs require provider access and independent review.

## Submission and limitations

The root README gives clean-checkout instructions; `PROJECT_DOCUMENTATION.md` is the full write-up; root and log `DECISIONS.md` files contain design rationale; `CONVERSATION.md` explains the development and selection narrative; and the JSONL transcript plus `manifest.json` provide observable session evidence.

Known limits include JavaScript-only or paywalled pages, scanned PDFs, changing web content, correlated errors from a shared model family, keyword memory misses, and finite corroboration coverage. These limits are recorded rather than hidden.

## Why these logs are included

The assignment evaluates the final code, the write-up, and how the system was built. These files preserve the observable coding-session record used to develop EvidenceLoop. They let a reviewer compare the implementation with the decisions and trade-offs described in `README.md`, `PROJECT_DOCUMENTATION.md`, and `logs/DECISIONS.md`.

This repository therefore includes runnable clean-checkout instructions, a full project write-up, decision rationale, and observable session evidence. The logs are evidence of the development process, not a replacement for tests or independent human review.

The JSONL exports here contain real local Codex user/assistant messages, tool calls, and tool results. They are not reconstructed summaries. `manifest.json` records the original-file hash at export time, exported hash, retained record count, and omissions.

Private model reasoning, system/developer instructions, environment snapshots, duplicate event notifications, and usage bookkeeping are excluded. Any configured credential occurring in visible records is redacted and counted. This is a complete **observable-session** export through the recorded export point, not a claim to contain internal reasoning or the complete raw internal rollout.

The active session can only include records already written when the export runs. Refresh after the final assistant response and before submission, from this project directory:

```powershell
.\.venv\Scripts\python.exe scripts\export_session.py
```

The script discovers actual files under `%USERPROFILE%\.codex\sessions` by matching their workspace metadata. It does not depend on an undocumented interface export button. If discovery fails, supply the real file with `--session 'C:\path\to\rollout.jsonl'`. Add exports from any other coding tools/sessions used for this project; do not replace them with a written recap.
