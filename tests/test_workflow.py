import json

import pytest
from fastapi.testclient import TestClient

from evidenceloop.app import create_app
from evidenceloop.challenge import FixtureFetcher, FixtureModel, challenge, make_claim
from evidenceloop.config import Settings
from evidenceloop.engine import Engine
from evidenceloop.models import Draft, Plan, Repair, ResearchRequest, Source
from evidenceloop.storage import Store
from evidenceloop.transfer import QUESTION, transfer


def settings(tmp_path):
    return Settings(_env_file=None, gemini_api_key="", google_api_key="", tavily_api_key="", database_path=str(tmp_path / "test.sqlite3"))


async def test_challenge_correction_memory_and_isolation(tmp_path):
    s = settings(tmp_path)
    store = Store(s.database_path)
    engine = Engine(s, store)
    run = engine.create("Fixture challenge", "challenge_fixture", False)
    await challenge(engine, run)
    assert run["status"] == "completed"
    assert run["challenge_score"] == dict(introduced_errors=6, errors_caught=6, correct_controls=3, correct_wrongly_flagged=0, unverifiable=1, exact_label_matches=9, labelled_cases=9, total_cases=10)
    assert all(x["attempt"] == 1 for x in run["repairs"])
    net_repair = next(x for x in run["repairs"] if x["claim_id"] == "C6")
    assert net_repair["first_verdict"]["verdict"] == "UNSUPPORTED"
    assert net_repair["final_verdict"]["verdict"] == "SUPPORTED"
    assert "net_additions" == net_repair["revision"]["metric"]
    assert store.lessons("challenge_fixture")
    assert store.lessons("live") == []
    assert store.use_lessons("retail store expansion", "heldout", "live") == []
    assert store.use_lessons("retail store expansion", "heldout", "challenge_fixture")
    assert store.get_run(run["id"])["audits"][5]["passage"].startswith("Store count increased by 50")
    follow = engine.create(QUESTION, "transfer_fixture")
    await transfer(engine, follow, run)
    assert follow["status"] == "completed"
    assert follow["transfer_arms"]["memory_off"]["lessons_used"] == []
    assert follow["transfer_arms"]["memory_on"]["lessons_used"]
    assert follow["transfer_arms"]["memory_on"]["claims"] == follow["transfer_arms"]["memory_off"]["claims"]
    assert "no answer-quality improvement" in follow["transfer_conclusion"]


async def test_full_research_flow_plans_before_tools_and_fetches_actual_pages(tmp_path):
    s = settings(tmp_path)
    store = Store(s.database_path)
    engine = Engine(s, store)
    run = engine.create("What was Aster Retail revenue in FY2024?")
    trace = engine.tracer(run)
    stages = []
    class Model(FixtureModel):
        async def generate(self, role, payload, schema):
            stages.append(payload["stage"])
            if schema is Plan:
                return Plan(entities=["Aster Retail"], subquestions=["What is revenue?"], date_range="2024", metric_definitions=["Revenue in INR crore"], required_evidence=["Annual report"], parallel_tasks=["Aster annual report"], stopping_conditions=["One supported figure"])
            if schema is Draft:
                assert payload["sources"][0]["text"] == "Aster Retail reported revenue of INR 120 crore for FY2024."
                assert "Snippet claims 900" not in str(payload)
                return Draft(claims=[make_claim("C1", payload["sources"][0]["text"])], evidence_gaps=[], coverage="One company, one fiscal year")
            return await super().generate(role, payload, schema)
    class Search:
        async def search(self, query):
            assert stages == ["plan"]
            return [{"url": "https://example.com/report", "content": "Snippet claims 900"}]
    source = Source(id="S1", url="https://example.com/report", text="Aster Retail reported revenue of INR 120 crore for FY2024.")
    await engine.research(run, ResearchRequest(question=run["question"]), model=Model(trace), search=Search(), fetcher=FixtureFetcher([source], trace))
    assert run["status"] == "completed"
    assert stages == ["plan", "draft", "audit"]
    assert run["final_audits"][0]["verdict"] == "SUPPORTED"
    assert [x["purpose"] for x in run["activity"] if x["kind"] == "fetch"] == ["analyst", "auditor"]


async def test_no_fetched_evidence_means_no_claims(tmp_path):
    s = settings(tmp_path)
    store = Store(s.database_path)
    engine = Engine(s, store)
    run = engine.create("What is the answer?")
    class Model:
        async def generate(self, role, payload, schema):
            assert schema is Plan
            return Plan(entities=[], subquestions=[], date_range="2024", metric_definitions=[], required_evidence=[], parallel_tasks=["search"], stopping_conditions=[])
    class Search:
        async def search(self, query):
            return []
    await engine.research(run, ResearchRequest(question=run["question"]), model=Model(), search=Search(), fetcher=None)
    assert run["claims"] == []
    assert any("No actual source pages" in x for x in run["evidence_gaps"])


def test_api_configuration_health_validation_and_ui(tmp_path):
    app = create_app(settings(tmp_path))
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        configuration = client.get("/api/config").json()
        assert configuration["missing"] == ["GEMINI_API_KEY", "TAVILY_API_KEY"]
        assert "api_key" not in json.dumps(configuration).lower().replace("gemini_api_key", "").replace("tavily_api_key", "")
        assert client.get("/").status_code == 200
        assert "EvidenceLoop" in client.get("/").text
        assert client.get("/static/app.js").status_code == 200
        assert client.post("/api/runs", json={"question": "too short", "start_date": "2025-01-01", "end_date": "2024-01-01"}).status_code == 422
        assert client.post("/api/runs", json={"question": "What is the company revenue?"}).status_code == 503
        assert client.post("/api/challenge", json={}, headers={"Origin": "https://evil.example"}).status_code == 403
        assert client.get("/api/runs/not-found").status_code == 404
        assert len(client.get("/api/evaluation").json()["questions"]) == 8


def test_interrupted_runs_are_recovered(tmp_path):
    store = Store(str(tmp_path / "recover.sqlite3"))
    run = Engine(settings(tmp_path), store).create("An interrupted question")
    store.recover_interrupted()
    assert store.get_run(run["id"])["status"] == "interrupted"


async def test_failed_repair_cannot_loop_or_create_memory(tmp_path):
    s = settings(tmp_path)
    engine = Engine(s, Store(s.database_path))
    run = engine.create("Aster Retail revenue?")
    trace = engine.tracer(run)
    claim = make_claim("C1", "Aster Retail reported revenue of INR 180 crore for FY2024.", value="180")
    source = Source(id="S1", url="fixture://unchanged", text="Aster Retail reported revenue of INR 120 crore for FY2024.")
    class UnchangingModel(FixtureModel):
        repair_calls = 0
        async def generate(self, role, payload, schema):
            if schema is Repair:
                self.repair_calls += 1
                return Repair(claim=claim, explanation="No change")
            return await super().generate(role, payload, schema)
    model = UnchangingModel(trace)
    await engine.audit_and_repair(run, [claim], [source], model, FixtureFetcher([source], trace), trace)
    assert model.repair_calls == 1
    assert run["final_audits"][0]["verdict"] == "CONTRADICTED"
    assert engine.store.lessons() == []
