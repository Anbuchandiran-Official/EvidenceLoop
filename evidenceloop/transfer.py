"""A second, unseen synthetic question to demonstrate scoped memory retrieval."""
from time import perf_counter

from .auditor import audit_claim
from .challenge import FixtureFetcher, FixtureModel
from .engine import ANALYST
from .models import Claim, Draft, Plan, Source
from .providers import Gemini


QUESTION = "How many stores did Cedar Retail open in FY2025? Distinguish gross openings from net store additions."
DOCUMENT = "Cedar Retail's store count increased by 35 in FY2025. Openings and closures were not disclosed."


async def transfer(engine, run, parent):
    started, trace = perf_counter(), engine.tracer(run)
    use_model = parent["mode"] == "challenge_model"
    source = Source(id="S1", url="fixture://transfer/cedar-fy2025", title="Synthetic Cedar Retail FY2025 report", text=DOCUMENT)
    run.update(status="running", parent_run_id=parent["id"], sources=[source.model_dump()], transfer_arms={},
               coverage="Held-out synthetic company and period. No live search or company facts.")
    try:
        candidates = [x for x in engine.store.lessons(parent["mode"]) if x["id"] in {l["id"] for l in parent["memory_written"]}]
        for enabled in (False, True):
            lessons = engine.store.use_lessons(QUESTION, run["id"], parent["mode"], candidates) if enabled else []
            if enabled:
                run["memory_used"] = lessons
            trace("memory_read", {"enabled": enabled, "lesson_ids": [x["id"] for x in lessons], "held_out": True})
            if use_model:
                model = Gemini(engine.settings, trace)
                plan = await model.generate(ANALYST, {"stage": "plan", "question": QUESTION, "date_range": "FY2025",
                    "lessons": [{"rule": x["rule"], "scope": x["scope"]} for x in lessons],
                    "instruction": "Plan a research check using the single fixed synthetic source. Do not invent web results."}, Plan)
                draft = await model.generate(ANALYST, {"stage": "draft", "question": QUESTION, "plan": plan.model_dump(), "sources": [source.model_dump()],
                    "instruction": "Answer only what the source establishes, using atomic claims and evidence gaps."}, Draft)
            else:
                model = FixtureModel(trace)
                plan = Plan(entities=["Cedar Retail"], subquestions=["Does the report disclose gross openings?"], date_range="FY2025",
                    metric_definitions=["Net additions = openings minus closures"], required_evidence=["Gross openings must be explicitly reported"],
                    parallel_tasks=["Re-read the fixed Cedar Retail document"], stopping_conditions=["Return the supported metric; record unavailable gross openings"],
                    memory_checks=[x["rule"] for x in lessons])
                # This conservative fixture analyst already distinguishes the metrics in both arms.
                # A forced error in memory-off would manufacture an improvement, so do not add one.
                draft = Draft(claims=[Claim(id="C1", text="Cedar Retail's store count increased by 35 in FY2025.",
                    entity="Cedar Retail", metric="net_additions", value="35", unit="stores", period="FY2025", source_ids=["S1"])],
                    evidence_gaps=["Gross openings and closures are not disclosed."], coverage="One synthetic annual report")
            trace("transfer_plan", {"memory_enabled": enabled, "plan": plan.model_dump()})
            audits = [await audit_claim(c, [source], FixtureFetcher([source], trace), model, trace) for c in draft.claims]
            arm = "memory_on" if enabled else "memory_off"
            run["transfer_arms"][arm] = {"plan": plan.model_dump(), "claims": [c.model_dump() for c in draft.claims],
                "audits": [a.model_dump() for a in audits], "evidence_gaps": draft.evidence_gaps,
                "lessons_used": [x["id"] for x in lessons]}
            if enabled:
                run.update(plan=plan.model_dump(), claims=[c.model_dump() for c in draft.claims], audits=[a.model_dump() for a in audits],
                    final_claims=[c.model_dump() for c in draft.claims], final_audits=[a.model_dump() for a in audits], evidence_gaps=draft.evidence_gaps)
        run.update(status="completed", transfer_conclusion=("Model judgments on one synthetic held-out question. Independent human review is required before claiming correctness or improvement."
            if use_model else "Both fixture arms retained the supported net-additions claim and reported gross openings as unknown. Memory retrieval worked; there was no answer-quality improvement in this deterministic test. This is not model evidence."))
    except Exception as exc:
        run.update(status="failed", error=f"Transfer failed ({type(exc).__name__})")
    engine.finish_metrics(run, started)
    if not use_model:
        run["metrics"].update(estimated_cost_inr=0, cost_note="Offline fixture transfer: no provider calls.")
    engine.store.save_run(run)
    return run
