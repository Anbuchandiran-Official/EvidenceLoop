# EvidenceLoop

EvidenceLoop is an analyst and auditor workspace for research answers that need a clear paper trail.

## What it does

- Turns a research question into an explicit evidence plan.
- Searches for relevant public sources and fetches the source pages.
- Breaks the answer into atomic, cited claims.
- Audits claims against independently fetched source text.
- Allows one evidence-based correction when a claim is challenged.
- Stores verified checking lessons for later research.
- Exports an observable run trace for review.

## Product areas

- **Research:** live, source-backed research runs.
- **Challenge Lab:** deterministic offline cases for demonstrating auditing and correction.
- **Feedback memory:** verified lessons and their later uses.
- **Evaluation:** training and held-out run reporting.

## Run locally

```powershell
.\scripts\setup.ps1
Copy-Item .env.example .env
.\scripts\run.ps1
```

Open `http://127.0.0.1:8000`.

Live research requires configured Gemini and Tavily credentials. The Challenge Lab fixture mode runs without provider credentials and is suitable for an offline demonstration.

## Validation

The project includes automated workflow, provider, verifier, and completion-review tests. The current test suite passes with `34 passed`.

## Security

Credentials belong only in `.env`. The repository ignores `.env`, local databases, logs, generated artifacts, and archives.
