import json

import httpx
import pytest

from evidenceloop.config import Settings
from evidenceloop.models import Judgment, Draft, Plan
from evidenceloop.providers import Gemini, ProviderError, Tavily, gemini_schema
from evidenceloop.engine import QuotaFallbackModel


def mock_client(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))


@pytest.mark.parametrize("style", ["legacy", "format"])
async def test_gemini_schema_modes_usage_and_no_header_secrets_in_trace(monkeypatch, style):
    secret = "test-credential-never-in-trace"
    output = dict(verdict="UNSUPPORTED", source_id="S1", passage="Source passage", explanation="Not enough information", mistake_type="metric", checked_dimensions=["entity", "amount", "unit", "date", "period", "metric"])
    def handler(request):
        assert request.headers["x-goog-api-key"] == secret
        assert secret not in str(request.url)
        body = json.loads(request.content)
        config = body["generationConfig"]
        if style == "legacy":
            assert config["responseMimeType"] == "application/json"
            assert "properties" in config["responseJsonSchema"]
        else:
            assert config["responseFormat"]["text"]["mimeType"] == "application/json"
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "private thought must be excluded", "thought": True}, {"text": json.dumps(output)}]}}], "usageMetadata": {"promptTokenCount": 30, "candidatesTokenCount": 15, "thoughtsTokenCount": 10, "totalTokenCount": 55}})
    mock_client(monkeypatch, handler)
    events = []
    model = Gemini(Settings(_env_file=None, gemini_api_key=secret, gemini_schema_style=style), lambda k, v: events.append({"kind": k, **v}))
    result = await model.generate("Audit", {"stage": "audit", "claim": "Some claim"}, Judgment)
    assert result.verdict == "UNSUPPORTED"
    usage = next(x for x in events if x["kind"] == "model")
    assert usage["thinking_tokens"] == 10 and usage["total_tokens"] == 55
    serialized = json.dumps(events)
    assert secret not in serialized
    assert "private thought" not in serialized


async def test_provider_failure_never_logs_response_body(monkeypatch):
    mock_client(monkeypatch, lambda request: httpx.Response(503, text="sensitive error body"))
    events = []
    model = Gemini(Settings(_env_file=None, gemini_api_key="private-test-key"), lambda k, d: events.append(d))
    with pytest.raises(ProviderError, match="HTTP 503") as error:
        await model.generate("Audit", {"stage": "audit"}, Judgment)
    assert "sensitive error body" not in str(error.value) + json.dumps(events)
    assert "private-test-key" not in str(error.value) + json.dumps(events)


async def test_tavily_uses_header_auth_and_discards_search_snippets(monkeypatch):
    def handler(request):
        assert request.headers["Authorization"] == "Bearer tavily-test-key"
        body = json.loads(request.content)
        assert body["include_answer"] is False
        assert body["search_depth"] == "basic"
        return httpx.Response(200, json={"results": [{"url": "https://example.com/report", "title": "Report", "content": "Unsupported snippet"}], "usage": {"credits": 1}})
    mock_client(monkeypatch, handler)
    events = []
    results = await Tavily(Settings(_env_file=None, tavily_api_key="tavily-test-key"), lambda k, d: events.append(d)).search("revenue")
    assert "content" not in results[0]
    assert "Unsupported snippet" not in json.dumps(events)
    assert events[0]["credits"] == 1


def test_gemini_schema_resolves_optional_refs_and_supported_subset():
    schema = gemini_schema(Draft)
    calculation = schema["properties"]["claims"]["items"]["properties"]["calculation"]
    assert "anyOf" not in str(schema)
    assert "$ref" not in str(schema)
    assert calculation["type"] == "object"
    assert "title" not in str(schema)


async def test_quota_fallback_switches_once_to_fixture(monkeypatch):
    class Primary:
        calls = 0
        async def generate(self, role, payload, schema):
            self.calls += 1
            raise ProviderError("Gemini HTTP 429; check quota")
    events = []
    settings = Settings(_env_file=None, gemini_fallback_mode="fixture")
    primary = Primary()
    model = QuotaFallbackModel(primary, settings, lambda kind, detail: events.append((kind, detail)))
    first = await model.generate("analyst", {"stage": "plan", "question": "What happened?", "date_range": "2024"}, Plan)
    second = await model.generate("analyst", {"stage": "draft", "question": "What happened?"}, Draft)
    assert first.parallel_tasks == ["What happened?"]
    assert second.claims == [] and "fallback" in second.coverage
    assert primary.calls == 1
    assert [kind for kind, _ in events].count("fallback") == 1
