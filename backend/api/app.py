from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.api.rate_limit import enforce_rate_limit
from backend.api.routes import approvals, auth, backtests, data, execution, ops, paper, research, strategies, vault
from backend.api.schemas import HealthResponse
from backend.auth.service import bootstrap_users
from backend.core.config import settings
from backend.core.logging import configure_logging
from backend.data.storage import ensure_data_dirs, get_sqlite
from backend.ops.metrics import REQUEST_COUNT, REQUEST_LATENCY, prometheus_payload
from backend.strategy.registry import bootstrap_builtin_specs
from backend.strategy.targets import bootstrap_default_target

app = FastAPI(title="Workbench API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
    allow_credentials=True,
)


@app.on_event("startup")
def startup() -> None:
    configure_logging(settings.app_log_path)
    ensure_data_dirs()
    get_sqlite()
    bootstrap_users()
    bootstrap_builtin_specs()
    bootstrap_default_target()


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    start = time.perf_counter()
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    if request.url.path not in {"/health", "/metrics"}:
        enforce_rate_limit(
            request,
            bucket=f"global:{request.url.path}:{request.method}",
            limit=settings.api_rate_limit_global_per_minute,
            window_seconds=60,
        )
    response = await call_next(request)
    latency = time.perf_counter() - start
    path = request.url.path
    REQUEST_LATENCY.labels(request.method, path).observe(latency)
    REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
    response.headers["X-Request-Id"] = request_id
    return response


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(data.router, prefix="/data", tags=["data"])
app.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
app.include_router(backtests.router, prefix="/backtests", tags=["backtests"])
app.include_router(paper.router, prefix="/paper", tags=["paper"])
app.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
app.include_router(execution.router, prefix="/execution", tags=["execution"])
app.include_router(ops.router, prefix="/ops", tags=["ops"])
app.include_router(vault.router, prefix="/vault", tags=["vault"])
app.include_router(research.router, prefix="/research", tags=["research"])


@app.get("/health", response_model=HealthResponse, summary="Service health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics", summary="Prometheus metrics")
async def metrics() -> Response:
    payload, content_type = prometheus_payload()
    return Response(content=payload, media_type=content_type)
