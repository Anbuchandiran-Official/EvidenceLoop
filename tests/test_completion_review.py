import copy

from evidenceloop.evaluation import finalize_report
from evidenceloop.storage import Store


def test_frozen_memory_retrieval_preserves_all_use_history(tmp_path):
    store = Store(str(tmp_path / "memory.sqlite3"))
    store.add_lesson(rule="Distinguish net additions from openings", scope=["store"],
                     evidence={}, run_id="train", mode="live", mistake_type="metric")
    snapshot = copy.deepcopy(store.lessons("live"))
    store.use_lessons("store expansion Q5", "heldout-5", snapshot=copy.deepcopy(snapshot))
    store.use_lessons("store expansion Q6", "heldout-6", snapshot=copy.deepcopy(snapshot))
    assert [x["run_id"] for x in store.lessons("live")[0]["uses"]] == ["heldout-5", "heldout-6"]
    assert snapshot[0]["uses"] == []


def test_failed_evaluation_is_not_reported_complete():
    report = {"training": [{"status": "failed"}] * 4,
              "pairs": [{"arms": {"memory_off": {"status": "failed"}, "memory_on": {"status": "failed"}}}] * 4}
    finalize_report(report)
    assert report["status"] == "incomplete"
    assert report["run_status_counts"] == {"failed": 12}


def test_complete_evaluation_still_requires_independent_review():
    report = {"training": [{"status": "completed"}] * 4,
              "pairs": [{"arms": {"memory_off": {"status": "completed"}, "memory_on": {"status": "completed"}}}] * 4}
    finalize_report(report)
    assert report["status"] == "completed"
    assert "human-labelled" in report["conclusion"]
