"""Synthetic labelled experiments. Expected labels are never sent to the auditor."""
import copy
import re
from time import perf_counter

from .models import Claim, Judgment, Repair, Source
from .providers import Gemini


def make_claim(id, text, entity="Aster Retail", metric="revenue", value="120", unit="INR crore", period="FY2024"):
    return Claim(id=id, text=text, entity=entity, metric=metric, value=value, unit=unit, period=period, source_ids=[f"S{id[1:]}"])


def cases():
    revenue = "Aster Retail reported revenue of INR 120 crore for FY2024."
    launch = "Aster Retail launched its flagship on 12 June 2024."
    net = "Store count increased by 50. Openings and closures were not disclosed."
    rows = [
        ("wrong_amount", make_claim("C1", revenue.replace("120", "180"), value="180"), revenue, "CONTRADICTED", True),
        ("wrong_date", make_claim("C2", launch.replace("12 June", "19 June"), metric="launch_date", value="19 June 2024", unit="date", period="2024"), launch, "CONTRADICTED", True),
        ("wrong_entity", make_claim("C3", revenue.replace("Aster", "Birch"), entity="Birch Retail"), revenue, "UNSUPPORTED", True),
        ("irrelevant_citation", make_claim("C4", revenue), "The city museum is closed on Mondays.", "UNSUPPORTED", True),
        ("stale_evidence", make_claim("C5", "Aster Retail has 200 stores as of 31 December 2025.", metric="store_count", value="200", unit="stores", period="2025-12-31"), "Aster Retail had 200 stores as of 31 December 2022.", "UNSUPPORTED", True),
        ("net_vs_gross", make_claim("C6", "The company opened 50 stores.", entity="The company", metric="gross_openings", value="50", unit="stores", period="reporting period"), net, "UNSUPPORTED", True),
        ("correct_amount", make_claim("C7", revenue), revenue, "SUPPORTED", False),
        ("correct_date", make_claim("C8", launch, metric="launch_date", value="12 June 2024", unit="date", period="2024"), launch, "SUPPORTED", False),
        ("correct_net", make_claim("C9", "Store count increased by 50.", entity="The company", metric="net_additions", value="50", unit="stores", period="reporting period"), net, "SUPPORTED", False),
        ("unavailable_page", make_claim("C10", revenue), "", None, False),
    ]
    return [dict(id=name, claim=claim, text=text, expected=label, introduced_error=error) for name, claim, text, label, error in rows]


class FixtureFetcher:
    def __init__(self, sources, trace):
        self.sources, self.trace = {s.url: s.model_dump() for s in sources}, trace

    async def fetch(self, url, source_id, purpose="analyst"):
        # Fresh independent read of a fixture document, no analyst excerpt.
        source = Source(**copy.deepcopy(self.sources[url]))
        source.id = source_id
        self.trace("fetch", {"url": url, "source_id": source_id, "purpose": purpose, "status": source.status, "fixture": True})
        return source


class FixtureModel:
    """Deliberately narrow rule verifier for transport/repair regression tests, NOT an LLM."""
    def __init__(self, trace):
        self.trace = trace

    async def generate(self, role, payload, schema):
        self.trace("fixture_rule", {"stage": payload["stage"], "note": "Deterministic fixture rule; no model tokens or model accuracy."})
        claim = Claim(**payload["claim"])
        documents = payload.get("sources", [])
        source = next((s for s in documents if s["id"] in claim.source_ids), None)
        text = source["text"] if source else ""
        if payload["stage"] == "repair":
            if not source or "museum" in text or (claim.entity not in text and claim.entity != "The company"):
                return Repair(claim=None, explanation="No evidence for the requested entity or metric; withdrawn.")
            revised = claim.model_copy(deep=True)
            revised.text = text.split(". ")[0].rstrip(".") + "."
            if "Store count increased" in text:
                revised.metric = "net_additions"
            elif "revenue" in text:
                revised.value = re.search(r"INR (\d+)", text).group(1)
            elif "launched" in text:
                revised.value = re.search(r"on (.+)\.", text).group(1)
            elif "2022" in text:
                revised.period = "2022-12-31"
            return Repair(claim=revised, explanation="Revised to the explicit source statement only.")
        verdict, mistake, explanation = "UNSUPPORTED", "citation", "The cited document does not establish this claim."
        if claim.text in text:
            verdict, mistake, explanation = "SUPPORTED", "none", "The exact atomic statement appears in the source."
        elif "opened" in claim.text and "Openings and closures were not disclosed" in text:
            mistake, explanation = "metric", "Net store additions do not prove gross openings; undisclosed closures leave the claim possible but unsupported."
        elif claim.entity not in text and claim.entity != "The company":
            mistake = "entity" if "Retail" in text else "citation"
        elif claim.period == "2025-12-31" and "2022" in text:
            mistake, explanation = "stale_evidence", "The source describes 2022, not the claimed 2025 date."
        elif "revenue" in claim.text and "revenue" in text:
            verdict, mistake, explanation = "CONTRADICTED", "amount", "The revenue amount for the same entity and period differs."
        elif "launched" in claim.text and "launched" in text:
            verdict, mistake, explanation = "CONTRADICTED", "date", "The source explicitly gives a different date for this launch."
        return Judgment(verdict=verdict, source_id=source["id"], passage=text, explanation=explanation, mistake_type=mistake,
                        checked_dimensions=["entity", "amount", "unit", "date", "period", "metric"])


def score_cases(rows, audits):
    by_id = {x["claim_id"]: x for x in audits}
    errors, correct = [r for r in rows if r["introduced_error"]], [r for r in rows if r["expected"] == "SUPPORTED"]
    def caught(row):
        return by_id[row["claim"].id]["verdict"] in ("UNSUPPORTED", "CONTRADICTED")
    return dict(introduced_errors=len(errors), errors_caught=sum(caught(r) for r in errors),
                correct_controls=len(correct), correct_wrongly_flagged=sum(caught(r) for r in correct),
                unverifiable=sum(a["verdict"] is None for a in audits),
                exact_label_matches=sum(by_id[r["claim"].id]["verdict"] == r["expected"] for r in rows if r["expected"] is not None),
                labelled_cases=sum(r["expected"] is not None for r in rows), total_cases=len(rows))


async def challenge(engine, run, use_model=False):
    started, trace = perf_counter(), engine.tracer(run)
    rows = cases()
    sources = [Source(id=r["claim"].source_ids[0], url=f"fixture://challenge/{r['id']}", title=f"Synthetic document: {r['id']}",
                      text=r["text"], status="OK" if r["text"] else "FETCH_FAILED") for r in rows]
    run.update(status="running", sources=[s.model_dump() for s in sources], claims=[r["claim"].model_dump() for r in rows],
        evaluator="Gemini on synthetic documents" if use_model else "Deterministic fixture rules (NOT model evaluation)",
        plan={"entities": ["Synthetic Aster Retail", "Synthetic Birch Retail"], "subquestions": ["Can the verifier identify six controlled error types while retaining correct controls?"],
              "date_range": "Frozen fixture dates, 2022–2025", "metric_definitions": ["Net additions = openings minus closures"],
              "required_evidence": ["Independently re-read synthetic documents; exact quote membership"],
              "parallel_tasks": ["Audit ten cases with bounded model concurrency"], "stopping_conditions": ["One repair per failed claim"], "memory_checks": []},
        coverage="Synthetic fixture experiment; these are not live company facts.")
    try:
        await engine.audit_and_repair(run, [r["claim"] for r in rows], sources,
            Gemini(engine.settings, trace) if use_model else FixtureModel(trace), FixtureFetcher(sources, trace), trace)
        run["challenge_score"] = score_cases(rows, run["audits"])
        run["labels"] = [{"id": r["id"], "claim_id": r["claim"].id, "expected": r["expected"], "introduced_error": r["introduced_error"]} for r in rows]
        run["status"] = "completed"
    except Exception as exc:
        run.update(status="failed", error=f"Challenge failed ({type(exc).__name__})")
    engine.finish_metrics(run, started)
    if not use_model:
        run["metrics"].update(estimated_cost_inr=0, cost_note="Offline fixture rules: no provider calls.")
    engine.store.save_run(run)
    return run
