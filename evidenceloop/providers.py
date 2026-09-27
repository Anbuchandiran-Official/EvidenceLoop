import asyncio
import hashlib
import io
import ipaddress
import json
import socket
from time import perf_counter
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from .models import Draft, Judgment, Plan, Repair, Source


def gemini_schema(model):
    """Convert Pydantic JSON Schema to Gemini's supported JSON-Schema subset.

    Gemini structured output accepts objects, arrays, primitive types and enums,
    but rejects optional ``anyOf`` unions and unresolved ``$ref`` definitions.
    The application models use optional calculation data, so resolve refs and
    omit nullable optional properties from the wire schema. Pydantic still
    validates the returned JSON after transport.
    """
    raw = model.model_json_schema()
    definitions = raw.pop("$defs", {})

    def clean(node):
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            key = node["$ref"].rsplit("/", 1)[-1]
            return clean(definitions.get(key, {"type": "object"}))
        if "anyOf" in node:
            options = [x for x in node["anyOf"] if x.get("type") != "null"]
            return clean(options[0] if options else {"type": "string"})
        result = {}
        for key in ("type", "enum", "properties", "required", "items"):
            if key in node:
                if key == "properties":
                    result[key] = {name: clean(value) for name, value in node[key].items()}
                elif key == "items":
                    result[key] = clean(node[key])
                else:
                    result[key] = node[key]
        return result
    return clean(raw)


class ProviderError(RuntimeError):
    """Safe, deliberately body-free provider failure."""


def is_quota_error(error):
    """Return true for throttling or unusable provider responses eligible for demo fallback."""
    message = str(error).lower()
    return any(token in message for token in ("http 429", "quota", "rate limit", "temporarily unavailable", "response failed validation"))


class FixtureFallbackModel:
    """Explicit demo response used when Gemini is throttled.

    It returns the same Pydantic structures as Gemini, but never invents facts.
    A fallback plan leads to an empty, clearly labelled draft with evidence gaps.
    """
    async def generate(self, role, payload, schema):
        stage = payload.get("stage")
        if schema is Plan:
            question = payload.get("question", "the submitted question")
            return Plan(entities=[], subquestions=[question], date_range=payload.get("date_range", ""),
                        metric_definitions=[], required_evidence=["A successfully fetched source page"],
                        parallel_tasks=[question], stopping_conditions=["Do not retain unsupported claims"], memory_checks=[])
        if schema is Draft:
            return Draft(claims=[], evidence_gaps=["Demo fixture fallback active: Gemini was unavailable, so no factual claim was generated."],
                         coverage="Demo fixture fallback; no factual answer retained because the model provider was unavailable.")
        if schema is Repair:
            return Repair(claim=None, explanation="Demo fixture fallback cannot repair claims without model verification.")
        if schema is Judgment:
            return Judgment(verdict="UNSUPPORTED", source_id="", passage="", explanation="Demo fixture fallback did not evaluate a factual claim.",
                            mistake_type="other", checked_dimensions=[])
        raise TypeError(f"Unsupported fallback schema: {schema.__name__}")


def has_url_credentials(url):
    parts = urlsplit(url)
    return bool(parts.username or parts.password or any(term in parts.query.lower() for term in
        ("api_key=", "apikey=", "access_token=", "signature=", "x-amz-", "token=", "key=")))


class Gemini:
    def __init__(self, settings, trace):
        self.settings, self.trace = settings, trace
        self.semaphore = asyncio.Semaphore(2)

    async def generate(self, role, payload, schema):
        if not self.settings.model_key:
            raise ProviderError("GEMINI_API_KEY is not configured")
        config = {"temperature": 0, "maxOutputTokens": 8192}
        if self.settings.gemini_schema_style == "format":
            config["responseFormat"] = {"text": {"mimeType": "application/json", "schema": gemini_schema(schema)}}
        else:
            config.update(responseMimeType="application/json", responseJsonSchema=gemini_schema(schema))
        body = {"systemInstruction": {"parts": [{"text": role}]},
                "contents": [{"role": "user", "parts": [{"text": json.dumps(payload)}]}], "generationConfig": config}
        self.trace("model_request", {"stage": payload.get("stage"), "instruction": role, "payload": payload, "schema": schema.__name__})
        started = perf_counter()
        async with self.semaphore, httpx.AsyncClient(timeout=90, trust_env=False) as client:
            try:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_model}:generateContent",
                    headers={"x-goog-api-key": self.settings.model_key}, json=body)
                if response.status_code != 200:
                    raise ProviderError(f"Gemini HTTP {response.status_code}; check model access, quota, and credentials locally")
                data = response.json()
                usage = data.get("usageMetadata", {})
                self.trace("model", {"model": self.settings.gemini_model, "stage": payload.get("stage"),
                    "input_tokens": usage.get("promptTokenCount", 0),
                    "output_tokens": usage.get("candidatesTokenCount", 0), "thinking_tokens": usage.get("thoughtsTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0), "usage_reported": bool(usage), "seconds": round(perf_counter() - started, 3), "status": "OK"})
                parts = data["candidates"][0]["content"]["parts"]
                answer = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                parsed = schema.model_validate_json(answer)
                self.trace("model_response", {"stage": payload.get("stage"), "output": parsed.model_dump()})
                return parsed
            except Exception as exc:
                self.trace("model_error", {"stage": payload.get("stage"), "error_type": type(exc).__name__, "seconds": round(perf_counter() - started, 3)})
                if isinstance(exc, ProviderError):
                    raise
                raise ProviderError(f"Gemini response failed validation or transport ({type(exc).__name__})") from None


class Tavily:
    def __init__(self, settings, trace):
        self.settings, self.trace = settings, trace
        self.semaphore = asyncio.Semaphore(2)

    async def search(self, query):
        if not self.settings.tavily_api_key:
            raise ProviderError("TAVILY_API_KEY is not configured")
        started = perf_counter()
        async with self.semaphore, httpx.AsyncClient(timeout=35, trust_env=False) as client:
            try:
                response = await client.post("https://api.tavily.com/search",
                    headers={"Authorization": f"Bearer {self.settings.tavily_api_key}"},
                    json={"query": query, "search_depth": "basic", "max_results": 4,
                          "include_answer": False, "include_raw_content": False, "include_usage": True})
                if response.status_code != 200:
                    raise ProviderError(f"Tavily HTTP {response.status_code}; check quota and credentials locally")
                data = response.json()
                results = [{"url": x["url"], "title": x.get("title", ""), "published_date": x.get("published_date")}
                           for x in data.get("results", []) if not has_url_credentials(x["url"])]
                self.trace("search", {"query": query, "results": results, "credits": data.get("usage", {}).get("credits"),
                                      "status": "OK", "seconds": round(perf_counter() - started, 3)})
                return results
            except Exception as exc:
                self.trace("search", {"query": query, "status": "FAILED", "error_type": type(exc).__name__})
                if isinstance(exc, ProviderError):
                    raise
                raise ProviderError(f"Tavily transport failure ({type(exc).__name__})") from None


async def public_url(url):
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Only public HTTP(S) URLs without credentials are allowed")
    if parts.port not in (None, 80, 443):
        raise ValueError("Nonstandard port blocked")
    # Query strings can carry signed access credentials; never retain or fetch those.
    if has_url_credentials(url):
        raise ValueError("Credential-bearing URL blocked")
    addresses = await asyncio.get_running_loop().getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Private or reserved network address blocked")


def extract(raw, content_type):
    if "pdf" in content_type or raw.startswith(b"%PDF"):
        reader = PdfReader(io.BytesIO(raw))
        pages = reader.pages[:60]
        return "\n".join(p.extract_text() or "" for p in pages), "PDF document", None, len(reader.pages) > 60
    if "html" in content_type:
        soup = BeautifulSoup(raw, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else "Untitled page"
        meta = soup.find("meta", attrs={"property": "article:published_time"}) or soup.find("meta", attrs={"name": "date"})
        published = meta.get("content") if meta else None
        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()
        return soup.get_text(" ", strip=True), title, published, False
    if "text/plain" in content_type:
        return raw.decode("utf-8", errors="replace"), "Text document", None, False
    raise TypeError("Unsupported content type")


class Fetcher:
    def __init__(self, settings, trace):
        self.trace = trace
        self.semaphore = asyncio.Semaphore(settings.fetch_concurrency)

    async def fetch(self, url, source_id, purpose="analyst"):
        started = perf_counter()
        source = Source(id=source_id, url=url)
        async with self.semaphore:
            try:
                async with httpx.AsyncClient(timeout=25, follow_redirects=False, trust_env=False,
                    headers={"User-Agent": "EvidenceLoop/0.1 research citation verifier"}) as client:
                    target = url
                    for _ in range(5):
                        await public_url(target)
                        async with client.stream("GET", target) as response:
                            if response.is_redirect:
                                target = str(response.url.join(response.headers["location"]))
                                continue
                            response.raise_for_status()
                            chunks, size = [], 0
                            async for chunk in response.aiter_bytes():
                                size += len(chunk)
                                if size > 5_000_000:
                                    raise ValueError("Document exceeds 5 MB fetch budget")
                                chunks.append(chunk)
                            raw = b"".join(chunks)
                            content_type = response.headers.get("content-type", "")
                            break
                    else:
                        raise ValueError("Redirect limit exceeded")
                text, title, published, truncated = await asyncio.to_thread(extract, raw, content_type)
                source.text = " ".join(text.split())[:45000]
                source.title, source.published_at = title, published
                source.truncated = truncated or len(" ".join(text.split())) > 45000
                source.content_hash = hashlib.sha256(source.text.encode()).hexdigest()
                if not source.text:
                    raise ValueError("Empty document; image-only PDFs require OCR")
            except Exception as exc:
                source.status = "BLOCKED" if isinstance(exc, ValueError) else "UNSUPPORTED_FORMAT" if isinstance(exc, TypeError) else "FETCH_FAILED"
                source.error = f"{type(exc).__name__}: page could not be retrieved within the fetch policy"
            self.trace("fetch", {"source_id": source_id, "url": url, "purpose": purpose, "status": source.status, "source": source.model_dump(),
                                 "characters": len(source.text), "seconds": round(perf_counter() - started, 3)})
        return source
