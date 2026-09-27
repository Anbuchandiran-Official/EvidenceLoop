"""Export actual observable Codex session records for this workspace, never summaries.

Private model reasoning, system/developer instructions, and environment snapshots are
excluded. Tool calls, tool outputs, user messages, and visible assistant text are preserved.
"""
import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", type=Path)
    args = parser.parse_args()
    workspace = Path.cwd().resolve()
    if args.session:
        paths = [args.session]
    else:
        paths = []
        for path in (Path.home() / ".codex" / "sessions").rglob("*.jsonl"):
            try:
                with path.open(encoding="utf-8") as file:
                    meta = json.loads(file.readline())
                cwd = meta.get("payload", {}).get("cwd")
                if cwd and Path(cwd).resolve() == workspace:
                    paths.append(path)
            except (OSError, ValueError):
                continue
    if not paths:
        raise SystemExit("No local session matching this workspace. Supply the real session file using --session.")
    logs = workspace / "logs"
    logs.mkdir(exist_ok=True)
    secrets = [v for k, v in os.environ.items() if any(s in k.upper() for s in ("API_KEY", "TOKEN", "SECRET")) and len(v) >= 8]
    manifest = []
    for path in paths:
        raw = path.read_bytes()
        lines, omitted, redactions = [], Counter(), 0
        for line in raw.decode("utf-8").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                omitted["incomplete_record"] += 1
                continue
            p = event.get("payload", {})
            keep = event.get("type") == "response_item" and (
                p.get("type") in ("function_call", "function_call_output", "custom_tool_call", "custom_tool_call_output", "web_search_call")
                or (p.get("type") == "message" and p.get("role") in ("user", "assistant") and p.get("channel") != "analysis"))
            if not keep:
                omitted[f'{event.get("type")}:{p.get("type", "metadata")}'] += 1
                continue
            for secret in secrets:
                if secret in line:
                    redactions += line.count(secret)
                    line = line.replace(secret, "[REDACTED_CREDENTIAL]")
            lines.append(line)
        exported = ("\n".join(lines) + "\n").encode("utf-8")
        target = logs / path.name
        target.write_bytes(exported)
        manifest.append({"source_file": path.name, "source_sha256_at_export": hashlib.sha256(raw).hexdigest(),
                         "source_bytes_at_export": len(raw), "export_file": target.name, "export_sha256": hashlib.sha256(exported).hexdigest(),
                         "preserved_records": len(lines), "omitted_record_counts": dict(omitted), "credential_redactions": redactions,
                         "scope": "Actual observable messages and tool records through export time. No summaries or reconstructed content. Active sessions need refresh after the final response."})
    (logs / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"sessions_exported": len(manifest), "records": sum(x["preserved_records"] for x in manifest), "credential_redactions": sum(x["credential_redactions"] for x in manifest)}))


if __name__ == "__main__":
    main()
