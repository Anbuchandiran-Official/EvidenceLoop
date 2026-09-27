"""One small real model request, with safe diagnostics and no credentials in output."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidenceloop.auditor import AUDITOR
from evidenceloop.challenge import cases
from evidenceloop.config import Settings
from evidenceloop.models import Judgment, now
from evidenceloop.providers import Gemini, ProviderError


async def main():
    settings = Settings()
    events = []
    report = {"at": now(), "model": settings.gemini_model, "missing_configuration": settings.missing(), "events": events}
    row = cases()[5]
    try:
        result = await Gemini(settings, lambda k, d: events.append({"kind": k, **d})).generate(AUDITOR,
            {"stage": "provider_preflight", "claim": row["claim"].model_dump(), "sources": [{"id": "S6", "text": row["text"]}]}, Judgment)
        report.update(status="completed", judgment=result.model_dump())
    except ProviderError as exc:
        report.update(status="blocked", error=str(exc))
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/provider-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "events"}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
