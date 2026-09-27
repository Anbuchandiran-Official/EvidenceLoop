"""Export a blinded human review sheet; import independently completed correctness labels."""
import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("artifacts"))
    parser.add_argument("--import-labels", type=Path)
    args = parser.parse_args()
    report_path = args.directory / "evaluation.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not report.get("pairs"):
        raise SystemExit("No completed held-out pairs to review.")
    mapping, rows = {}, []
    for pair in report["pairs"]:
        for arm, summary in pair["arms"].items():
            run = json.loads((args.directory / f'{pair["question_id"]}-{arm}.json').read_text(encoding="utf-8"))
            review_id = run["id"]
            mapping[review_id] = summary
            # Include a question-level row so abstentions, omissions, and completeness get reviewed.
            items = [("ANSWER", run["question"] + " | Gaps: " + "; ".join(run["evidence_gaps"]), "")]
            items += [(c["id"], c["text"], " ".join(s["url"] for s in run["sources"] if s["id"] in c["source_ids"])) for c in run["final_claims"]]
            for claim_id, claim, urls in items:
                rows.append({"review_id": review_id, "claim_id": claim_id, "text": claim, "source_urls": urls,
                    "correct": "", "reviewer": "", "evidence_passage": "", "notes": ""})
    if not args.import_labels:
        random.Random(37).shuffle(rows)
        target = args.directory / "human-review.csv"
        with target.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"Blinded review sheet: {target}. Use correct=1, 0, or unknown; supply reviewer and evidence passage. ANSWER rows assess completeness and appropriate abstention.")
        return
    expected = {(r["review_id"], r["claim_id"]) for r in rows}
    seen, grouped = set(), defaultdict(list)
    with args.import_labels.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = (row["review_id"], row["claim_id"])
            if key not in expected or key in seen:
                raise SystemExit("Unknown or duplicate review row")
            seen.add(key)
            if row["correct"] not in ("1", "0", "unknown") or not row["reviewer"].strip() or not row["evidence_passage"].strip():
                raise SystemExit("Every row needs a valid label, reviewer, and supporting evidence passage")
            grouped[row["review_id"]].append(row)
    if seen != expected:
        raise SystemExit("Review is incomplete; expected every exported row")
    for run_id, labels in grouped.items():
        answer = next(x for x in labels if x["claim_id"] == "ANSWER")
        mapping[run_id]["human_correctness"] = int(answer["correct"]) if answer["correct"] != "unknown" else None
        mapping[run_id]["human_labels"] = labels
        mapping[run_id]["correctness_status"] = "HUMAN_REVIEWED"
    paired = [(p["arms"]["memory_off"]["human_correctness"], p["arms"]["memory_on"]["human_correctness"]) for p in report["pairs"]]
    complete = [(off, on) for off, on in paired if off is not None and on is not None]
    report["human_correctness_sample_size"] = len(complete)
    report["human_comparison"] = {"complete_pairs": len(complete), "off_correct": sum(x[0] for x in complete), "on_correct": sum(x[1] for x in complete),
        "paired_difference": sum(x[1]-x[0] for x in complete), "note": "Descriptive result on a small sample, not causal proof. Unknown pairs excluded and counted."}
    report["conclusion"] = "Human review recorded. Inspect paired correctness, coverage, time and cost together; no significance or improvement claim is generated automatically."
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["human_comparison"], indent=2))


if __name__ == "__main__":
    main()
