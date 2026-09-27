# EvidenceLoop design decisions

## Design principles

### Evidence before fluency

The application does not render a free-form answer paragraph as truth. It retains atomic claims with an entity, metric, value, unit, period, citation IDs, and audit state. Missing evidence becomes an evidence gap rather than a plausible completion.

### Generation and verification are separate

The analyst and auditor use separate contexts. The auditor receives the claim and freshly fetched source documents, not the analyst's hidden reasoning, selected excerpts, memory, or expected labels. This reduces self-approval and makes verification inspectable.

### Abstention is valid

`SUPPORTED`, `UNSUPPORTED`, and `CONTRADICTED` mean different things. A fetch or model failure is recorded as an evaluation failure, not silently converted into a factual verdict.

### Learn checking rules, not cached answers

Feedback memory stores verified correction lessons with scope, evidence, origin, and later uses. It does not cache answers. Facts are fetched again, and held-out evaluation uses a frozen snapshot to prevent leakage.

### Bound cost and failure

Searches, sources, claims, concurrency, repairs, and runtime are bounded. A claim gets one repair opportunity. Low-quota mode reduces free-tier budgets. Provider fallback does not retry a quota error.

## Architecture

```text
Browser UI → FastAPI routes → Engine
  → lesson retrieval → analyst plan → parallel Tavily search
  → bounded HTML/PDF fetches → atomic claim draft
  → independent auditor refetch → quote/calculation gates
  → one repair and re-audit → verified lesson write
  → SQLite runs, sources, audits, repairs, memory, metrics
  → JSON trace export
```

Explicit orchestration was chosen instead of a large agent framework. The workflow has a small number of state transitions, and Pydantic models make them visible and testable. Async tasks parallelize independent searches and fetches without requiring a distributed queue for a local single-user take-home project.

## Decisions that matter to review

1. **The auditor refetches citations.** Analyst excerpts are not trusted; the auditor opens the cited URL again and checks the source text.
2. **Quote membership is programmatic.** The returned passage must occur in the fetched document after normalization; arithmetic is checked separately.
3. **Metric semantics are explicit.** Net store additions do not prove gross openings. 22-carat and 24-carat gold are separate metrics. Dates, units, and entities must match.
4. **Repairs are limited.** One revision is allowed, and the original, verdict, revision, and final result remain visible.
5. **Fixture and live modes are separate.** Offline challenge scores are deterministic regression results, never live model accuracy.
6. **Quota fallback is explicit.** A Gemini quota failure can produce a labelled no-facts fixture response; it never fabricates a factual answer.
7. **Evaluation is paired and frozen.** Four training questions create memory; four held-out questions run with memory off and on from the same frozen snapshot. Writes are disabled in held-out arms and order alternates.

## What was tried, measured, and rejected

- Purely model-generated answers were rejected because a citation can exist without supporting the exact claim.
- Treating the auditor as ground truth was rejected. Fixed challenge labels and independent human review are required.
- Forcing memory-off errors was rejected because it would manufacture improvement; the fixture transfer records equal correctness when both arms are already right.
- Retrying Gemini after HTTP 429 was rejected because it can worsen quota exhaustion.
- Reusing analyst page text inside the auditor was rejected to preserve independent retrieval.

## Known weaknesses

- A shared model family can produce correlated analyst and auditor mistakes.
- Quote membership proves provenance, not complete semantic entailment.
- JavaScript-only sites, paywalls, scanned PDFs, and changing pages can fail fetching.
- Keyword lesson retrieval can miss paraphrases.
- Bounded corroboration cannot establish exhaustive web coverage.
- Live accuracy, human labels, and rupee cost trends require provider access and verified prices.

These weaknesses are recorded explicitly so a reviewer can see where the system can fail before discovering it independently.
