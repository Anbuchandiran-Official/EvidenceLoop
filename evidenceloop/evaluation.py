"""Paired held-out evaluation. Correctness requires human labels, never self-grading."""
import argparse
import asyncio
import copy
import json
from collections import Counter
from pathlib import Path

from .challenge import challenge
from .config import Settings
from .engine import Engine
from .models import ResearchRequest, now
from .storage import Store
from .transfer import QUESTION, transfer


QUESTIONS = [
    {"id": "Q1", "split": "train", "difficulty": 1, "entities": ["Titan"], "question": "What jewellery revenue did Titan report for FY2023-24? Distinguish segment revenue from total company revenue.", "start_date": "2023-04-01", "end_date": "2024-03-31"},
    {"id": "Q2", "split": "train", "difficulty": 2, "entities": ["Kalyan Jewellers"], "question": "How many Kalyan Jewellers showrooms existed at 31 March 2024, and which geographies does that count include?", "start_date": "2023-04-01", "end_date": "2024-03-31"},
    {"id": "Q3", "split": "train", "difficulty": 3, "entities": ["Zepto"], "question": "What amount did Zepto raise in its June 2024 funding round, on what date, and from which named investors? Separate amount from valuation.", "start_date": "2024-06-01", "end_date": "2024-06-30"},
    {"id": "Q4", "split": "train", "difficulty": 4, "entities": ["Senco Gold"], "question": "For Senco Gold FY2023-24, distinguish gross store openings, closures, net additions and closing store count. Report undisclosed values as unknown.", "start_date": "2023-04-01", "end_date": "2024-03-31"},
    {"id": "Q5", "split": "held_out", "difficulty": 5, "entities": ["Titan"], "question": "For Titan's Tanishq stores in India in FY2024-25, distinguish gross openings, net additions and closing count, and explain any unavailable metric.", "start_date": "2024-04-01", "end_date": "2025-03-31"},
    {"id": "Q6", "split": "held_out", "difficulty": 6, "entities": ["Kalyan Jewellers", "Senco Gold"], "question": "Compare Kalyan Jewellers and Senco Gold store expansion in FY2024-25 using the same geography and metric. Can gross openings be established for both?", "start_date": "2024-04-01", "end_date": "2025-03-31"},
    {"id": "Q7", "split": "held_out", "difficulty": 7, "entities": ["Zepto", "Blinkit", "Swiggy Instamart"], "question": "Compare publicly disclosed funding for Zepto, Blinkit and Swiggy Instamart during calendar 2024. Distinguish parent-company funding, primary capital, and secondary transactions; do not claim exhaustive coverage.", "start_date": "2024-01-01", "end_date": "2024-12-31"},
    {"id": "Q8", "split": "held_out", "difficulty": 8, "entities": ["Titan", "Kalyan Jewellers", "Senco Gold"], "question": "Among Titan, Kalyan Jewellers and Senco Gold, which had the greatest documented gross jewellery-store openings in India across FY2023-24 and FY2024-25? Preserve calculation inputs; abstain from ranking if definitions or coverage are incompatible.", "start_date": "2023-04-01", "end_date": "2025-03-31"},
]


def summarize(run, known_types):
    mistakes = Counter(a["mistake_type"] for a in run["audits"] if a["verdict"] in ("UNSUPPORTED", "CONTRADICTED"))
    return {"run_id": run["id"], "status": run["status"], "memory_enabled": run["memory_enabled"],
            "memory_used": [x["id"] for x in run["memory_used"]], "metrics": run["metrics"],
            "auditor_flagged_mistakes": dict(mistakes), "repeated_mistake_types": {k: v for k, v in mistakes.items() if k in known_types},
            "human_correctness": None, "human_labels": [], "correctness_status": "UNREVIEWED; auditor verdicts are not ground truth"}


def finalize_report(report):
    runs = report["training"] + [arm for pair in report["pairs"] for arm in pair["arms"].values()]
    counts = dict(Counter(r["status"] for r in runs))
    report["run_status_counts"] = counts
    complete = len(runs) == 12 and counts.get("completed", 0) == 12
    report["status"] = "completed" if complete else "incomplete"
    report["conclusion"] = (
        "Inconclusive until independently human-labelled. Four paired questions, one run per arm; live-web drift and shared-model errors remain confounds."
        if complete else
        "Evaluation incomplete: not all 12 research runs completed. Resolve failures before comparing correctness, cost or memory effects."
    )


async def evaluate(args):
    settings = Settings()
    # The assignment's live evaluation must never leave one question hanging for
    # the normal server's generous 10-minute demo budget. Keep each evaluation
    # question below the requested two-minute ceiling.
    settings.run_timeout_seconds = min(settings.run_timeout_seconds, args.question_timeout)
    store = Store(args.database)
    engine = Engine(settings, store)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if args.mode in ("fixture", "challenge-model"):
        run = engine.create("Controlled challenge evaluation", "challenge_model" if args.mode == "challenge-model" else "challenge_fixture", False)
        await challenge(engine, run, args.mode == "challenge-model")
        (output / f"{args.mode}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
        if run["memory_written"]:
            follow = engine.create(QUESTION, "transfer_model" if args.mode == "challenge-model" else "transfer_fixture")
            await transfer(engine, follow, run)
            (output / f"{args.mode}-transfer.json").write_text(json.dumps(follow, indent=2), encoding="utf-8")
        print(json.dumps({"mode": args.mode, "score": run.get("challenge_score"), "metrics": run["metrics"]}, indent=2))
        return
    report = {"created_at": now(), "mode": "live_paired", "questions": QUESTIONS, "training": [], "pairs": [],
              "conclusion": "Not yet measured", "memory_snapshot": [], "human_correctness_sample_size": 0}
    path = output / "evaluation.json"
    def save():
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if settings.missing():
        report.update(status="blocked", blockers=settings.missing(), conclusion="No live evaluation was run. Set the missing environment variables locally.")
        save()
        print(json.dumps({"status": "blocked", "missing": settings.missing()}))
        return
    report["status"] = "running"
    # Each live experiment gets a fresh DB, preventing previous held-out runs contaminating training.
    from uuid import uuid4
    store = Store(str(Path(args.database).with_name(f"evaluation-{uuid4().hex[:12]}.sqlite3")))
    engine = Engine(settings, store)
    # Train only on Q1–Q4. Freeze the resulting memory before any held-out question.
    for q in QUESTIONS[:4]:
        print(f"Running {q['id']} (training)...", flush=True)
        req = ResearchRequest(**{k: q[k] for k in ("question", "start_date", "end_date")})
        run = engine.create(req.question)
        await engine.research(run, req)
        report["training"].append({"question_id": q["id"], **summarize(run, set())})
        (output / f'{q["id"]}-train.json').write_text(json.dumps(run, indent=2), encoding="utf-8")
        save()
    snapshot = copy.deepcopy(store.lessons("live"))
    report["memory_snapshot"] = snapshot
    known_types = {x["mistake_type"] for x in snapshot}
    for i, q in enumerate(QUESTIONS[4:]):
        pair = {"question_id": q["id"], "arms": {}}
        # Alternate order to reduce consistent time/order advantage.
        for enabled in ([False, True] if i % 2 == 0 else [True, False]):
            print(f"Running {q['id']} ({'memory_on' if enabled else 'memory_off'})...", flush=True)
            req = ResearchRequest(**{k: q[k] for k in ("question", "start_date", "end_date")}, memory_enabled=enabled)
            run = engine.create(req.question, memory_enabled=enabled)
            await engine.research(run, req, memory_snapshot=copy.deepcopy(snapshot), write_memory=False)
            arm = "memory_on" if enabled else "memory_off"
            pair["arms"][arm] = summarize(run, known_types)
            (output / f'{q["id"]}-{arm}.json').write_text(json.dumps(run, indent=2), encoding="utf-8")
        report["pairs"].append(pair)
        save()
    finalize_report(report)
    save()
    print(f"Saved evaluation to {path}. Complete human review before claiming correctness or improvement.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["fixture", "challenge-model", "live"], default="fixture")
    parser.add_argument("--database", default="data/evaluation.sqlite3")
    parser.add_argument("--output", default="artifacts")
    parser.add_argument("--question-timeout", type=int, default=120,
                        help="Maximum seconds allowed for each live question (default: 120).")
    asyncio.run(evaluate(parser.parse_args()))


if __name__ == "__main__":
    main()
