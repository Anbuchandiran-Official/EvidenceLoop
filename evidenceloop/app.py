import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .challenge import challenge
from .config import Settings
from .engine import Engine
from .models import ResearchRequest
from .storage import Store
from .transfer import QUESTION, transfer


class ChallengeRequest(BaseModel):
    use_model: bool = False


class TransferRequest(BaseModel):
    parent_run_id: str


def create_app(settings=None):
    settings = settings or Settings()
    store = Store(settings.database_path)
    engine = Engine(settings, store)
    tasks = set()

    @asynccontextmanager
    async def lifespan(app):
        store.recover_interrupted()
        yield
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(title="EvidenceLoop", version="0.1.0", lifespan=lifespan)
    app.state.store, app.state.engine = store, engine

    @app.middleware("http")
    async def same_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method == "POST" and origin and urlsplit(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Cross-origin writes are disabled"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: https:; frame-ancestors 'none'; base-uri 'none'"
        return response

    def launch(coroutine):
        task = asyncio.create_task(coroutine)
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    def available():
        if tasks:
            raise HTTPException(409, "A run is already in progress. Wait for it to finish.")

    @app.get("/health")
    def health():
        return {"status": "ok", "app": "EvidenceLoop"}

    @app.get("/api/config")
    def config():
        low_quota = settings.research_quota_mode.lower() == "low"
        return {"live_ready": not settings.missing(), "missing": settings.missing(), "model_ready": bool(settings.model_key),
                "model": settings.gemini_model, "quota_mode": settings.research_quota_mode,
                "budgets": {"searches": 2 if low_quota else settings.max_searches,
                             "sources": 4 if low_quota else settings.max_sources,
                             "claims": 3 if low_quota else settings.max_claims}}

    @app.post("/api/runs", status_code=202)
    async def start_run(request: ResearchRequest):
        available()
        if settings.missing():
            raise HTTPException(503, "Configure locally: " + ", ".join(settings.missing()))
        run = engine.create(request.question, memory_enabled=request.memory_enabled)
        launch(engine.research(run, request))
        return {"id": run["id"]}

    @app.post("/api/challenge", status_code=202)
    async def start_challenge(request: ChallengeRequest):
        available()
        if request.use_model and not settings.model_key:
            raise HTTPException(503, "Configure GEMINI_API_KEY locally for a model challenge")
        run = engine.create("Challenge → correct: ten controlled citation cases", "challenge_model" if request.use_model else "challenge_fixture", False)
        launch(challenge(engine, run, request.use_model))
        return {"id": run["id"]}

    @app.get("/api/runs")
    def runs():
        return store.list_runs()

    @app.post("/api/transfer", status_code=202)
    async def start_transfer(request: TransferRequest):
        available()
        parent = store.get_run(request.parent_run_id)
        if not parent or parent["mode"] not in ("challenge_fixture", "challenge_model") or not parent["memory_written"]:
            raise HTTPException(400, "Run a challenge with at least one verified correction lesson first.")
        run = engine.create(QUESTION, "transfer_model" if parent["mode"] == "challenge_model" else "transfer_fixture", True)
        launch(transfer(engine, run, parent))
        return {"id": run["id"]}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(404, "Run not found")
        return run

    @app.get("/api/runs/{run_id}/export")
    def export_run(run_id: str):
        return JSONResponse(get_run(run_id), headers={"Content-Disposition": f'attachment; filename="run-{run_id}.json"'})

    @app.get("/api/memory")
    def memory():
        return store.lessons()

    @app.get("/api/evaluation")
    def evaluation():
        import json
        from .evaluation import QUESTIONS
        path = Path("artifacts/evaluation.json")
        return {"questions": QUESTIONS, "results": json.loads(path.read_text(encoding="utf-8")) if path.exists() else None}

    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    return app


app = create_app()
