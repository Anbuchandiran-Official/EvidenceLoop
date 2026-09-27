import json
import sqlite3
import uuid
from pathlib import Path

from .models import now


class Store:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT, mode TEXT, body TEXT);
                CREATE TABLE IF NOT EXISTS lessons (id TEXT PRIMARY KEY, body TEXT);
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def save_run(self, run):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?)", (run["id"], run["created_at"], run["mode"], json.dumps(run)))

    def get_run(self, run_id):
        with self.connect() as db:
            row = db.execute("SELECT body FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_runs(self, limit=40):
        with self.connect() as db:
            rows = db.execute("SELECT body FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [{k: r.get(k) for k in ("id", "created_at", "mode", "question", "status", "metrics")} for r in map(lambda x: json.loads(x[0]), rows)]

    def lessons(self, mode=None):
        with self.connect() as db:
            rows = db.execute("SELECT body FROM lessons").fetchall()
        lessons = [json.loads(row[0]) for row in rows]
        return [x for x in lessons if mode is None or x["mode"] == mode]

    def save_lesson(self, lesson):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO lessons VALUES (?,?)", (lesson["id"], json.dumps(lesson)))

    def add_lesson(self, *, rule, scope, evidence, run_id, mode, mistake_type):
        old = next((x for x in self.lessons(mode) if x["rule"] == rule), None)
        if old:
            return old
        lesson = dict(id=uuid.uuid4().hex[:12], rule=rule, scope=scope, evidence=evidence, triggering_run_id=run_id,
                      mode=mode, mistake_type=mistake_type, verification_status="VERIFIED", created_at=now(), uses=[])
        self.save_lesson(lesson)
        return lesson

    def use_lessons(self, question, run_id, mode="live", snapshot=None):
        candidates = self.lessons(mode) if snapshot is None else snapshot
        matches = [x for x in candidates if x["verification_status"] == "VERIFIED" and x["mode"] == mode
                   and any(term.lower() in question.lower() for term in x["scope"])]
        for lesson in matches:
            # The frozen snapshot controls retrieval, but use history must append to
            # current persisted state rather than overwrite it with an old snapshot.
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT body FROM lessons WHERE id=?", (lesson["id"],)).fetchone()
                current = json.loads(row[0]) if row else dict(lesson)
                current["uses"] = [*current["uses"], {"run_id": run_id, "at": now()}]
                db.execute("INSERT OR REPLACE INTO lessons VALUES (?,?)", (current["id"], json.dumps(current)))
        return matches

    def recover_interrupted(self):
        with self.connect() as db:
            rows = db.execute("SELECT body FROM runs").fetchall()
        for row in rows:
            run = json.loads(row[0])
            if run["status"] in ("queued", "running"):
                run.update(status="interrupted", error="Server restarted before this run completed.")
                self.save_run(run)
