# Real coding-session transcripts

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
