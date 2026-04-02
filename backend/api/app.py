from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import approvals, auth, backtests, data, execution, ops, paper, strategies, vault
from backend.auth.service import bootstrap_users
from backend.core.config import settings
from backend.data.storage import ensure_data_dirs, get_sqlite
from backend.scheduler import setup_scheduler
from backend.strategy.registry import bootstrap_builtin_specs
from backend.strategy.targets import bootstrap_default_target

app = FastAPI(title="Workbench API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    ensure_data_dirs()
    get_sqlite()
    bootstrap_users()
    bootstrap_builtin_specs()
    bootstrap_default_target()
    if settings.scheduler_enabled:
        setup_scheduler()


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(data.router, prefix="/data", tags=["data"])
app.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
app.include_router(backtests.router, prefix="/backtests", tags=["backtests"])
app.include_router(paper.router, prefix="/paper", tags=["paper"])
app.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
app.include_router(execution.router, prefix="/execution", tags=["execution"])
app.include_router(ops.router, prefix="/ops", tags=["ops"])
app.include_router(vault.router, prefix="/vault", tags=["vault"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
