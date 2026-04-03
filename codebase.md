# CryptoSwarms Codebase

## `.env`

```
BINANCE_BASE_URL=https://fapi.binance.com
HYPERLIQUID_BASE_URL=https://api.hyperliquid.xyz
OPENROUTER_API_KEY=
OPENROUTER_MODEL=anthropic/claude-3.5-haiku
AUTH_VIEWER_TOKEN=3bFM_nH38T0xLy-0kTq6IiN9h7N5vKjY0DG7QX8mU4A
AUTH_OPERATOR_TOKEN=Y0a9e8Hf7qJk2nLmP4rTsV6wXzB1cD3gF5hI7jK9mNQ
AUTH_ADMIN_TOKEN=Qp5wEr7tYu9iOp1aSd3fGh5jKl7zXc9vBn2mLq4rTsV
VAULT_PASSPHRASE=Vf8j2Lq9mPw4sDx7hZn3kRc6tBy1uAe5
VAULT_FILE_PATH=./data/meta/secrets.vault
RAW_DATA_ROOT=./data/raw
CURATED_DB_PATH=./data/curated/workbench.duckdb
META_DB_PATH=./data/meta/workbench.db
PAPER_INITIAL_CAPITAL_USD=100000
PAPER_SLIPPAGE_BPS=3.0
PAPER_TRADING_ENABLED=true
PAPER_MAX_OPEN_POSITIONS=4
PAPER_DAILY_LOSS_LIMIT_USD=1500
PAPER_DAY_RESET_HOUR_UTC=0
DATA_READINESS_COVERAGE_DAYS=20
PAPER_READINESS_MIN_EVENTS=10
LIVE_TRADING_ENABLED=false
LIVE_APPROVAL_MODE=true
LIVE_NETWORK_ENABLED=false
BINANCE_API_KEY=
BINANCE_API_SECRET=
HYPERLIQUID_PRIVATE_KEY=
HYPERLIQUID_ACCOUNT_ADDRESS=
SCHEDULER_ENABLED=false

```

## `.env.example`

```bash
BINANCE_BASE_URL=https://fapi.binance.com
HYPERLIQUID_BASE_URL=https://api.hyperliquid.xyz
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=anthropic/claude-3.5-haiku
AUTH_VIEWER_TOKEN=replace-with-random-viewer-token
AUTH_OPERATOR_TOKEN=replace-with-random-operator-token
AUTH_ADMIN_TOKEN=replace-with-random-admin-token
AUTH_COOKIE_NAME=workbench_token
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_MAX_AGE_SECONDS=28800
VAULT_PASSPHRASE=change-me
VAULT_FILE_PATH=./data/meta/secrets.vault
APP_LOG_PATH=./data/meta/workbench.log
RAW_DATA_ROOT=./data/raw
CURATED_DB_PATH=./data/curated/workbench.duckdb
META_DB_PATH=./data/meta/workbench.db
PAPER_INITIAL_CAPITAL_USD=100000
PAPER_FEE_BPS=4.0
PAPER_SLIPPAGE_BPS=3.0
PAPER_TRADING_ENABLED=true
PAPER_MAX_OPEN_POSITIONS=4
PAPER_MAX_GROSS_EXPOSURE_USD=40000
PAPER_MAX_SIGNAL_CORRELATION=0.92
PAPER_DAILY_LOSS_LIMIT_USD=1500
PAPER_DAY_RESET_HOUR_UTC=0
DATA_READINESS_COVERAGE_DAYS=20
PAPER_READINESS_MIN_EVENTS=10
LIVE_TRADING_ENABLED=false
LIVE_APPROVAL_MODE=true
LIVE_NETWORK_ENABLED=false
BINANCE_API_KEY=
BINANCE_API_SECRET=
HYPERLIQUID_PRIVATE_KEY=
HYPERLIQUID_ACCOUNT_ADDRESS=
SCHEDULER_ENABLED=false
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CORS_ALLOW_METHODS=GET,POST,OPTIONS
CORS_ALLOW_HEADERS=Content-Type,X-Workbench-Token
API_RATE_LIMIT_GLOBAL_PER_MINUTE=600
API_RATE_LIMIT_AUTH_TOKEN_PER_MINUTE=10
API_RATE_LIMIT_TICKET_APPROVE_PER_MINUTE=20
WORKER_MAX_RETRIES=3
WORKER_RETRY_BACKOFF_SECONDS=5
WORKER_HEARTBEAT_TTL_SECONDS=30
MARKET_STREAMS_ENABLED=false
ALERTS_TELEGRAM_BOT_TOKEN=
ALERTS_TELEGRAM_CHAT_ID=
ALERTS_DISCORD_WEBHOOK_URL=
ALERTS_EMAIL_SMTP_HOST=
ALERTS_EMAIL_SMTP_PORT=587
ALERTS_EMAIL_USERNAME=
ALERTS_EMAIL_PASSWORD=
ALERTS_EMAIL_FROM=
ALERTS_EMAIL_TO=

```

## `.gitignore`

```
# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Frontend / Node
node_modules/
.npm-cache/

# Testing
.pytest_cache/
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.playwright-cli/

# IDE / OS
.idea/
.vscode/
*.swp
*.swo
.DS_Store
Thumbs.db

# Logs
*.log

```

## `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: secret-scan
        name: Secret Scan
        entry: python scripts/scan_secrets.py
        language: system
        pass_filenames: false

```

## `docker-compose.yml`

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    env_file:
      - .env.example
    volumes:
      - ./data:/app/data
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5).read()"]
      interval: 15s
      timeout: 5s
      retries: 5

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    env_file:
      - .env.example
    environment:
      SCHEDULER_ENABLED: "true"
    volumes:
      - ./data:/app/data
    depends_on:
      - api
    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import sqlite3,datetime; con=sqlite3.connect('/app/data/meta/workbench.db'); row=con.execute(\"SELECT last_seen FROM worker_heartbeat ORDER BY last_seen DESC LIMIT 1\").fetchone(); assert row and (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(row[0])).total_seconds()<45",
        ]
      interval: 20s
      timeout: 5s
      retries: 5

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "4173:4173"
    depends_on:
      - api

```

## `Dockerfile.api`

```
FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

```

## `Dockerfile.worker`

```
FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "backend.worker.main"]

```

## `pyproject.toml`

```toml
[project]
name = "workbench"
version = "0.1.0"
description = "Local-first crypto research and paper trading workbench"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "apscheduler>=3.10",
  "cryptography>=43.0",
  "duckdb>=1.0",
  "fastapi>=0.111",
  "httpx>=0.27",
  "pandas>=2.2",
  "prometheus-client>=0.21",
  "pyarrow>=16",
  "pydantic>=2.7",
  "python-dotenv>=1.0",
  "structlog>=24.2",
  "uvicorn[standard]>=0.30",
  "websockets>=12",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
  "pytest-asyncio>=0.23",
]

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = [
  "backend",
  "backend.api",
  "backend.api.routes",
  "backend.auth",
  "backend.backtest",
  "backend.core",
  "backend.data",
  "backend.data.adapters",
  "backend.data.streams",
  "backend.execution",
  "backend.ops",
  "backend.paper",
  "backend.research",
  "backend.research.agents",
  "backend.secrets",
  "backend.strategy",
  "backend.strategy.signals",
  "backend.worker",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

```

## `README.md`

```markdown
# Workbench

Local-first crypto research, backtesting, and paper-trading workbench built from the spec in `Cs.txt`.

## Backend

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn backend.api.app:app --reload
```

Default local auth roles:

- `viewer` token: `viewer-token`
- `operator` token: `operator-token`
- `admin` token: `admin-token`

Vault-backed exchange secrets:

- Set `VAULT_PASSPHRASE` in your environment.
- Store exchange credentials through the admin vault API instead of plain env secrets.

Bootstrap a safe local runtime:

```powershell
py -3.13 scripts\bootstrap_secure_runtime.py
```

Store secrets in the vault:

```powershell
py -3.13 scripts\set_vault_secret.py binance_api_key YOUR_KEY
py -3.13 scripts\set_vault_secret.py binance_api_secret YOUR_SECRET
py -3.13 scripts\set_vault_secret.py hyperliquid_private_key YOUR_PRIVATE_KEY
py -3.13 scripts\set_vault_secret.py hyperliquid_account_address YOUR_ADDRESS
```

Enable live approval mode without live network submission:

```powershell
py -3.13 scripts\enable_live_approval_mode.py
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Worker

```powershell
py -3.11 -m backend.worker.main
```

## Docker Compose

```powershell
docker compose up --build
```

```

## `Shufa.txt`

```
# CryptoSwarms — Deep Technical & Product Review

> Owner · Crypto Expert · Senior Software Engineer perspective  
> Reviewed: April 2026 | Codebase version 0.1.0

-----

## Executive Summary

CryptoSwarms is a thoughtfully scaffolded local-first crypto research workbench with a solid conceptual spine: ingest → feature engineering → backtest → paper trade → gated live execution. The architecture is intentional and conservative — paper trading must pass promotion gates before live orders are even possible. That is the right default.

However, in its current state the system is **not yet trustworthy enough to run live money**, and **not yet powerful enough to outperform even a naive systematic trader**. This document catalogs every critical defect, meaningful weakness, and feature gap found in the review, then provides a concrete improvement roadmap.

Severity legend used throughout:  
🔴 **Critical** — data loss, money loss, or security breach risk  
🟠 **High** — incorrect results, silent failures, or broken core features  
🟡 **Medium** — degraded experience, missing guard-rails, or reliability risk  
🟢 **Low / Enhancement** — quality-of-life, competitive edge, or operational maturity

-----

## Part 1 — Security Audit 🔴🔴🔴

### 1.1 Production Secret Committed to Repository 🔴

**File:** `.env`

```
VAULT_PASSPHRASE=Wl6o2wcrMBPhbGJ82Z-JBJOTTd7RUHlx
```

The vault passphrase — the single key protecting all exchange credentials — is committed in plaintext to the repo. **Any git history exposure, misconfigured git remote, or accidental push to a public fork will leak this key and compromise all secrets stored in the vault.**

**Fix:**

- Rotate the passphrase immediately
- Add `.env` to `.gitignore` (it already is, but clearly someone edited `.env` directly instead of using `.env.example`)
- Add a pre-commit hook that scans for high-entropy strings
- Use `git-secrets` or `truffleHog` in CI to prevent future commits

### 1.2 Trivially Guessable Default Auth Tokens 🔴

**File:** `.env`, `backend/auth/service.py`

```
AUTH_VIEWER_TOKEN=viewer-token
AUTH_OPERATOR_TOKEN=operator-token
AUTH_ADMIN_TOKEN=admin-token
```

These are the hardcoded defaults in both `.env.example` and the actual `.env`. Anyone who knows the API base URL can immediately authenticate as admin. The `bootstrap_secure_runtime.py` script generates a strong vault passphrase but **does not generate random auth tokens**.

**Fix:**

```python
# In bootstrap_secure_runtime.py, replace:
"AUTH_VIEWER_TOKEN": "viewer-token",
# With:
"AUTH_VIEWER_TOKEN": secrets.token_urlsafe(32),
"AUTH_OPERATOR_TOKEN": secrets.token_urlsafe(32),
"AUTH_ADMIN_TOKEN": secrets.token_urlsafe(32),
```

### 1.3 No Rate Limiting on Any API Endpoint 🔴

A brute-force attack against `/auth/token` can enumerate tokens in seconds. The execution endpoints — including `/execution/tickets/{id}/approve` — have no rate limiting, making it trivial to replay or spam approval requests.

**Fix:** Add `slowapi` (built on `limits`) middleware:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# Then on sensitive endpoints:
@router.post("/token")
@limiter.limit("10/minute")
def token_session(...): ...
```

### 1.4 CORS Allows All Methods and Headers from Any localhost Origin 🟠

**File:** `backend/api/app.py`

```python
allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
allow_methods=["*"],
allow_headers=["*"],
```

This is fine for local development but the `allow_methods=["*"]` and `allow_headers=["*"]` combination is overly permissive. In a Docker/cloud deployment the origins list must become configurable via environment variable rather than hardcoded.

### 1.5 Auth Token Stored in localStorage — XSS Exploitable 🟠

**File:** `frontend/src/api/client.ts`

```typescript
window.localStorage.setItem(TOKEN_KEY, token);
```

`localStorage` is accessible to any JavaScript on the page. A single XSS vector anywhere in the frontend (e.g., a strategy name with injected script content rendered without escaping) will steal the admin token.

**Fix:** Use `httpOnly` cookies set by the server, or at minimum move to `sessionStorage` with a short expiry. For a local tool, this is acceptable risk, but must be documented.

### 1.6 SQL Injection Risk in Dynamic LIMIT Clauses 🟡

**File:** `backend/data/storage.py` (pattern used across routes)

```python
fetch_all(f"SELECT * FROM audit_events ORDER BY created_at DESC LIMIT {int(limit)}")
```

The `int(limit)` cast mitigates injection but the pattern should use parameterized queries consistently:

```python
fetch_all("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?", [limit])
```

### 1.7 Execution Adapter HMAC Bug Under Python Strict Mode 🟠

**File:** `backend/execution/adapters.py`

```python
signature = hmac.new(self.api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
```

`hmac.new` is a legacy alias that works in CPython but is not part of the public API contract. The correct call is:

```python
signature = hmac.HMAC(
    self.api_secret.encode("utf-8"),
    query.encode("utf-8"),
    hashlib.sha256
).hexdigest()
```

This will silently fail on some Python distributions and pypy.

-----

## Part 2 — Correctness Bugs (Silent Wrong Results) 🔴🟠

### 2.1 Perturbation Sharpe Is Not Actually Computed 🔴

**File:** `backend/backtest/engine.py`

```python
perturbation_sharpe_mean=sharpe,   # ← same as base sharpe
perturbation_sharpe_std=0.0,       # ← always zero
oos_sharpe=sharpe * 0.9,           # ← 90% of in-sample, not walk-forward
```

The promotion policy checks `min_perturbation_sharpe` and `min_oos_sharpe` — two of the five gates that determine whether a strategy gets promoted. Both checks pass on synthetic numbers that are mathematically derived from the in-sample Sharpe, guaranteeing that **every backtest with a positive Sharpe will pass these gates regardless of robustness**. This is the most dangerous correctness bug in the system.

**Fix — Real Perturbation (noise injection):**

```python
import numpy as np

def compute_perturbation_sharpe(spec, bars, config, n_runs=20):
    sharpes = []
    for _ in range(n_runs):
        noised = bars.copy()
        noised["close"] *= np.random.uniform(0.998, 1.002, size=len(noised))
        result = run_backtest(spec, noised, config)
        sharpes.append(result.sharpe)
    return float(np.mean(sharpes)), float(np.std(sharpes))
```

**Fix — Real OOS Sharpe (walk-forward split):**

```python
def compute_oos_sharpe(spec, bars, config, oos_fraction=0.3):
    split = int(len(bars) * (1 - oos_fraction))
    oos_bars = bars.iloc[split:].reset_index(drop=True)
    oos_start = oos_bars["ts_open"].iloc[0].to_pydatetime()
    oos_config = replace(config, start_date=oos_start)
    oos_result = run_backtest(spec, oos_bars, oos_config)
    return oos_result.sharpe
```

### 2.2 Funding Reversion Strategy Will Never Fire in Production 🔴

**File:** `backend/data/service.py` (implied), `backend/backtest/service.py`

```python
def load_funding_like_series(...):
    # Returns empty DataFrame with columns ["ts", "rate"]
```

The `builtin-funding-mean-reversion` strategy requires `funding_zscore` — a feature that requires a populated funding rate history. `load_funding_like_series` always returns an empty frame (the actual Binance/Hyperliquid funding ingestion is not implemented). As a result:

- `funding_rate` is always `0.0` after `add_funding_features`
- `funding_zscore` is always `0.0` (or NaN)
- `entry_long` rule `funding_zscore < -2.0` **never triggers**
- `entry_short` rule `funding_zscore > 2.0` **never triggers**
- Total trades in backtests: **0**

This strategy silently appears to work (the backtest runs without error) but produces meaningless results.

**Fix — Implement Binance Funding Rate Ingestion:**

```python
async def fetch_binance_funding_history(symbol: str, start_ms: int, end_ms: int) -> list[dict]:
    url = f"{settings.binance_base_url}/fapi/v1/fundingRate"
    params = {"symbol": symbol, "startTime": start_ms, "endTime": end_ms, "limit": 1000}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=15.0)
        resp.raise_for_status()
        return resp.json()
```

### 2.3 `trend_signal` Feature Is Referenced But Never Computed 🔴

**File:** `backend/strategy/signals/momentum.py`, `backend/data/features.py` (missing)

The momentum strategy entry rules require `trend_signal`:

```python
RuleBlock(feature="trend_signal", operator="gt", threshold=0),
```

But `trend_signal` is not in the feature computation pipeline. The `evaluate_rule` function silently returns `False` for unknown features:

```python
def evaluate_rule(rule, features):
    if rule.feature not in features:
        return False  # ← silent failure, looks like "no signal"
```

The momentum strategy will only generate signals on the `ret_4` and `vol_ratio` conditions being met, then fail on `trend_signal`, meaning **the third condition always blocks entry**. Momentum strategy produces zero trades for the same reason.

**Fix:**

```python
# In features.py compute_features():
def compute_trend_signal(close: pd.Series, fast: int = 20, slow: int = 50) -> pd.Series:
    ema_fast = close.ewm(span=fast).mean()
    ema_slow = close.ewm(span=slow).mean()
    return np.sign(ema_fast - ema_slow)  # +1 uptrend, -1 downtrend
```

### 2.4 Backtest Engine Misses Position After Last Bar 🟠

**File:** `backend/backtest/engine.py`

```python
for row in frame.to_dict(orient="records"):
    ...
# After loop: open position is silently abandoned, not closed
```

If the final signal is `long` or `short` at the end of the backtest window, the open position is never closed and never added to `trades`. This understates trade count and can materially distort win-rate and profit-factor calculations for strategies with long hold periods.

**Fix:**

```python
# After the main loop, force-close any open position:
if current_side in {"long", "short"} and frame is not empty:
    last_price = float(frame.iloc[-1]["close"])
    last_ts = pd.Timestamp(frame.iloc[-1]["ts_open"]).to_pydatetime()
    # ... close position with last_price
```

### 2.5 Daily Loss Limit Uses UTC Midnight — Wrong for Crypto Markets 🟡

**File:** `backend/paper/runner.py`

```python
start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, ...).isoformat()
```

Crypto never closes; there is no canonical “day” reset. Using UTC midnight means the loss limit resets at different local times across time zones and does not align with funding windows (which reset at 00:00, 08:00, 16:00 UTC). This should be configurable with a `PAPER_DAY_RESET_HOUR_UTC` env var.

### 2.6 Unrealized PnL Does Not Account for Fees 🟡

**File:** `backend/paper/runner.py`

```python
unrealized = raw_pnl + float(position["accrued_funding_usd"])
```

Open position unrealized PnL does not deduct the opening fee. A position that is flat (price unchanged) shows `$0` PnL when it should show `-fee`. This makes paper trading appear slightly more profitable than reality.

-----

## Part 3 — Architecture & Reliability 🟠🟡

### 3.1 In-Process APScheduler Is Fragile in Multi-Worker Deployment

**File:** `backend/scheduler.py`, `docker-compose.yml`

The Docker Compose file runs both an `api` container and a `worker` container. The `api` container runs the scheduler on startup if `SCHEDULER_ENABLED=true`. But `docker-compose.yml` passes `SCHEDULER_ENABLED=true` only to the worker. However `backend/api/app.py` also calls `setup_scheduler()` if the flag is set — meaning in a misconfigured deployment, two scheduler instances can run simultaneously, causing duplicate bar processing and double-entry of paper trades.

**Fix:** The scheduler should run exclusively in the worker process. The API should never run the scheduler. Remove the `setup_scheduler()` call from `backend/api/app.py` startup.

### 3.2 SQLite Has No Connection Pooling or WAL Mode

**File:** `backend/data/storage.py`

Under concurrent requests (multiple browser tabs, automated tests, scheduler ticks), SQLite will produce `database is locked` errors. The meta database should use WAL mode:

```python
def get_sqlite():
    con = sqlite3.connect(str(META_DB), check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.row_factory = sqlite3.Row
    return con
```

Additionally, `get_sqlite()` creates a new connection on every call. A module-level connection pool (even a simple `threading.local()` cache) is needed.

### 3.3 No Retry Logic for External HTTP Calls

**File:** `backend/execution/adapters.py`, `backend/data/adapters/`

All HTTP calls use `httpx` with a single attempt. A transient network error during bar ingestion, live order submission, or funding rate fetch will propagate as an unhandled exception. For execution-critical paths, this is unacceptable.

**Fix:**

```python
import tenacity

@tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
    stop=tenacity.stop_after_attempt(3),
    reraise=True,
)
async def _fetch_with_retry(url, params):
    ...
```

### 3.4 `save_json_record` Is Not Atomic (TOCTOU Race) 🟡

**File:** `backend/data/storage.py`

The pattern `fetch_one(...) → INSERT or UPDATE` is a classic check-then-act race condition. Under concurrent scheduler ticks (which is likely), two bar-close handlers can both read “no record exists” and then both attempt an INSERT, causing a unique constraint violation or duplicate data.

**Fix:** Use `INSERT OR REPLACE INTO` (SQLite upsert) as a single atomic statement.

### 3.5 Worker Queue Has No Dead-Letter Queue or Retry Policy

**File:** `backend/worker/service.py`

A failed `execution_submit` job is marked `failed` and never retried. In live execution, a transient network error causes the order to be permanently abandoned with no alert. There is also no maximum retry count, no exponential backoff, and no alerting hook.

### 3.6 No Health Check for the Worker Process

The `docker-compose.yml` has a health check endpoint (`/health`) on the API but nothing monitoring the worker loop. If the worker crashes, jobs queue silently forever with no operator notification.

-----

## Part 4 — Missing Crypto-Critical Features

### 4.1 No Real-Time Price Feed (WebSocket) 🔴

The entire paper trading loop depends on `latest_feature_bar_async` which reads from stored bars. There is no live price feed. This means:

- Paper P&L is stale between bar closes (up to 15 minutes)
- No intrabar stop-loss execution
- No live mark-to-market
- No liquidation risk monitoring

**Required addition:** Binance USDS-M Futures WebSocket stream for mark price and book ticker, plus a Hyperliquid WebSocket for the same.

```python
# backend/data/streams/binance_ws.py
import websockets, json

async def stream_mark_prices(symbols: list[str], callback):
    streams = "/".join(f"{s.lower()}usdt@markPrice" for s in symbols)
    url = f"wss://fstream.binance.com/stream?streams={streams}"
    async with websockets.connect(url) as ws:
        async for msg in ws:
            data = json.loads(msg)
            await callback(data["data"])
```

### 4.2 Funding Rate Ingestion Is Entirely Missing

Binance perpetuals pay funding every 8 hours. Hyperliquid pays every hour. These rates directly affect PnL for any position held through a funding window. The backtest engine has `funding_included=True` in `BacktestConfig` but the funding values are never actually loaded.

**Required additions:**

1. `backend/data/adapters/binance_funding.py` — fetch `/fapi/v1/fundingRate` history
1. `backend/data/adapters/hyperliquid_funding.py` — fetch Hyperliquid funding history
1. Scheduler job to ingest funding every 8h for Binance, 1h for Hyperliquid
1. Storage schema for funding rate time-series in DuckDB

### 4.3 No Open Interest or Liquidation Data

Open Interest (OI) and liquidation cascade data are among the highest-signal features for crypto perpetuals:

- OI divergence from price = exhaustion signal
- Liquidation clusters = support/resistance levels
- Large liquidation events = volatility regime change trigger

Neither is ingested, stored, or used as a feature.

### 4.4 No Order Book Data (Market Microstructure Blind)

Bid-ask spread, order book imbalance, and large order detection are critical for:

- Realistic slippage modeling (current slippage is a flat BPS constant — wrong)
- Entry timing within bars
- Detecting manipulation ahead of large moves

### 4.5 Only Three Hard-Coded Strategies — No User-Defined Strategy DSL

The strategy engine is excellent (rule-based, declarative, serializable) but the three built-in strategies cover only a small portion of the strategy space. Users cannot define new strategies without writing Python. A web-based strategy builder should expose:

- Feature selector dropdowns
- Operator selector (gt, lt, between, crossover)
- Threshold inputs with live preview
- Hypothesis text field
- Save to registry button

### 4.6 No Walk-Forward Optimization Framework

Walk-forward optimization (WFO) is the industry standard for avoiding overfitting in systematic trading. The current sweep only runs in-sample across parameter grids. A proper WFO would:

1. Split data into N windows (train + test)
1. Optimize parameters on train
1. Evaluate on test
1. Concatenate test-period equity curves
1. Report stability score = mean(test_sharpe) / std(test_sharpe)

### 4.7 No Portfolio-Level Risk Management

Each strategy runs independently with its own position limits. There is no:

- Portfolio-level gross/net exposure cap
- Correlation check between open positions
- Portfolio VaR / CVaR calculation
- Drawdown-based position sizing adjustment
- Cross-strategy margin usage tracking

### 4.8 No Alerts or Notifications System

When a position is opened, closed, or a stop-loss fires, operators have no notification. This is the single most common operational failure in algo trading: the system is doing something unexpected and nobody knows.

**Minimum viable alerts:**

- Telegram bot webhook (easy to implement, widely used in crypto ops)
- Discord webhook
- Email via SMTP
- Configurable trigger conditions: daily_pnl, position_opened, kill_switch_fired, execution_blocked

### 4.9 No Stop-Loss or Take-Profit in Paper Trading

**File:** `backend/paper/runner.py`

The paper trading engine only closes positions on signal reversal. There are no:

- Fixed-percentage stop losses
- ATR-based trailing stops
- Time-based exits (max hold period)
- Take-profit targets

The `RiskLimits` dataclass has `stop_loss_atr_mult` and `take_profit_atr_mult` fields — these are defined but never evaluated anywhere. This is a dead code trap.

**Fix:** Add stop/TP evaluation in `run_bar()`:

```python
def _check_stop_take(position, current_price, spec) -> str | None:
    entry = float(position["entry_price"])
    pnl_pct = (current_price - entry) / entry
    if position["direction"] == "short":
        pnl_pct = -pnl_pct
    if spec.risk_limits.stop_loss_atr_mult:
        atr = current_bar.get("atr_14", 0)
        stop_dist = spec.risk_limits.stop_loss_atr_mult * atr / entry
        if pnl_pct <= -stop_dist:
            return "stop_loss"
    if spec.risk_limits.take_profit_atr_mult:
        atr = current_bar.get("atr_14", 0)
        tp_dist = spec.risk_limits.take_profit_atr_mult * atr / entry
        if pnl_pct >= tp_dist:
            return "take_profit"
    return None
```

### 4.10 Sizing Is Always Fixed Notional — Vol Targeting Not Implemented

The `SizingSpec` supports `vol_target` and `kelly_half` methods but both fall through to the `fixed_notional_usd` default in the paper runner:

```python
size_usd = spec.sizing.fixed_notional_usd or 1_000.0
```

Volatility-targeted sizing is critical for risk-adjusted returns and should be the default for professional use.

### 4.11 No Correlation Analysis Between Strategies

Running long BTC momentum and long ETH momentum simultaneously in the same market regime is effectively doubling concentrated directional exposure. There is no:

- Pairwise correlation of strategy returns
- Regime-conditional correlation computation
- Diversification benefit calculation
- Warning when adding a correlated strategy to the active set

### 4.12 No Monte Carlo / Synthetic Equity Curve Analysis

Beyond perturbation testing, professional quant shops run:

- Bootstrap resampling of trade PnL to compute equity curve confidence bands
- Worst-case scenario analysis (what if the 10 worst trades came consecutively?)
- Kelly criterion estimation from trade distribution
- Probability of ruin calculation

-----

## Part 5 — Feature Engineering Gaps

### 5.1 Missing ATR (Average True Range)

ATR is referenced in `RiskLimits.stop_loss_atr_mult` and `take_profit_atr_mult` but is not computed in `compute_features()`. It is also in `KNOWN_FEATURES` in the validator but returns `False` when evaluated.

### 5.2 Missing Features for Complete Coverage

Current computed features vs what’s declared in `KNOWN_FEATURES`:

|Feature         |Computed?|Notes              |
|----------------|---------|-------------------|
|`ret_1`         |✅        |1-bar return       |
|`ret_4`         |✅        |4-bar return       |
|`vol_20`        |✅        |Rolling vol        |
|`vol_ratio`     |✅        |Recent/baseline vol|
|`atr_14`        |❌        |**Missing**        |
|`rsi_14`        |✅        |RSI                |
|`pct_rank_20`   |✅        |Price rank         |
|`trend_signal`  |❌        |**Missing**        |
|`funding_rate`  |❌        |**No data source** |
|`funding_zscore`|❌        |**No data source** |
|`close`         |✅        |Pass-through       |
|`volume_quote`  |✅        |Pass-through       |

### 5.3 No Cross-Asset Features

BTC dominance, BTC/ETH ratio, and correlation to SPX/Gold are among the strongest regime filters for altcoin strategies. None are implemented.

### 5.4 On-Chain Features Not Considered

Exchange net flow, whale wallet activity, and miner outflows are now available via APIs (Glassnode, CryptoQuant, Nansen). These are alpha sources unavailable to most retail traders and particularly valuable for mean-reversion strategies.

-----

## Part 6 — Frontend / UX Issues

### 6.1 No Real-Time Updates — Everything Is Stale

The frontend uses `useQuery` with default settings (no `refetchInterval`). Once loaded, data does not update. A paper trading dashboard that shows stale positions is operationally dangerous.

**Fix:** Add polling intervals to critical queries:

```typescript
const query = useQuery({
  queryKey: ["paper-portfolio"],
  queryFn: ...,
  refetchInterval: 10_000, // 10 seconds
  refetchIntervalInBackground: true,
});
```

Or implement a WebSocket connection to the backend for push updates.

### 6.2 No Error Boundaries — Any API Failure Crashes the Full Page

If the API returns an error, `useQuery` surfaces it but there are no `ErrorBoundary` components wrapping page-level sections. A single failing endpoint breaks the entire view.

### 6.3 No Loading Skeletons — Flash of Empty Tables

All tables render empty initially while data loads. Users see empty tables before data appears, which feels broken.

### 6.4 Backtest Equity Curve Uses Raw Dates — Unreadable X-Axis

```tsx
<XAxis dataKey="ts" hide />
```

The X-axis is hidden entirely. A chart without a time axis loses its primary context for a time-series.

### 6.5 No Strategy Performance Comparison Chart

There is no chart that plots the equity curves of multiple strategies overlaid, which is the primary tool for strategy selection.

### 6.6 Frontend Has No Dark Mode

The body background is dark (`#08111f`) but the main content panels are `rgba(255,255,255,0.94)` — effectively white. This creates a jarring contrast and makes the app unsuitable for extended use at night (when most crypto traders are active).

### 6.7 No Keyboard Shortcuts for Power Users

Running a backtest, approving a ticket, and triggering a paper cycle are all mouse-only interactions. Power users need keyboard shortcuts.

-----

## Part 7 — Observability & Operations Gaps

### 7.1 No Structured Logging to File or Aggregator

`structlog` is imported and configured but logs only go to stdout. In production (Docker), logs need to be:

- Persisted to rotating files
- Forwarded to a log aggregator (Loki, Datadog, etc.)
- Correlated with trace IDs across the request lifecycle

### 7.2 No Metrics Endpoint (Prometheus)

There is no `/metrics` endpoint exposing:

- Trade count per strategy per hour
- Bar processing latency
- API request latency by endpoint
- Queue depth
- Open position count
- Daily PnL

Without this, you are flying blind in production.

### 7.3 No Alerting on System Health Degradation

If bar ingestion starts failing (exchange API down), the system silently serves stale data. There is no health degradation alert, no circuit breaker, and no fallback.

### 7.4 No Backup Strategy for SQLite / DuckDB

Both databases are mounted as Docker volumes. There is no automated backup, no point-in-time recovery, and no integrity check job. One Docker volume corruption event loses all trade history.

### 7.5 No API Documentation / OpenAPI Enrichment

FastAPI auto-generates OpenAPI docs but none of the endpoints have docstrings, response models, or example payloads. The `/docs` endpoint is effectively useless as-is.

-----

## Part 8 — Test Coverage Gaps

### 8.1 No Test for the Paper Runner Full Cycle (Signal → Order → Fill → Position)

`test_paper_runner.py` only tests the risk-block path. There is no test that verifies:

- A valid signal with sufficient volume opens a position
- A signal reversal closes the position
- PnL is correctly calculated

### 8.2 Perturbation and OOS Sharpe Are Never Tested

Given that both are synthetic (bugs documented in Part 2), there is no test that would catch if they became genuinely wrong.

### 8.3 No Integration Test for the Full Backtest → Promote → Paper Pipeline

The most important user journey — run backtest, pass promotion, enable paper trading, receive paper trade — has no end-to-end test.

### 8.4 No Test for HMAC Signing Logic

The Binance adapter signing logic is never tested. A bug here in live mode would cause all orders to fail with `401 Invalid signature`.

-----

## Part 9 — Full Feature Roadmap

Prioritized by value-to-effort ratio:

### Sprint 1 — Fix Critical Correctness Bugs (1–2 days)

1. Implement real perturbation Sharpe (noise injection loop)
1. Implement real walk-forward OOS Sharpe
1. Implement `trend_signal` feature computation (EMA crossover)
1. Fix end-of-backtest open position not being closed
1. Implement Binance funding rate ingestion
1. Implement `atr_14` feature computation

### Sprint 2 — Security Hardening (1 day)

1. Rotate vault passphrase and auth tokens
1. Generate random tokens in bootstrap script
1. Add rate limiting middleware
1. Fix HMAC call to use `hmac.HMAC`
1. SQLite WAL mode + module-level connection cache
1. Add pre-commit hook for secret scanning

### Sprint 3 — Stop-Loss / Take-Profit / Alerts (2–3 days)

1. Implement stop-loss and take-profit execution in paper runner
1. Implement vol-targeted position sizing
1. Telegram/Discord webhook notifications
1. Alert triggers: position opened/closed, daily loss limit, kill switch

### Sprint 4 — Real-Time Infrastructure (3–5 days)

1. Binance WebSocket mark price stream
1. Hyperliquid WebSocket stream
1. Live P&L mark-to-market every 5 seconds
1. Frontend polling or WebSocket connection for live data

### Sprint 5 — Advanced Backtesting (3–5 days)

1. Proper walk-forward optimization framework
1. Monte Carlo trade resampling
1. Portfolio-level backtest (multiple strategies simultaneously)
1. Realistic slippage model (volume-proportional)
1. Funding payment simulation in backtest

### Sprint 6 — Open Interest & Liquidation Data (2–3 days)

1. Binance `/fapi/v1/openInterest` history ingestion
1. Binance `/futures/data/takerBuySellVol` ingestion
1. `oi_change_pct`, `buy_sell_ratio`, `liquidation_intensity` features
1. Strategy builder: expose new features in UI

### Sprint 7 — Strategy Builder UI (3–5 days)

1. Web-based rule builder (drag-and-drop RuleBlocks)
1. Live feature preview on latest bar
1. Strategy hypothesis text field with AI-assist via existing OpenRouter integration
1. One-click backtest from builder

### Sprint 8 — Observability (1–2 days)

1. Prometheus `/metrics` endpoint
1. Structured log forwarding configuration
1. SQLite/DuckDB automated backup job
1. Grafana dashboard template (backtest KPIs, paper PnL, system health)

### Sprint 9 — Correlation & Portfolio Risk (2–3 days)

1. Pairwise strategy return correlation matrix
1. Portfolio VaR/CVaR using historical simulation
1. Position sizing Kelly fraction calculator
1. Probability of ruin estimation
1. Cross-strategy exposure cap enforcement

### Sprint 10 — Market Research Agent Enhancement (2 days)

1. Connect market structure analysis to live feature data (currently takes a `feature_summary` dict but no caller populates it from live data)
1. Scheduled daily research digest
1. Catalyst agent wired to news API (Cryptopanic or TheBlock)
1. Risk review agent triggered before any promotion approval

-----

## Part 10 — Quick-Win Code Improvements

### 10.1 Strategy Registry Should Not Re-Bootstrap on Every List Call

```python
# registry.py — called on every GET /strategies
def list_specs() -> list[dict]:
    bootstrap_builtin_specs()  # ← DB write on every read request
```

Move `bootstrap_builtin_specs()` to the startup event only.

### 10.2 `dataclass_to_dict` Recursion Is Fragile with Nested Tuples

The equity curve is a `list[tuple[datetime, float]]`. After `dataclass_to_dict`, it becomes a `list[list]`. The frontend types this as `Array<[string, number]>` — this works but is fragile. Define an explicit `EquityPoint` dataclass.

### 10.3 `fetch_all` with No Parameters Passes `[]` Silently

```python
def fetch_all(query: str, params: list | None = None) -> list:
    ...
    con.execute(query, params or [])
```

This hides parameter omission bugs. Make `params` required.

### 10.4 Approval Route Hardcodes `'operator'` as `approved_by`

```python
# approvals.py
con.execute("UPDATE ... SET approved_by='operator' ...")
```

Should use the authenticated user’s `display_name` from the `Depends(require_role("admin"))` dependency, which is already available.

### 10.5 `run_bar` Import Is Inside a Function Body

```python
# paper/runner.py
from backend.paper.broker import update_unrealized_pnl  # ← inside loop!
```

This import runs on every bar for every open position. Move it to module level.

### 10.6 `compare_runs` Catches HTTPException but Silently Discards Errors

```python
except HTTPException:
    comparisons.append({..., "sharpe": None, ...})
```

Non-HTTP exceptions (e.g., `DuckDBException`, `OSError`) are not caught and will abort the entire compare run. Catch `Exception` and log the error.

-----

## Part 11 — Schema Improvements

### 11.1 Missing Indexes on Foreign Keys and Common Query Patterns

The SQLite meta database has no explicit indexes beyond primary keys. Every `fetch_all` with a `WHERE spec_id=?` clause does a full table scan.

**Required indexes:**

```sql
CREATE INDEX IF NOT EXISTS idx_paper_positions_spec_id ON paper_positions(spec_id);
CREATE INDEX IF NOT EXISTS idx_paper_positions_closed ON paper_positions(closed_at);
CREATE INDEX IF NOT EXISTS idx_paper_orders_spec ON paper_orders(spec_id);
CREATE INDEX IF NOT EXISTS idx_strategy_targets_spec ON strategy_targets(spec_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_job_queue_status ON job_queue(status, priority, created_at);
```

### 11.2 No Schema Migration System

As the schema evolves, there is no migration system. Adding a column requires manual SQL or dropping the database. Use `yoyo-migrations` or a simple versioned migration runner.

### 11.3 `paper_positions` Has No `close_price` Column in Schema

The broker calls `con.execute("UPDATE paper_positions SET close_price=? ...")` but `close_price` is not in the CREATE TABLE statement. This will silently fail on fresh databases.

-----

## Summary Scorecard

|Dimension           |Current State                                          |Target State|
|--------------------|-------------------------------------------------------|------------|
|Security            |3/10 — secrets in repo, weak tokens, no rate limiting  |8/10        |
|Correctness         |4/10 — 3 strategies produce zero trades, OOS is fake   |9/10        |
|Reliability         |5/10 — no retry, no WAL, race conditions               |8/10        |
|Feature Completeness|4/10 — no real-time, no stops, no funding data         |8/10        |
|Observability       |3/10 — no metrics, no alerts, no backups               |7/10        |
|Test Coverage       |5/10 — happy paths covered, critical paths missing     |8/10        |
|Frontend UX         |5/10 — functional but stale, no dark mode, no real-time|7/10        |
|**Overall**         |**4.1/10**                                             |**8/10**    |

-----

## Immediate Action Items (Do These First)

1. **Rotate** `VAULT_PASSPHRASE` and all auth tokens right now — they are in git history
1. **Fix** perturbation + OOS Sharpe computation — the promotion gate is currently meaningless
1. **Implement** `trend_signal` and `atr_14` features — two of three strategies produce zero trades
1. **Implement** Binance funding rate ingestion — funding mean-reversion strategy is completely broken
1. **Add** SQLite WAL mode — concurrent access will cause lock errors in production
1. **Fix** the in-loop import in `paper/runner.py` — it’s a performance bug that fires on every bar
1. **Add** stop-loss execution to paper runner — running without stops is not serious algo trading
1. **Add** `refetchInterval` to paper portfolio query — stale positions are an operational hazard

-----

*This review was conducted against codebase version 0.1.0. The architecture and vision are sound — the gaps are implementation-level, not conceptual. With the corrections above, this system can become a genuinely powerful and trustworthy crypto research and paper trading platform.*
```

## `.github/workflows/secret-scan.yml`

```yaml
name: Secret Scan

on:
  pull_request:
  push:
    branches:
      - main
      - master

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Run repository secret scan
        run: python scripts/scan_secrets.py

```

## `backend/scheduler.py`

```python
from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import structlog

from backend.core.config import settings
from backend.core.types import Timeframe
from backend.data.service import (
    default_instruments,
    ingest_defaults,
    ingest_funding_defaults,
    ingest_mark_price,
    ingest_market_context_defaults,
    latest_feature_bar_async,
    mark_processed,
    refresh_health,
    should_process_bar,
)
from backend.data.streams import binance_ws, hyperliquid_ws
from backend.ops.alerts import notify_event
from backend.ops.backup import backup_datastores
from backend.ops.readiness import readiness_snapshot
from backend.research.service import research_digest
from backend.worker.service import process_next_job
from backend.paper.runner import run_bar

log = structlog.get_logger()
scheduler = AsyncIOScheduler()
_stream_tasks: list[asyncio.Task] = []


async def on_15m_bar_close() -> None:
    log.info("15m bar close tick")
    await ingest_defaults(lookback_days=3)
    processed = 0
    for instrument in default_instruments():
        for timeframe in (Timeframe.M15, Timeframe.H1, Timeframe.H4):
            bar = await latest_feature_bar_async(instrument, timeframe)
            if not bar:
                continue
            job_name = f"paper:{instrument.key}:{timeframe.value}"
            if should_process_bar(job_name, bar["ts"]):
                run_bar(bar)
                mark_processed(job_name, bar["ts"])
                processed += 1
    log.info("paper cycle finished", processed=processed)


async def run_quality_checks() -> None:
    log.info("quality check tick")
    snapshot = refresh_health()
    issues = [row for row in snapshot if row["quality"] != "healthy"]
    if issues:
        notify_event("health_degraded", "Dataset health degraded", {"issues": issues[:10], "issue_count": len(issues)})
    readiness = readiness_snapshot()
    if readiness["summary"]["blockers"]:
        notify_event(
            "health_degraded",
            "Readiness blockers detected",
            {"blockers": readiness["summary"]["blockers"][:10], "generated_at": readiness["generated_at"]},
        )


async def repair_gaps() -> None:
    log.info("gap repair tick")
    await ingest_defaults(lookback_days=10)


async def process_worker_queue() -> None:
    log.info("worker queue tick")
    processed = 0
    while True:
        job = process_next_job()
        if job is None:
            break
        processed += 1
    log.info("worker queue finished", processed=processed)


def run_backup() -> None:
    summary = backup_datastores()
    log.info("backup completed", **summary)


async def mark_to_market_refresh() -> None:
    # Keep unrealized PnL fresh even if streams are disabled or disconnected.
    instruments = default_instruments()
    for inst in instruments:
        bar = await latest_feature_bar_async(inst, Timeframe.M15, lookback_bars=50)
        if not bar:
            continue
        ingest_mark_price(inst.venue.value, inst.symbol, float(bar["close"]))


async def ingest_funding_updates() -> None:
    summaries = await ingest_funding_defaults(lookback_days=3)
    log.info("funding ingestion tick", updated=len(summaries))


async def ingest_market_context_updates() -> None:
    summaries = await ingest_market_context_defaults(lookback_days=7)
    log.info("market context ingestion tick", updated=len(summaries))


async def run_research_digest() -> None:
    digest = await research_digest()
    log.info("research digest", analysis=digest.get("analysis", {}))


async def _stream_loop(venue: str, symbols: list[str]) -> None:
    async def callback(payload: dict) -> None:
        ingest_mark_price(payload["venue"], payload["symbol"], float(payload["price"]), payload.get("ts"))

    while True:
        try:
            if venue == "binance":
                await binance_ws.stream_mark_prices(symbols, callback)
            else:
                await hyperliquid_ws.stream_mark_prices(symbols, callback)
        except Exception as exc:  # pragma: no cover - network runtime
            log.warning("market stream disconnected", venue=venue, error=str(exc))
            await asyncio.sleep(2)


def _ensure_stream_tasks() -> None:
    if not settings.market_streams_enabled:
        return
    if _stream_tasks:
        return
    symbols = sorted({inst.symbol for inst in default_instruments()})
    _stream_tasks.append(asyncio.create_task(_stream_loop("binance", symbols)))
    _stream_tasks.append(asyncio.create_task(_stream_loop("hyperliquid", symbols)))
    log.info("market streams started", symbols=symbols)


def setup_scheduler() -> AsyncIOScheduler:
    if scheduler.running:
        return scheduler
    scheduler.add_job(on_15m_bar_close, CronTrigger(minute="1,16,31,46"), id="bar_15m", replace_existing=True)
    scheduler.add_job(run_quality_checks, CronTrigger(minute=5), id="quality_check", replace_existing=True)
    scheduler.add_job(repair_gaps, CronTrigger(hour="0,4,8,12,16,20", minute=10), id="gap_repair", replace_existing=True)
    scheduler.add_job(process_worker_queue, CronTrigger(minute="*/2"), id="worker_queue", replace_existing=True)
    scheduler.add_job(run_backup, CronTrigger(hour=0, minute=30), id="backup_job", replace_existing=True)
    scheduler.add_job(mark_to_market_refresh, IntervalTrigger(seconds=5), id="mark_to_market_refresh", replace_existing=True)
    scheduler.add_job(ingest_funding_updates, CronTrigger(minute=7), id="funding_hourly", replace_existing=True)
    scheduler.add_job(ingest_market_context_updates, CronTrigger(minute=9), id="market_context_hourly", replace_existing=True)
    scheduler.add_job(run_research_digest, CronTrigger(hour=9, minute=0), id="research_digest", replace_existing=True)
    scheduler.start()
    _ensure_stream_tasks()
    return scheduler

```

## `backend/__init__.py`

```python
"""Workbench backend package."""

```

## `backend/api/app.py`

```python
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.api.rate_limit import enforce_rate_limit
from backend.api.routes import approvals, auth, backtests, data, execution, ops, paper, strategies, vault
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


@app.get("/health", response_model=HealthResponse, summary="Service health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics", summary="Prometheus metrics")
async def metrics() -> Response:
    payload, content_type = prometheus_payload()
    return Response(content=payload, media_type=content_type)

```

## `backend/api/rate_limit.py`

```python
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_LOCK = Lock()


def _check_limit(key: str, limit: int, window_seconds: int) -> None:
    now = time.time()
    cutoff = now - window_seconds
    with _LOCK:
        bucket = _WINDOWS[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"rate_limit_exceeded:{limit}/{window_seconds}s",
            )
        bucket.append(now)


def enforce_rate_limit(request: Request, bucket: str, limit: int, window_seconds: int = 60) -> None:
    client_ip = request.client.host if request.client else "unknown"
    key = f"{bucket}:{client_ip}"
    _check_limit(key, limit=limit, window_seconds=window_seconds)

```

## `backend/api/schemas.py`

```python
from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class UserPublicResponse(BaseModel):
    user_id: str
    display_name: str
    role: str
    created_at: str


class LogoutResponse(BaseModel):
    ok: bool


class DatasetHealthRow(BaseModel):
    instrument_key: str
    timeframe: str
    quality: str
    last_bar_ts: str | None = None
    gap_count: int
    duplicate_count: int
    coverage_days: float
    checked_at: str


class BarIngestSummaryResponse(BaseModel):
    instrument_key: str
    timeframe: str
    rows_written: int
    start: str
    end: str
    quality: str


class FundingIngestSummaryResponse(BaseModel):
    instrument_key: str
    rows_written: int
    start: str
    end: str


class MarketContextIngestSummaryResponse(BaseModel):
    instrument_key: str
    start: str
    end: str
    rows: dict[str, int]


class MarketMarkResponse(BaseModel):
    instrument_key: str
    symbol: str
    venue: str
    price: float
    ts: str

```

## `backend/api/__init__.py`

```python
"""FastAPI application package."""

```

## `backend/api/routes/approvals.py`

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.service import require_role
from backend.data.storage import fetch_all, fetch_one, get_sqlite
from backend.ops.readiness import readiness_snapshot

router = APIRouter()


@router.get("")
def list_approvals() -> list[dict]:
    rows = fetch_all("SELECT * FROM promotion_decisions ORDER BY decided_at DESC", [])
    return [dict(row) for row in rows]


@router.post("/{decision_id}/approve")
def approve(decision_id: str, user: dict = Depends(require_role("admin"))) -> dict:
    row = fetch_one("SELECT * FROM promotion_decisions WHERE decision_id=?", [decision_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    readiness = readiness_snapshot()
    if not readiness["summary"]["paper_ready"]:
        raise HTTPException(status_code=409, detail="risk_review_blocked:paper_not_ready")
    con = get_sqlite()
    con.execute(
        """
        UPDATE promotion_decisions
        SET passed=1, approved_by=?
        WHERE decision_id=?
        """,
        [user["display_name"], decision_id],
    )
    con.execute(
        """
        UPDATE strategy_specs
        SET status='promoted'
        WHERE spec_id=?
        """,
        [row["spec_id"]],
    )
    con.commit()
    return {"ok": True, "decision_id": decision_id}

```

## `backend/api/routes/auth.py`

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.api.rate_limit import enforce_rate_limit
from backend.api.schemas import LogoutResponse, UserPublicResponse
from backend.auth.service import current_user, get_user_by_token, list_users, public_user, require_role
from backend.core.config import settings

router = APIRouter()


@router.get("/session", response_model=UserPublicResponse, summary="Current authenticated user")
def session(user: dict = Depends(current_user)) -> dict:
    return public_user(user)


@router.get("/users", response_model=list[UserPublicResponse], summary="List configured users")
def users(user: dict = Depends(require_role("admin"))) -> list[dict]:
    return list_users()


@router.post(
    "/login",
    response_model=UserPublicResponse,
    summary="Authenticate by role",
    description="Sets a secure HTTP-only auth cookie and returns the user profile.",
)
def login(payload: dict, response: Response) -> dict:
    role = payload.get("role", "operator")
    user = next((item for item in list_users(include_tokens=True) if item["role"] == role), None)
    if user is None:
        raise HTTPException(status_code=404, detail="role_not_found")
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=user["token"],
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_cookie_max_age_seconds,
    )
    return public_user(user)


@router.post(
    "/token",
    response_model=UserPublicResponse,
    summary="Authenticate by token",
    description="Validates a token and sets an HTTP-only auth cookie.",
)
def token_session(payload: dict, request: Request, response: Response) -> dict:
    enforce_rate_limit(
        request,
        bucket="auth_token",
        limit=settings.api_rate_limit_auth_token_per_minute,
        window_seconds=60,
    )
    user = get_user_by_token(payload.get("token"))
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=user["token"],
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_cookie_max_age_seconds,
    )
    return public_user(user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Clear auth session",
    description="Clears the HTTP-only auth cookie.",
)
def logout(response: Response) -> dict:
    response.delete_cookie(key=settings.auth_cookie_name)
    return {"ok": True}

```

## `backend/api/routes/backtests.py`

```python
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from backend.backtest.service import compare_runs, correlation_for_spec, execute_backtest, monte_carlo_for_run, sweep_runs, walk_forward
from backend.auth.service import require_role
from backend.data.storage import fetch_all, fetch_one, save_json_record
from backend.ops.audit import record_audit_event
from backend.strategy.targets import sync_target_with_backtest

router = APIRouter()


@router.get("")
def list_backtests() -> list[dict]:
    rows = fetch_all("SELECT * FROM backtest_runs ORDER BY ran_at DESC", [])
    return [
        {
            "run_id": row["run_id"],
            "spec_id": row["spec_id"],
            "config": json.loads(row["config_json"]),
            "result": json.loads(row["result_json"]),
            "ran_at": row["ran_at"],
        }
        for row in rows
    ]


@router.post("")
def create_backtest(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    spec_id = payload["spec_id"]
    target = None
    result, decision = execute_backtest(
        spec_id=spec_id,
        symbol=payload.get("symbol"),
        venue=payload.get("venue"),
        lookback_days=payload.get("lookback_days", 120),
    )
    save_json_record(
        "backtest_runs",
        {
            "run_id": result["run_id"],
            "spec_id": result["spec_id"],
            "config_json": json.dumps(result["config"]),
            "result_json": json.dumps(result),
            "ran_at": result["ran_at"],
        },
        "run_id",
    )
    save_json_record(
        "promotion_decisions",
        {
            "decision_id": f"{result['run_id']}:auto",
            "spec_id": result["spec_id"],
            "run_id": result["run_id"],
            "policy_json": json.dumps(decision["policy"]),
            "passed": 1 if decision["passed"] else 0,
            "failures_json": json.dumps(decision["failures"]),
            "decided_at": decision["decided_at"],
            "approved_by": decision["approved_by"],
        },
        "decision_id",
    )
    if payload.get("symbol") and payload.get("venue"):
        target = sync_target_with_backtest(
            spec_id=spec_id,
            symbol=payload["symbol"],
            venue=payload["venue"],
            result=result,
            decision=decision,
        )
    record_audit_event(
        event_type="backtest.completed",
        entity_type="backtest_run",
        entity_id=result["run_id"],
        payload={
            "spec_id": result["spec_id"],
            "instrument": result["config"].get("instrument"),
            "sharpe": result["sharpe"],
            "total_return_pct": result["total_return_pct"],
            "total_trades": result["total_trades"],
            "promotion_passed": decision["passed"],
            "target_status": target["status"] if target else None,
        },
    )
    return {"result": result, "promotion": decision, "target": target}


@router.post("/compare")
def compare_backtests(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    spec_id = payload["spec_id"]
    lookback_days = payload.get("lookback_days", 180)
    return {"comparisons": compare_runs(spec_id, lookback_days)}


@router.post("/sweep")
def sweep_backtests(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    spec_id = payload["spec_id"]
    lookback_days = payload.get("lookback_days", 180)
    return {
        "results": sweep_runs(
            spec_id=spec_id,
            symbol=payload.get("symbol"),
            venue=payload.get("venue"),
            lookback_days=lookback_days,
        )
    }


@router.post("/walk-forward")
def walk_forward_backtest(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    return {
        "analysis": walk_forward(
            spec_id=payload["spec_id"],
            symbol=payload.get("symbol"),
            venue=payload.get("venue"),
            lookback_days=payload.get("lookback_days", 180),
            windows=payload.get("windows", 4),
        )
    }


@router.get("/{run_id}/monte-carlo")
def monte_carlo(run_id: str, simulations: int = 500) -> dict:
    return {"run_id": run_id, "analysis": monte_carlo_for_run(run_id, simulations=simulations)}


@router.post("/correlation")
def correlation(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    return {
        "analysis": correlation_for_spec(
            spec_id=payload["spec_id"],
            lookback_days=payload.get("lookback_days", 120),
        )
    }


@router.get("/{run_id}")
def get_backtest(run_id: str) -> dict:
    row = fetch_one("SELECT * FROM backtest_runs WHERE run_id=?", [run_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return {
        "run_id": row["run_id"],
        "spec_id": row["spec_id"],
        "config": json.loads(row["config_json"]),
        "result": json.loads(row["result_json"]),
        "ran_at": row["ran_at"],
    }


@router.get("/{run_id}/equity")
def get_equity(run_id: str) -> dict:
    row = fetch_one("SELECT result_json FROM backtest_runs WHERE run_id=?", [run_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    result = json.loads(row["result_json"])
    return {"run_id": run_id, "equity_curve": result.get("equity_curve", [])}

```

## `backend/api/routes/data.py`

```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.schemas import (
    BarIngestSummaryResponse,
    DatasetHealthRow,
    FundingIngestSummaryResponse,
    MarketContextIngestSummaryResponse,
    MarketMarkResponse,
)
from backend.auth.service import require_role
from backend.data.service import (
    ingest_defaults,
    ingest_funding_defaults,
    ingest_market_context_defaults,
    refresh_health as refresh_health_service,
)
from backend.data.storage import fetch_all
from backend.ops.audit import record_audit_event

router = APIRouter()


@router.get("/health", response_model=list[DatasetHealthRow], summary="Dataset health snapshot")
def list_health() -> list[dict]:
    rows = fetch_all("SELECT * FROM dataset_health ORDER BY instrument_key, timeframe", [])
    return [dict(row) for row in rows]


@router.post("/refresh-health", response_model=list[DatasetHealthRow], summary="Run and persist health checks")
def refresh_health(user: dict = Depends(require_role("operator"))) -> list[dict]:
    result = refresh_health_service()
    record_audit_event(
        event_type="data.health_refreshed",
        entity_type="dataset_health",
        entity_id="defaults",
        payload={"rows": len(result)},
    )
    return result


@router.post("/ingest", response_model=list[BarIngestSummaryResponse], summary="Ingest default OHLCV bars")
async def ingest(payload: dict | None = None, user: dict = Depends(require_role("operator"))) -> list[dict]:
    lookback_days = (payload or {}).get("lookback_days", 30)
    result = await ingest_defaults(lookback_days=lookback_days)
    record_audit_event(
        event_type="data.ingested",
        entity_type="dataset_batch",
        entity_id=f"defaults:{lookback_days}",
        payload={"lookback_days": lookback_days, "rows": len(result)},
    )
    return result


@router.post("/funding/ingest", response_model=list[FundingIngestSummaryResponse], summary="Ingest funding rates")
async def ingest_funding(payload: dict | None = None, user: dict = Depends(require_role("operator"))) -> list[dict]:
    lookback_days = (payload or {}).get("lookback_days", 14)
    result = await ingest_funding_defaults(lookback_days=lookback_days)
    record_audit_event(
        event_type="data.funding_ingested",
        entity_type="funding_batch",
        entity_id=f"defaults:{lookback_days}",
        payload={"lookback_days": lookback_days, "rows": len(result)},
    )
    return result


@router.post(
    "/market-context/ingest",
    response_model=list[MarketContextIngestSummaryResponse],
    summary="Ingest market context (OI, taker flow, liquidations)",
)
async def ingest_market_context(payload: dict | None = None, user: dict = Depends(require_role("operator"))) -> list[dict]:
    lookback_days = (payload or {}).get("lookback_days", 14)
    result = await ingest_market_context_defaults(lookback_days=lookback_days)
    record_audit_event(
        event_type="data.market_context_ingested",
        entity_type="market_context_batch",
        entity_id=f"defaults:{lookback_days}",
        payload={"lookback_days": lookback_days, "rows": len(result)},
    )
    return result


@router.get("/marks", response_model=list[MarketMarkResponse], summary="Latest mark prices")
def latest_marks(limit: int = 50, user: dict = Depends(require_role("operator"))) -> list[dict]:
    rows = fetch_all("SELECT * FROM market_marks ORDER BY ts DESC LIMIT ?", [int(limit)])
    return [dict(row) for row in rows]

```

## `backend/api/routes/execution.py`

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.api.rate_limit import enforce_rate_limit
from backend.auth.service import require_role
from backend.core.config import settings
from backend.execution.service import (
    approve_execution_ticket,
    create_execution_ticket,
    list_execution_tickets,
    list_reconciliation,
    live_secrets_status,
    reconcile_venue,
    reject_execution_ticket,
)
from backend.worker.jobs import list_dead_letters, list_jobs
from backend.worker.service import job_metrics, process_next_job

router = APIRouter()


@router.get("/tickets")
def tickets(limit: int = 100) -> list[dict]:
    return list_execution_tickets(limit=limit)


@router.post("/tickets")
def create_ticket(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    return create_execution_ticket(
        spec_id=payload["spec_id"],
        symbol=payload["symbol"],
        venue=payload["venue"],
        direction=payload["direction"],
        action=payload.get("action", "open"),
        size_usd=float(payload.get("size_usd", 1000.0)),
        requested_by=payload.get("requested_by", user["display_name"]),
        rationale=payload.get("rationale"),
    )


@router.post("/tickets/{ticket_id}/approve", summary="Approve execution ticket")
def approve_ticket(
    ticket_id: str,
    request: Request,
    payload: dict | None = None,
    user: dict = Depends(require_role("admin")),
) -> dict:
    enforce_rate_limit(
        request,
        bucket="execution_ticket_approve",
        limit=settings.api_rate_limit_ticket_approve_per_minute,
        window_seconds=60,
    )
    approved_by = (payload or {}).get("approved_by", user["display_name"])
    return approve_execution_ticket(ticket_id, approved_by=approved_by)


@router.post("/tickets/{ticket_id}/reject", summary="Reject execution ticket")
def reject_ticket(
    ticket_id: str,
    request: Request,
    payload: dict | None = None,
    user: dict = Depends(require_role("admin")),
) -> dict:
    enforce_rate_limit(
        request,
        bucket="execution_ticket_reject",
        limit=settings.api_rate_limit_ticket_approve_per_minute,
        window_seconds=60,
    )
    reason = (payload or {}).get("reason", "operator_rejected")
    rejected_by = (payload or {}).get("rejected_by", user["display_name"])
    return reject_execution_ticket(ticket_id, reason=reason, rejected_by=rejected_by)


@router.get("/secrets")
def secrets() -> dict:
    return live_secrets_status()


@router.get("/reconciliation")
def reconciliation(limit: int = 50) -> list[dict]:
    return list_reconciliation(limit=limit)


@router.post("/reconciliation/run")
def run_reconciliation(payload: dict | None = None, user: dict = Depends(require_role("operator"))) -> dict:
    venue = (payload or {}).get("venue", "binance")
    return reconcile_venue(venue)


@router.get("/jobs")
def jobs(limit: int = 100) -> list[dict]:
    return list_jobs(limit=limit)


@router.get("/jobs/dead-letters")
def dead_letters(limit: int = 100) -> list[dict]:
    return list_dead_letters(limit=limit)


@router.get("/jobs/metrics")
def metrics() -> dict:
    return job_metrics()


@router.post("/jobs/process")
def process_job(payload: dict | None = None, user: dict = Depends(require_role("admin"))) -> dict:
    job_type = (payload or {}).get("job_type")
    result = process_next_job(job_type=job_type)
    return {"job": result}

```

## `backend/api/routes/ops.py`

```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth.service import require_role
from backend.ops.audit import list_audit_events, list_paper_cycle_events
from backend.ops.backup import backup_datastores
from backend.ops.readiness import readiness_snapshot
from backend.research.service import research_digest
from backend.worker.service import worker_health

router = APIRouter()


@router.get("/readiness")
def readiness() -> dict:
    return readiness_snapshot()


@router.get("/audit")
def audit(limit: int = 50, user: dict = Depends(require_role("operator"))) -> list[dict]:
    return list_audit_events(limit=limit)


@router.get("/paper-events")
def paper_events(limit: int = 100, user: dict = Depends(require_role("operator"))) -> list[dict]:
    return list_paper_cycle_events(limit=limit)


@router.get("/worker-health")
def worker_status(user: dict = Depends(require_role("operator"))) -> dict:
    return worker_health()


@router.post("/backup")
def create_backup(user: dict = Depends(require_role("admin"))) -> dict:
    return backup_datastores()


@router.get("/research-digest")
async def get_research_digest(user: dict = Depends(require_role("operator"))) -> dict:
    return await research_digest()

```

## `backend/api/routes/paper.py`

```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth.service import require_role
from backend.core.types import Timeframe
from backend.data.service import default_instruments, latest_feature_bar_async, mark_processed, should_process_bar
from backend.data.storage import get_sqlite
from backend.ops.alerts import notify_event
from backend.ops.audit import record_audit_event
from backend.paper.activity import list_recent_orders, portfolio_snapshot
from backend.paper.runner import run_bar

router = APIRouter()


@router.get("/portfolio")
def portfolio() -> dict:
    return portfolio_snapshot()


@router.get("/orders")
def orders() -> list[dict]:
    return list_recent_orders(limit=100)


@router.post("/kill")
def kill_switch(user: dict = Depends(require_role("admin"))) -> dict:
    con = get_sqlite()
    updated = con.execute(
        """
        UPDATE paper_positions
        SET closed_at=datetime('now'), realized_pnl_usd=COALESCE(realized_pnl_usd, 0)
        WHERE closed_at IS NULL
        """
    ).rowcount
    con.commit()
    record_audit_event(
        event_type="paper.kill_switch",
        entity_type="paper_portfolio",
        entity_id="global",
        payload={"closed_positions": updated},
    )
    notify_event("kill_switch_fired", "Paper kill switch triggered", {"closed_positions": updated, "actor": user["display_name"]})
    return {"closed_positions": updated}


@router.post("/run-once")
async def run_once(user: dict = Depends(require_role("operator"))) -> dict:
    processed: list[dict] = []
    for instrument in default_instruments():
        for timeframe in (Timeframe.M15, Timeframe.H1, Timeframe.H4):
            bar = await latest_feature_bar_async(instrument, timeframe)
            if not bar:
                continue
            job_name = f"paper:{instrument.key}:{timeframe.value}"
            if should_process_bar(job_name, bar["ts"]):
                run_bar(bar)
                mark_processed(job_name, bar["ts"])
                processed.append(
                    {
                        "instrument_key": instrument.key,
                        "timeframe": timeframe.value,
                        "ts": bar["ts"].isoformat(),
                    }
                )
    record_audit_event(
        event_type="paper.run_once",
        entity_type="paper_runner",
        entity_id="manual",
        payload={"processed": processed},
    )
    return {"processed": processed}

```

## `backend/api/routes/strategies.py`

```python
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.service import require_role
from backend.core.types import dataclass_to_dict, strategy_spec_from_dict
from backend.data.storage import fetch_one, save_json_record
from backend.ops.audit import record_audit_event
from backend.strategy.registry import list_specs
from backend.strategy.targets import list_targets, update_target_state
from backend.strategy.validator import validate_spec

router = APIRouter()

@router.get("")
def list_strategies() -> list[dict]:
    return list_specs()


@router.get("/{spec_id}")
def get_strategy(spec_id: str) -> dict:
    row = fetch_one("SELECT * FROM strategy_specs WHERE spec_id=?", [spec_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return dict(row)


@router.post("")
def create_strategy(spec_payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    spec = strategy_spec_from_dict(spec_payload)
    validation = validate_spec(spec)
    if not validation.valid:
        raise HTTPException(status_code=400, detail=validation.errors)
    save_json_record(
        "strategy_specs",
        {
            "spec_id": spec.spec_id,
            "name": spec.name,
            "version": spec.version,
            "parent_id": spec.parent_id,
            "status": "proposed",
            "spec_json": json.dumps(dataclass_to_dict(spec)),
            "created_at": spec.created_at.isoformat(),
        },
        "spec_id",
    )
    record_audit_event(
        event_type="strategy.created",
        entity_type="strategy_spec",
        entity_id=spec.spec_id,
        payload={"name": spec.name, "version": spec.version, "hypothesis": spec.hypothesis},
    )
    return {"ok": True, "spec_id": spec.spec_id}


@router.get("/{spec_id}/targets")
def get_targets(spec_id: str) -> list[dict]:
    return list_targets(spec_id)


@router.post("/{spec_id}/targets")
def upsert_target(spec_id: str, payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    symbol = payload["symbol"]
    venue = payload["venue"]
    return update_target_state(
        spec_id=spec_id,
        symbol=symbol,
        venue=venue,
        status=payload.get("status"),
        paper_enabled=payload.get("paper_enabled"),
        notes=payload.get("notes"),
        last_backtest_run_id=payload.get("last_backtest_run_id"),
    )

```

## `backend/api/routes/vault.py`

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.service import require_role
from backend.ops.audit import record_audit_event
from backend.secrets.vault import delete_secret, get_secret, set_secret, vault_status

router = APIRouter()


@router.get("/status")
def status(user: dict = Depends(require_role("admin"))) -> dict:
    return vault_status()


@router.post("/secrets")
def put_secret(payload: dict, user: dict = Depends(require_role("admin"))) -> dict:
    try:
        result = set_secret(payload["name"], payload["value"], payload.get("passphrase"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    record_audit_event(
        event_type="vault.secret_set",
        entity_type="vault",
        entity_id=payload["name"],
        payload={"updated_by": user["display_name"]},
    )
    return result


@router.post("/secrets/delete")
def remove_secret(payload: dict, user: dict = Depends(require_role("admin"))) -> dict:
    try:
        result = delete_secret(payload["name"], payload.get("passphrase"))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    record_audit_event(
        event_type="vault.secret_deleted",
        entity_type="vault",
        entity_id=payload["name"],
        payload={"deleted_by": user["display_name"]},
    )
    return result


@router.get("/peek/{name}")
def peek_secret(name: str, user: dict = Depends(require_role("admin"))) -> dict:
    return {"name": name, "configured": bool(get_secret(name))}

```

## `backend/api/routes/__init__.py`

```python
"""API routes."""

```

## `backend/auth/service.py`

```python
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request

from backend.core.config import settings
from backend.data.storage import fetch_all, fetch_one, save_json_record

ROLE_PRIORITY = {"viewer": 1, "operator": 2, "admin": 3}


def bootstrap_users() -> None:
    defaults = [
        ("viewer", "Viewer", settings.auth_viewer_token),
        ("operator", "Operator", settings.auth_operator_token),
        ("admin", "Admin", settings.auth_admin_token),
    ]
    created_at = datetime.now(timezone.utc).isoformat()
    for role, display_name, token in defaults:
        if not token:
            continue
        existing = fetch_one("SELECT user_id FROM app_users WHERE token=?", [token])
        if existing is None:
            save_json_record(
                "app_users",
                {
                    "user_id": role,
                    "display_name": display_name,
                    "role": role,
                    "token": token,
                    "created_at": created_at,
                },
                "user_id",
            )


def list_users(include_tokens: bool = False) -> list[dict]:
    bootstrap_users()
    rows = fetch_all("SELECT user_id, display_name, role, token, created_at FROM app_users ORDER BY created_at", [])
    users = [dict(row) for row in rows]
    if include_tokens:
        return users
    for user in users:
        user.pop("token", None)
    return users


def public_user(user: dict) -> dict:
    return {
        "user_id": user["user_id"],
        "display_name": user["display_name"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


def get_user_by_token(token: str | None) -> dict:
    bootstrap_users()
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    row = fetch_one("SELECT user_id, display_name, role, token, created_at FROM app_users WHERE token=?", [token])
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid auth token")
    return dict(row)


def current_user(
    request: Request,
    x_workbench_token: str | None = Header(default=None),
) -> dict:
    auth_cookie = request.cookies.get(settings.auth_cookie_name)
    token = x_workbench_token or auth_cookie
    return get_user_by_token(token)


def require_role(min_role: str):
    def dependency(user: dict = Depends(current_user)) -> dict:
        current_priority = ROLE_PRIORITY.get(user["role"], 0)
        needed = ROLE_PRIORITY.get(min_role, 999)
        if current_priority < needed:
            raise HTTPException(status_code=403, detail=f"{min_role}_role_required")
        return user

    return dependency

```

## `backend/auth/__init__.py`

```python
from __future__ import annotations


```

## `backend/backtest/advanced.py`

```python
from __future__ import annotations

import random
import statistics
from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.backtest.engine import run_backtest
from backend.backtest.tuning import strategy_sweep_variants
from backend.core.types import BacktestConfig, Instrument, StrategySpec
from backend.data.storage import read_bars


def walk_forward_analysis(spec: StrategySpec, instrument: Instrument, lookback_days: int = 180, windows: int = 4) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    bars = read_bars(instrument, spec.primary_timeframe, start, end)
    if bars.empty or len(bars) < max(60, windows * 12):
        return {"windows": [], "stability_score": 0.0}

    stride = max(10, len(bars) // windows)
    results: list[dict] = []
    for window_index in range(windows):
        train_start = window_index * stride
        train_end = min(train_start + stride, len(bars) - 1)
        test_end = min(train_end + stride, len(bars))
        if test_end - train_end < 5:
            continue
        train = bars.iloc[train_start:train_end].reset_index(drop=True)
        test = bars.iloc[train_end:test_end].reset_index(drop=True)
        best_label = "base"
        best_spec = spec
        best_sharpe = float("-inf")
        train_config = BacktestConfig(
            start_date=pd.Timestamp(train["ts_open"].iloc[0]).to_pydatetime(),
            end_date=pd.Timestamp(train["ts_open"].iloc[-1]).to_pydatetime(),
            instrument=instrument,
        )
        for label, variant in strategy_sweep_variants(spec):
            train_result = run_backtest(variant, train, train_config)
            if train_result.sharpe > best_sharpe:
                best_sharpe = train_result.sharpe
                best_label = label
                best_spec = variant
        test_config = BacktestConfig(
            start_date=pd.Timestamp(test["ts_open"].iloc[0]).to_pydatetime(),
            end_date=pd.Timestamp(test["ts_open"].iloc[-1]).to_pydatetime(),
            instrument=instrument,
        )
        test_result = run_backtest(best_spec, test, test_config)
        results.append(
            {
                "window": window_index + 1,
                "best_variant": best_label,
                "train_sharpe": round(best_sharpe, 4),
                "test_sharpe": round(test_result.sharpe, 4),
                "test_return_pct": round(test_result.total_return_pct, 4),
                "test_trades": test_result.total_trades,
            }
        )
    test_sharpes = [item["test_sharpe"] for item in results]
    if len(test_sharpes) > 1 and statistics.pstdev(test_sharpes) > 0:
        stability_score = statistics.fmean(test_sharpes) / statistics.pstdev(test_sharpes)
    else:
        stability_score = 0.0
    return {"windows": results, "stability_score": round(float(stability_score), 4)}


def monte_carlo_trade_paths(trades: list[dict], simulations: int = 500) -> dict:
    pnl_values = [float(item.get("pnl_usd", 0.0)) for item in trades]
    if not pnl_values:
        return {"simulations": simulations, "p5": 0.0, "p50": 0.0, "p95": 0.0}
    rng = random.Random(42)
    finals: list[float] = []
    for _ in range(simulations):
        path = [rng.choice(pnl_values) for _ in range(len(pnl_values))]
        finals.append(sum(path))
    ordered = sorted(finals)
    p5 = ordered[int(0.05 * (len(ordered) - 1))]
    p50 = ordered[int(0.50 * (len(ordered) - 1))]
    p95 = ordered[int(0.95 * (len(ordered) - 1))]
    return {
        "simulations": simulations,
        "p5": round(float(p5), 4),
        "p50": round(float(p50), 4),
        "p95": round(float(p95), 4),
        "mean": round(float(statistics.fmean(finals)), 4),
    }


def strategy_correlation(spec: StrategySpec, lookback_days: int = 120) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    series: dict[str, pd.Series] = {}
    for instrument in spec.universe:
        bars = read_bars(instrument, spec.primary_timeframe, start, end)
        if bars.empty:
            continue
        closes = bars.sort_values("ts_open")["close"].astype(float).pct_change().fillna(0.0)
        series[f"{instrument.symbol}/{instrument.venue.value}"] = closes.reset_index(drop=True)
    if len(series) < 2:
        return {"matrix": {}, "warning": "insufficient_series"}
    frame = pd.DataFrame(series).dropna()
    matrix = frame.corr().round(4)
    return {
        "matrix": matrix.to_dict(),
        "warning": None,
    }

```

## `backend/backtest/broker.py`

```python
from __future__ import annotations


def round_trip_cost(size_usd: float, fee_bps: float, slippage_bps: float) -> float:
    return size_usd * ((fee_bps + slippage_bps * 2) / 10_000)

```

## `backend/backtest/engine.py`

```python
from __future__ import annotations

import random
import statistics
import uuid
from datetime import datetime
from decimal import Decimal

import pandas as pd

from backend.backtest.broker import round_trip_cost
from backend.backtest.metrics import annualized_return, compute_max_drawdown
from backend.core.types import BacktestConfig, BacktestResult, EquityPoint, StrategySpec, TradeRecord, utc_now
from backend.strategy.engine import get_signal


def run_backtest(
    spec: StrategySpec,
    bars: pd.DataFrame,
    config: BacktestConfig,
    *,
    compute_robustness: bool = True,
) -> BacktestResult:
    frame = bars.copy().sort_values("ts_open").reset_index(drop=True)
    capital = config.initial_capital_usd
    equity = capital
    equity_curve: list[EquityPoint] = []
    trades: list[TradeRecord] = []
    current_side = "flat"
    entry_price = 0.0
    entry_ts: datetime | None = None
    size_usd = spec.sizing.fixed_notional_usd or 1_000.0
    signal_counts = {"long": 0, "short": 0, "flat": 0}

    for row in frame.to_dict(orient="records"):
        signal = get_signal(spec, row)
        signal_counts[signal] += 1
        price = float(row["close"])
        ts = pd.Timestamp(row["ts_open"]).to_pydatetime()

        if current_side == "flat" and signal in {"long", "short"}:
            current_side = signal
            entry_price = price
            entry_ts = ts
        elif current_side in {"long", "short"} and signal != current_side:
            raw_pnl = ((price - entry_price) / entry_price) * size_usd
            if current_side == "short":
                raw_pnl = -raw_pnl
            fees = round_trip_cost(size_usd, config.fee_bps, config.slippage_bps)
            funding = 0.0
            pnl = raw_pnl - fees + funding
            equity += pnl
            trades.append(
                TradeRecord(
                    trade_id=str(uuid.uuid4()),
                    spec_id=spec.spec_id,
                    instrument=spec.universe[0],
                    direction=current_side,
                    entry_ts=entry_ts or ts,
                    exit_ts=ts,
                    entry_price=Decimal(str(round(entry_price, 6))),
                    exit_price=Decimal(str(round(price, 6))),
                    size_usd=size_usd,
                    pnl_usd=pnl,
                    fees_usd=fees,
                    funding_usd=funding,
                    exit_reason="signal",
                )
            )
            current_side = "flat"
            entry_price = 0.0
            entry_ts = None

        equity_curve.append(EquityPoint(ts=ts, equity=equity))

    if current_side in {"long", "short"} and not frame.empty:
        last_row = frame.iloc[-1]
        last_price = float(last_row["close"])
        last_ts = pd.Timestamp(last_row["ts_open"]).to_pydatetime()
        raw_pnl = ((last_price - entry_price) / entry_price) * size_usd if entry_price else 0.0
        if current_side == "short":
            raw_pnl = -raw_pnl
        fees = round_trip_cost(size_usd, config.fee_bps, config.slippage_bps)
        funding = 0.0
        pnl = raw_pnl - fees + funding
        equity += pnl
        trades.append(
            TradeRecord(
                trade_id=str(uuid.uuid4()),
                spec_id=spec.spec_id,
                instrument=spec.universe[0],
                direction=current_side,
                entry_ts=entry_ts or last_ts,
                exit_ts=last_ts,
                entry_price=Decimal(str(round(entry_price, 6))),
                exit_price=Decimal(str(round(last_price, 6))),
                size_usd=size_usd,
                pnl_usd=pnl,
                fees_usd=fees,
                funding_usd=funding,
                exit_reason="end_of_backtest",
            )
        )
        if equity_curve:
            equity_curve[-1] = EquityPoint(ts=last_ts, equity=equity)
        else:
            equity_curve.append(EquityPoint(ts=last_ts, equity=equity))

    pnl_values = [trade.pnl_usd for trade in trades]
    total_return_pct = ((equity / capital) - 1) * 100 if capital else 0.0
    days = max((config.end_date - config.start_date).days, 1)
    avg_trade = sum(pnl_values) / len(pnl_values) if pnl_values else 0.0
    wins = [p for p in pnl_values if p > 0]
    losses = [abs(p) for p in pnl_values if p < 0]
    profit_factor = (sum(wins) / sum(losses)) if losses else float(sum(wins) > 0)
    returns = pd.Series([0.0] + pnl_values)
    sharpe = float((returns.mean() / returns.std()) * (252 ** 0.5)) if len(returns) > 1 and returns.std() else 0.0
    negative = returns[returns < 0]
    sortino = float((returns.mean() / negative.std()) * (252 ** 0.5)) if len(negative) > 1 and negative.std() else 0.0
    max_dd_pct, max_dd_duration = compute_max_drawdown(equity_curve)
    calmar = (annualized_return(total_return_pct, days) / max_dd_pct) if max_dd_pct else 0.0
    avg_hold_bars = float(sum((trade.exit_ts - trade.entry_ts).total_seconds() for trade in trades) / len(trades) / 3600) if trades else 0.0
    diagnostics = {
        "bars_seen": int(len(frame)),
        "signal_counts": signal_counts,
        "feature_ranges": {
            column: {
                "min": float(frame[column].min()),
                "max": float(frame[column].max()),
            }
            for column in ("ret_4", "vol_20", "vol_ratio", "funding_rate", "funding_zscore", "rsi_14", "pct_rank_20")
            + (
                "oi_change_pct",
                "buy_sell_ratio",
                "liquidation_intensity",
                "spread_bps",
                "orderbook_imbalance",
                "btc_ret_1",
                "rel_strength_20",
                "beta_btc_20",
                "onchain_pressure",
            )
            if column in frame.columns and len(frame[column]) > 0
        },
    }

    result = BacktestResult(
        run_id=str(uuid.uuid4()),
        spec_id=spec.spec_id,
        config=config,
        ran_at=utc_now(),
        total_return_pct=total_return_pct,
        annualized_return_pct=annualized_return(total_return_pct, days),
        sharpe=sharpe,
        sortino=sortino,
        calmar=calmar,
        max_drawdown_pct=max_dd_pct,
        max_drawdown_duration_days=max_dd_duration,
        win_rate=(len(wins) / len(trades)) if trades else 0.0,
        profit_factor=profit_factor,
        avg_trade_pnl_usd=avg_trade,
        total_trades=len(trades),
        avg_hold_bars=avg_hold_bars,
        perturbation_sharpe_mean=sharpe,
        perturbation_sharpe_std=0.0,
        oos_sharpe=sharpe,
        diagnostics=diagnostics,
        trades=trades,
        equity_curve=equity_curve,
    )
    if not compute_robustness:
        return result

    perturb_mean, perturb_std = _compute_perturbation_sharpe(spec, frame, config)
    result.perturbation_sharpe_mean = perturb_mean
    result.perturbation_sharpe_std = perturb_std
    result.oos_sharpe = _compute_oos_sharpe(spec, frame, config)
    return result


def _compute_perturbation_sharpe(
    spec: StrategySpec,
    bars: pd.DataFrame,
    config: BacktestConfig,
    n_runs: int = 20,
) -> tuple[float, float]:
    if bars.empty or "close" not in bars.columns:
        return 0.0, 0.0
    rng = random.Random(42)
    sharpes: list[float] = []
    for _ in range(n_runs):
        noised = bars.copy()
        noised["close"] = noised["close"].astype(float).map(lambda price: price * rng.uniform(0.998, 1.002))
        noised_result = run_backtest(spec, noised, config, compute_robustness=False)
        sharpes.append(noised_result.sharpe)
    return float(statistics.fmean(sharpes)), float(statistics.pstdev(sharpes))


def _compute_oos_sharpe(
    spec: StrategySpec,
    bars: pd.DataFrame,
    config: BacktestConfig,
    oos_fraction: float = 0.3,
) -> float:
    if bars.empty or len(bars) < 2:
        return 0.0
    split = int(len(bars) * (1 - oos_fraction))
    split = max(1, min(split, len(bars) - 1))
    oos_bars = bars.iloc[split:].reset_index(drop=True)
    oos_start = pd.Timestamp(oos_bars["ts_open"].iloc[0]).to_pydatetime()
    oos_config = BacktestConfig(
        start_date=oos_start,
        end_date=config.end_date,
        instrument=config.instrument,
        initial_capital_usd=config.initial_capital_usd,
        fee_bps=config.fee_bps,
        slippage_bps=config.slippage_bps,
        funding_included=config.funding_included,
    )
    oos_result = run_backtest(spec, oos_bars, oos_config, compute_robustness=False)
    return float(oos_result.sharpe)

```

## `backend/backtest/metrics.py`

```python
from __future__ import annotations

from backend.core.types import BacktestResult, EquityPoint, PromotionDecision, PromotionPolicy, utc_now


def compute_max_drawdown(equity_curve: list[tuple] | list[EquityPoint]) -> tuple[float, float]:
    if not equity_curve:
        return 0.0, 0.0
    first = equity_curve[0]
    if isinstance(first, EquityPoint):
        peak = first.equity
        peak_time = first.ts
        iterator = ((point.ts, point.equity) for point in equity_curve)
    else:
        peak = first[1]
        peak_time = first[0]
        iterator = ((point[0], point[1]) for point in equity_curve)
    max_dd = 0.0
    max_duration = 0.0
    for ts, value in iterator:
        if value >= peak:
            peak = value
            peak_time = ts
        drawdown = (peak - value) / peak if peak else 0.0
        if drawdown > max_dd:
            max_dd = drawdown
            max_duration = max(max_duration, (ts - peak_time).total_seconds() / 86400)
    return max_dd * 100, max_duration


def annualized_return(total_return_pct: float, days: float) -> float:
    if days <= 0:
        return 0.0
    total = 1 + total_return_pct / 100
    return (total ** (365 / days) - 1) * 100 if total > 0 else -100.0


def evaluate_promotion(result: BacktestResult, policy: PromotionPolicy | None = None) -> PromotionDecision:
    policy = policy or PromotionPolicy()
    failures: list[str] = []
    if result.avg_trade_pnl_usd < policy.min_net_expectancy_usd:
        failures.append("avg_trade_pnl_below_min")
    if result.oos_sharpe < policy.min_oos_sharpe:
        failures.append("oos_sharpe_below_min")
    if result.max_drawdown_pct > policy.max_drawdown_pct * 100:
        failures.append("max_drawdown_above_limit")
    if result.total_trades < policy.min_trade_count:
        failures.append("trade_count_below_min")
    if result.perturbation_sharpe_mean < policy.min_perturbation_sharpe:
        failures.append("perturbation_sharpe_below_min")

    return PromotionDecision(
        spec_id=result.spec_id,
        backtest_run_id=result.run_id,
        policy=policy,
        passed=not failures,
        failures=failures,
        decided_at=utc_now(),
        approved_by="auto" if not failures else None,
    )

```

## `backend/backtest/service.py`

```python
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
import pandas as pd
import structlog

from backend.backtest.advanced import monte_carlo_trade_paths, strategy_correlation, walk_forward_analysis
from backend.backtest.engine import run_backtest
from backend.backtest.metrics import evaluate_promotion
from backend.backtest.tuning import strategy_sweep_variants
from backend.core.types import BacktestConfig, Instrument, Venue, dataclass_to_dict
from backend.data.features import add_funding_features, compute_features
from backend.data.service import attach_benchmark_close, load_funding_like_series
from backend.data.storage import read_bars
from backend.strategy.registry import load_spec
from backend.data.adapters import binance, hyperliquid

log = structlog.get_logger()


def resolve_instrument(spec_id: str, symbol: str | None, venue: str | None) -> tuple:
    spec = load_spec(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    filtered = spec.universe
    if symbol:
        filtered = [inst for inst in filtered if inst.symbol == symbol]
    if venue:
        filtered = [inst for inst in filtered if inst.venue.value == venue]
    if not filtered:
        raise HTTPException(status_code=400, detail="Requested symbol/venue is not available for this strategy")
    return spec, filtered[0]


def build_feature_frame(instrument: Instrument, timeframe, lookback_days: int):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=lookback_days)
    bars = read_bars(instrument, timeframe, start, now)
    if bars.empty:
        raise HTTPException(status_code=400, detail="No bars available for backtest")
    bars = attach_benchmark_close(instrument, timeframe, bars)
    features = compute_features(bars)
    features = _merge_market_context(features, instrument)
    funding = load_funding_like_series(instrument, timeframe, start, now)
    enriched = add_funding_features(features, funding)
    return enriched, start, now


def _merge_market_context(features, instrument: Instrument):
    try:
        if instrument.venue == Venue.BINANCE:
            oi = asyncio.run(binance.fetch_open_interest_history(instrument))
            taker = asyncio.run(binance.fetch_taker_buy_sell_volume(instrument))
            liquidations = asyncio.run(binance.fetch_liquidation_history(instrument))
            book = asyncio.run(binance.fetch_order_book_snapshot(instrument))
        else:
            oi = asyncio.run(hyperliquid.fetch_open_interest_history(instrument))
            taker = asyncio.run(hyperliquid.fetch_taker_buy_sell_volume(instrument))
            liquidations = asyncio.run(hyperliquid.fetch_liquidation_history(instrument))
            book = asyncio.run(hyperliquid.fetch_order_book_snapshot(instrument))
    except Exception:
        oi = None
        taker = None
        liquidations = None
        book = {"spread_bps": 0.0, "orderbook_imbalance": 0.0}
    merged = features.copy().sort_values("ts_open").reset_index(drop=True)
    if oi is not None and not oi.empty:
        merged = pd.merge_asof(merged, oi.sort_values("ts"), left_on="ts_open", right_on="ts", direction="backward")
        merged.drop(columns=[col for col in ["ts"] if col in merged.columns], inplace=True)
    if taker is not None and not taker.empty:
        merged = pd.merge_asof(merged, taker.sort_values("ts"), left_on="ts_open", right_on="ts", direction="backward")
        merged.drop(columns=[col for col in ["ts"] if col in merged.columns], inplace=True)
    if liquidations is not None and not liquidations.empty:
        merged = pd.merge_asof(merged, liquidations.sort_values("ts"), left_on="ts_open", right_on="ts", direction="backward")
        merged.drop(columns=[col for col in ["ts"] if col in merged.columns], inplace=True)
    merged["spread_bps"] = float(book.get("spread_bps") or 0.0)
    merged["orderbook_imbalance"] = float(book.get("orderbook_imbalance") or 0.0)
    return merged


def execute_backtest(spec_id: str, symbol: str | None, venue: str | None, lookback_days: int) -> tuple[dict, dict]:
    spec, instrument = resolve_instrument(spec_id, symbol, venue)
    features, start, end = build_feature_frame(instrument, spec.primary_timeframe, lookback_days)
    config = BacktestConfig(start_date=start, end_date=end, instrument=instrument)
    result = run_backtest(spec, features, config)
    decision = evaluate_promotion(result)
    return dataclass_to_dict(result), dataclass_to_dict(decision)


def compare_runs(spec_id: str, lookback_days: int) -> list[dict]:
    spec = load_spec(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    comparisons: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for instrument in spec.universe:
        key = (instrument.symbol, instrument.venue.value)
        if key in seen:
            continue
        seen.add(key)
        try:
            result, decision = execute_backtest(spec_id, instrument.symbol, instrument.venue.value, lookback_days)
            comparisons.append(
                {
                    "symbol": instrument.symbol,
                    "venue": instrument.venue.value,
                    "sharpe": result["sharpe"],
                    "total_return_pct": result["total_return_pct"],
                    "total_trades": result["total_trades"],
                    "passed": decision["passed"],
                }
            )
        except Exception as exc:
            log.warning("backtest compare failed", symbol=instrument.symbol, venue=instrument.venue.value, error=str(exc))
            comparisons.append(
                {
                    "symbol": instrument.symbol,
                    "venue": instrument.venue.value,
                    "sharpe": None,
                    "total_return_pct": None,
                    "total_trades": 0,
                    "passed": False,
                }
            )
    return comparisons


def sweep_runs(spec_id: str, symbol: str | None, venue: str | None, lookback_days: int) -> list[dict]:
    spec, instrument = resolve_instrument(spec_id, symbol, venue)
    features, start, end = build_feature_frame(instrument, spec.primary_timeframe, lookback_days)
    results: list[dict] = []
    for label, variant in strategy_sweep_variants(spec):
        config = BacktestConfig(start_date=start, end_date=end, instrument=instrument)
        result = run_backtest(variant, features, config)
        results.append(
            {
                "label": label,
                "sharpe": result.sharpe,
                "return_pct": result.total_return_pct,
                "trades": result.total_trades,
                "drawdown_pct": result.max_drawdown_pct,
            }
        )
    return sorted(results, key=lambda item: (item["sharpe"], item["return_pct"]), reverse=True)


def walk_forward(spec_id: str, symbol: str | None, venue: str | None, lookback_days: int, windows: int = 4) -> dict:
    spec, instrument = resolve_instrument(spec_id, symbol, venue)
    return walk_forward_analysis(spec, instrument, lookback_days=lookback_days, windows=windows)


def monte_carlo_for_run(run_id: str, simulations: int = 500) -> dict:
    from backend.data.storage import fetch_one

    row = fetch_one("SELECT result_json FROM backtest_runs WHERE run_id=?", [run_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    import json

    result = json.loads(row["result_json"])
    return monte_carlo_trade_paths(result.get("trades", []), simulations=simulations)


def correlation_for_spec(spec_id: str, lookback_days: int = 120) -> dict:
    spec = load_spec(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy_correlation(spec, lookback_days=lookback_days)

```

## `backend/backtest/tuning.py`

```python
from __future__ import annotations

from copy import deepcopy

from backend.core.types import RuleBlock, StrategySpec


def strategy_sweep_variants(spec: StrategySpec) -> list[tuple[str, StrategySpec]]:
    if spec.spec_id == "builtin-funding-mean-reversion":
        return _funding_variants(spec)
    if spec.spec_id == "builtin-momentum-with-vol-filter":
        return _momentum_variants(spec)
    if spec.spec_id == "builtin-range-breakout":
        return _breakout_variants(spec)
    return [("baseline", spec)]


def _funding_variants(spec: StrategySpec) -> list[tuple[str, StrategySpec]]:
    variants: list[tuple[str, StrategySpec]] = []
    for funding_threshold in (1.5, 2.0, 2.5):
        for vol_cap in (0.05, 0.08, 0.12):
            clone = deepcopy(spec)
            clone.name = f"{spec.name} [{funding_threshold:.1f}/{vol_cap:.2f}]"
            clone.entry_long[0].threshold = -funding_threshold
            clone.entry_short[0].threshold = funding_threshold
            clone.regime_filters[0].threshold = vol_cap
            variants.append((f"z={funding_threshold:.1f}, vol<{vol_cap:.2f}", clone))
    return variants


def _momentum_variants(spec: StrategySpec) -> list[tuple[str, StrategySpec]]:
    variants: list[tuple[str, StrategySpec]] = []
    for ret_threshold in (0.005, 0.01, 0.015):
        for vol_ratio in (1.0, 1.2, 1.4):
            clone = deepcopy(spec)
            clone.name = f"{spec.name} [{ret_threshold:.3f}/{vol_ratio:.1f}]"
            clone.entry_long[0].threshold = ret_threshold
            clone.entry_short[0].threshold = -ret_threshold
            clone.entry_long[1].threshold = vol_ratio
            clone.entry_short[1].threshold = vol_ratio
            variants.append((f"ret={ret_threshold:.3f}, vr>{vol_ratio:.1f}", clone))
    return variants


def _breakout_variants(spec: StrategySpec) -> list[tuple[str, StrategySpec]]:
    variants: list[tuple[str, StrategySpec]] = []
    for rank in (0.9, 0.95, 0.98):
        for vol_ratio in (1.2, 1.5, 1.8):
            clone = deepcopy(spec)
            clone.name = f"{spec.name} [{rank:.2f}/{vol_ratio:.1f}]"
            clone.entry_long[0].threshold = rank
            clone.entry_short[0].threshold = round(1 - rank, 2)
            clone.entry_long[1].threshold = vol_ratio
            clone.entry_short[1].threshold = vol_ratio
            variants.append((f"rank={rank:.2f}, vr>{vol_ratio:.1f}", clone))
    return variants

```

## `backend/backtest/__init__.py`

```python
"""Backtest engine and metrics."""

```

## `backend/core/config.py`

```python
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _list_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    binance_base_url: str = os.getenv("BINANCE_BASE_URL", "https://fapi.binance.com")
    hyperliquid_base_url: str = os.getenv("HYPERLIQUID_BASE_URL", "https://api.hyperliquid.xyz")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-haiku")
    auth_viewer_token: str = os.getenv("AUTH_VIEWER_TOKEN", "viewer-token")
    auth_operator_token: str = os.getenv("AUTH_OPERATOR_TOKEN", "operator-token")
    auth_admin_token: str = os.getenv("AUTH_ADMIN_TOKEN", "admin-token")
    auth_cookie_name: str = os.getenv("AUTH_COOKIE_NAME", "workbench_token")
    auth_cookie_secure: bool = _bool_env("AUTH_COOKIE_SECURE", False)
    auth_cookie_max_age_seconds: int = int(os.getenv("AUTH_COOKIE_MAX_AGE_SECONDS", str(60 * 60 * 8)))
    binance_api_key: str = os.getenv("BINANCE_API_KEY", "")
    binance_api_secret: str = os.getenv("BINANCE_API_SECRET", "")
    hyperliquid_private_key: str = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")
    hyperliquid_account_address: str = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "")
    vault_passphrase: str = os.getenv("VAULT_PASSPHRASE", "")
    raw_data_root: Path = Path(os.getenv("RAW_DATA_ROOT", "./data/raw"))
    curated_db_path: Path = Path(os.getenv("CURATED_DB_PATH", "./data/curated/workbench.duckdb"))
    meta_db_path: Path = Path(os.getenv("META_DB_PATH", "./data/meta/workbench.db"))
    vault_file_path: Path = Path(os.getenv("VAULT_FILE_PATH", "./data/meta/secrets.vault"))
    app_log_path: Path = Path(os.getenv("APP_LOG_PATH", "./data/meta/workbench.log"))
    paper_initial_capital_usd: float = float(os.getenv("PAPER_INITIAL_CAPITAL_USD", "100000"))
    paper_fee_bps: float = float(os.getenv("PAPER_FEE_BPS", "4.0"))
    paper_slippage_bps: float = float(os.getenv("PAPER_SLIPPAGE_BPS", "3.0"))
    paper_trading_enabled: bool = _bool_env("PAPER_TRADING_ENABLED", True)
    paper_max_open_positions: int = int(os.getenv("PAPER_MAX_OPEN_POSITIONS", "4"))
    paper_max_gross_exposure_usd: float = float(os.getenv("PAPER_MAX_GROSS_EXPOSURE_USD", "40000"))
    paper_max_signal_correlation: float = float(os.getenv("PAPER_MAX_SIGNAL_CORRELATION", "0.92"))
    paper_daily_loss_limit_usd: float = float(os.getenv("PAPER_DAILY_LOSS_LIMIT_USD", "1500"))
    paper_day_reset_hour_utc: int = int(os.getenv("PAPER_DAY_RESET_HOUR_UTC", "0"))
    data_readiness_coverage_days: float = float(os.getenv("DATA_READINESS_COVERAGE_DAYS", "20"))
    paper_readiness_min_events: int = int(os.getenv("PAPER_READINESS_MIN_EVENTS", "10"))
    live_trading_enabled: bool = _bool_env("LIVE_TRADING_ENABLED", False)
    live_approval_mode: bool = _bool_env("LIVE_APPROVAL_MODE", True)
    live_network_enabled: bool = _bool_env("LIVE_NETWORK_ENABLED", False)
    scheduler_enabled: bool = _bool_env("SCHEDULER_ENABLED", False)
    worker_max_retries: int = int(os.getenv("WORKER_MAX_RETRIES", "3"))
    worker_retry_backoff_seconds: int = int(os.getenv("WORKER_RETRY_BACKOFF_SECONDS", "5"))
    worker_heartbeat_ttl_seconds: int = int(os.getenv("WORKER_HEARTBEAT_TTL_SECONDS", "30"))
    alerts_telegram_bot_token: str = os.getenv("ALERTS_TELEGRAM_BOT_TOKEN", "")
    alerts_telegram_chat_id: str = os.getenv("ALERTS_TELEGRAM_CHAT_ID", "")
    alerts_discord_webhook_url: str = os.getenv("ALERTS_DISCORD_WEBHOOK_URL", "")
    alerts_email_smtp_host: str = os.getenv("ALERTS_EMAIL_SMTP_HOST", "")
    alerts_email_smtp_port: int = int(os.getenv("ALERTS_EMAIL_SMTP_PORT", "587"))
    alerts_email_username: str = os.getenv("ALERTS_EMAIL_USERNAME", "")
    alerts_email_password: str = os.getenv("ALERTS_EMAIL_PASSWORD", "")
    alerts_email_from: str = os.getenv("ALERTS_EMAIL_FROM", "")
    alerts_email_to: str = os.getenv("ALERTS_EMAIL_TO", "")
    market_streams_enabled: bool = _bool_env("MARKET_STREAMS_ENABLED", False)
    cors_allow_origins: list[str] = field(
        default_factory=lambda: _list_env("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )
    cors_allow_methods: list[str] = field(default_factory=lambda: _list_env("CORS_ALLOW_METHODS", "GET,POST,OPTIONS"))
    cors_allow_headers: list[str] = field(
        default_factory=lambda: _list_env("CORS_ALLOW_HEADERS", "Content-Type,X-Workbench-Token")
    )
    api_rate_limit_global_per_minute: int = int(os.getenv("API_RATE_LIMIT_GLOBAL_PER_MINUTE", "600"))
    api_rate_limit_auth_token_per_minute: int = int(os.getenv("API_RATE_LIMIT_AUTH_TOKEN_PER_MINUTE", "10"))
    api_rate_limit_ticket_approve_per_minute: int = int(os.getenv("API_RATE_LIMIT_TICKET_APPROVE_PER_MINUTE", "20"))


settings = Settings()

```

## `backend/core/logging.py`

```python
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog


def configure_logging(log_path: Path | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                log_path,
                maxBytes=2_000_000,
                backupCount=5,
                encoding="utf-8",
            )
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=handlers,
        force=True,
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

```

## `backend/core/retry.py`

```python
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 4.0,
) -> T:
    delay = initial_delay
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except Exception as exc:  # pragma: no cover - network failure paths
            last_error = exc
            if attempt >= attempts:
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)
    if last_error is None:  # pragma: no cover
        raise RuntimeError("retry_async_failed_without_exception")
    raise last_error


def retry_sync(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 4.0,
) -> T:
    delay = initial_delay
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - network failure paths
            last_error = exc
            if attempt >= attempts:
                break
            time.sleep(delay)
            delay = min(delay * 2, max_delay)
    if last_error is None:  # pragma: no cover
        raise RuntimeError("retry_sync_failed_without_exception")
    raise last_error

```

## `backend/core/types.py`

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Literal


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Venue(str, Enum):
    BINANCE = "binance"
    HYPERLIQUID = "hyperliquid"


class VenueMode(str, Enum):
    SPOT = "spot"
    PERP = "perp"


class Timeframe(str, Enum):
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"


class DataQuality(str, Enum):
    HEALTHY = "healthy"
    STALE = "stale"
    GAPPED = "gapped"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class Instrument:
    symbol: str
    venue: Venue
    mode: VenueMode
    quote: str = "USDT"

    @property
    def key(self) -> str:
        return f"{self.venue.value}:{self.mode.value}:{self.symbol}/{self.quote}"

    @property
    def venue_symbol(self) -> str:
        if self.venue == Venue.BINANCE:
            return f"{self.symbol}{self.quote}"
        return self.symbol


@dataclass(frozen=True)
class MarketBar:
    instrument: Instrument
    timeframe: Timeframe
    ts_open: datetime
    ts_close: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    volume_quote: Decimal
    trades: int | None = None


@dataclass(frozen=True)
class FundingPoint:
    instrument: Instrument
    ts: datetime
    rate: Decimal
    predicted: Decimal | None = None


@dataclass
class FeatureSet:
    instrument: Instrument
    timeframe: Timeframe
    ts: datetime
    features: dict[str, float] = field(default_factory=dict)


@dataclass
class DatasetHealth:
    instrument: Instrument
    timeframe: Timeframe
    quality: DataQuality
    last_bar_ts: datetime | None
    gap_count: int
    duplicate_count: int
    coverage_days: float
    checked_at: datetime


@dataclass
class RuleBlock:
    feature: str
    operator: str
    threshold: float | tuple[float, float]
    timeframe: Timeframe | None = None


@dataclass
class SizingSpec:
    method: Literal["fixed_notional", "vol_target", "kelly_half"] = "fixed_notional"
    target_vol: float | None = None
    fixed_notional_usd: float | None = 1_000.0
    max_position_pct: float = 0.10


@dataclass
class RiskLimits:
    max_drawdown_pct: float = 0.15
    max_daily_loss_usd: float | None = None
    max_open_positions: int = 4
    stop_loss_atr_mult: float | None = None
    take_profit_atr_mult: float | None = None


@dataclass
class ExecutionConstraints:
    bar_close_only: bool = True
    min_volume_usd: float = 500_000
    max_spread_bps: float = 10.0


@dataclass
class StrategySpec:
    spec_id: str
    name: str
    version: int = 1
    parent_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    universe: list[Instrument] = field(default_factory=list)
    venue_mode: VenueMode = VenueMode.PERP
    primary_timeframe: Timeframe = Timeframe.H1
    aux_timeframes: list[Timeframe] = field(default_factory=list)
    feature_inputs: list[str] = field(default_factory=list)
    regime_filters: list[RuleBlock] = field(default_factory=list)
    entry_long: list[RuleBlock] = field(default_factory=list)
    entry_short: list[RuleBlock] = field(default_factory=list)
    exit_long: list[RuleBlock] = field(default_factory=list)
    exit_short: list[RuleBlock] = field(default_factory=list)
    sizing: SizingSpec = field(default_factory=SizingSpec)
    risk_limits: RiskLimits = field(default_factory=RiskLimits)
    execution: ExecutionConstraints = field(default_factory=ExecutionConstraints)
    hypothesis: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class BacktestConfig:
    start_date: datetime
    end_date: datetime
    instrument: Instrument | None = None
    initial_capital_usd: float = 100_000
    fee_bps: float = 4.0
    slippage_bps: float = 2.0
    funding_included: bool = True


@dataclass
class TradeRecord:
    trade_id: str
    spec_id: str
    instrument: Instrument
    direction: Literal["long", "short"]
    entry_ts: datetime
    exit_ts: datetime
    entry_price: Decimal
    exit_price: Decimal
    size_usd: float
    pnl_usd: float
    fees_usd: float
    funding_usd: float
    exit_reason: str


@dataclass
class EquityPoint:
    ts: datetime
    equity: float


@dataclass
class BacktestResult:
    run_id: str
    spec_id: str
    config: BacktestConfig
    ran_at: datetime
    total_return_pct: float
    annualized_return_pct: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown_pct: float
    max_drawdown_duration_days: float
    win_rate: float
    profit_factor: float
    avg_trade_pnl_usd: float
    total_trades: int
    avg_hold_bars: float
    perturbation_sharpe_mean: float
    perturbation_sharpe_std: float
    oos_sharpe: float
    diagnostics: dict[str, Any] = field(default_factory=dict)
    trades: list[TradeRecord] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)


@dataclass
class PaperPosition:
    position_id: str
    spec_id: str
    instrument: Instrument
    direction: Literal["long", "short"]
    opened_at: datetime
    entry_price: Decimal
    size_usd: float
    unrealized_pnl_usd: float = 0.0
    accrued_funding_usd: float = 0.0
    entry_fees_usd: float = 0.0


@dataclass
class PaperOrder:
    order_id: str
    spec_id: str
    instrument: Instrument
    direction: Literal["long", "short"]
    action: Literal["open", "close"]
    triggered_at: datetime
    size_usd: float
    fill_price: Decimal | None = None
    filled_at: datetime | None = None
    status: Literal["pending", "filled", "rejected"] = "pending"


@dataclass
class PromotionPolicy:
    min_net_expectancy_usd: float = 50.0
    min_oos_sharpe: float = 0.5
    max_drawdown_pct: float = 0.20
    min_trade_count: int = 30
    min_perturbation_sharpe: float = 0.3
    slippage_reality_tolerance: float = 0.20


@dataclass
class PromotionDecision:
    spec_id: str
    backtest_run_id: str
    policy: PromotionPolicy
    passed: bool
    failures: list[str]
    decided_at: datetime
    approved_by: str | None = None


def dataclass_to_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {k: dataclass_to_dict(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: dataclass_to_dict(v) for k, v in value.items()}
    if isinstance(value, list):
        return [dataclass_to_dict(v) for v in value]
    if isinstance(value, tuple):
        return [dataclass_to_dict(v) for v in value]
    return value


def instrument_from_dict(data: dict[str, Any]) -> Instrument:
    return Instrument(
        symbol=data["symbol"],
        venue=Venue(data["venue"]),
        mode=VenueMode(data["mode"]),
        quote=data.get("quote", "USDT"),
    )


def rule_from_dict(data: dict[str, Any]) -> RuleBlock:
    threshold = data["threshold"]
    if isinstance(threshold, list):
        threshold = tuple(threshold)
    timeframe = Timeframe(data["timeframe"]) if data.get("timeframe") else None
    return RuleBlock(
        feature=data["feature"],
        operator=data["operator"],
        threshold=threshold,
        timeframe=timeframe,
    )


def strategy_spec_from_dict(data: dict[str, Any]) -> StrategySpec:
    return StrategySpec(
        spec_id=data["spec_id"],
        name=data["name"],
        version=data.get("version", 1),
        parent_id=data.get("parent_id"),
        created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", utc_now()),
        universe=[instrument_from_dict(item) for item in data.get("universe", [])],
        venue_mode=VenueMode(data.get("venue_mode", VenueMode.PERP.value)),
        primary_timeframe=Timeframe(data.get("primary_timeframe", Timeframe.H1.value)),
        aux_timeframes=[Timeframe(item) for item in data.get("aux_timeframes", [])],
        feature_inputs=data.get("feature_inputs", []),
        regime_filters=[rule_from_dict(item) for item in data.get("regime_filters", [])],
        entry_long=[rule_from_dict(item) for item in data.get("entry_long", [])],
        entry_short=[rule_from_dict(item) for item in data.get("entry_short", [])],
        exit_long=[rule_from_dict(item) for item in data.get("exit_long", [])],
        exit_short=[rule_from_dict(item) for item in data.get("exit_short", [])],
        sizing=SizingSpec(**data.get("sizing", {})),
        risk_limits=RiskLimits(**data.get("risk_limits", {})),
        execution=ExecutionConstraints(**data.get("execution", {})),
        hypothesis=data.get("hypothesis", ""),
        tags=data.get("tags", []),
    )

```

## `backend/core/__init__.py`

```python
"""Core domain types and configuration."""

```

## `backend/execution/adapters.py`

```python
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlencode

import httpx

from backend.core.config import settings
from backend.core.retry import retry_sync
from backend.core.types import Instrument
from backend.secrets.vault import secret_or_env


@dataclass
class ExecutionPreview:
    instrument_key: str
    direction: str
    action: str
    size_usd: float
    estimated_fee_usd: float
    estimated_slippage_bps: float
    notional_limit_ok: bool
    approval_required: bool


class LiveExecutionAdapter:
    venue: str

    def preview_order(self, instrument: Instrument, direction: str, action: str, size_usd: float) -> ExecutionPreview:
        raise NotImplementedError

    def submit_order(self, instrument: Instrument, direction: str, action: str, size_usd: float) -> dict:
        raise NotImplementedError

    def reconcile(self) -> dict:
        raise NotImplementedError


class ApprovalModeAdapter(LiveExecutionAdapter):
    def __init__(self, venue: str) -> None:
        self.venue = venue

    def preview_order(self, instrument: Instrument, direction: str, action: str, size_usd: float) -> ExecutionPreview:
        estimated_fee_usd = round(size_usd * 0.0004, 4)
        return ExecutionPreview(
            instrument_key=instrument.key,
            direction=direction,
            action=action,
            size_usd=size_usd,
            estimated_fee_usd=estimated_fee_usd,
            estimated_slippage_bps=settings.paper_slippage_bps,
            notional_limit_ok=size_usd <= 5_000,
            approval_required=True,
        )

    def submit_order(self, instrument: Instrument, direction: str, action: str, size_usd: float) -> dict:
        return {
            "broker_order_id": f"approval:{self.venue}:{instrument.symbol}:{datetime.now(timezone.utc).timestamp()}",
            "status": "approval_only",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

    def reconcile(self) -> dict:
        return {
            "venue": self.venue,
            "status": "approval_mode",
            "remote_positions": [],
            "remote_orders": [],
            "notes": "Live adapter is running in approval mode only.",
        }


class BinanceFuturesAdapter(LiveExecutionAdapter):
    venue = "binance"

    def __init__(self) -> None:
        self.base_url = settings.binance_base_url.rstrip("/")
        self.api_key = secret_or_env("binance_api_key") or ""
        self.api_secret = secret_or_env("binance_api_secret") or ""

    def preview_order(self, instrument: Instrument, direction: str, action: str, size_usd: float) -> ExecutionPreview:
        estimated_fee_usd = round(size_usd * 0.0004, 4)
        return ExecutionPreview(
            instrument_key=instrument.key,
            direction=direction,
            action=action,
            size_usd=size_usd,
            estimated_fee_usd=estimated_fee_usd,
            estimated_slippage_bps=settings.paper_slippage_bps,
            notional_limit_ok=size_usd <= 5_000,
            approval_required=settings.live_approval_mode,
        )

    def submit_order(self, instrument: Instrument, direction: str, action: str, size_usd: float) -> dict:
        if not settings.live_network_enabled:
            return {
                "broker_order_id": f"binance-dry:{instrument.symbol}:{datetime.now(timezone.utc).timestamp()}",
                "status": "network_disabled",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "transport": "binance_hmac_scaffold",
            }
        price = self._mark_price(instrument)
        quantity = self._quantity_for_notional(instrument, size_usd, price)
        side = "BUY" if direction == "long" else "SELL"
        payload = {
            "symbol": instrument.venue_symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
            "timestamp": self._timestamp(),
            "recvWindow": 5000,
        }
        if action == "close":
            payload["reduceOnly"] = "true"
        response = self._signed_request("POST", "/fapi/v1/order", payload)
        return {
            "broker_order_id": str(response.get("orderId")),
            "status": response.get("status", "submitted"),
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "transport": "binance_hmac",
            "response": response,
        }

    def reconcile(self) -> dict:
        if not settings.live_network_enabled:
            return {
                "venue": self.venue,
                "status": "binance_network_disabled",
                "remote_positions": [],
                "remote_orders": [],
                "notes": "Binance HMAC adapter is configured, but LIVE_NETWORK_ENABLED is false.",
            }
        positions = self._signed_request("GET", "/fapi/v2/positionRisk", {"timestamp": self._timestamp(), "recvWindow": 5000})
        orders = self._signed_request("GET", "/fapi/v1/openOrders", {"timestamp": self._timestamp(), "recvWindow": 5000})
        return {
            "venue": self.venue,
            "status": "binance_reconciled",
            "remote_positions": positions,
            "remote_orders": orders,
            "notes": "Signed Binance reconciliation completed.",
        }

    def _timestamp(self) -> int:
        return int(datetime.now(timezone.utc).timestamp() * 1000)

    def _mark_price(self, instrument: Instrument) -> Decimal:
        response = retry_sync(
            lambda: httpx.get(
                f"{self.base_url}/fapi/v1/premiumIndex",
                params={"symbol": instrument.venue_symbol},
                timeout=10.0,
            )
        )
        response.raise_for_status()
        payload = response.json()
        return Decimal(str(payload["markPrice"]))

    def _quantity_for_notional(self, instrument: Instrument, size_usd: float, mark_price: Decimal) -> str:
        info = retry_sync(lambda: httpx.get(f"{self.base_url}/fapi/v1/exchangeInfo", timeout=10.0))
        info.raise_for_status()
        symbol_info = next(item for item in info.json()["symbols"] if item["symbol"] == instrument.venue_symbol)
        quantity_precision = int(symbol_info.get("quantityPrecision", 3))
        raw_quantity = Decimal(str(size_usd)) / mark_price
        quantum = Decimal("1").scaleb(-quantity_precision)
        quantity = raw_quantity.quantize(quantum, rounding=ROUND_DOWN)
        return format(quantity, "f")

    def _signed_request(self, method: str, path: str, params: dict) -> dict:
        query = urlencode(params, doseq=True)
        signature = hmac.HMAC(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers = {"X-MBX-APIKEY": self.api_key}
        with httpx.Client(base_url=self.base_url, timeout=15.0, headers=headers) as client:
            response = retry_sync(lambda: client.request(method, f"{path}?{query}&signature={signature}"))
            response.raise_for_status()
            return response.json()


class HyperliquidSdkAdapter(LiveExecutionAdapter):
    venue = "hyperliquid"

    def __init__(self) -> None:
        self.private_key = secret_or_env("hyperliquid_private_key") or ""
        self.account_address = secret_or_env("hyperliquid_account_address") or ""
        self.base_url = settings.hyperliquid_base_url

    def preview_order(self, instrument: Instrument, direction: str, action: str, size_usd: float) -> ExecutionPreview:
        estimated_fee_usd = round(size_usd * 0.00035, 4)
        return ExecutionPreview(
            instrument_key=instrument.key,
            direction=direction,
            action=action,
            size_usd=size_usd,
            estimated_fee_usd=estimated_fee_usd,
            estimated_slippage_bps=settings.paper_slippage_bps,
            notional_limit_ok=size_usd <= 5_000,
            approval_required=settings.live_approval_mode,
        )

    def submit_order(self, instrument: Instrument, direction: str, action: str, size_usd: float) -> dict:
        if not settings.live_network_enabled:
            return {
                "broker_order_id": f"hyperliquid-dry:{instrument.symbol}:{datetime.now(timezone.utc).timestamp()}",
                "status": "network_disabled",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "transport": "hyperliquid_sdk_scaffold",
            }
        try:
            from hyperliquid.exchange import Exchange  # type: ignore
            from hyperliquid.info import Info  # type: ignore
            from eth_account import Account  # type: ignore
        except Exception as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError("hyperliquid_sdk_not_installed") from exc

        account = Account.from_key(self.private_key)
        info = Info(self.base_url, skip_ws=True)
        exchange = Exchange(account, self.base_url, account_address=self.account_address or account.address)
        mids = info.all_mids()
        mark_price = Decimal(str(mids[instrument.symbol]))
        quantity = float((Decimal(str(size_usd)) / mark_price).quantize(Decimal("0.001"), rounding=ROUND_DOWN))
        is_buy = direction == "long"
        result = exchange.market_open(instrument.symbol, is_buy, quantity, None if action == "open" else True)
        return {
            "broker_order_id": result.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("resting", {}).get("oid"),
            "status": "submitted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "transport": "hyperliquid_sdk",
            "response": result,
        }

    def reconcile(self) -> dict:
        if not settings.live_network_enabled:
            return {
                "venue": self.venue,
                "status": "hyperliquid_network_disabled",
                "remote_positions": [],
                "remote_orders": [],
                "notes": "Hyperliquid SDK adapter is configured, but LIVE_NETWORK_ENABLED is false.",
            }
        try:
            from hyperliquid.info import Info  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("hyperliquid_sdk_not_installed") from exc

        info = Info(self.base_url, skip_ws=True)
        address = self.account_address
        positions = info.user_state(address).get("assetPositions", [])
        orders = info.open_orders(address)
        return {
            "venue": self.venue,
            "status": "hyperliquid_reconciled",
            "remote_positions": positions,
            "remote_orders": orders,
            "notes": "Hyperliquid SDK reconciliation completed.",
        }


def adapter_for_venue(venue: str) -> LiveExecutionAdapter:
    if venue == "binance" and secret_or_env("binance_api_key") and secret_or_env("binance_api_secret"):
        return BinanceFuturesAdapter()
    if venue == "hyperliquid" and secret_or_env("hyperliquid_private_key") and secret_or_env("hyperliquid_account_address"):
        return HyperliquidSdkAdapter()
    return ApprovalModeAdapter(venue)

```

## `backend/execution/service.py`

```python
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from backend.core.config import settings
from backend.core.types import Instrument, Venue, VenueMode
from backend.data.storage import fetch_all, fetch_one, save_json_record
from backend.execution.adapters import adapter_for_venue
from backend.ops.alerts import notify_event
from backend.ops.audit import record_audit_event
from backend.secrets.vault import secret_or_env
from backend.worker.jobs import enqueue_job


def create_execution_ticket(
    spec_id: str,
    symbol: str,
    venue: str,
    direction: str,
    action: str,
    size_usd: float,
    requested_by: str | None = "operator",
    rationale: str | None = None,
) -> dict:
    instrument = Instrument(symbol=symbol, venue=Venue(venue), mode=VenueMode.PERP)
    adapter = adapter_for_venue(venue)
    preview = adapter.preview_order(instrument, direction, action, size_usd)
    ticket = {
        "ticket_id": str(uuid.uuid4()),
        "spec_id": spec_id,
        "symbol": symbol,
        "venue": venue,
        "direction": direction,
        "action": action,
        "size_usd": size_usd,
        "status": "pending_approval",
        "approval_mode": "manual" if settings.live_approval_mode else "direct",
        "requested_by": requested_by,
        "rationale": rationale,
        "preview_json": json.dumps(preview.__dict__),
        "broker_order_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approved_at": None,
        "submitted_at": None,
    }
    save_json_record("execution_tickets", ticket, "ticket_id")
    record_audit_event(
        event_type="execution.ticket_created",
        entity_type="execution_ticket",
        entity_id=ticket["ticket_id"],
        payload={
            "spec_id": spec_id,
            "symbol": symbol,
            "venue": venue,
            "direction": direction,
            "action": action,
            "size_usd": size_usd,
        },
    )
    return hydrate_ticket(ticket)


def hydrate_ticket(row: dict) -> dict:
    item = dict(row)
    item["preview"] = json.loads(item.pop("preview_json"))
    return item


def list_execution_tickets(limit: int = 100) -> list[dict]:
    rows = fetch_all("SELECT * FROM execution_tickets ORDER BY created_at DESC LIMIT ?", [int(limit)])
    return [hydrate_ticket(dict(row)) for row in rows]


def approve_execution_ticket(ticket_id: str, approved_by: str = "operator") -> dict:
    row = fetch_one("SELECT * FROM execution_tickets WHERE ticket_id=?", [ticket_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Execution ticket not found")
    ticket = dict(row)
    if ticket["status"] not in {"pending_approval", "blocked"}:
        return hydrate_ticket(ticket)

    preview = json.loads(ticket["preview_json"])
    if not preview["notional_limit_ok"]:
        ticket["status"] = "blocked"
    elif not settings.live_trading_enabled:
        ticket["status"] = "blocked"
    elif not live_secrets_status()["all_present"]:
        ticket["status"] = "blocked"
    else:
        job = enqueue_job(
            "execution_submit",
            {
                "ticket_id": ticket_id,
                "spec_id": ticket["spec_id"],
                "symbol": ticket["symbol"],
                "venue": ticket["venue"],
                "direction": ticket["direction"],
                "action": ticket["action"],
                "size_usd": float(ticket["size_usd"]),
            },
            priority=10,
        )
        ticket["status"] = "queued"
        ticket["broker_order_id"] = job["job_id"]

    ticket["approved_at"] = datetime.now(timezone.utc).isoformat()
    save_json_record("execution_tickets", ticket, "ticket_id")
    if ticket["status"] == "blocked":
        notify_event(
            "execution_blocked",
            f"Execution blocked for {ticket['symbol']} {ticket['venue']}",
            {"ticket_id": ticket_id, "preview": preview},
        )
    record_audit_event(
        event_type="execution.ticket_approved",
        entity_type="execution_ticket",
        entity_id=ticket_id,
        payload={"approved_by": approved_by, "status": ticket["status"]},
    )
    return hydrate_ticket(ticket)


def reject_execution_ticket(ticket_id: str, reason: str, rejected_by: str = "operator") -> dict:
    row = fetch_one("SELECT * FROM execution_tickets WHERE ticket_id=?", [ticket_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Execution ticket not found")
    ticket = dict(row)
    ticket["status"] = "rejected"
    ticket["rationale"] = reason
    ticket["approved_at"] = datetime.now(timezone.utc).isoformat()
    save_json_record("execution_tickets", ticket, "ticket_id")
    record_audit_event(
        event_type="execution.ticket_rejected",
        entity_type="execution_ticket",
        entity_id=ticket_id,
        payload={"rejected_by": rejected_by, "reason": reason},
    )
    return hydrate_ticket(ticket)


def live_secrets_status() -> dict:
    per_venue = {
        "binance": bool(secret_or_env("binance_api_key") and secret_or_env("binance_api_secret")),
        "hyperliquid": bool(secret_or_env("hyperliquid_private_key") and secret_or_env("hyperliquid_account_address")),
    }
    return {"all_present": all(per_venue.values()), "venues": per_venue}


def reconcile_venue(venue: str) -> dict:
    adapter = adapter_for_venue(venue)
    summary = adapter.reconcile()
    record = {
        "reconciliation_id": str(uuid.uuid4()),
        "venue": venue,
        "status": summary["status"],
        "summary_json": json.dumps(summary),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_json_record("execution_reconciliation", record, "reconciliation_id")
    record_audit_event(
        event_type="execution.reconciled",
        entity_type="execution_reconciliation",
        entity_id=record["reconciliation_id"],
        payload=summary,
    )
    return {
        "reconciliation_id": record["reconciliation_id"],
        "venue": venue,
        "status": summary["status"],
        "summary": summary,
        "created_at": record["created_at"],
    }


def process_execution_job(payload: dict) -> dict:
    ticket_id = payload["ticket_id"]
    row = fetch_one("SELECT * FROM execution_tickets WHERE ticket_id=?", [ticket_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Execution ticket not found")
    ticket = dict(row)
    instrument = Instrument(symbol=ticket["symbol"], venue=Venue(ticket["venue"]), mode=VenueMode.PERP)
    adapter = adapter_for_venue(ticket["venue"])
    submitted = adapter.submit_order(instrument, ticket["direction"], ticket["action"], float(ticket["size_usd"]))
    ticket["status"] = "submitted"
    ticket["broker_order_id"] = submitted["broker_order_id"]
    ticket["submitted_at"] = submitted["submitted_at"]
    save_json_record("execution_tickets", ticket, "ticket_id")
    record_audit_event(
        event_type="execution.ticket_submitted",
        entity_type="execution_ticket",
        entity_id=ticket_id,
        payload={"broker_order_id": ticket["broker_order_id"], "transport": submitted.get("transport", "unknown")},
    )
    return {"ticket_id": ticket_id, "submission": submitted}


def list_reconciliation(limit: int = 50) -> list[dict]:
    rows = fetch_all("SELECT * FROM execution_reconciliation ORDER BY created_at DESC LIMIT ?", [int(limit)])
    return [
        {
            "reconciliation_id": row["reconciliation_id"],
            "venue": row["venue"],
            "status": row["status"],
            "summary": json.loads(row["summary_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]

```

## `backend/execution/__init__.py`

```python
from __future__ import annotations


```

## `backend/ops/alerts.py`

```python
from __future__ import annotations

import smtplib
from email.message import EmailMessage

import httpx

from backend.core.config import settings
from backend.core.retry import retry_sync


def _send_telegram(message: str) -> bool:
    if not settings.alerts_telegram_bot_token or not settings.alerts_telegram_chat_id:
        return False
    url = f"https://api.telegram.org/bot{settings.alerts_telegram_bot_token}/sendMessage"
    payload = {"chat_id": settings.alerts_telegram_chat_id, "text": message}
    response = retry_sync(lambda: httpx.post(url, json=payload, timeout=10.0))
    response.raise_for_status()
    return True


def _send_discord(message: str) -> bool:
    if not settings.alerts_discord_webhook_url:
        return False
    response = retry_sync(
        lambda: httpx.post(
            settings.alerts_discord_webhook_url,
            json={"content": message},
            timeout=10.0,
        )
    )
    response.raise_for_status()
    return True


def _send_email(subject: str, body: str) -> bool:
    if not (settings.alerts_email_smtp_host and settings.alerts_email_to and settings.alerts_email_from):
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.alerts_email_from
    msg["To"] = settings.alerts_email_to
    msg.set_content(body)
    with smtplib.SMTP(settings.alerts_email_smtp_host, settings.alerts_email_smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if settings.alerts_email_username:
            smtp.login(settings.alerts_email_username, settings.alerts_email_password)
        smtp.send_message(msg)
    return True


def notify_event(event_type: str, title: str, details: dict) -> dict:
    message = f"[{event_type}] {title}\n{details}"
    sent = {"telegram": False, "discord": False, "email": False}
    try:
        sent["telegram"] = _send_telegram(message)
    except Exception:
        sent["telegram"] = False
    try:
        sent["discord"] = _send_discord(message)
    except Exception:
        sent["discord"] = False
    try:
        sent["email"] = _send_email(f"CryptoSwarms {event_type}", message)
    except Exception:
        sent["email"] = False
    return sent

```

## `backend/ops/audit.py`

```python
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from backend.data.storage import fetch_all, save_json_record


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_audit_event(event_type: str, entity_type: str, entity_id: str, payload: dict) -> dict:
    record = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload_json": json.dumps(payload),
        "created_at": _now_iso(),
    }
    save_json_record("audit_events", record, "event_id")
    return record


def list_audit_events(limit: int = 50) -> list[dict]:
    rows = fetch_all("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?", [int(limit)])
    return [
        {
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def record_paper_cycle_event(
    spec_id: str,
    symbol: str,
    venue: str,
    timeframe: str,
    event_type: str,
    reason: str,
    payload: dict,
) -> dict:
    record = {
        "event_id": str(uuid.uuid4()),
        "spec_id": spec_id,
        "symbol": symbol,
        "venue": venue,
        "timeframe": timeframe,
        "event_type": event_type,
        "reason": reason,
        "payload_json": json.dumps(payload),
        "created_at": _now_iso(),
    }
    save_json_record("paper_cycle_events", record, "event_id")
    record_audit_event(
        event_type=f"paper.{event_type}",
        entity_type="paper_target",
        entity_id=f"{spec_id}:{symbol}:{venue}",
        payload={"reason": reason, **payload},
    )
    return record


def list_paper_cycle_events(limit: int = 100) -> list[dict]:
    rows = fetch_all("SELECT * FROM paper_cycle_events ORDER BY created_at DESC LIMIT ?", [int(limit)])
    return [
        {
            "event_id": row["event_id"],
            "spec_id": row["spec_id"],
            "symbol": row["symbol"],
            "venue": row["venue"],
            "timeframe": row["timeframe"],
            "event_type": row["event_type"],
            "reason": row["reason"],
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]

```

## `backend/ops/backup.py`

```python
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from backend.core.config import settings
from backend.data.storage import get_sqlite


def backup_datastores() -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = Path("./data/backups") / ts
    backup_root.mkdir(parents=True, exist_ok=True)

    sqlite_src = settings.meta_db_path
    duckdb_src = settings.curated_db_path
    sqlite_dst = backup_root / sqlite_src.name
    duckdb_dst = backup_root / duckdb_src.name
    if sqlite_src.exists():
        shutil.copy2(sqlite_src, sqlite_dst)
    if duckdb_src.exists():
        shutil.copy2(duckdb_src, duckdb_dst)

    integrity = get_sqlite().execute("PRAGMA integrity_check").fetchone()[0]
    return {
        "created_at": ts,
        "backup_dir": str(backup_root),
        "sqlite_copied": sqlite_dst.exists(),
        "duckdb_copied": duckdb_dst.exists(),
        "sqlite_integrity": integrity,
    }

```

## `backend/ops/metrics.py`

```python
from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "workbench_http_requests_total",
    "Total HTTP requests by path and method.",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "workbench_http_request_latency_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)
PAPER_POSITION_GAUGE = Gauge("workbench_open_positions", "Current open paper positions.")
WORKER_QUEUE_GAUGE = Gauge("workbench_worker_queue_depth", "Current queued jobs.")
TRADE_EVENTS = Counter(
    "workbench_trade_events_total",
    "Paper trade events.",
    ["event_type", "spec_id"],
)


def prometheus_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST

```

## `backend/ops/readiness.py`

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.core.config import settings
from backend.data.storage import fetch_all
from backend.execution.service import live_secrets_status
from backend.paper.activity import portfolio_snapshot
from backend.strategy.targets import best_target_snapshot
from backend.worker.service import worker_health

FRESHNESS_WINDOWS = {
    "15m": timedelta(minutes=30),
    "1h": timedelta(hours=2),
    "4h": timedelta(hours=6),
}


def _parse_ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def readiness_snapshot() -> dict:
    now = datetime.now(timezone.utc)
    health_rows = [dict(row) for row in fetch_all("SELECT * FROM dataset_health ORDER BY instrument_key, timeframe", [])]
    audit_count = fetch_all("SELECT COUNT(*) AS count FROM audit_events", [])[0]["count"] if health_rows is not None else 0
    paper_event_count = fetch_all("SELECT COUNT(*) AS count FROM paper_cycle_events", [])[0]["count"]
    reconciliation_count = fetch_all("SELECT COUNT(*) AS count FROM execution_reconciliation", [])[0]["count"]
    promoted_targets = fetch_all(
        "SELECT COUNT(*) AS count FROM strategy_targets WHERE status='promoted'",
        [],
    )[0]["count"]
    paper_targets = fetch_all(
        "SELECT COUNT(*) AS count FROM strategy_targets WHERE paper_enabled=1 AND status IN ('candidate','promoted')",
        [],
    )[0]["count"]

    health_issues: list[str] = []
    healthy_rows = 0
    fresh_rows = 0
    for row in health_rows:
        if row["quality"] == "healthy":
            healthy_rows += 1
        last_bar_ts = _parse_ts(row["last_bar_ts"])
        freshness_limit = FRESHNESS_WINDOWS.get(row["timeframe"], timedelta(hours=2))
        if last_bar_ts and now - last_bar_ts <= freshness_limit:
            fresh_rows += 1
        else:
            health_issues.append(f"stale_dataset:{row['instrument_key']}:{row['timeframe']}")
        if row["quality"] != "healthy":
            health_issues.append(f"quality_{row['quality']}:{row['instrument_key']}:{row['timeframe']}")
        if float(row["coverage_days"] or 0.0) < settings.data_readiness_coverage_days:
            health_issues.append(f"low_coverage:{row['instrument_key']}:{row['timeframe']}")

    data_ready = bool(health_rows) and not health_issues
    paper_ready = paper_targets > 0 and paper_event_count >= settings.paper_readiness_min_events
    best_target = best_target_snapshot()
    portfolio = portfolio_snapshot(limit=20)
    secrets = live_secrets_status()
    workers = worker_health()

    blockers: list[str] = []
    if not data_ready:
        blockers.append("data_health_not_ready")
    if promoted_targets == 0:
        blockers.append("no_promoted_targets")
    if paper_targets == 0:
        blockers.append("no_active_paper_targets")
    if paper_event_count < settings.paper_readiness_min_events:
        blockers.append("insufficient_paper_event_history")
    if not settings.paper_trading_enabled:
        blockers.append("paper_trading_disabled")
    if not settings.live_trading_enabled:
        blockers.append("live_trading_disabled_by_config")
    if not secrets["all_present"]:
        blockers.append("live_exchange_secrets_missing")
    if reconciliation_count == 0:
        blockers.append("no_execution_reconciliation_history")
    if not workers["healthy"]:
        blockers.append("worker_unhealthy")

    live_ready = (
        settings.live_trading_enabled
        and data_ready
        and promoted_targets > 0
        and paper_ready
        and secrets["all_present"]
        and reconciliation_count > 0
        and len(portfolio["positions"]) <= settings.paper_max_open_positions
    )

    return {
        "generated_at": now.isoformat(),
        "summary": {
            "data_ready": data_ready,
            "paper_ready": paper_ready,
            "live_ready": live_ready,
            "blockers": blockers,
        },
        "counts": {
            "datasets": len(health_rows),
            "healthy_datasets": healthy_rows,
            "fresh_datasets": fresh_rows,
            "audit_events": audit_count,
            "paper_cycle_events": paper_event_count,
            "reconciliation_runs": reconciliation_count,
            "promoted_targets": promoted_targets,
            "active_paper_targets": paper_targets,
            "open_positions": len(portfolio["positions"]),
            "workers": len(workers["workers"]),
        },
        "risk": {
            "paper_trading_enabled": settings.paper_trading_enabled,
            "live_trading_enabled": settings.live_trading_enabled,
            "live_approval_mode": settings.live_approval_mode,
            "paper_max_open_positions": settings.paper_max_open_positions,
            "paper_max_gross_exposure_usd": settings.paper_max_gross_exposure_usd,
            "paper_max_signal_correlation": settings.paper_max_signal_correlation,
            "paper_daily_loss_limit_usd": settings.paper_daily_loss_limit_usd,
            "live_secrets": secrets,
            "worker_health": workers["healthy"],
        },
        "best_target": best_target,
        "recent_health_issues": health_issues[:20],
    }

```

## `backend/ops/__init__.py`

```python
from __future__ import annotations


```

## `backend/paper/activity.py`

```python
from __future__ import annotations

import json
from datetime import datetime, timezone

from backend.core.types import Instrument, Venue, VenueMode
from backend.data.storage import fetch_all, get_mark_price
from backend.ops.metrics import PAPER_POSITION_GAUGE
from backend.strategy.targets import list_active_paper_targets


def _decode_instrument(raw_json: str) -> dict:
    inst = json.loads(raw_json)
    return {
        "symbol": inst["symbol"],
        "venue": inst["venue"],
        "mode": inst.get("mode", "perp"),
        "quote": inst.get("quote", "USDT"),
    }


def list_open_positions() -> list[dict]:
    rows = fetch_all("SELECT * FROM paper_positions WHERE closed_at IS NULL ORDER BY opened_at DESC", [])
    positions: list[dict] = []
    for row in rows:
        item = dict(row)
        item.update(_decode_instrument(item.pop("instrument_json")))
        instrument = Instrument(symbol=item["symbol"], venue=Venue(item["venue"]), mode=VenueMode(item.get("mode", "perp")))
        mark = get_mark_price(instrument.key)
        if mark:
            item["mark_price"] = mark["price"]
            item["mark_ts"] = mark["ts"]
        positions.append(item)
    return positions


def list_recent_positions(limit: int = 100) -> list[dict]:
    rows = fetch_all("SELECT * FROM paper_positions ORDER BY COALESCE(closed_at, opened_at) DESC LIMIT ?", [int(limit)])
    positions: list[dict] = []
    for row in rows:
        item = dict(row)
        item.update(_decode_instrument(item.pop("instrument_json")))
        positions.append(item)
    return positions


def list_recent_orders(limit: int = 50) -> list[dict]:
    rows = fetch_all("SELECT * FROM paper_orders ORDER BY COALESCE(filled_at, triggered_at) DESC LIMIT ?", [int(limit)])
    orders: list[dict] = []
    for row in rows:
        item = dict(row)
        item.update(_decode_instrument(item.pop("instrument_json")))
        orders.append(item)
    return orders


def summarize_target_activity(limit: int = 50) -> tuple[list[dict], list[dict], list[dict]]:
    active_targets = [
        {
            "spec_id": row["spec_id"],
            "name": row["name"],
            "symbol": row["symbol"],
            "venue": row["venue"],
            "status": row["status"],
            "paper_enabled": row["paper_enabled"],
            "last_backtest_run_id": row["last_backtest_run_id"],
        }
        for row in list_active_paper_targets()
    ]
    open_positions = list_open_positions()
    recent_positions = list_recent_positions(limit)
    recent_orders = list_recent_orders(limit)

    activity: list[dict] = []
    for target in active_targets:
        key = (target["spec_id"], target["symbol"], target["venue"])
        target_open_positions = [
            row for row in open_positions if (row["spec_id"], row["symbol"], row["venue"]) == key
        ]
        target_positions = [
            row for row in recent_positions if (row["spec_id"], row["symbol"], row["venue"]) == key
        ]
        target_orders = [
            row for row in recent_orders if (row["spec_id"], row["symbol"], row["venue"]) == key
        ]
        last_order = target_orders[0] if target_orders else None
        event_times = [
            row["filled_at"] or row["triggered_at"]
            for row in target_orders
            if row.get("filled_at") or row.get("triggered_at")
        ]
        event_times.extend(
            row["closed_at"] or row["opened_at"]
            for row in target_positions
            if row.get("closed_at") or row.get("opened_at")
        )
        last_event_at = max(event_times) if event_times else None
        realized_pnl_usd = sum(float(row.get("realized_pnl_usd") or 0.0) for row in target_positions)
        activity.append(
            {
                **target,
                "open_positions": len(target_open_positions),
                "recent_orders": len(target_orders),
                "last_event_at": last_event_at,
                "last_order_action": last_order["action"] if last_order else None,
                "last_order_status": last_order["status"] if last_order else None,
                "last_direction": last_order["direction"] if last_order else None,
                "last_fill_price": last_order["fill_price"] if last_order else None,
                "realized_pnl_usd": realized_pnl_usd,
            }
        )
    activity.sort(
        key=lambda item: (
            datetime.fromisoformat(item["last_event_at"])
            if item["last_event_at"]
            else datetime.min.replace(tzinfo=timezone.utc)
        ),
        reverse=True,
    )
    return active_targets, activity, recent_orders


def portfolio_snapshot(limit: int = 50) -> dict:
    positions = list_open_positions()
    PAPER_POSITION_GAUGE.set(len(positions))
    active_targets, target_activity, recent_orders = summarize_target_activity(limit=limit)
    total_unrealized = sum(float(position["unrealized_pnl_usd"]) for position in positions)
    return {
        "positions": positions,
        "orders": recent_orders,
        "active_targets": active_targets,
        "target_activity": target_activity,
        "total_unrealized_pnl_usd": total_unrealized,
    }

```

## `backend/paper/broker.py`

```python
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from backend.core.config import settings
from backend.core.types import Instrument, PaperOrder, PaperPosition, StrategySpec
from backend.data.storage import get_sqlite
from backend.ops.audit import record_audit_event


def submit_order(spec: StrategySpec, inst: Instrument, direction: str, action: str, size_usd: float, triggered_at: datetime) -> PaperOrder:
    order = PaperOrder(
        order_id=str(uuid.uuid4()),
        spec_id=spec.spec_id,
        instrument=inst,
        direction=direction,
        action=action,
        triggered_at=triggered_at,
        size_usd=size_usd,
    )
    con = get_sqlite()
    con.execute(
        """
        INSERT INTO paper_orders (
            order_id, spec_id, instrument_json, direction, action,
            triggered_at, size_usd, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order.order_id,
            order.spec_id,
            json.dumps({"symbol": inst.symbol, "venue": inst.venue.value, "mode": inst.mode.value, "quote": inst.quote}),
            order.direction,
            order.action,
            order.triggered_at.isoformat(),
            order.size_usd,
            order.status,
        ),
    )
    con.commit()
    record_audit_event(
        event_type="paper.order_submitted",
        entity_type="paper_order",
        entity_id=order.order_id,
        payload={
            "spec_id": order.spec_id,
            "symbol": inst.symbol,
            "venue": inst.venue.value,
            "direction": order.direction,
            "action": order.action,
            "size_usd": order.size_usd,
        },
    )
    return order


def fill_order(order: PaperOrder, bar_close_price: float) -> PaperOrder:
    slip_mult = settings.paper_slippage_bps / 10_000
    if order.action == "open" and order.direction == "long":
        fill = bar_close_price * (1 + slip_mult)
    elif order.action == "open" and order.direction == "short":
        fill = bar_close_price * (1 - slip_mult)
    else:
        fill = bar_close_price
    order.fill_price = Decimal(str(round(fill, 6)))
    order.filled_at = datetime.now(timezone.utc)
    order.status = "filled"
    con = get_sqlite()
    con.execute(
        """
        UPDATE paper_orders
        SET fill_price=?, filled_at=?, status=?
        WHERE order_id=?
        """,
        (str(order.fill_price), order.filled_at.isoformat(), order.status, order.order_id),
    )
    con.commit()
    record_audit_event(
        event_type="paper.order_filled",
        entity_type="paper_order",
        entity_id=order.order_id,
        payload={
            "spec_id": order.spec_id,
            "symbol": order.instrument.symbol,
            "venue": order.instrument.venue.value,
            "fill_price": str(order.fill_price),
            "status": order.status,
        },
    )
    return order


def open_position(order: PaperOrder) -> PaperPosition:
    entry_fee = order.size_usd * (settings.paper_fee_bps / 10_000)
    position = PaperPosition(
        position_id=str(uuid.uuid4()),
        spec_id=order.spec_id,
        instrument=order.instrument,
        direction=order.direction,
        opened_at=order.filled_at or datetime.now(timezone.utc),
        entry_price=order.fill_price or Decimal("0"),
        size_usd=order.size_usd,
        entry_fees_usd=entry_fee,
    )
    con = get_sqlite()
    con.execute(
        """
        INSERT INTO paper_positions (
            position_id, spec_id, instrument_json, direction, opened_at,
            entry_price, size_usd, unrealized_pnl_usd, accrued_funding_usd, entry_fees_usd
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            position.position_id,
            position.spec_id,
            json.dumps({"symbol": position.instrument.symbol, "venue": position.instrument.venue.value, "mode": position.instrument.mode.value, "quote": position.instrument.quote}),
            position.direction,
            position.opened_at.isoformat(),
            str(position.entry_price),
            position.size_usd,
            position.unrealized_pnl_usd,
            position.accrued_funding_usd,
            position.entry_fees_usd,
        ),
    )
    con.commit()
    record_audit_event(
        event_type="paper.position_opened",
        entity_type="paper_position",
        entity_id=position.position_id,
        payload={
            "spec_id": position.spec_id,
            "symbol": position.instrument.symbol,
            "venue": position.instrument.venue.value,
            "direction": position.direction,
            "entry_price": str(position.entry_price),
            "size_usd": position.size_usd,
        },
    )
    return position


def close_position(position: PaperPosition, fill_price: float) -> float:
    entry = float(position.entry_price)
    raw_pnl = ((fill_price - entry) / entry) * position.size_usd if entry else 0.0
    if position.direction == "short":
        raw_pnl = -raw_pnl
    exit_fee = position.size_usd * (settings.paper_fee_bps / 10_000)
    realized = raw_pnl + position.accrued_funding_usd - position.entry_fees_usd - exit_fee
    con = get_sqlite()
    con.execute(
        """
        UPDATE paper_positions
        SET closed_at=?, close_price=?, realized_pnl_usd=?
        WHERE position_id=?
        """,
        (datetime.now(timezone.utc).isoformat(), str(round(fill_price, 6)), realized, position.position_id),
    )
    con.commit()
    record_audit_event(
        event_type="paper.position_closed",
        entity_type="paper_position",
        entity_id=position.position_id,
        payload={
            "spec_id": position.spec_id,
            "symbol": position.instrument.symbol,
            "venue": position.instrument.venue.value,
            "close_price": round(fill_price, 6),
            "realized_pnl_usd": realized,
        },
    )
    return realized


def update_unrealized_pnl(position_id: str, unrealized_pnl_usd: float) -> None:
    con = get_sqlite()
    con.execute(
        """
        UPDATE paper_positions
        SET unrealized_pnl_usd=?
        WHERE position_id=?
        """,
        (unrealized_pnl_usd, position_id),
    )
    con.commit()

```

## `backend/paper/portfolio.py`

```python
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

from backend.core.types import Instrument, PaperPosition, Venue, VenueMode
from backend.data.storage import fetch_all
from backend.paper.broker import update_unrealized_pnl


def _instrument_from_json(raw: str) -> Instrument:
    data = json.loads(raw)
    return Instrument(symbol=data["symbol"], venue=Venue(data["venue"]), mode=VenueMode(data["mode"]), quote=data.get("quote", "USDT"))


def list_open_positions() -> list[PaperPosition]:
    rows = fetch_all("SELECT * FROM paper_positions WHERE closed_at IS NULL ORDER BY opened_at DESC", [])
    positions: list[PaperPosition] = []
    for row in rows:
        positions.append(
            PaperPosition(
                position_id=row["position_id"],
                spec_id=row["spec_id"],
                instrument=_instrument_from_json(row["instrument_json"]),
                direction=row["direction"],
                opened_at=datetime.fromisoformat(row["opened_at"]),
                entry_price=Decimal(row["entry_price"]),
                size_usd=row["size_usd"],
                unrealized_pnl_usd=row["unrealized_pnl_usd"],
                accrued_funding_usd=row["accrued_funding_usd"],
                entry_fees_usd=float(row["entry_fees_usd"] or 0.0),
            )
        )
    return positions


def mark_to_market(symbol: str, venue: str, price: float) -> int:
    rows = fetch_all("SELECT * FROM paper_positions WHERE closed_at IS NULL ORDER BY opened_at DESC", [])
    updated = 0
    for row in rows:
        inst = _instrument_from_json(row["instrument_json"])
        if inst.symbol != symbol or inst.venue.value != venue:
            continue
        entry = float(row["entry_price"])
        raw_pnl = ((price - entry) / entry) * float(row["size_usd"]) if entry else 0.0
        if row["direction"] == "short":
            raw_pnl = -raw_pnl
        unrealized = raw_pnl + float(row["accrued_funding_usd"] or 0.0) - float(row["entry_fees_usd"] or 0.0)
        update_unrealized_pnl(row["position_id"], unrealized)
        updated += 1
    return updated

```

## `backend/paper/runner.py`

```python
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd

from backend.core.config import settings
from backend.core.types import Instrument, PaperPosition, StrategySpec, Venue, VenueMode, strategy_spec_from_dict
from backend.data.storage import fetch_all, read_bars
from backend.ops.alerts import notify_event
from backend.ops.audit import record_paper_cycle_event
from backend.ops.metrics import TRADE_EVENTS
from backend.paper.broker import close_position, fill_order, open_position, submit_order, update_unrealized_pnl
from backend.strategy.engine import get_signal
from backend.strategy.targets import instrument_for_target, list_active_paper_targets


def run_bar(current_bar: dict) -> None:
    targets = _load_active_targets()
    for target in targets:
        spec = target["spec"]
        target_inst = target["instrument"]
        if spec.primary_timeframe.value != current_bar["timeframe"]:
            continue
        if current_bar["symbol"] != target_inst.symbol or current_bar["venue"] != target_inst.venue.value:
            continue
        target_key = {
            "spec_id": spec.spec_id,
            "symbol": target_inst.symbol,
            "venue": target_inst.venue.value,
            "timeframe": current_bar["timeframe"],
        }
        signal = get_signal(spec, current_bar)
        positions = _get_open_positions(spec.spec_id, target_inst)
        close_price = float(current_bar["close"])
        if not settings.paper_trading_enabled:
            _log_cycle_event(target_key, "skipped", "paper_trading_disabled", {"signal": signal})
            continue
        risk_reason = _risk_block_reason(spec, current_bar, target_inst)
        if risk_reason:
            _log_cycle_event(target_key, "skipped", risk_reason, {"signal": signal, "close_price": close_price})
            continue
        remaining_positions: list[dict] = []
        for position in positions:
            stop_take_reason = _check_stop_take(spec, position, close_price, current_bar)
            if stop_take_reason:
                realized = close_position(_row_to_position(position), close_price)
                _log_cycle_event(
                    target_key,
                    "position_closed",
                    stop_take_reason,
                    {"position_id": position["position_id"], "realized_pnl_usd": realized},
                )
            elif position["direction"] != signal:
                realized = close_position(_row_to_position(position), close_price)
                _log_cycle_event(
                    target_key,
                    "position_closed",
                    "signal_flip",
                    {"position_id": position["position_id"], "realized_pnl_usd": realized},
                )
            else:
                entry = float(position["entry_price"])
                raw_pnl = ((close_price - entry) / entry) * float(position["size_usd"]) if entry else 0.0
                if position["direction"] == "short":
                    raw_pnl = -raw_pnl
                unrealized = raw_pnl + float(position["accrued_funding_usd"]) - float(position.get("entry_fees_usd") or 0.0)
                update_unrealized_pnl(position["position_id"], unrealized)
                remaining_positions.append(position)

        if signal in {"long", "short"} and not remaining_positions:
            size_usd = _resolve_size_usd(spec, current_bar)
            order = submit_order(spec, target_inst, signal, "open", size_usd, current_bar["ts"])
            filled = fill_order(order, close_price)
            position = open_position(filled)
            _log_cycle_event(
                target_key,
                "position_opened",
                "signal_entry",
                {
                    "order_id": order.order_id,
                    "position_id": position.position_id,
                    "direction": signal,
                    "fill_price": str(filled.fill_price),
                    "size_usd": size_usd,
                },
            )
        elif signal in {"long", "short"} and remaining_positions:
            _log_cycle_event(
                target_key,
                "skipped",
                "position_already_open",
                {"signal": signal, "open_positions": len(remaining_positions)},
            )
        else:
            _log_cycle_event(target_key, "skipped", "no_signal", {"signal": signal})


def _load_active_targets() -> list[dict]:
    rows = list_active_paper_targets()
    return [
        {
            "spec": strategy_spec_from_dict(json.loads(row["spec_json"])),
            "instrument": instrument_for_target(row),
            "target": row,
        }
        for row in rows
    ]


def _risk_block_reason(spec: StrategySpec, current_bar: dict, instrument: Instrument) -> str | None:
    volume_quote = float(current_bar.get("volume_quote") or 0.0)
    if volume_quote < spec.execution.min_volume_usd:
        return "min_volume_not_met"
    if _open_position_count() >= settings.paper_max_open_positions:
        return "max_open_positions_reached"
    if _gross_exposure_usd() >= settings.paper_max_gross_exposure_usd:
        return "gross_exposure_limit_breached"
    correlation_reason = _correlation_block_reason(spec, instrument, current_bar)
    if correlation_reason:
        return correlation_reason
    daily_realized = _daily_realized_pnl()
    if daily_realized <= -abs(settings.paper_daily_loss_limit_usd):
        return "daily_loss_limit_breached"
    return None


def _open_position_count() -> int:
    row = fetch_all("SELECT COUNT(*) AS count FROM paper_positions WHERE closed_at IS NULL", [])
    return int(row[0]["count"])


def _gross_exposure_usd() -> float:
    row = fetch_all("SELECT COALESCE(SUM(size_usd), 0) AS total FROM paper_positions WHERE closed_at IS NULL", [])
    return float(row[0]["total"] or 0.0)


def _daily_realized_pnl() -> float:
    now = datetime.now(timezone.utc)
    reset_hour = settings.paper_day_reset_hour_utc % 24
    start_of_day_dt = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
    if now < start_of_day_dt:
        start_of_day_dt -= timedelta(days=1)
    start_of_day = start_of_day_dt.isoformat()
    row = fetch_all(
        "SELECT COALESCE(SUM(realized_pnl_usd), 0) AS total FROM paper_positions WHERE closed_at IS NOT NULL AND closed_at>=?",
        [start_of_day],
    )
    return float(row[0]["total"] or 0.0)


def _check_stop_take(spec: StrategySpec, position: dict, current_price: float, current_bar: dict) -> str | None:
    entry = float(position.get("entry_price") or 0.0)
    if entry <= 0:
        return None
    pnl_pct = (current_price - entry) / entry
    if position.get("direction") == "short":
        pnl_pct = -pnl_pct
    atr = float(current_bar.get("atr_14") or 0.0)
    if atr <= 0:
        return None

    stop_mult = spec.risk_limits.stop_loss_atr_mult
    if stop_mult:
        stop_dist = (float(stop_mult) * atr) / entry
        if pnl_pct <= -stop_dist:
            return "stop_loss"

    take_mult = spec.risk_limits.take_profit_atr_mult
    if take_mult:
        take_dist = (float(take_mult) * atr) / entry
        if pnl_pct >= take_dist:
            return "take_profit"
    return None


def _resolve_size_usd(spec: StrategySpec, current_bar: dict) -> float:
    method = spec.sizing.method
    fixed = spec.sizing.fixed_notional_usd or 1_000.0
    if method == "fixed_notional":
        return float(fixed)
    if method == "vol_target":
        target_vol = float(spec.sizing.target_vol or 0.02)
        realized_vol = max(float(current_bar.get("vol_20") or 0.0), 1e-6)
        raw_size = settings.paper_initial_capital_usd * (target_vol / realized_vol)
        cap = settings.paper_initial_capital_usd * spec.sizing.max_position_pct
        return float(max(100.0, min(raw_size, cap)))
    if method == "kelly_half":
        # Conservative half-kelly proxy when no explicit expectancy model is available.
        cap = settings.paper_initial_capital_usd * spec.sizing.max_position_pct
        return float(max(100.0, min(fixed * 1.5, cap)))
    return float(fixed)


def _correlation_block_reason(spec: StrategySpec, instrument: Instrument, current_bar: dict) -> str | None:
    threshold = float(settings.paper_max_signal_correlation)
    if threshold <= 0:
        return None
    open_rows = fetch_all("SELECT instrument_json FROM paper_positions WHERE closed_at IS NULL", [])
    if not open_rows:
        return None
    as_of = current_bar.get("ts") or datetime.now(timezone.utc)
    as_of_ts = pd.Timestamp(as_of)
    if as_of_ts.tzinfo is None:
        as_of_ts = as_of_ts.tz_localize("UTC")
    else:
        as_of_ts = as_of_ts.tz_convert("UTC")
    end = as_of_ts.to_pydatetime()
    start = end - timedelta(days=14)
    target_bars = read_bars(instrument, spec.primary_timeframe, start, end)
    if target_bars.empty or len(target_bars) < 40:
        return None
    target_ret = (
        target_bars[["ts_open", "close"]]
        .sort_values("ts_open")
        .assign(target_ret=lambda frame: frame["close"].astype(float).pct_change())
        .dropna(subset=["target_ret"])
    )
    if target_ret.empty:
        return None
    for row in open_rows:
        inst_json = json.loads(row["instrument_json"])
        other = Instrument(
            symbol=inst_json["symbol"],
            venue=Venue(inst_json["venue"]),
            mode=VenueMode(inst_json["mode"]),
            quote=inst_json.get("quote", "USDT"),
        )
        if other.symbol == instrument.symbol and other.venue == instrument.venue:
            continue
        other_bars = read_bars(other, spec.primary_timeframe, start, end)
        if other_bars.empty or len(other_bars) < 40:
            continue
        other_ret = (
            other_bars[["ts_open", "close"]]
            .sort_values("ts_open")
            .assign(other_ret=lambda frame: frame["close"].astype(float).pct_change())
            .dropna(subset=["other_ret"])
        )
        merged = target_ret.merge(other_ret, on="ts_open", how="inner")
        if len(merged) < 20:
            continue
        corr = merged["target_ret"].corr(merged["other_ret"])
        if pd.notna(corr) and abs(float(corr)) >= threshold:
            return "correlation_limit_breached"
    return None


def _log_cycle_event(target_key: dict, event_type: str, reason: str, payload: dict) -> None:
    if event_type in {"position_opened", "position_closed"}:
        TRADE_EVENTS.labels(event_type=event_type, spec_id=target_key["spec_id"]).inc()
        notify_event(event_type, f"{target_key['symbol']} {target_key['venue']} {reason}", {"target": target_key, **payload})
    if reason in {"daily_loss_limit_breached", "stop_loss"}:
        notify_event("risk_alert", reason, {"target": target_key, **payload})
    record_paper_cycle_event(
        spec_id=target_key["spec_id"],
        symbol=target_key["symbol"],
        venue=target_key["venue"],
        timeframe=target_key["timeframe"],
        event_type=event_type,
        reason=reason,
        payload=payload,
    )


def _get_open_positions(spec_id: str, instrument: Instrument) -> list[dict]:
    rows = fetch_all("SELECT * FROM paper_positions WHERE spec_id=? AND closed_at IS NULL", [spec_id])
    filtered = []
    for row in rows:
        item = dict(row)
        inst_json = json.loads(item["instrument_json"])
        if inst_json["symbol"] == instrument.symbol and inst_json["venue"] == instrument.venue.value:
            filtered.append(item)
    return filtered


def _row_to_position(row: dict) -> PaperPosition:
    inst_json = json.loads(row["instrument_json"])
    inst = Instrument(
        symbol=inst_json["symbol"],
        venue=Venue(inst_json["venue"]),
        mode=VenueMode(inst_json["mode"]),
        quote=inst_json.get("quote", "USDT"),
    )
    return PaperPosition(
        position_id=row["position_id"],
        spec_id=row["spec_id"],
        instrument=inst,
        direction=row["direction"],
        opened_at=datetime.fromisoformat(row["opened_at"]),
        entry_price=Decimal(row["entry_price"]),
        size_usd=row["size_usd"],
        unrealized_pnl_usd=row["unrealized_pnl_usd"],
        accrued_funding_usd=row["accrued_funding_usd"],
        entry_fees_usd=float(row.get("entry_fees_usd") or 0.0),
    )

```

## `backend/paper/__init__.py`

```python
"""Paper trading workflow."""

```

## `backend/research/orchestrator.py`

```python
from __future__ import annotations

import json

import httpx

from backend.core.config import settings

SYSTEM_MARKET_STRUCTURE = """
You are a market structure analyst for BTC and ETH perpetual futures.
Return JSON only with keys:
regime, confidence, funding_bias, key_observations, suggested_regime_filter_adjustments.
"""


async def run_market_structure_analysis(feature_summary: dict) -> dict:
    if not settings.openrouter_api_key:
        return {
            "regime": "unknown",
            "confidence": 0.0,
            "funding_bias": "neutral",
            "key_observations": ["OPENROUTER_API_KEY is not configured."],
            "suggested_regime_filter_adjustments": [],
        }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_MARKET_STRUCTURE},
                    {"role": "user", "content": json.dumps(feature_summary)},
                ],
                "temperature": 0.1,
                "max_tokens": 500,
            },
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]["content"]
    return json.loads(message)

```

## `backend/research/service.py`

```python
from __future__ import annotations

from datetime import datetime, timezone

from backend.core.types import Timeframe
from backend.data.service import default_instruments, latest_feature_bar_async
from backend.research.orchestrator import run_market_structure_analysis


async def build_feature_summary() -> dict:
    summary = {"generated_at": datetime.now(timezone.utc).isoformat(), "markets": []}
    for inst in default_instruments():
        bar = await latest_feature_bar_async(inst, Timeframe.H1)
        if not bar:
            continue
        summary["markets"].append(
            {
                "symbol": inst.symbol,
                "venue": inst.venue.value,
                "ret_4": float(bar.get("ret_4", 0.0)),
                "vol_20": float(bar.get("vol_20", 0.0)),
                "vol_ratio": float(bar.get("vol_ratio", 0.0)),
                "funding_zscore": float(bar.get("funding_zscore", 0.0)),
                "oi_change_pct": float(bar.get("oi_change_pct", 0.0)),
            }
        )
    return summary


async def research_digest() -> dict:
    feature_summary = await build_feature_summary()
    analysis = await run_market_structure_analysis(feature_summary)
    return {"feature_summary": feature_summary, "analysis": analysis}

```

## `backend/research/__init__.py`

```python
"""Agent-assisted research orchestration."""

```

## `backend/research/agents/catalyst.py`

```python
SYSTEM_PROMPT = "Summarize catalyst and news impact for BTC and ETH as structured JSON."

```

## `backend/research/agents/market_structure.py`

```python
SYSTEM_PROMPT = "Analyze BTC and ETH market structure and output JSON only."

```

## `backend/research/agents/risk_review.py`

```python
SYSTEM_PROMPT = "Review strategy risk and operational caveats. Output JSON only."

```

## `backend/research/agents/__init__.py`

```python
"""Research agent prompts and helpers."""

```

## `backend/secrets/vault.py`

```python
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTOGRAPHY_AVAILABLE = True
except ModuleNotFoundError:
    Fernet = None
    hashes = None
    PBKDF2HMAC = None
    CRYPTOGRAPHY_AVAILABLE = False

from backend.core.config import settings

VAULT_KEYS = {
    "binance_api_key",
    "binance_api_secret",
    "hyperliquid_private_key",
    "hyperliquid_account_address",
}


def _require_cryptography() -> None:
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError("vault_dependency_missing")


def _vault_path() -> Path:
    path = settings.vault_file_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_passphrase(passphrase: str | None = None) -> str:
    resolved = passphrase or settings.vault_passphrase
    if not resolved:
        raise ValueError("vault_passphrase_required")
    return resolved


def _derive_fernet(passphrase: str, salt: bytes) -> Fernet:
    _require_cryptography()
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000)
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    return Fernet(key)


def _read_vault(passphrase: str | None = None) -> dict[str, str]:
    path = _vault_path()
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    salt = base64.b64decode(payload["salt"])
    fernet = _derive_fernet(_resolve_passphrase(passphrase), salt)
    decrypted = fernet.decrypt(payload["ciphertext"].encode("utf-8")).decode("utf-8")
    return json.loads(decrypted)


def _write_vault(data: dict[str, str], passphrase: str | None = None) -> None:
    path = _vault_path()
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    salt = base64.b64decode(existing["salt"]) if existing else os.urandom(16)
    fernet = _derive_fernet(_resolve_passphrase(passphrase), salt)
    ciphertext = fernet.encrypt(json.dumps(data).encode("utf-8")).decode("utf-8")
    path.write_text(
        json.dumps({"salt": base64.b64encode(salt).decode("utf-8"), "ciphertext": ciphertext}, indent=2),
        encoding="utf-8",
    )


def set_secret(name: str, value: str, passphrase: str | None = None) -> dict:
    _require_cryptography()
    if name not in VAULT_KEYS:
        raise ValueError("unsupported_secret_name")
    data = _read_vault(passphrase)
    data[name] = value
    _write_vault(data, passphrase)
    return vault_status(passphrase)


def delete_secret(name: str, passphrase: str | None = None) -> dict:
    _require_cryptography()
    data = _read_vault(passphrase)
    data.pop(name, None)
    _write_vault(data, passphrase)
    return vault_status(passphrase)


def get_secret(name: str, passphrase: str | None = None) -> str | None:
    try:
        data = _read_vault(passphrase)
    except (ValueError, RuntimeError):
        return None
    return data.get(name)


def secret_or_env(name: str) -> str | None:
    return get_secret(name) or getattr(settings, name, "")


def vault_status(passphrase: str | None = None) -> dict:
    path = _vault_path()
    data: dict[str, str] = {}
    unlocked = False
    dependency_error = None
    try:
        data = _read_vault(passphrase)
        unlocked = True
    except RuntimeError as exc:
        dependency_error = str(exc)
        unlocked = False
    except Exception:
        unlocked = False
    return {
        "path": str(path),
        "available": CRYPTOGRAPHY_AVAILABLE,
        "exists": path.exists(),
        "unlocked": unlocked,
        "configured_keys": sorted(data.keys()) if unlocked else [],
        "required_keys": sorted(VAULT_KEYS),
        "dependency_error": dependency_error,
    }

```

## `backend/secrets/__init__.py`

```python
from __future__ import annotations


```

## `backend/strategy/engine.py`

```python
from __future__ import annotations

from backend.core.types import RuleBlock, StrategySpec


def evaluate_rule(rule: RuleBlock, features: dict[str, float]) -> bool:
    if rule.feature not in features:
        return False
    value = features[rule.feature]
    threshold = rule.threshold
    match rule.operator:
        case "gt":
            return value > threshold
        case "lt":
            return value < threshold
        case "gte":
            return value >= threshold
        case "lte":
            return value <= threshold
        case "eq":
            return value == threshold
        case "neq":
            return value != threshold
        case "between":
            lower, upper = threshold
            return lower <= value <= upper
        case "crossover":
            previous = features.get(f"{rule.feature}_prev")
            return previous is not None and previous <= threshold < value
        case "crossunder":
            previous = features.get(f"{rule.feature}_prev")
            return previous is not None and previous >= threshold > value
        case _:
            return False


def evaluate_rules(rules: list[RuleBlock], features: dict[str, float]) -> bool:
    return all(evaluate_rule(rule, features) for rule in rules)


def get_signal(spec: StrategySpec, features: dict[str, float]) -> str:
    if spec.regime_filters and not evaluate_rules(spec.regime_filters, features):
        return "flat"
    if spec.entry_long and evaluate_rules(spec.entry_long, features):
        return "long"
    if spec.entry_short and evaluate_rules(spec.entry_short, features):
        return "short"
    return "flat"

```

## `backend/strategy/registry.py`

```python
from __future__ import annotations

import json

from backend.core.types import StrategySpec, dataclass_to_dict, strategy_spec_from_dict
from backend.data.storage import fetch_all, fetch_one, save_json_record
from backend.strategy.signals import funding_reversion, momentum, vol_regime
from backend.strategy.targets import strategy_status_summary


BUILTIN_BUILDERS = (
    funding_reversion.build,
    momentum.build,
    vol_regime.build,
)


def bootstrap_builtin_specs() -> None:
    for builder in BUILTIN_BUILDERS:
        spec = builder()
        row = fetch_one("SELECT spec_id FROM strategy_specs WHERE spec_id=?", [spec.spec_id])
        if row is None:
            save_json_record(
                "strategy_specs",
                {
                    "spec_id": spec.spec_id,
                    "name": spec.name,
                    "version": spec.version,
                    "parent_id": spec.parent_id,
                    "status": "proposed",
                    "spec_json": json.dumps(dataclass_to_dict(spec)),
                    "created_at": spec.created_at.isoformat(),
                },
                "spec_id",
            )


def list_specs() -> list[dict]:
    rows = fetch_all("SELECT spec_id, name, version, parent_id, status, created_at, spec_json FROM strategy_specs ORDER BY created_at DESC", [])
    results = []
    for row in rows:
        target_summary = strategy_status_summary(row["spec_id"])
        results.append(
            {
                "spec_id": row["spec_id"],
                "name": row["name"],
                "version": row["version"],
                "parent_id": row["parent_id"],
                "status": target_summary["status"],
                "created_at": row["created_at"],
                "spec": json.loads(row["spec_json"]),
                "paper_enabled_count": target_summary["paper_enabled_count"],
                "targets": target_summary["targets"],
            }
        )
    return results


def load_spec(spec_id: str) -> StrategySpec | None:
    row = fetch_one("SELECT spec_json FROM strategy_specs WHERE spec_id=?", [spec_id])
    if row is None:
        return None
    return strategy_spec_from_dict(json.loads(row["spec_json"]))

```

## `backend/strategy/spec.py`

```python
from __future__ import annotations

from backend.core.types import Instrument, StrategySpec, Timeframe, Venue, VenueMode


def major_perp_universe() -> list[Instrument]:
    return [
        Instrument(symbol="BTC", venue=Venue.BINANCE, mode=VenueMode.PERP),
        Instrument(symbol="ETH", venue=Venue.BINANCE, mode=VenueMode.PERP),
        Instrument(symbol="BTC", venue=Venue.HYPERLIQUID, mode=VenueMode.PERP),
        Instrument(symbol="ETH", venue=Venue.HYPERLIQUID, mode=VenueMode.PERP),
    ]


def new_strategy(name: str, hypothesis: str, feature_inputs: list[str], primary_timeframe: Timeframe = Timeframe.H1) -> StrategySpec:
    slug = name.lower().replace(" ", "-")
    return StrategySpec(
        spec_id=f"builtin-{slug}",
        name=name,
        hypothesis=hypothesis,
        feature_inputs=feature_inputs,
        primary_timeframe=primary_timeframe,
        universe=major_perp_universe(),
    )

```

## `backend/strategy/targets.py`

```python
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from backend.core.types import Instrument, Venue, VenueMode
from backend.data.storage import fetch_all, fetch_one, save_json_record

STATUS_PRIORITY = {
    "rejected": 0,
    "proposed": 1,
    "shortlist": 2,
    "candidate": 3,
    "promoted": 4,
}

DEFAULT_TARGET = {
    "spec_id": "builtin-range-breakout",
    "symbol": "ETH",
    "venue": "binance",
    "mode": "perp",
    "timeframe": "1h",
    "status": "candidate",
    "paper_enabled": 0,
    "notes": "Seeded as the first paper candidate based on the strongest early result.",
}


def bootstrap_default_target() -> None:
    row = fetch_one(
        "SELECT target_id FROM strategy_targets WHERE spec_id=? AND symbol=? AND venue=?",
        [DEFAULT_TARGET["spec_id"], DEFAULT_TARGET["symbol"], DEFAULT_TARGET["venue"]],
    )
    if row is None:
        save_target(DEFAULT_TARGET)


def save_target(payload: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    existing = fetch_one(
        "SELECT target_id FROM strategy_targets WHERE spec_id=? AND symbol=? AND venue=?",
        [payload["spec_id"], payload["symbol"], payload["venue"]],
    )
    target_id = payload.get("target_id") or (existing["target_id"] if existing else str(uuid.uuid4()))
    record = {
        "target_id": target_id,
        "spec_id": payload["spec_id"],
        "symbol": payload["symbol"],
        "venue": payload["venue"],
        "mode": payload.get("mode", "perp"),
        "timeframe": payload.get("timeframe", "1h"),
        "status": payload.get("status", "shortlist"),
        "paper_enabled": 1 if payload.get("paper_enabled") else 0,
        "notes": payload.get("notes"),
        "last_backtest_run_id": payload.get("last_backtest_run_id"),
        "updated_at": now,
    }
    save_json_record("strategy_targets", record, "target_id")
    from backend.ops.audit import record_audit_event

    record_audit_event(
        event_type="target.updated",
        entity_type="strategy_target",
        entity_id=record["target_id"],
        payload={
            "spec_id": record["spec_id"],
            "symbol": record["symbol"],
            "venue": record["venue"],
            "status": record["status"],
            "paper_enabled": record["paper_enabled"],
            "last_backtest_run_id": record["last_backtest_run_id"],
            "notes": record["notes"],
        },
    )
    return record


def update_target_state(spec_id: str, symbol: str, venue: str, status: str | None = None, paper_enabled: bool | None = None, notes: str | None = None, last_backtest_run_id: str | None = None) -> dict:
    current = fetch_one(
        "SELECT * FROM strategy_targets WHERE spec_id=? AND symbol=? AND venue=?",
        [spec_id, symbol, venue],
    )
    payload = dict(current) if current else {"spec_id": spec_id, "symbol": symbol, "venue": venue}
    if status is not None:
        payload["status"] = status
    if paper_enabled is not None:
        payload["paper_enabled"] = 1 if paper_enabled else 0
    if notes is not None:
        payload["notes"] = notes
    if last_backtest_run_id is not None:
        payload["last_backtest_run_id"] = last_backtest_run_id
    payload.setdefault("mode", "perp")
    payload.setdefault("timeframe", "1h")
    return save_target(payload)


def list_targets(spec_id: str | None = None) -> list[dict]:
    if spec_id:
        rows = fetch_all("SELECT * FROM strategy_targets WHERE spec_id=? ORDER BY updated_at DESC", [spec_id])
    else:
        rows = fetch_all("SELECT * FROM strategy_targets ORDER BY updated_at DESC", [])
    return [dict(row) for row in rows]


def list_active_paper_targets() -> list[dict]:
    rows = fetch_all(
        """
        SELECT t.*, s.name, s.spec_json
        FROM strategy_targets t
        JOIN strategy_specs s ON s.spec_id = t.spec_id
        WHERE t.paper_enabled = 1
          AND t.status IN ('candidate', 'promoted')
        ORDER BY t.updated_at DESC
        """,
        [],
    )
    return [dict(row) for row in rows]


def instrument_for_target(target: dict) -> Instrument:
    return Instrument(
        symbol=target["symbol"],
        venue=Venue(target["venue"]),
        mode=VenueMode(target.get("mode", "perp")),
    )


def infer_target_status(result: dict, decision: dict) -> tuple[str, str]:
    policy = decision.get("policy", {})
    sharpe = float(result.get("sharpe") or 0.0)
    total_return_pct = float(result.get("total_return_pct") or 0.0)
    total_trades = int(result.get("total_trades") or 0)
    max_drawdown_pct = float(result.get("max_drawdown_pct") or 0.0)
    min_trade_count = int(policy.get("min_trade_count", 30) or 30)

    if decision.get("passed"):
        return "promoted", "Auto-promoted after passing the full promotion policy."

    if (
        sharpe >= 1.0
        and total_return_pct > 0
        and total_trades >= max(20, int(min_trade_count * 0.75))
        and max_drawdown_pct <= 8.0
    ):
        return "promoted", "Auto-promoted on strong Sharpe, positive return, and acceptable drawdown."

    if (
        sharpe >= 0.35
        and total_return_pct >= 0
        and total_trades >= max(12, int(min_trade_count * 0.5))
        and max_drawdown_pct <= 12.0
    ):
        return "candidate", "Auto-marked candidate after a constructive run with enough trades."

    if sharpe >= 0 and total_trades >= 8:
        return "shortlist", "Auto-shortlisted for more tuning before paper promotion."

    return "rejected", "Auto-rejected after the latest run failed the working thresholds."


def sync_target_with_backtest(spec_id: str, symbol: str, venue: str, result: dict, decision: dict) -> dict:
    status, note = infer_target_status(result, decision)
    current = fetch_one(
        "SELECT paper_enabled FROM strategy_targets WHERE spec_id=? AND symbol=? AND venue=?",
        [spec_id, symbol, venue],
    )
    paper_enabled = False if status == "rejected" else (bool(current["paper_enabled"]) if current else None)
    return update_target_state(
        spec_id=spec_id,
        symbol=symbol,
        venue=venue,
        status=status,
        paper_enabled=paper_enabled,
        notes=note,
        last_backtest_run_id=result["run_id"],
    )


def best_target_snapshot() -> dict | None:
    rows = fetch_all(
        """
        SELECT t.*, s.name, b.result_json, b.config_json, b.ran_at
        FROM strategy_targets t
        JOIN strategy_specs s ON s.spec_id = t.spec_id
        LEFT JOIN backtest_runs b ON b.run_id = t.last_backtest_run_id
        WHERE t.last_backtest_run_id IS NOT NULL
        """,
        [],
    )
    snapshots: list[dict] = []
    for row in rows:
        if row["result_json"] is None:
            continue
        result = json.loads(row["result_json"])
        config = json.loads(row["config_json"])
        snapshots.append(
            {
                "target_id": row["target_id"],
                "spec_id": row["spec_id"],
                "name": row["name"],
                "symbol": row["symbol"],
                "venue": row["venue"],
                "status": row["status"],
                "paper_enabled": row["paper_enabled"],
                "notes": row["notes"],
                "last_backtest_run_id": row["last_backtest_run_id"],
                "ran_at": row["ran_at"],
                "config": config,
                "result": result,
            }
        )
    if not snapshots:
        return None
    return max(
        snapshots,
        key=lambda item: (
            STATUS_PRIORITY.get(item["status"], 0),
            float(item["result"].get("sharpe") or 0.0),
            float(item["result"].get("total_return_pct") or 0.0),
            int(item["result"].get("total_trades") or 0),
        ),
    )


def strategy_status_summary(spec_id: str) -> dict:
    rows = list_targets(spec_id)
    if not rows:
        return {"status": "proposed", "paper_enabled_count": 0, "targets": []}
    statuses = [row["status"] for row in rows]
    if "promoted" in statuses:
        status = "promoted"
    elif "candidate" in statuses:
        status = "candidate"
    elif "shortlist" in statuses:
        status = "shortlist"
    elif all(item == "rejected" for item in statuses):
        status = "rejected"
    else:
        status = "proposed"
    return {
        "status": status,
        "paper_enabled_count": sum(int(row["paper_enabled"]) for row in rows),
        "targets": rows,
    }

```

## `backend/strategy/validator.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field

from backend.core.types import RuleBlock, StrategySpec

ALLOWED_OPERATORS = {"gt", "lt", "gte", "lte", "between", "crossover", "crossunder", "eq", "neq"}
KNOWN_FEATURES = {
    "ret_1",
    "ret_4",
    "vol_20",
    "vol_ratio",
    "atr_14",
    "rsi_14",
    "pct_rank_20",
    "trend_signal",
    "funding_rate",
    "funding_zscore",
    "oi_change_pct",
    "buy_sell_ratio",
    "liquidation_intensity",
    "spread_bps",
    "orderbook_imbalance",
    "btc_ret_1",
    "rel_strength_20",
    "beta_btc_20",
    "exchange_netflow",
    "whale_txn_count",
    "miner_outflow",
    "onchain_pressure",
    "close",
    "volume_quote",
}


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def _validate_rule(rule: RuleBlock, errors: list[str], field_name: str) -> None:
    if rule.feature not in KNOWN_FEATURES:
        errors.append(f"{field_name}: unknown feature '{rule.feature}'")
    if rule.operator not in ALLOWED_OPERATORS:
        errors.append(f"{field_name}: unsupported operator '{rule.operator}'")
    if rule.operator == "between" and not isinstance(rule.threshold, tuple):
        errors.append(f"{field_name}: 'between' requires a tuple threshold")


def validate_spec(spec: StrategySpec) -> ValidationResult:
    errors: list[str] = []
    if not spec.name.strip():
        errors.append("name is required")
    if not spec.hypothesis.strip():
        errors.append("hypothesis is required")
    if not spec.universe:
        errors.append("universe cannot be empty")

    for field_name in ("regime_filters", "entry_long", "entry_short", "exit_long", "exit_short"):
        rules = getattr(spec, field_name)
        for index, rule in enumerate(rules):
            _validate_rule(rule, errors, f"{field_name}[{index}]")

    if not spec.entry_long and not spec.entry_short:
        errors.append("at least one entry side must be defined")

    if spec.sizing.method == "fixed_notional" and not spec.sizing.fixed_notional_usd:
        errors.append("fixed_notional method requires fixed_notional_usd")

    return ValidationResult(valid=not errors, errors=errors)

```

## `backend/strategy/__init__.py`

```python
"""Strategy spec handling and signal evaluation."""

```

## `backend/strategy/signals/funding_reversion.py`

```python
from __future__ import annotations

from backend.core.types import RuleBlock
from backend.strategy.spec import new_strategy


def build():
    spec = new_strategy(
        name="Funding Mean Reversion",
        hypothesis="Extreme funding is often followed by short-term reversion once positioning becomes crowded.",
        feature_inputs=["funding_rate", "funding_zscore", "vol_20"],
    )
    spec.regime_filters = [RuleBlock(feature="vol_20", operator="lt", threshold=0.08)]
    spec.entry_long = [RuleBlock(feature="funding_zscore", operator="lt", threshold=-2.0)]
    spec.entry_short = [RuleBlock(feature="funding_zscore", operator="gt", threshold=2.0)]
    spec.exit_long = [RuleBlock(feature="funding_zscore", operator="gte", threshold=0.0)]
    spec.exit_short = [RuleBlock(feature="funding_zscore", operator="lte", threshold=0.0)]
    spec.tags = ["funding", "mean_reversion"]
    return spec

```

## `backend/strategy/signals/momentum.py`

```python
from __future__ import annotations

from backend.core.types import RuleBlock
from backend.strategy.spec import new_strategy


def build():
    spec = new_strategy(
        name="Momentum With Vol Filter",
        hypothesis="Moderate-vol trend continuation persists when momentum and participation expand together.",
        feature_inputs=["ret_4", "vol_ratio", "trend_signal", "vol_20"],
    )
    spec.regime_filters = [RuleBlock(feature="vol_20", operator="between", threshold=(0.02, 0.08))]
    spec.entry_long = [
        RuleBlock(feature="ret_4", operator="gt", threshold=0.01),
        RuleBlock(feature="vol_ratio", operator="gt", threshold=1.2),
        RuleBlock(feature="trend_signal", operator="gt", threshold=0),
    ]
    spec.entry_short = [
        RuleBlock(feature="ret_4", operator="lt", threshold=-0.01),
        RuleBlock(feature="vol_ratio", operator="gt", threshold=1.2),
        RuleBlock(feature="trend_signal", operator="lt", threshold=0),
    ]
    spec.tags = ["momentum", "trend"]
    return spec

```

## `backend/strategy/signals/vol_regime.py`

```python
from __future__ import annotations

from backend.core.types import RuleBlock
from backend.strategy.spec import new_strategy


def build():
    spec = new_strategy(
        name="Range Breakout",
        hypothesis="Breaks of a tight range with expanding volume tend to continue in the direction of the breakout.",
        feature_inputs=["pct_rank_20", "vol_ratio"],
    )
    spec.entry_long = [
        RuleBlock(feature="pct_rank_20", operator="gt", threshold=0.95),
        RuleBlock(feature="vol_ratio", operator="gt", threshold=1.5),
    ]
    spec.entry_short = [
        RuleBlock(feature="pct_rank_20", operator="lt", threshold=0.05),
        RuleBlock(feature="vol_ratio", operator="gt", threshold=1.5),
    ]
    spec.tags = ["breakout", "range"]
    return spec

```

## `backend/strategy/signals/__init__.py`

```python
"""Hand-coded strategy spec factories."""

```

## `backend/worker/jobs.py`

```python
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from backend.data.storage import fetch_all, fetch_one, get_sqlite, save_json_record


def enqueue_job(job_type: str, payload: dict, priority: int = 100) -> dict:
    record = {
        "job_id": str(uuid.uuid4()),
        "job_type": job_type,
        "status": "queued",
        "payload_json": json.dumps(payload),
        "result_json": None,
        "priority": priority,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "claimed_at": None,
        "finished_at": None,
        "attempt_count": 0,
        "last_error": None,
        "next_attempt_at": None,
    }
    save_json_record("job_queue", record, "job_id")
    return hydrate_job(record)


def hydrate_job(row: dict) -> dict:
    item = dict(row)
    item["payload"] = json.loads(item.pop("payload_json"))
    item["result"] = json.loads(item["result_json"]) if item.get("result_json") else None
    item.pop("result_json", None)
    return item


def list_jobs(limit: int = 100) -> list[dict]:
    rows = fetch_all("SELECT * FROM job_queue ORDER BY created_at DESC LIMIT ?", [int(limit)])
    return [hydrate_job(dict(row)) for row in rows]


def claim_next_job(job_type: str | None = None) -> dict | None:
    con = get_sqlite()
    if job_type:
        row = con.execute(
            """
            SELECT * FROM job_queue
            WHERE status='queued' AND job_type=?
              AND (next_attempt_at IS NULL OR next_attempt_at<=?)
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            """,
            [job_type, datetime.now(timezone.utc).isoformat()],
        ).fetchone()
    else:
        row = con.execute(
            """
            SELECT * FROM job_queue
            WHERE status='queued'
              AND (next_attempt_at IS NULL OR next_attempt_at<=?)
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            """,
            [datetime.now(timezone.utc).isoformat()],
        ).fetchone()
    if row is None:
        return None
    record = dict(row)
    record["status"] = "claimed"
    record["claimed_at"] = datetime.now(timezone.utc).isoformat()
    save_json_record("job_queue", record, "job_id")
    return hydrate_job(record)


def finish_job(job_id: str, status: str, result: dict) -> dict:
    row = fetch_one("SELECT * FROM job_queue WHERE job_id=?", [job_id])
    if row is None:
        raise ValueError("job_not_found")
    record = dict(row)
    record["status"] = status
    record["result_json"] = json.dumps(result)
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    save_json_record("job_queue", record, "job_id")
    return hydrate_job(record)


def requeue_job(job_id: str, *, next_attempt_at: datetime, error: str) -> dict:
    row = fetch_one("SELECT * FROM job_queue WHERE job_id=?", [job_id])
    if row is None:
        raise ValueError("job_not_found")
    record = dict(row)
    record["status"] = "queued"
    record["claimed_at"] = None
    record["attempt_count"] = int(record.get("attempt_count") or 0) + 1
    record["last_error"] = error
    record["next_attempt_at"] = next_attempt_at.isoformat()
    save_json_record("job_queue", record, "job_id")
    return hydrate_job(record)


def dead_letter_job(job_id: str, error: str) -> dict:
    row = fetch_one("SELECT * FROM job_queue WHERE job_id=?", [job_id])
    if row is None:
        raise ValueError("job_not_found")
    record = dict(row)
    record["status"] = "failed"
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    record["last_error"] = error
    save_json_record("job_queue", record, "job_id")
    dead_letter = {
        "dead_letter_id": str(uuid.uuid4()),
        "job_id": record["job_id"],
        "job_type": record["job_type"],
        "payload_json": record["payload_json"],
        "last_error": error,
        "failed_at": record["finished_at"],
    }
    save_json_record("job_dead_letters", dead_letter, "dead_letter_id")
    return hydrate_job(record)


def list_dead_letters(limit: int = 100) -> list[dict]:
    rows = fetch_all("SELECT * FROM job_dead_letters ORDER BY failed_at DESC LIMIT ?", [int(limit)])
    return [dict(row) for row in rows]

```

## `backend/worker/main.py`

```python
from __future__ import annotations

import asyncio
import socket

from backend.core.config import settings
from backend.core.logging import configure_logging
from backend.scheduler import setup_scheduler
from backend.worker.service import process_next_job, update_worker_heartbeat


async def worker_loop() -> None:
    worker_id = f"{socket.gethostname()}:{id(asyncio.current_task())}"
    if settings.scheduler_enabled:
        setup_scheduler()
    heartbeat_tick = 0
    while True:
        heartbeat_tick += 1
        if heartbeat_tick % 4 == 0:
            update_worker_heartbeat(worker_id, "running", {"scheduler_enabled": settings.scheduler_enabled})
        processed = process_next_job()
        if processed is None:
            await asyncio.sleep(2)
        else:
            await asyncio.sleep(0.25)


def main() -> None:
    configure_logging(settings.app_log_path)
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()

```

## `backend/worker/service.py`

```python
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from backend.core.config import settings
from backend.data.storage import fetch_all, save_json_record
from backend.execution.service import process_execution_job
from backend.ops.metrics import WORKER_QUEUE_GAUGE
from backend.ops.audit import record_audit_event
from backend.worker.jobs import claim_next_job, dead_letter_job, finish_job, list_jobs, requeue_job


def process_next_job(job_type: str | None = None) -> dict | None:
    job = claim_next_job(job_type)
    if job is None:
        return None
    attempts = int(job.get("attempt_count") or 0)
    try:
        if job["job_type"] == "execution_submit":
            result = process_execution_job(job["payload"])
            completed = finish_job(job["job_id"], "completed", result)
        else:
            completed = dead_letter_job(job["job_id"], "unsupported_job_type")
    except Exception as exc:  # pragma: no cover - runtime failure handling
        error = f"{type(exc).__name__}:{exc}"
        if attempts + 1 < settings.worker_max_retries:
            backoff_seconds = settings.worker_retry_backoff_seconds * (2 ** attempts)
            completed = requeue_job(
                job["job_id"],
                next_attempt_at=datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds),
                error=error,
            )
            completed["status"] = "retry_scheduled"
        else:
            completed = dead_letter_job(job["job_id"], error)
    record_audit_event(
        event_type="worker.job_processed",
        entity_type="job_queue",
        entity_id=completed["job_id"],
        payload={"job_type": completed["job_type"], "status": completed["status"]},
    )
    return completed


def job_metrics() -> dict:
    jobs = list_jobs(limit=500)
    dead_letters = fetch_all("SELECT COUNT(*) AS count FROM job_dead_letters", [])[0]["count"]
    queued = sum(1 for job in jobs if job["status"] == "queued")
    WORKER_QUEUE_GAUGE.set(queued)
    return {
        "queued": queued,
        "claimed": sum(1 for job in jobs if job["status"] == "claimed"),
        "completed": sum(1 for job in jobs if job["status"] == "completed"),
        "failed": sum(1 for job in jobs if job["status"] == "failed"),
        "retry_scheduled": sum(1 for job in jobs if job.get("next_attempt_at") and job["status"] == "queued"),
        "dead_letters": int(dead_letters),
    }


def update_worker_heartbeat(worker_id: str, status: str, details: dict | None = None) -> None:
    save_json_record(
        "worker_heartbeat",
        {
            "worker_id": worker_id,
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "details_json": json.dumps(details or {}),
        },
        "worker_id",
    )


def worker_health() -> dict:
    now = datetime.now(timezone.utc)
    rows = [dict(row) for row in fetch_all("SELECT * FROM worker_heartbeat ORDER BY last_seen DESC", [])]
    ttl = timedelta(seconds=settings.worker_heartbeat_ttl_seconds)
    workers = []
    for row in rows:
        last_seen = datetime.fromisoformat(row["last_seen"])
        workers.append(
            {
                "worker_id": row["worker_id"],
                "last_seen": row["last_seen"],
                "status": row["status"],
                "healthy": (now - last_seen) <= ttl,
                "details": json.loads(row["details_json"] or "{}"),
            }
        )
    return {
        "generated_at": now.isoformat(),
        "ttl_seconds": settings.worker_heartbeat_ttl_seconds,
        "workers": workers,
        "healthy": bool(workers) and all(item["healthy"] for item in workers),
    }

```

## `backend/worker/__init__.py`

```python
from __future__ import annotations


```

## `frontend/Dockerfile`

```
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 4173

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]

```

## `frontend/index.html`

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <title>Workbench</title>
    <script type="module" src="/src/main.tsx"></script>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>

```

## `frontend/package.json`

```json
{
  "name": "workbench-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.59.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "recharts": "^2.13.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.4",
    "vite": "^5.4.2"
  }
}

```

## `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": []
}

```

## `frontend/vite.config.ts`

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173
  }
});

```

## `frontend/public/favicon.svg`

```
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none">
  <rect width="64" height="64" rx="16" fill="#0c1827" />
  <path d="M18 42L28 22L36 34L44 18" stroke="#ff8f00" stroke-linecap="round" stroke-linejoin="round" stroke-width="5" />
  <circle cx="44" cy="18" r="5" fill="#00adb5" />
</svg>

```

## `frontend/src/App.tsx`

```tsx
import { useEffect, useState } from "react";
import { apiPost } from "./api/client";
import { DataHealthPage } from "./pages/DataHealthPage";
import { ExecutionPage } from "./pages/ExecutionPage";
import { PaperPortfolioPage } from "./pages/PaperPortfolioPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StrategyRegistryPage } from "./pages/StrategyRegistryPage";

type TabKey = "health" | "strategies" | "paper" | "execution" | "settings";

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: "health", label: "Data Health" },
  { key: "strategies", label: "Strategy Registry" },
  { key: "paper", label: "Paper Portfolio" },
  { key: "execution", label: "Execution" },
  { key: "settings", label: "Settings" }
];

export function App() {
  const [tab, setTab] = useState<TabKey>("health");
  const [role, setRole] = useState<string>("operator");
  const [identity, setIdentity] = useState<string>("Operator");
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    if (typeof window === "undefined") return "dark";
    return (window.localStorage.getItem("workbench_theme") as "dark" | "light") || "dark";
  });

  useEffect(() => {
    apiPost<{ role: string; display_name: string }>("/auth/login", { role })
      .then((user) => {
        setIdentity(user.display_name);
      })
      .catch(() => {
        setIdentity("Unknown");
      });
  }, [role]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("workbench_theme", theme);
  }, [theme]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.ctrlKey) {
        if (event.key === "1") setTab("health");
        if (event.key === "2") setTab("strategies");
        if (event.key === "3") setTab("paper");
        if (event.key === "4") setTab("execution");
        if (event.key === "5") setTab("settings");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="eyebrow">Crypto Workbench</div>
          <h1>Research. Falsify. Paper trade.</h1>
        </div>
        <div className="auth-panel">
          <div className="eyebrow">Operator</div>
          <div className="auth-name">{identity}</div>
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="viewer">viewer</option>
            <option value="operator">operator</option>
            <option value="admin">admin</option>
          </select>
          <button className="secondary-button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            Theme: {theme}
          </button>
        </div>
        <nav className="nav">
          {tabs.map((item) => (
            <button
              key={item.key}
              className={item.key === tab ? "nav-item active" : "nav-item"}
              onClick={() => setTab(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="muted" style={{ marginTop: "1rem", fontSize: "0.82rem" }}>
          Shortcuts: `Ctrl+1..5` tabs, `Alt+B` backtest, `Alt+R` paper cycle, `Alt+A` approve.
        </div>
      </aside>
      <main className="content">
        <div className="workspace">
          {tab === "health" && <DataHealthPage />}
          {tab === "strategies" && <StrategyRegistryPage />}
          {tab === "paper" && <PaperPortfolioPage />}
          {tab === "execution" && <ExecutionPage />}
          {tab === "settings" && <SettingsPage />}
        </div>
      </main>
    </div>
  );
}

```

## `frontend/src/main.tsx`

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "./App";
import { AppErrorBoundary } from "./components/AppErrorBoundary";
import "./styles.css";

const client = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>
    </AppErrorBoundary>
  </React.StrictMode>
);

```

## `frontend/src/styles.css`

```css
:root {
  color-scheme: dark;
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  color: #e8eef8;
  --bg-top: #08111f;
  --bg-bottom: #0c1827;
  --panel-bg: rgba(11, 20, 33, 0.92);
  --panel-text: #eaf2ff;
  --muted: #9db0cb;
  --border-soft: rgba(255, 255, 255, 0.08);
}

:root[data-theme="light"] {
  color-scheme: light;
  color: #0d1420;
  --bg-top: #eef4ff;
  --bg-bottom: #dbe7ff;
  --panel-bg: rgba(255, 255, 255, 0.94);
  --panel-text: #0d1420;
  --muted: #4a5a70;
  --border-soft: rgba(16, 29, 45, 0.08);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(255, 196, 0, 0.12), transparent 24%),
    radial-gradient(circle at top right, rgba(0, 173, 181, 0.12), transparent 20%),
    linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 100%);
}

button {
  border: 0;
  border-radius: 999px;
  background: #ff8f00;
  color: #101d2d;
  padding: 0.7rem 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 140ms ease, opacity 140ms ease, background 140ms ease;
}

button:hover {
  transform: translateY(-1px);
}

.app-shell {
  display: grid;
  grid-template-columns: 300px 1fr;
  min-height: 100svh;
}

.sidebar {
  padding: 2rem;
  color: #f8fbff;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.02), transparent);
}

.brand h1 {
  margin-top: 0.5rem;
  font-size: clamp(2rem, 5vw, 3.4rem);
  line-height: 0.95;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: #ffca6b;
  font-size: 0.75rem;
}

.nav {
  display: grid;
  gap: 0.75rem;
  margin-top: 2rem;
}

.auth-panel {
  margin-top: 1.5rem;
  display: grid;
  gap: 0.45rem;
}

.auth-name {
  font-size: 1rem;
  font-weight: 700;
}

.auth-panel select {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  padding: 0.75rem 0.9rem;
  background: rgba(255, 255, 255, 0.06);
  color: white;
  font: inherit;
}

.nav-item {
  text-align: left;
  background: rgba(255, 255, 255, 0.06);
  color: white;
}

.nav-item.active {
  background: #00adb5;
  color: #041015;
}

.content {
  padding: 2rem;
  background:
    radial-gradient(circle at 10% 10%, rgba(255, 255, 255, 0.03), transparent 22%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0));
}

.workspace {
  max-width: 1480px;
  margin: 0 auto;
}

.panel {
  background: var(--panel-bg);
  color: var(--panel-text);
  border-radius: 28px;
  padding: 1.5rem;
  box-shadow: 0 20px 80px rgba(8, 17, 31, 0.12);
}

.stack {
  display: grid;
  gap: 1.25rem;
}

.strategy-hero {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 1.25rem;
  align-items: start;
}

.compact-hero {
  padding-top: 1.1rem;
  padding-bottom: 1rem;
}

.hero-title {
  margin: 0.35rem 0 0.75rem;
  font-size: clamp(1.8rem, 3vw, 3rem);
  line-height: 0.96;
  max-width: 12ch;
}

.hero-title.compact {
  font-size: clamp(1.45rem, 2.2vw, 2.35rem);
  max-width: 15ch;
}

.hero-copy,
.muted {
  color: var(--muted);
  max-width: 56ch;
}

.eyebrow.dark {
  color: #9d6a08;
}

.run-controls {
  display: grid;
  gap: 0.9rem;
  justify-items: stretch;
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.field {
  display: grid;
  gap: 0.45rem;
}

.field span {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #5d6c7f;
}

.field select {
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  padding: 0.85rem 1rem;
  background: white;
  font: inherit;
}

.field input {
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  padding: 0.85rem 1rem;
  background: white;
  font: inherit;
}

.status-strip {
  grid-column: 1 / -1;
  border-top: 1px solid var(--border-soft);
  padding-top: 1rem;
  color: #233246;
  font-weight: 600;
}

.target-summary-strip {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) auto;
  gap: 1rem;
  align-items: center;
}

.target-summary-title {
  margin-top: 0.25rem;
  font-size: 1.4rem;
  font-weight: 700;
  color: #0d1420;
}

.target-summary-copy {
  margin: 0.45rem 0 0;
}

.target-summary-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  color: #233246;
  font-weight: 700;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.72rem;
}

.status-pill.promoted {
  background: rgba(0, 173, 181, 0.14);
  color: #006b73;
}

.status-pill.candidate {
  background: rgba(255, 143, 0, 0.16);
  color: #9d5c00;
}

.status-pill.shortlist {
  background: rgba(31, 63, 102, 0.12);
  color: #244b72;
}

.status-pill.rejected {
  background: rgba(187, 61, 61, 0.12);
  color: #8f2323;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.secondary-button {
  background: rgba(16, 29, 45, 0.08);
  color: #102034;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  text-align: left;
  padding: 0.8rem 0.5rem;
  border-bottom: 1px solid var(--border-soft);
  vertical-align: top;
}

.selected-row {
  background: rgba(0, 173, 181, 0.08);
}

.inspector-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.85fr);
  gap: 1.25rem;
}

.inspector-main,
.inspector-side {
  display: grid;
  gap: 1.25rem;
}

.chart-shell {
  min-height: 280px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 143, 0, 0.08), rgba(16, 29, 45, 0.02));
  padding: 0.75rem 0.5rem;
}

.run-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  color: var(--muted);
  font-size: 0.92rem;
  font-weight: 600;
}

.empty-state {
  min-height: 240px;
  display: grid;
  place-items: center;
  color: var(--muted);
}

.section-title {
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  font-weight: 700;
}

.trade-log {
  display: grid;
  gap: 0.75rem;
}

.compact-table th,
.compact-table td {
  padding-top: 0.65rem;
  padding-bottom: 0.65rem;
  font-size: 0.95rem;
}

.diagnostics-list,
.range-list {
  display: grid;
  gap: 0.7rem;
}

.diagnostics-list div,
.range-list div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid var(--border-soft);
}

.skeleton-block {
  min-height: 180px;
  display: grid;
  place-items: center;
  color: var(--muted);
  border: 1px dashed var(--border-soft);
}

.metrics-grid,
.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.metric-card,
.setting-card {
  background: linear-gradient(135deg, #101d2d, #19314d);
  color: white;
  border-radius: 20px;
  padding: 1rem;
}

.metric-card.warm {
  background: linear-gradient(135deg, #152538, #234767);
}

.metric-label {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.8;
}

.metric-value {
  margin-top: 0.4rem;
  font-size: 1.4rem;
  font-weight: 700;
}

@media (max-width: 900px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .strategy-hero,
  .inspector-grid,
  .target-summary-strip {
    grid-template-columns: 1fr;
  }

  .control-grid {
    grid-template-columns: 1fr;
  }
}

```

## `frontend/src/api/client.ts`

```typescript
const API_BASE =
  typeof window === "undefined"
    ? "http://127.0.0.1:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`;

let authTokenOverride = "";

export function getAuthToken(): string {
  return authTokenOverride;
}

export function setAuthToken(token: string): void {
  authTokenOverride = token;
}

export async function apiGet<T>(path: string): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {};
  if (token) headers["X-Workbench-Token"] = token;
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["X-Workbench-Token"] = token;
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers,
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

```

## `frontend/src/components/AppErrorBoundary.tsx`

```tsx
import { Component, ReactNode } from "react";

type Props = {
  children: ReactNode;
};

type State = {
  hasError: boolean;
  message: string;
};

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: unknown): State {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : "Unexpected UI failure"
    };
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="panel">
          <h2>Something broke in this view</h2>
          <p className="muted">{this.state.message}</p>
        </section>
      );
    }
    return this.props.children;
  }
}

```

## `frontend/src/components/MetricCard.tsx`

```tsx
type MetricCardProps = {
  label: string;
  value: string | number;
};

export function MetricCard({ label, value }: MetricCardProps) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
}

```

## `frontend/src/pages/DataHealthPage.tsx`

```tsx
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "../api/client";

type HealthRow = {
  instrument_key: string;
  timeframe: string;
  quality: string;
  last_bar_ts: string | null;
  gap_count: number;
  duplicate_count: number;
  coverage_days: number;
};

export function DataHealthPage() {
  const query = useQuery({
    queryKey: ["data-health"],
    queryFn: () => apiGet<HealthRow[]>("/data/health"),
    refetchInterval: 30_000,
    refetchIntervalInBackground: true
  });
  if (query.isLoading) {
    return <section className="panel skeleton-block">Loading data health...</section>;
  }
  if (query.isError) {
    return <section className="panel">Failed to load data health.</section>;
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Data Health</h2>
          <p>Quality checks for each instrument and timeframe.</p>
        </div>
        <div className="button-row">
          <button onClick={() => apiPost("/data/ingest", { lookback_days: 30 }).then(() => query.refetch())}>
            Ingest 30d
          </button>
          <button className="secondary-button" onClick={() => apiPost("/data/funding/ingest", { lookback_days: 14 })}>
            Ingest Funding
          </button>
          <button
            className="secondary-button"
            onClick={() => apiPost("/data/market-context/ingest", { lookback_days: 14 })}
          >
            Ingest Context
          </button>
          <button onClick={() => apiPost("/data/refresh-health").then(() => query.refetch())}>Refresh</button>
        </div>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Instrument</th>
            <th>Timeframe</th>
            <th>Quality</th>
            <th>Last Bar</th>
            <th>Gaps</th>
            <th>Duplicates</th>
            <th>Coverage (days)</th>
          </tr>
        </thead>
        <tbody>
          {(query.data ?? []).map((row) => (
            <tr key={`${row.instrument_key}-${row.timeframe}`}>
              <td>{row.instrument_key}</td>
              <td>{row.timeframe}</td>
              <td>{row.quality}</td>
              <td>{row.last_bar_ts ?? "n/a"}</td>
              <td>{row.gap_count}</td>
              <td>{row.duplicate_count}</td>
              <td>{row.coverage_days}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

```

## `frontend/src/pages/ExecutionPage.tsx`

```tsx
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "../api/client";

type StrategyRow = {
  spec_id: string;
  name: string;
  targets: Array<{
    symbol: string;
    venue: string;
    status: string;
    paper_enabled: number;
  }>;
};

type TicketRow = {
  ticket_id: string;
  spec_id: string;
  symbol: string;
  venue: string;
  direction: string;
  action: string;
  size_usd: number;
  status: string;
  approval_mode: string;
  rationale?: string | null;
  preview: {
    estimated_fee_usd: number;
    estimated_slippage_bps: number;
    notional_limit_ok: boolean;
    approval_required: boolean;
  };
  created_at: string;
  approved_at?: string | null;
  submitted_at?: string | null;
};

type ReconciliationRow = {
  reconciliation_id: string;
  venue: string;
  status: string;
  created_at: string;
  summary: {
    notes?: string;
  };
};

type SecretsResponse = {
  all_present: boolean;
  venues: Record<string, boolean>;
};

type JobRow = {
  job_id: string;
  job_type: string;
  status: string;
  created_at: string;
  payload: {
    ticket_id?: string;
    venue?: string;
    symbol?: string;
  };
  result?: Record<string, unknown> | null;
};

type JobMetrics = {
  queued: number;
  claimed: number;
  completed: number;
  failed: number;
  retry_scheduled: number;
  dead_letters: number;
};

export function ExecutionPage() {
  const [selectedSpecId, setSelectedSpecId] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("ETH");
  const [selectedVenue, setSelectedVenue] = useState("binance");
  const [direction, setDirection] = useState("long");
  const [sizeUsd, setSizeUsd] = useState(1000);
  const [message, setMessage] = useState("");

  const strategies = useQuery({
    queryKey: ["execution-strategies"],
    queryFn: () => apiGet<StrategyRow[]>("/strategies"),
    refetchInterval: 15_000,
    refetchIntervalInBackground: true
  });
  const tickets = useQuery({
    queryKey: ["execution-tickets"],
    queryFn: () => apiGet<TicketRow[]>("/execution/tickets"),
    refetchInterval: 10_000,
    refetchIntervalInBackground: true
  });
  const reconciliation = useQuery({
    queryKey: ["execution-reconciliation"],
    queryFn: () => apiGet<ReconciliationRow[]>("/execution/reconciliation"),
    refetchInterval: 20_000,
    refetchIntervalInBackground: true
  });
  const secrets = useQuery({
    queryKey: ["execution-secrets"],
    queryFn: () => apiGet<SecretsResponse>("/execution/secrets"),
    refetchInterval: 30_000,
    refetchIntervalInBackground: true
  });
  const jobs = useQuery({
    queryKey: ["execution-jobs"],
    queryFn: () => apiGet<JobRow[]>("/execution/jobs"),
    refetchInterval: 10_000,
    refetchIntervalInBackground: true
  });
  const deadLetters = useQuery({
    queryKey: ["execution-dead-letters"],
    queryFn: () => apiGet<Array<{ dead_letter_id: string; job_type: string; last_error?: string; failed_at: string }>>("/execution/jobs/dead-letters"),
    refetchInterval: 20_000,
    refetchIntervalInBackground: true
  });
  const jobMetrics = useQuery({
    queryKey: ["execution-job-metrics"],
    queryFn: () => apiGet<JobMetrics>("/execution/jobs/metrics"),
    refetchInterval: 10_000,
    refetchIntervalInBackground: true
  });
  useEffect(() => {
    if (!selectedSpecId && strategies.data?.length) {
      setSelectedSpecId(strategies.data[0].spec_id);
    }
  }, [selectedSpecId, strategies.data]);

  const selectedStrategy = strategies.data?.find((item) => item.spec_id === selectedSpecId) ?? strategies.data?.[0];
  const targetOptions = selectedStrategy?.targets ?? [];

  useEffect(() => {
    const match = targetOptions.find((item) => item.symbol === selectedSymbol && item.venue === selectedVenue);
    if (!match && targetOptions[0]) {
      setSelectedSymbol(targetOptions[0].symbol);
      setSelectedVenue(targetOptions[0].venue);
    }
  }, [selectedSymbol, selectedVenue, targetOptions]);

  const pendingTickets = useMemo(
    () => (tickets.data ?? []).filter((item) => item.status === "pending_approval"),
    [tickets.data]
  );

  async function createTicket() {
    if (!selectedStrategy) return;
    setMessage("Creating execution ticket...");
    try {
      await apiPost("/execution/tickets", {
        spec_id: selectedStrategy.spec_id,
        symbol: selectedSymbol,
        venue: selectedVenue,
        direction,
        action: "open",
        size_usd: sizeUsd,
        rationale: "Operator requested approval-mode live ticket"
      });
      await tickets.refetch();
      await jobs.refetch();
      await jobMetrics.refetch();
      setMessage("Execution ticket created.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to create ticket.");
    }
  }

  async function approve(ticketId: string) {
    setMessage("Approving ticket...");
    try {
      await apiPost(`/execution/tickets/${ticketId}/approve`, {});
      await Promise.all([tickets.refetch(), reconciliation.refetch(), jobs.refetch(), jobMetrics.refetch()]);
      setMessage("Ticket processed.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Approval failed.");
    }
  }

  async function reject(ticketId: string) {
    setMessage("Rejecting ticket...");
    try {
      await apiPost(`/execution/tickets/${ticketId}/reject`, { reason: "operator_rejected" });
      await tickets.refetch();
      await jobs.refetch();
      await jobMetrics.refetch();
      setMessage("Ticket rejected.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Reject failed.");
    }
  }

  async function reconcileVenue(venue: string) {
    setMessage(`Reconciling ${venue}...`);
    try {
      await apiPost("/execution/reconciliation/run", { venue });
      await reconciliation.refetch();
      setMessage(`Reconciliation completed for ${venue}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Reconciliation failed.");
    }
  }

  async function processQueue() {
    setMessage("Processing next worker job...");
    try {
      await apiPost("/execution/jobs/process", { job_type: "execution_submit" });
      await Promise.all([tickets.refetch(), jobs.refetch(), jobMetrics.refetch()]);
      setMessage("Processed next queued job.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Job processing failed.");
    }
  }

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.altKey && event.key.toLowerCase() === "a" && pendingTickets[0]) {
        void approve(pendingTickets[0].ticket_id);
      }
      if (event.altKey && event.key.toLowerCase() === "j") {
        void processQueue();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pendingTickets]);

  if (strategies.isLoading || tickets.isLoading || reconciliation.isLoading || jobs.isLoading || jobMetrics.isLoading || deadLetters.isLoading) {
    return <section className="panel skeleton-block">Loading execution control...</section>;
  }
  if (strategies.isError || tickets.isError || reconciliation.isError || jobs.isError || jobMetrics.isError || deadLetters.isError) {
    return <section className="panel">Failed to load execution control data.</section>;
  }

  return (
    <section className="stack">
      <div className="panel strategy-hero compact-hero">
        <div>
          <div className="eyebrow dark">Execution Control</div>
          <h2 className="hero-title compact">Gate live orders through approval and reconciliation.</h2>
          <p className="hero-copy">
            This stays in approval mode until data, paper evidence, secrets, and reconciliation are all strong enough.
          </p>
        </div>
        <div className="run-controls">
          <div className="control-grid">
            <label className="field">
              <span>Strategy</span>
              <select value={selectedSpecId} onChange={(event) => setSelectedSpecId(event.target.value)}>
                {(strategies.data ?? []).map((item) => (
                  <option key={item.spec_id} value={item.spec_id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Target</span>
              <select
                value={`${selectedSymbol}:${selectedVenue}`}
                onChange={(event) => {
                  const [symbol, venue] = event.target.value.split(":");
                  setSelectedSymbol(symbol);
                  setSelectedVenue(venue);
                }}
              >
                {targetOptions.map((item) => (
                  <option key={`${item.symbol}:${item.venue}`} value={`${item.symbol}:${item.venue}`}>
                    {item.symbol} / {item.venue} ({item.status})
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Direction</span>
              <select value={direction} onChange={(event) => setDirection(event.target.value)}>
                <option value="long">long</option>
                <option value="short">short</option>
              </select>
            </label>
          </div>
          <div className="control-grid">
            <label className="field">
              <span>Size USD</span>
              <input
                type="number"
                min={100}
                step={100}
                value={sizeUsd}
                onChange={(event) => setSizeUsd(Number(event.target.value))}
              />
            </label>
          </div>
          <div className="button-row">
            <button onClick={createTicket}>Create Ticket</button>
            <button className="secondary-button" onClick={() => reconcileVenue("binance")}>
              Reconcile Binance
            </button>
            <button className="secondary-button" onClick={() => reconcileVenue("hyperliquid")}>
              Reconcile Hyperliquid
            </button>
          </div>
        </div>
        <div className="status-strip">{message || "Create approval-mode execution tickets instead of sending live orders directly."}</div>
      </div>

      <div className="metrics-grid">
        <div className="metric-card warm">
          <div className="metric-label">Pending Tickets</div>
          <div className="metric-value">{pendingTickets.length}</div>
        </div>
        <div className="metric-card warm">
          <div className="metric-label">Queued Jobs</div>
          <div className="metric-value">{jobMetrics.data?.queued ?? 0}</div>
        </div>
        <div className="metric-card warm">
          <div className="metric-label">Reconciliation Runs</div>
          <div className="metric-value">{reconciliation.data?.length ?? 0}</div>
        </div>
        <div className="metric-card warm">
          <div className="metric-label">Secrets Ready</div>
          <div className="metric-value">{secrets.data?.all_present ? "yes" : "no"}</div>
        </div>
        <div className="metric-card warm">
          <div className="metric-label">Dead Letters</div>
          <div className="metric-value">{jobMetrics.data?.dead_letters ?? 0}</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Execution Tickets</h2>
            <p>Every live intent becomes an approval artifact first.</p>
          </div>
          <div className="button-row">
            <button className="secondary-button" onClick={processQueue}>
              Process Queue
            </button>
          </div>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Market</th>
              <th>Side</th>
              <th>Preview</th>
              <th>Status</th>
              <th>When</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {(tickets.data ?? []).map((ticket) => (
              <tr key={ticket.ticket_id}>
                <td>{ticket.spec_id}</td>
                <td>
                  {ticket.symbol} / {ticket.venue}
                </td>
                <td>
                  {ticket.action} {ticket.direction}
                </td>
                <td>
                  Fee ${ticket.preview.estimated_fee_usd.toFixed(2)} | Slip {ticket.preview.estimated_slippage_bps}bps
                </td>
                <td>{ticket.status}</td>
                <td>{new Date(ticket.created_at).toLocaleString()}</td>
                <td className="button-row">
                  <button className="secondary-button" disabled={ticket.status !== "pending_approval"} onClick={() => approve(ticket.ticket_id)}>
                    Approve
                  </button>
                  <button className="secondary-button" disabled={ticket.status !== "pending_approval"} onClick={() => reject(ticket.ticket_id)}>
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="inspector-grid">
        <div className="panel inspector-main">
          <div className="section-title">Worker Queue</div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Job</th>
                <th>Status</th>
                <th>Payload</th>
              </tr>
            </thead>
            <tbody>
              {(jobs.data ?? []).map((job) => (
                <tr key={job.job_id}>
                  <td>{job.job_type}</td>
                  <td>{job.status}</td>
                  <td>{job.payload.ticket_id ?? `${job.payload.symbol ?? ""} ${job.payload.venue ?? ""}`.trim()}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="section-title">Venue Secrets</div>
          <div className="range-list">
            {Object.entries(secrets.data?.venues ?? {}).map(([venue, ready]) => (
              <div key={venue}>
                <strong>{venue}</strong>
                <span>{ready ? "configured" : "missing"}</span>
              </div>
            ))}
          </div>

          <div className="section-title">Dead Letter Queue</div>
          <div className="range-list">
            {(deadLetters.data ?? []).slice(0, 6).map((item) => (
              <div key={item.dead_letter_id}>
                <strong>{item.job_type}</strong>
                <span>{item.last_error || "unknown_error"}</span>
              </div>
            ))}
            {(deadLetters.data ?? []).length === 0 ? (
              <div>
                <strong>No dead letters</strong>
                <span>Queue is healthy.</span>
              </div>
            ) : null}
          </div>
        </div>
        <div className="panel inspector-side">
          <div className="section-title">Reconciliation</div>
          <div className="range-list">
            {(reconciliation.data ?? []).map((item) => (
              <div key={item.reconciliation_id}>
                <strong>{item.venue}</strong>
                <span>
                  {item.status} | {new Date(item.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

```

## `frontend/src/pages/PaperPortfolioPage.tsx`

```tsx
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { apiGet, apiPost } from "../api/client";
import { MetricCard } from "../components/MetricCard";

type PortfolioResponse = {
  positions: Array<Record<string, string | number | null>>;
  orders: Array<Record<string, string | number | null>>;
  active_targets: Array<Record<string, string | number | null>>;
  target_activity: Array<Record<string, string | number | null>>;
  total_unrealized_pnl_usd: number;
};

export function PaperPortfolioPage() {
  const query = useQuery({
    queryKey: ["paper-portfolio"],
    queryFn: () => apiGet<PortfolioResponse>("/paper/portfolio"),
    refetchInterval: 10_000,
    refetchIntervalInBackground: true
  });
  async function runPaperCycle() {
    await apiPost("/paper/run-once");
    await query.refetch();
  }

  async function runKillSwitch() {
    await apiPost("/paper/kill");
    await query.refetch();
  }

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.altKey && event.key.toLowerCase() === "r") {
        void runPaperCycle();
      }
      if (event.altKey && event.key.toLowerCase() === "k") {
        void runKillSwitch();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (query.isLoading) {
    return <section className="panel skeleton-block">Loading paper portfolio...</section>;
  }
  if (query.isError) {
    return <section className="panel">Failed to load paper portfolio.</section>;
  }

  const data = query.data;

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Paper Portfolio</h2>
          <p>Open positions, recent fills, and emergency controls.</p>
        </div>
        <div className="button-row">
          <button onClick={() => void runPaperCycle()}>Run Paper Cycle</button>
          <button onClick={() => void runKillSwitch()}>Kill Switch</button>
        </div>
      </div>

      <div className="metrics-grid">
        <MetricCard label="Open Positions" value={data?.positions.length ?? 0} />
        <MetricCard label="Recent Orders" value={data?.orders.length ?? 0} />
        <MetricCard label="Active Targets" value={data?.active_targets.length ?? 0} />
        <MetricCard label="Unrealized PnL" value={`$${(data?.total_unrealized_pnl_usd ?? 0).toFixed(2)}`} />
      </div>

      <h3>Active Paper Targets</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Spec</th>
            <th>Symbol</th>
            <th>Venue</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {(data?.active_targets ?? []).map((row) => (
            <tr key={`${row.spec_id}-${row.symbol}-${row.venue}`}>
              <td>{row.name}</td>
              <td>{row.spec_id}</td>
              <td>{row.symbol}</td>
              <td>{row.venue}</td>
              <td>{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Target Activity</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Market</th>
            <th>Open Positions</th>
            <th>Recent Orders</th>
            <th>Last Activity</th>
            <th>Last Order</th>
            <th>Realized PnL</th>
          </tr>
        </thead>
        <tbody>
          {(data?.target_activity ?? []).map((row) => (
            <tr key={`${row.spec_id}-${row.symbol}-${row.venue}`}>
              <td>{row.name}</td>
              <td>
                {row.symbol} / {row.venue}
              </td>
              <td>{row.open_positions}</td>
              <td>{row.recent_orders}</td>
              <td>{row.last_event_at ? new Date(String(row.last_event_at)).toLocaleString() : "No activity yet"}</td>
              <td>
                {row.last_order_action
                  ? `${row.last_order_action} ${row.last_direction ?? ""} (${row.last_order_status ?? "n/a"})`
                  : "No orders yet"}
              </td>
              <td>${Number(row.realized_pnl_usd ?? 0).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Recent Orders</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Spec</th>
            <th>Market</th>
            <th>Action</th>
            <th>Status</th>
            <th>Triggered</th>
            <th>Fill</th>
            <th>Size USD</th>
          </tr>
        </thead>
        <tbody>
          {(data?.orders ?? []).map((row) => (
            <tr key={String(row.order_id)}>
              <td>{row.spec_id}</td>
              <td>
                {row.symbol} / {row.venue}
              </td>
              <td>
                {row.action} {row.direction}
              </td>
              <td>{row.status}</td>
              <td>{row.triggered_at ? new Date(String(row.triggered_at)).toLocaleString() : "n/a"}</td>
              <td>{row.fill_price ?? "n/a"}</td>
              <td>{row.size_usd}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Open Positions</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Spec</th>
            <th>Market</th>
            <th>Direction</th>
            <th>Opened</th>
            <th>Entry</th>
            <th>Mark</th>
            <th>Unrealized</th>
            <th>Size USD</th>
          </tr>
        </thead>
        <tbody>
          {(data?.positions ?? []).map((row) => (
            <tr key={String(row.position_id)}>
              <td>{row.spec_id}</td>
              <td>
                {row.symbol} / {row.venue}
              </td>
              <td>{row.direction}</td>
              <td>{row.opened_at ? new Date(String(row.opened_at)).toLocaleString() : "n/a"}</td>
              <td>{row.entry_price}</td>
              <td>{row.mark_price ?? "n/a"}</td>
              <td>${Number(row.unrealized_pnl_usd ?? 0).toFixed(2)}</td>
              <td>{row.size_usd}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

```

## `frontend/src/pages/SettingsPage.tsx`

```tsx
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiGet, apiPost } from "../api/client";

type ReadinessResponse = {
  generated_at: string;
  summary: {
    data_ready: boolean;
    paper_ready: boolean;
    live_ready: boolean;
    blockers: string[];
  };
  counts: {
    datasets: number;
    healthy_datasets: number;
    fresh_datasets: number;
    audit_events: number;
    paper_cycle_events: number;
    reconciliation_runs: number;
    promoted_targets: number;
    active_paper_targets: number;
    open_positions: number;
  };
  risk: {
    paper_trading_enabled: boolean;
    live_trading_enabled: boolean;
    live_approval_mode: boolean;
    paper_max_open_positions: number;
    paper_max_gross_exposure_usd: number;
    paper_daily_loss_limit_usd: number;
    live_secrets: {
      all_present: boolean;
      venues: Record<string, boolean>;
    };
  };
  best_target?: {
    name: string;
    symbol: string;
    venue: string;
    status: string;
    result: {
      sharpe: number;
      total_return_pct: number;
      total_trades: number;
    };
  } | null;
  recent_health_issues: string[];
};

type AuditRow = {
  event_id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  created_at: string;
};

type PaperEventRow = {
  event_id: string;
  spec_id: string;
  symbol: string;
  venue: string;
  timeframe: string;
  event_type: string;
  reason: string;
  created_at: string;
};

type VaultStatus = {
  path: string;
  exists: boolean;
  unlocked: boolean;
  configured_keys: string[];
  required_keys: string[];
};

type WorkerHealth = {
  healthy: boolean;
  workers: Array<{ worker_id: string; healthy: boolean; last_seen: string; status: string }>;
};

function statusText(value: boolean) {
  return value ? "Ready" : "Blocked";
}

export function SettingsPage() {
  const [vaultPassphrase, setVaultPassphrase] = useState("");
  const [vaultName, setVaultName] = useState("binance_api_key");
  const [vaultValue, setVaultValue] = useState("");
  const [vaultMessage, setVaultMessage] = useState("");
  const readiness = useQuery({
    queryKey: ["ops-readiness"],
    queryFn: () => apiGet<ReadinessResponse>("/ops/readiness"),
    refetchInterval: 20_000,
    refetchIntervalInBackground: true
  });
  const audit = useQuery({
    queryKey: ["ops-audit"],
    queryFn: () => apiGet<AuditRow[]>("/ops/audit?limit=20"),
    refetchInterval: 20_000,
    refetchIntervalInBackground: true
  });
  const paperEvents = useQuery({
    queryKey: ["ops-paper-events"],
    queryFn: () => apiGet<PaperEventRow[]>("/ops/paper-events?limit=20"),
    refetchInterval: 20_000,
    refetchIntervalInBackground: true
  });
  const vault = useQuery({
    queryKey: ["vault-status"],
    queryFn: () => apiGet<VaultStatus>("/vault/status"),
    retry: false
  });
  const workerHealth = useQuery({
    queryKey: ["ops-worker-health"],
    queryFn: () => apiGet<WorkerHealth>("/ops/worker-health"),
    refetchInterval: 15_000,
    refetchIntervalInBackground: true
  });
  if (readiness.isLoading || audit.isLoading || paperEvents.isLoading) {
    return <section className="panel skeleton-block">Loading operations snapshot...</section>;
  }
  if (readiness.isError || audit.isError || paperEvents.isError) {
    return <section className="panel">Failed to load operations snapshot.</section>;
  }

  const data = readiness.data;

  async function saveVaultSecret() {
    setVaultMessage("Saving vault secret...");
    try {
      const response = await apiPost<VaultStatus>("/vault/secrets", {
        name: vaultName,
        value: vaultValue,
        passphrase: vaultPassphrase
      });
      await vault.refetch();
      setVaultValue("");
      setVaultMessage(`Vault updated. ${response.configured_keys.length} keys configured.`);
    } catch (error) {
      setVaultMessage(error instanceof Error ? error.message : "Vault update failed.");
    }
  }

  return (
    <section className="stack">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Operations</h2>
            <p>Readiness, guardrails, and audit surfaces for production hardening.</p>
          </div>
          <div className="muted">
            {data ? `Snapshot ${new Date(data.generated_at).toLocaleString()}` : "Loading readiness snapshot..."}
          </div>
        </div>

        <div className="settings-grid">
          <div className="setting-card">
            <div className="metric-label">Data Readiness</div>
            <div className="metric-value">{statusText(Boolean(data?.summary.data_ready))}</div>
          </div>
          <div className="setting-card">
            <div className="metric-label">Paper Readiness</div>
            <div className="metric-value">{statusText(Boolean(data?.summary.paper_ready))}</div>
          </div>
          <div className="setting-card">
            <div className="metric-label">Live Readiness</div>
            <div className="metric-value">{statusText(Boolean(data?.summary.live_ready))}</div>
          </div>
          <div className="setting-card">
            <div className="metric-label">Audit Events</div>
            <div className="metric-value">{data?.counts.audit_events ?? 0}</div>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Blockers</h2>
            <p>The system should stay conservative until these are cleared.</p>
          </div>
        </div>
        <div className="range-list">
          {(data?.summary.blockers ?? []).length > 0 ? (
            (data?.summary.blockers ?? []).map((blocker) => (
              <div key={blocker}>
                <strong>{blocker}</strong>
                <span>Needs operator attention</span>
              </div>
            ))
          ) : (
            <div>
              <strong>No blockers</strong>
              <span>The current snapshot passed all active checks.</span>
            </div>
          )}
        </div>
      </div>

      <div className="inspector-grid">
        <div className="panel inspector-main">
          <div className="panel-header">
            <div>
              <h2>Readiness Counters</h2>
              <p>Coverage across data, strategy promotion, and paper history.</p>
            </div>
          </div>
          <div className="metrics-grid">
            <div className="metric-card warm">
              <div className="metric-label">Datasets</div>
              <div className="metric-value">{data?.counts.datasets ?? 0}</div>
            </div>
            <div className="metric-card warm">
              <div className="metric-label">Healthy</div>
              <div className="metric-value">{data?.counts.healthy_datasets ?? 0}</div>
            </div>
            <div className="metric-card warm">
            <div className="metric-label">Paper Events</div>
            <div className="metric-value">{data?.counts.paper_cycle_events ?? 0}</div>
          </div>
          <div className="metric-card warm">
            <div className="metric-label">Recon Runs</div>
            <div className="metric-value">{data?.counts.reconciliation_runs ?? 0}</div>
          </div>
          </div>

          <div className="section-title">Best Current Target</div>
          <div className="range-list">
            {data?.best_target ? (
              <div>
                <strong>
                  {data.best_target.name} on {data.best_target.symbol} / {data.best_target.venue}
                </strong>
                <span>
                  {data.best_target.status} | Sharpe {data.best_target.result.sharpe.toFixed(2)} | Trades{" "}
                  {data.best_target.result.total_trades}
                </span>
              </div>
            ) : (
              <div>
                <strong>No best target yet</strong>
                <span>Run more backtests before promoting anything.</span>
              </div>
            )}
          </div>

          <div className="section-title">Recent Audit</div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Entity</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {(audit.data ?? []).map((row) => (
                <tr key={row.event_id}>
                  <td>{row.event_type}</td>
                  <td>
                    {row.entity_type} / {row.entity_id}
                  </td>
                  <td>{new Date(row.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel inspector-side">
          <div className="section-title">Risk Controls</div>
          <div className="range-list">
            <div>
              <strong>Paper Trading</strong>
              <span>{data?.risk.paper_trading_enabled ? "enabled" : "disabled"}</span>
            </div>
            <div>
              <strong>Live Trading</strong>
              <span>{data?.risk.live_trading_enabled ? "enabled" : "forced off"}</span>
            </div>
            <div>
              <strong>Approval Mode</strong>
              <span>{data?.risk.live_approval_mode ? "manual" : "direct"}</span>
            </div>
            <div>
              <strong>Max Open Positions</strong>
              <span>{data?.risk.paper_max_open_positions ?? 0}</span>
            </div>
            <div>
              <strong>Daily Loss Limit</strong>
              <span>${Number(data?.risk.paper_daily_loss_limit_usd ?? 0).toFixed(0)}</span>
            </div>
            <div>
              <strong>Gross Exposure Cap</strong>
              <span>${Number(data?.risk.paper_max_gross_exposure_usd ?? 0).toFixed(0)}</span>
            </div>
            <div>
              <strong>Live Secrets</strong>
              <span>{data?.risk.live_secrets?.all_present ? "ready" : "missing"}</span>
            </div>
            <div>
              <strong>Worker Health</strong>
              <span>{workerHealth.data?.healthy ? "healthy" : "degraded"}</span>
            </div>
          </div>

          <div className="section-title">Health Issues</div>
          <div className="range-list">
            {(data?.recent_health_issues ?? []).slice(0, 8).map((issue) => (
              <div key={issue}>
                <strong>{issue}</strong>
                <span>Investigate before live enablement</span>
              </div>
            ))}
            {(data?.recent_health_issues ?? []).length === 0 ? (
              <div>
                <strong>No current health issues</strong>
                <span>The last health pass came back clean.</span>
              </div>
            ) : null}
          </div>

          <div className="section-title">Paper Cycle Feed</div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Market</th>
                <th>Event</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {(paperEvents.data ?? []).map((row) => (
                <tr key={row.event_id}>
                  <td>
                    {row.symbol} / {row.venue}
                  </td>
                  <td>
                    {row.event_type} / {row.reason}
                  </td>
                  <td>{new Date(row.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="section-title">Vault</div>
          <div className="range-list">
            <div>
              <strong>Status</strong>
              <span>{vault.data ? (vault.data.unlocked ? "unlocked" : "locked") : "admin only"}</span>
            </div>
            <div>
              <strong>Configured</strong>
              <span>{vault.data?.configured_keys.join(", ") || "none"}</span>
            </div>
          </div>
          <div className="field">
            <span>Vault Passphrase</span>
            <input type="password" value={vaultPassphrase} onChange={(event) => setVaultPassphrase(event.target.value)} />
          </div>
          <div className="field">
            <span>Secret Name</span>
            <select value={vaultName} onChange={(event) => setVaultName(event.target.value)}>
              <option value="binance_api_key">binance_api_key</option>
              <option value="binance_api_secret">binance_api_secret</option>
              <option value="hyperliquid_private_key">hyperliquid_private_key</option>
              <option value="hyperliquid_account_address">hyperliquid_account_address</option>
            </select>
          </div>
          <div className="field">
            <span>Secret Value</span>
            <input value={vaultValue} onChange={(event) => setVaultValue(event.target.value)} />
          </div>
          <div className="button-row">
            <button className="secondary-button" onClick={saveVaultSecret}>
              Save To Vault
            </button>
          </div>
          <div className="muted">{vaultMessage}</div>
        </div>
      </div>
    </section>
  );
}

```

## `frontend/src/pages/StrategyRegistryPage.tsx`

```tsx
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet, apiPost } from "../api/client";

type StrategyUniverseItem = {
  symbol: string;
  venue: string;
};

type StrategyRow = {
  spec_id: string;
  name: string;
  version: number;
  status: string;
  created_at: string;
  paper_enabled_count: number;
  targets: Array<{
    target_id: string;
    spec_id: string;
    symbol: string;
    venue: string;
    status: string;
    paper_enabled: number;
    notes?: string | null;
    last_backtest_run_id?: string | null;
  }>;
  spec: {
    hypothesis: string;
    universe: StrategyUniverseItem[];
  };
};

type BacktestRow = {
  run_id: string;
  spec_id: string;
  ran_at: string;
  config: {
    start_date: string;
    end_date: string;
    instrument?: {
      symbol: string;
      venue: string;
      mode: string;
      quote: string;
    };
  };
  result: {
    sharpe: number;
    total_trades: number;
    total_return_pct: number;
    max_drawdown_pct: number;
    diagnostics?: {
      bars_seen?: number;
      signal_counts?: Record<string, number>;
      feature_ranges?: Record<string, { min: number; max: number }>;
    };
    equity_curve: Array<[string, number] | { ts: string; equity: number }>;
    trades: Array<{
      trade_id: string;
      direction: string;
      entry_ts: string;
      exit_ts: string;
      pnl_usd: number;
      exit_reason: string;
    }>;
  };
};

type CompareRow = {
  symbol: string;
  venue: string;
  sharpe: number | null;
  total_return_pct: number | null;
  total_trades: number;
  passed: boolean;
};

type SweepRow = {
  label: string;
  sharpe: number;
  return_pct: number;
  trades: number;
  drawdown_pct: number;
};

type TargetSnapshot = {
  spec_id: string;
  name: string;
  symbol: string;
  venue: string;
  status: string;
  paper_enabled: number;
  notes?: string | null;
  run?: BacktestRow;
};

const LOOKBACK_OPTIONS = [60, 120, 180, 365];
const BUILDER_FEATURES = [
  "ret_4",
  "vol_ratio",
  "trend_signal",
  "funding_zscore",
  "rsi_14",
  "pct_rank_20",
  "oi_change_pct",
  "buy_sell_ratio",
  "liquidation_intensity",
  "btc_ret_1",
  "rel_strength_20",
  "beta_btc_20",
  "onchain_pressure"
];
const STATUS_PRIORITY: Record<string, number> = {
  rejected: 0,
  proposed: 1,
  shortlist: 2,
  candidate: 3,
  promoted: 4
};

export function StrategyRegistryPage() {
  const [selectedSpecId, setSelectedSpecId] = useState<string>("");
  const [selectedSymbol, setSelectedSymbol] = useState<string>("BTC");
  const [selectedVenue, setSelectedVenue] = useState<string>("binance");
  const [lookbackDays, setLookbackDays] = useState<number>(180);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [compareRows, setCompareRows] = useState<CompareRow[]>([]);
  const [sweepRows, setSweepRows] = useState<SweepRow[]>([]);
  const [builderName, setBuilderName] = useState<string>("Custom Signal");
  const [builderHypothesis, setBuilderHypothesis] = useState<string>("User-defined strategy idea.");
  const [builderFeature, setBuilderFeature] = useState<string>("ret_4");
  const [builderOperator, setBuilderOperator] = useState<string>("gt");
  const [builderThreshold, setBuilderThreshold] = useState<number>(0.01);

  const strategies = useQuery({
    queryKey: ["strategies"],
    queryFn: () => apiGet<StrategyRow[]>("/strategies"),
    refetchInterval: 30_000,
    refetchIntervalInBackground: true
  });
  const backtests = useQuery({
    queryKey: ["backtests"],
    queryFn: () => apiGet<BacktestRow[]>("/backtests"),
    refetchInterval: 30_000,
    refetchIntervalInBackground: true
  });

  useEffect(() => {
    if (!selectedSpecId && strategies.data?.length) {
      setSelectedSpecId(strategies.data[0].spec_id);
    }
  }, [selectedSpecId, strategies.data]);

  const selectedStrategy = strategies.data?.find((row) => row.spec_id === selectedSpecId) ?? strategies.data?.[0];
  const availableSymbols = Array.from(new Set((selectedStrategy?.spec.universe ?? []).map((item) => item.symbol)));
  const availableVenues = Array.from(
    new Set(
      (selectedStrategy?.spec.universe ?? [])
        .filter((item) => item.symbol === selectedSymbol)
        .map((item) => item.venue)
    )
  );

  useEffect(() => {
    if (!availableSymbols.includes(selectedSymbol)) {
      setSelectedSymbol(availableSymbols[0] ?? "BTC");
    }
  }, [availableSymbols, selectedSymbol]);

  useEffect(() => {
    if (!availableVenues.includes(selectedVenue)) {
      setSelectedVenue(availableVenues[0] ?? "binance");
    }
  }, [availableVenues, selectedVenue]);

  const latestBySpec = new Map<string, BacktestRow>();
  for (const run of backtests.data ?? []) {
    if (!latestBySpec.has(run.spec_id)) {
      latestBySpec.set(run.spec_id, run);
    }
  }

  const selectedRun =
    (backtests.data ?? []).find(
      (run) =>
        run.spec_id === selectedStrategy?.spec_id &&
        run.config.instrument?.symbol === selectedSymbol &&
        run.config.instrument?.venue === selectedVenue
    ) ??
    (selectedStrategy ? latestBySpec.get(selectedStrategy.spec_id) : undefined);
  const selectedTarget =
    selectedStrategy?.targets?.find((target) => target.symbol === selectedSymbol && target.venue === selectedVenue) ?? null;
  const diagnostics = selectedRun?.result.diagnostics;
  const targetSnapshots = useMemo<TargetSnapshot[]>(
    () =>
      (strategies.data ?? [])
        .flatMap((strategy) =>
          (strategy.targets ?? []).map((target) => ({
            spec_id: strategy.spec_id,
            name: strategy.name,
            symbol: target.symbol,
            venue: target.venue,
            status: target.status,
            paper_enabled: target.paper_enabled,
            notes: target.notes,
            run: (backtests.data ?? []).find((item) => item.run_id === target.last_backtest_run_id)
          }))
        )
        .filter((item) => item.run)
        .sort((left, right) => {
          const leftScore = STATUS_PRIORITY[left.status] ?? 0;
          const rightScore = STATUS_PRIORITY[right.status] ?? 0;
          if (leftScore !== rightScore) return rightScore - leftScore;
          if ((right.run?.result.sharpe ?? 0) !== (left.run?.result.sharpe ?? 0)) {
            return (right.run?.result.sharpe ?? 0) - (left.run?.result.sharpe ?? 0);
          }
          if ((right.run?.result.total_return_pct ?? 0) !== (left.run?.result.total_return_pct ?? 0)) {
            return (right.run?.result.total_return_pct ?? 0) - (left.run?.result.total_return_pct ?? 0);
          }
          return (right.run?.result.total_trades ?? 0) - (left.run?.result.total_trades ?? 0);
        }),
    [backtests.data, strategies.data]
  );
  const bestTarget = targetSnapshots[0];
  const equityData = useMemo(
    () =>
      (selectedRun?.result.equity_curve ?? []).map((point) => {
        const ts = Array.isArray(point) ? point[0] : point.ts;
        const value = Array.isArray(point) ? point[1] : point.equity;
        return {
          ts,
          tsLabel: new Date(ts).toLocaleDateString(),
          equity: Number(Number(value).toFixed(2))
        };
      }),
    [selectedRun]
  );
  const comparisonChartData = useMemo(
    () =>
      targetSnapshots
        .slice(0, 5)
        .map((item) => ({
          label: `${item.symbol}/${item.venue}`,
          sharpe: Number(item.run?.result.sharpe?.toFixed(2) ?? 0),
          returnPct: Number(item.run?.result.total_return_pct?.toFixed(2) ?? 0)
        })),
    [targetSnapshots]
  );

  async function runBacktest(specId: string, symbol: string, venue: string) {
    setSelectedSpecId(specId);
    setSelectedSymbol(symbol);
    setSelectedVenue(venue);
    setStatusMessage(`Running ${symbol} on ${venue}...`);
    try {
      const response = await apiPost<{ target?: { status?: string } }>("/backtests", {
        spec_id: specId,
        symbol,
        venue,
        lookback_days: lookbackDays
      });
      setStatusMessage(
        response.target?.status ? `Backtest completed. Target is now ${response.target.status}.` : "Backtest completed."
      );
      await Promise.all([backtests.refetch(), strategies.refetch()]);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Backtest failed.");
    }
  }

  async function runCompare() {
    if (!selectedStrategy) return;
    setStatusMessage("Running symbol and venue comparison...");
    try {
      const response = await apiPost<{ comparisons: CompareRow[] }>("/backtests/compare", {
        spec_id: selectedStrategy.spec_id,
        lookback_days: lookbackDays
      });
      setCompareRows(response.comparisons);
      setStatusMessage("Comparison completed.");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Comparison failed.");
    }
  }

  async function runSweep() {
    if (!selectedStrategy) return;
    setStatusMessage("Running parameter sweep...");
    try {
      const response = await apiPost<{ results: SweepRow[] }>("/backtests/sweep", {
        spec_id: selectedStrategy.spec_id,
        symbol: selectedSymbol,
        venue: selectedVenue,
        lookback_days: lookbackDays
      });
      setSweepRows(response.results.slice(0, 6));
      setStatusMessage("Sweep completed.");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Sweep failed.");
    }
  }

  async function setTargetState(status: string | null, paperEnabled: boolean | null) {
    if (!selectedStrategy) return;
    setStatusMessage("Updating target...");
    try {
      await apiPost(`/strategies/${selectedStrategy.spec_id}/targets`, {
        symbol: selectedSymbol,
        venue: selectedVenue,
        status: status ?? selectedTarget?.status ?? "shortlist",
        paper_enabled: paperEnabled ?? Boolean(selectedTarget?.paper_enabled),
        last_backtest_run_id: selectedRun?.run_id
      });
      await strategies.refetch();
      setStatusMessage("Target updated.");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Target update failed.");
    }
  }

  async function createStrategyFromBuilder() {
    const specId = `custom-${builderName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "")}`;
    const payload = {
      spec_id: specId,
      name: builderName,
      version: 1,
      created_at: new Date().toISOString(),
      universe: [{ symbol: selectedSymbol, venue: selectedVenue, mode: "perp", quote: "USDT" }],
      primary_timeframe: "1h",
      feature_inputs: [builderFeature],
      entry_long: [{ feature: builderFeature, operator: builderOperator, threshold: builderThreshold }],
      entry_short: [{ feature: builderFeature, operator: builderOperator === "gt" ? "lt" : "gt", threshold: builderThreshold }],
      sizing: { method: "fixed_notional", fixed_notional_usd: 1000 },
      risk_limits: { max_open_positions: 4 },
      execution: { bar_close_only: true, min_volume_usd: 500000, max_spread_bps: 10 },
      hypothesis: builderHypothesis,
      tags: ["custom", "ui-builder"]
    };
    setStatusMessage("Creating strategy from builder...");
    try {
      await apiPost("/strategies", payload);
      await strategies.refetch();
      setSelectedSpecId(specId);
      setStatusMessage(`Created ${specId}.`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Builder create failed.");
    }
  }

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (!selectedStrategy) return;
      if (event.altKey && event.key.toLowerCase() === "b") {
        void runBacktest(selectedStrategy.spec_id, selectedSymbol, selectedVenue);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedStrategy, selectedSymbol, selectedVenue, lookbackDays]);

  if (strategies.isLoading || backtests.isLoading) {
    return <section className="panel skeleton-block">Loading strategy registry...</section>;
  }
  if (strategies.isError || backtests.isError) {
    return <section className="panel">Failed to load strategy registry.</section>;
  }

  return (
    <section className="stack">
      <div className="panel strategy-hero compact-hero">
        <div>
          <div className="eyebrow dark">Strategy Registry</div>
          <h2 className="hero-title compact">Run, compare, and reject with evidence.</h2>
          <p className="hero-copy">
            Choose symbol, venue, and lookback. Then inspect the latest run, compare markets, and sweep thresholds.
          </p>
        </div>
        <div className="run-controls">
          <div className="control-grid">
            <label className="field">
              <span>Lookback</span>
              <select value={lookbackDays} onChange={(event) => setLookbackDays(Number(event.target.value))}>
                {LOOKBACK_OPTIONS.map((days) => (
                  <option key={days} value={days}>
                    {days} days
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Symbol</span>
              <select value={selectedSymbol} onChange={(event) => setSelectedSymbol(event.target.value)}>
                {availableSymbols.map((symbol) => (
                  <option key={symbol} value={symbol}>
                    {symbol}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Venue</span>
              <select value={selectedVenue} onChange={(event) => setSelectedVenue(event.target.value)}>
                {availableVenues.map((venue) => (
                  <option key={venue} value={venue}>
                    {venue}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="button-row">
            <button disabled={!selectedStrategy} onClick={() => selectedStrategy && runBacktest(selectedStrategy.spec_id, selectedSymbol, selectedVenue)}>
              Run Selected
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={runCompare}>
              Compare Markets
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={runSweep}>
              Sweep Params
            </button>
          </div>
          <div className="button-row">
            <button className="secondary-button" disabled={!selectedStrategy} onClick={() => setTargetState("shortlist", null)}>
              Shortlist
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={() => setTargetState("candidate", null)}>
              Candidate
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={() => setTargetState("promoted", null)}>
              Promote
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={() => setTargetState("rejected", false)}>
              Reject
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={() => setTargetState(null, !Boolean(selectedTarget?.paper_enabled))}>
              {selectedTarget?.paper_enabled ? "Disable Paper" : "Enable Paper"}
            </button>
          </div>
        </div>
        <div className="status-strip">{statusMessage || "Select a strategy to inspect the latest run."}</div>
      </div>

      {bestTarget ? (
        <div className="panel target-summary-strip">
          <div>
            <div className="eyebrow dark">Best Current Target</div>
            <div className="target-summary-title">
              {bestTarget.name} on {bestTarget.symbol} / {bestTarget.venue}
            </div>
            <p className="muted target-summary-copy">
              {bestTarget.notes || "This target currently has the strongest evidence-adjusted score in the registry."}
            </p>
          </div>
          <div className="target-summary-metrics">
            <span className={`status-pill ${bestTarget.status}`}>{bestTarget.status}</span>
            <span>Sharpe {bestTarget.run?.result.sharpe.toFixed(2)}</span>
            <span>Return {bestTarget.run ? `${bestTarget.run.result.total_return_pct.toFixed(2)}%` : "n/a"}</span>
            <span>Trades {bestTarget.run?.result.total_trades ?? "n/a"}</span>
            <span>Paper {bestTarget.paper_enabled ? "enabled" : "off"}</span>
          </div>
          <div className="button-row">
            <button
              className="secondary-button"
              onClick={() => {
                setSelectedSpecId(bestTarget.spec_id);
                setSelectedSymbol(bestTarget.symbol);
                setSelectedVenue(bestTarget.venue);
                setStatusMessage(`Focused ${bestTarget.name} on ${bestTarget.symbol} / ${bestTarget.venue}.`);
              }}
            >
              Inspect Best
            </button>
            <button onClick={() => runBacktest(bestTarget.spec_id, bestTarget.symbol, bestTarget.venue)}>Run Best Again</button>
          </div>
        </div>
      ) : null}

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Strategy Builder</h2>
            <p>Create a rule-based strategy without editing Python.</p>
          </div>
        </div>
        <div className="control-grid">
          <label className="field">
            <span>Name</span>
            <input value={builderName} onChange={(event) => setBuilderName(event.target.value)} />
          </label>
          <label className="field">
            <span>Feature</span>
            <select value={builderFeature} onChange={(event) => setBuilderFeature(event.target.value)}>
              {BUILDER_FEATURES.map((feature) => (
                <option key={feature} value={feature}>
                  {feature}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Operator</span>
            <select value={builderOperator} onChange={(event) => setBuilderOperator(event.target.value)}>
              <option value="gt">gt</option>
              <option value="lt">lt</option>
            </select>
          </label>
          <label className="field">
            <span>Threshold</span>
            <input type="number" value={builderThreshold} onChange={(event) => setBuilderThreshold(Number(event.target.value))} />
          </label>
        </div>
        <label className="field">
          <span>Hypothesis</span>
          <input value={builderHypothesis} onChange={(event) => setBuilderHypothesis(event.target.value)} />
        </label>
        <div className="button-row">
          <button onClick={createStrategyFromBuilder}>Save Strategy</button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Strategy Table</h2>
            <p>Built-in specs stay proposed until the evidence is good enough to promote them.</p>
          </div>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Version</th>
              <th>Status</th>
              <th>Hypothesis</th>
              <th>Latest Backtest</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {(strategies.data ?? []).map((row) => (
              <tr
                key={row.spec_id}
                className={row.spec_id === selectedSpecId ? "selected-row" : undefined}
                onClick={() => setSelectedSpecId(row.spec_id)}
              >
                <td>{row.name}</td>
                <td>{row.version}</td>
                <td>{row.status}</td>
                <td>{row.spec.hypothesis}</td>
                <td>
                  {latestBySpec.has(row.spec_id)
                    ? `Sharpe ${latestBySpec.get(row.spec_id)!.result.sharpe.toFixed(2)} | Trades ${latestBySpec.get(row.spec_id)!.result.total_trades}`
                    : "No run yet"}
                </td>
                <td>
                  <button
                    onClick={(event) => {
                      event.stopPropagation();
                      runBacktest(row.spec_id, selectedSymbol, selectedVenue);
                    }}
                  >
                    Run Backtest
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="inspector-grid">
        <div className="panel inspector-main">
          <div className="panel-header">
            <div>
              <h2>{selectedStrategy?.name ?? "Selected Run"}</h2>
              <p>{selectedRun ? `Latest run at ${new Date(selectedRun.ran_at).toLocaleString()}` : "Run a backtest to inspect details."}</p>
            </div>
          </div>

          <div className="metrics-grid">
            <div className="metric-card warm">
              <div className="metric-label">Sharpe</div>
              <div className="metric-value">{selectedRun?.result.sharpe?.toFixed(2) ?? "n/a"}</div>
            </div>
            <div className="metric-card warm">
              <div className="metric-label">Return</div>
              <div className="metric-value">{selectedRun ? `${selectedRun.result.total_return_pct.toFixed(2)}%` : "n/a"}</div>
            </div>
            <div className="metric-card warm">
              <div className="metric-label">Trades</div>
              <div className="metric-value">{selectedRun?.result.total_trades ?? "n/a"}</div>
            </div>
            <div className="metric-card warm">
              <div className="metric-label">Max Drawdown</div>
              <div className="metric-value">{selectedRun ? `${selectedRun.result.max_drawdown_pct.toFixed(2)}%` : "n/a"}</div>
            </div>
          </div>

          <div className="run-meta">
            <span>Target Status: {selectedTarget?.status ?? "proposed"}</span>
            <span>Paper: {selectedTarget?.paper_enabled ? "enabled" : "off"}</span>
            <span>Venue: {selectedRun?.config.instrument?.venue ?? "n/a"}</span>
            <span>Symbol: {selectedRun?.config.instrument?.symbol ?? "n/a"}</span>
            <span>
              Window:{" "}
              {selectedRun
                ? `${new Date(selectedRun.config.start_date).toLocaleDateString()} - ${new Date(selectedRun.config.end_date).toLocaleDateString()}`
                : "n/a"}
            </span>
          </div>

          <div className="chart-shell">
            {equityData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={equityData}>
                  <XAxis dataKey="tsLabel" minTickGap={30} />
                  <YAxis domain={["dataMin", "dataMax"]} width={84} />
                  <Tooltip labelFormatter={(value) => String(value)} />
                  <Line type="monotone" dataKey="equity" stroke="#ff8f00" strokeWidth={3} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state">No equity curve yet. Run a backtest first.</div>
            )}
          </div>

          <div className="chart-shell">
            {comparisonChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={comparisonChartData}>
                  <XAxis dataKey="label" />
                  <YAxis yAxisId="left" width={62} />
                  <YAxis yAxisId="right" orientation="right" width={72} />
                  <Tooltip />
                  <Line yAxisId="left" type="monotone" dataKey="sharpe" stroke="#00adb5" strokeWidth={2} dot />
                  <Line yAxisId="right" type="monotone" dataKey="returnPct" stroke="#ff8f00" strokeWidth={2} dot />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state">No comparison data yet.</div>
            )}
          </div>

          <div className="trade-log">
            <div className="section-title">Latest Trades</div>
            <table className="table compact-table">
              <thead>
                <tr>
                  <th>Direction</th>
                  <th>Entry</th>
                  <th>Exit</th>
                  <th>PnL USD</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {(selectedRun?.result.trades ?? []).slice(0, 8).map((trade) => (
                  <tr key={trade.trade_id}>
                    <td>{trade.direction}</td>
                    <td>{new Date(trade.entry_ts).toLocaleString()}</td>
                    <td>{new Date(trade.exit_ts).toLocaleString()}</td>
                    <td>{trade.pnl_usd.toFixed(2)}</td>
                    <td>{trade.exit_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel inspector-side">
          <div className="section-title">Target Note</div>
          <p className="muted">
            {selectedTarget?.notes || "Run a target-specific backtest to let the app classify this market pair automatically."}
          </p>

          <div className="section-title">Funding Debug Note</div>
          <p className="muted">
            Funding reversion now runs with funding features merged into the bar frame. Use the compare and sweep tools below to see whether the idea fails everywhere or only on certain venue-symbol pairs.
          </p>

          <div className="section-title">Signal Diagnostics</div>
          <div className="diagnostics-list">
            <div>
              <strong>Bars Seen</strong>
              <span>{diagnostics?.bars_seen ?? "n/a"}</span>
            </div>
            <div>
              <strong>Long Signals</strong>
              <span>{diagnostics?.signal_counts?.long ?? 0}</span>
            </div>
            <div>
              <strong>Short Signals</strong>
              <span>{diagnostics?.signal_counts?.short ?? 0}</span>
            </div>
            <div>
              <strong>Flat Bars</strong>
              <span>{diagnostics?.signal_counts?.flat ?? 0}</span>
            </div>
          </div>

          <div className="section-title">Feature Ranges</div>
          <div className="range-list">
            {Object.entries(diagnostics?.feature_ranges ?? {}).map(([feature, range]) => (
              <div key={feature}>
                <strong>{feature}</strong>
                <span>
                  {range.min.toFixed(4)} to {range.max.toFixed(4)}
                </span>
              </div>
            ))}
          </div>

          <div className="section-title">Market Compare</div>
          <div className="range-list">
            {compareRows.map((row) => (
              <div key={`${row.symbol}-${row.venue}`}>
                <strong>
                  {row.symbol} / {row.venue}
                </strong>
                <span>{row.sharpe === null ? "no data" : `Sharpe ${row.sharpe.toFixed(2)} | Trades ${row.total_trades}`}</span>
              </div>
            ))}
          </div>

          <div className="section-title">Top Sweep Results</div>
          <div className="range-list">
            {sweepRows.map((row) => (
              <div key={row.label}>
                <strong>{row.label}</strong>
                <span>Sharpe {row.sharpe.toFixed(2)} | Trades {row.trades}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

```

## `scripts/bootstrap_secure_runtime.py`

```python
from __future__ import annotations

import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


DEFAULTS = {
    "BINANCE_BASE_URL": "https://fapi.binance.com",
    "HYPERLIQUID_BASE_URL": "https://api.hyperliquid.xyz",
    "OPENROUTER_API_KEY": "",
    "OPENROUTER_MODEL": "anthropic/claude-3.5-haiku",
    "AUTH_VIEWER_TOKEN": secrets.token_urlsafe(32),
    "AUTH_OPERATOR_TOKEN": secrets.token_urlsafe(32),
    "AUTH_ADMIN_TOKEN": secrets.token_urlsafe(32),
    "AUTH_COOKIE_NAME": "workbench_token",
    "AUTH_COOKIE_SECURE": "false",
    "AUTH_COOKIE_MAX_AGE_SECONDS": "28800",
    "VAULT_PASSPHRASE": secrets.token_urlsafe(24),
    "VAULT_FILE_PATH": "./data/meta/secrets.vault",
    "APP_LOG_PATH": "./data/meta/workbench.log",
    "RAW_DATA_ROOT": "./data/raw",
    "CURATED_DB_PATH": "./data/curated/workbench.duckdb",
    "META_DB_PATH": "./data/meta/workbench.db",
    "PAPER_INITIAL_CAPITAL_USD": "100000",
    "PAPER_FEE_BPS": "4.0",
    "PAPER_SLIPPAGE_BPS": "3.0",
    "PAPER_TRADING_ENABLED": "true",
    "PAPER_MAX_OPEN_POSITIONS": "4",
    "PAPER_MAX_GROSS_EXPOSURE_USD": "40000",
    "PAPER_DAILY_LOSS_LIMIT_USD": "1500",
    "PAPER_DAY_RESET_HOUR_UTC": "0",
    "DATA_READINESS_COVERAGE_DAYS": "20",
    "PAPER_READINESS_MIN_EVENTS": "10",
    "LIVE_TRADING_ENABLED": "false",
    "LIVE_APPROVAL_MODE": "true",
    "LIVE_NETWORK_ENABLED": "false",
    "BINANCE_API_KEY": "",
    "BINANCE_API_SECRET": "",
    "HYPERLIQUID_PRIVATE_KEY": "",
    "HYPERLIQUID_ACCOUNT_ADDRESS": "",
    "SCHEDULER_ENABLED": "false",
    "CORS_ALLOW_ORIGINS": "http://localhost:5173,http://127.0.0.1:5173",
    "CORS_ALLOW_METHODS": "GET,POST,OPTIONS",
    "CORS_ALLOW_HEADERS": "Content-Type,X-Workbench-Token",
    "API_RATE_LIMIT_GLOBAL_PER_MINUTE": "600",
    "API_RATE_LIMIT_AUTH_TOKEN_PER_MINUTE": "10",
    "API_RATE_LIMIT_TICKET_APPROVE_PER_MINUTE": "20",
    "WORKER_MAX_RETRIES": "3",
    "WORKER_RETRY_BACKOFF_SECONDS": "5",
    "WORKER_HEARTBEAT_TTL_SECONDS": "30",
    "MARKET_STREAMS_ENABLED": "false",
    "ALERTS_TELEGRAM_BOT_TOKEN": "",
    "ALERTS_TELEGRAM_CHAT_ID": "",
    "ALERTS_DISCORD_WEBHOOK_URL": "",
    "ALERTS_EMAIL_SMTP_HOST": "",
    "ALERTS_EMAIL_SMTP_PORT": "587",
    "ALERTS_EMAIL_USERNAME": "",
    "ALERTS_EMAIL_PASSWORD": "",
    "ALERTS_EMAIL_FROM": "",
    "ALERTS_EMAIL_TO": "",
}


def main() -> None:
    if ENV_PATH.exists():
        print(f".env already exists at {ENV_PATH}")
        return
    content = "\n".join(f"{key}={value}" for key, value in DEFAULTS.items()) + "\n"
    ENV_PATH.write_text(content, encoding="utf-8")
    print(f"Created secure runtime .env at {ENV_PATH}")
    print("LIVE_TRADING_ENABLED=false and LIVE_NETWORK_ENABLED=false were left off for safety.")


if __name__ == "__main__":
    main()

```

## `scripts/enable_live_approval_mode.py`

```python
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def main() -> None:
    if not ENV_PATH.exists():
        raise SystemExit(".env not found. Run scripts/bootstrap_secure_runtime.py first.")
    text = ENV_PATH.read_text(encoding="utf-8")
    replacements = {
        "LIVE_TRADING_ENABLED=false": "LIVE_TRADING_ENABLED=true",
        "LIVE_APPROVAL_MODE=true": "LIVE_APPROVAL_MODE=true",
        "LIVE_NETWORK_ENABLED=false": "LIVE_NETWORK_ENABLED=false",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    ENV_PATH.write_text(text, encoding="utf-8")
    print("Live approval mode enabled in .env with network execution still disabled.")


if __name__ == "__main__":
    main()

```

## `scripts/scan_secrets.py`

```python
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", ".venv", ".pytest_cache", ".npm-cache", "node_modules", "data"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".parquet", ".duckdb", ".db", ".wal", ".shm", ".lock"}

PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|passphrase)\s*=\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
]


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        files.append(path)
    return files


def main() -> int:
    findings: list[str] = []
    for path in _iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for pattern in PATTERNS:
            for match in pattern.finditer(text):
                snippet = match.group(0)
                findings.append(f"{path.relative_to(ROOT)} :: {snippet[:90]}")
    if findings:
        print("Potential secrets detected:")
        for item in findings:
            print(f"- {item}")
        return 1
    print("Secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

## `scripts/set_vault_secret.py`

```python
from __future__ import annotations

import argparse
import sys

from backend.secrets.vault import set_secret


def main() -> int:
    parser = argparse.ArgumentParser(description="Store an exchange secret in the local encrypted vault.")
    parser.add_argument("name", help="Secret name")
    parser.add_argument("value", help="Secret value")
    parser.add_argument("--passphrase", help="Vault passphrase override", default=None)
    args = parser.parse_args()
    try:
        result = set_secret(args.name, args.value, args.passphrase)
    except Exception as exc:
        print(f"Failed to store secret: {exc}")
        return 1
    print("Vault updated.")
    print("Configured keys:", ", ".join(result["configured_keys"]) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

## `tests/test_auth_and_worker.py`

```python
from backend.auth.service import bootstrap_users, get_user_by_token
from backend.core.config import settings
from backend.data import storage
from backend.execution.service import approve_execution_ticket, create_execution_ticket
from backend.worker.jobs import list_jobs
from backend.worker.service import job_metrics


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_bootstrap_users_supports_default_operator_tokens(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    bootstrap_users()

    operator = get_user_by_token(settings.auth_operator_token)

    assert operator["role"] == "operator"
    assert operator["display_name"] == "Operator"


def test_approved_live_ticket_queues_when_enabled_and_secrets_present(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    from backend.execution import service

    monkeypatch.setattr(service, "live_secrets_status", lambda: {"all_present": True, "venues": {"binance": True, "hyperliquid": True}})
    monkeypatch.setattr(
        service,
        "settings",
        type("DummySettings", (), {"live_trading_enabled": True, "live_approval_mode": True})(),
    )

    ticket = create_execution_ticket(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        direction="long",
        action="open",
        size_usd=1000.0,
    )
    approved = approve_execution_ticket(ticket["ticket_id"])
    jobs = list_jobs()
    metrics = job_metrics()

    assert approved["status"] == "queued"
    assert len(jobs) == 1
    assert jobs[0]["job_type"] == "execution_submit"
    assert metrics["queued"] == 1

```

## `tests/test_backtest_robustness.py`

```python
from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.backtest import engine
from backend.core.types import BacktestConfig
from backend.strategy.signals.momentum import build as build_momentum


def test_backtest_robustness_metrics_are_applied(monkeypatch) -> None:
    spec = build_momentum()
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(90):
        rows.append(
            {
                "ts_open": start + timedelta(hours=index),
                "close": 100 + index * 0.5,
                "ret_4": 0.02 if index % 9 < 5 else -0.02,
                "vol_ratio": 1.5,
                "trend_signal": 1 if index % 9 < 5 else -1,
                "vol_20": 0.05,
            }
        )
    frame = pd.DataFrame(rows)
    config = BacktestConfig(start_date=start, end_date=start + timedelta(hours=90))

    monkeypatch.setattr(engine, "_compute_perturbation_sharpe", lambda *args, **kwargs: (1.23, 0.11))
    monkeypatch.setattr(engine, "_compute_oos_sharpe", lambda *args, **kwargs: 0.77)

    result = engine.run_backtest(spec, frame, config)

    assert result.perturbation_sharpe_mean == 1.23
    assert result.perturbation_sharpe_std == 0.11
    assert result.oos_sharpe == 0.77

```

## `tests/test_backtest_service.py`

```python
from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.backtest import service
from backend.core.types import Instrument, Timeframe, Venue, VenueMode
from backend.data import storage
from backend.strategy import registry


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def _seed_bars(inst: Instrument) -> None:
    start = datetime.now(timezone.utc) - timedelta(hours=220)
    bars = pd.DataFrame(
        {
            "ts_open": pd.date_range(start, periods=220, freq="1h", tz="UTC"),
            "ts_close": pd.date_range(start + timedelta(hours=1), periods=220, freq="1h", tz="UTC"),
            "open": [float(100 + idx) for idx in range(220)],
            "high": [float(101 + idx) for idx in range(220)],
            "low": [float(99 + idx) for idx in range(220)],
            "close": [float(100 + idx) for idx in range(220)],
            "volume": [10.0] * 220,
            "volume_quote": [1_000_000.0] * 220,
            "trades": [5] * 220,
        }
    )
    storage.write_bars(inst, Timeframe.H1, bars)


def test_resolve_instrument_supports_venue_specific_runs(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()

    spec, instrument = service.resolve_instrument("builtin-range-breakout", "BTC", "hyperliquid")

    assert spec.spec_id == "builtin-range-breakout"
    assert instrument.symbol == "BTC"
    assert instrument.venue.value == "hyperliquid"


def test_compare_runs_covers_multiple_venues(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()
    instruments = [
        Instrument(symbol="BTC", venue=Venue.BINANCE, mode=VenueMode.PERP),
        Instrument(symbol="ETH", venue=Venue.BINANCE, mode=VenueMode.PERP),
        Instrument(symbol="BTC", venue=Venue.HYPERLIQUID, mode=VenueMode.PERP),
        Instrument(symbol="ETH", venue=Venue.HYPERLIQUID, mode=VenueMode.PERP),
    ]
    for instrument in instruments:
        _seed_bars(instrument)

    monkeypatch.setattr(
        service,
        "load_funding_like_series",
        lambda *args, **kwargs: pd.DataFrame(columns=["ts", "rate"]),
    )

    results = service.compare_runs("builtin-range-breakout", 30)

    assert len(results) == 4
    assert {row["venue"] for row in results} == {"binance", "hyperliquid"}


def test_sweep_runs_returns_ranked_results(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()
    instrument = Instrument(symbol="BTC", venue=Venue.BINANCE, mode=VenueMode.PERP)
    _seed_bars(instrument)
    monkeypatch.setattr(
        service,
        "load_funding_like_series",
        lambda *args, **kwargs: pd.DataFrame(columns=["ts", "rate"]),
    )

    results = service.sweep_runs("builtin-momentum-with-vol-filter", "BTC", "binance", 30)

    assert len(results) > 1
    assert results[0]["sharpe"] >= results[-1]["sharpe"]

```

## `tests/test_data_service.py`

```python
import asyncio
from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.core.types import Instrument, Timeframe, Venue, VenueMode
from backend.data import service, storage
from backend.strategy import registry


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_ingest_bars_writes_parquet_and_health(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    inst = Instrument(symbol="BTC", venue=Venue.BINANCE, mode=VenueMode.PERP)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=3)

    async def fake_fetch(inst_arg, timeframe_arg, start_arg, end_arg):
        assert inst_arg == inst
        assert timeframe_arg == Timeframe.M15
        return pd.DataFrame(
            {
                "ts_open": pd.date_range(start_arg, periods=12, freq="15min", tz="UTC"),
                "ts_close": pd.date_range(start_arg + timedelta(minutes=15), periods=12, freq="15min", tz="UTC"),
                "open": [100.0] * 12,
                "high": [101.0] * 12,
                "low": [99.0] * 12,
                "close": [100.0] * 12,
                "volume": [10.0] * 12,
                "volume_quote": [1000.0] * 12,
                "trades": [5] * 12,
            }
        )

    monkeypatch.setattr(service, "_fetch_bars", fake_fetch)

    summary = asyncio.run(service.ingest_bars(inst, Timeframe.M15, start, end))
    saved = storage.read_bars(inst, Timeframe.M15, start, end + timedelta(days=1))

    assert summary.rows_written == 12
    assert not saved.empty
    assert len(saved) == 12


def test_latest_feature_bar_returns_computed_fields(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    inst = Instrument(symbol="BTC", venue=Venue.BINANCE, mode=VenueMode.PERP)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    bars = pd.DataFrame(
        {
            "ts_open": pd.date_range(start, periods=60, freq="1h", tz="UTC"),
            "ts_close": pd.date_range(start + timedelta(hours=1), periods=60, freq="1h", tz="UTC"),
            "open": [float(100 + idx) for idx in range(60)],
            "high": [float(101 + idx) for idx in range(60)],
            "low": [float(99 + idx) for idx in range(60)],
            "close": [float(100 + idx) for idx in range(60)],
            "volume": [10.0] * 60,
            "volume_quote": [1_000_000.0] * 60,
            "trades": [5] * 60,
        }
    )
    storage.write_bars(inst, Timeframe.H1, bars)

    async def fake_funding(*args, **kwargs):
        return pd.DataFrame(columns=["ts", "rate"])

    async def fake_context(*args, **kwargs):
        return {
            "open_interest": pd.DataFrame(columns=["ts", "open_interest"]),
            "taker_flow": pd.DataFrame(columns=["ts", "taker_buy_volume", "taker_sell_volume"]),
            "liquidations": pd.DataFrame(columns=["ts", "liquidation_volume"]),
        }

    monkeypatch.setattr(service, "load_funding_like_series_async", fake_funding)
    monkeypatch.setattr(service, "fetch_market_context_series", fake_context)

    latest = service.latest_feature_bar(inst, Timeframe.H1)

    assert latest is not None
    assert "ret_4" in latest
    assert "rsi_14" in latest
    assert latest["timeframe"] == "1h"


def test_funding_feature_range_moves_off_zero_when_history_exists(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    inst = Instrument(symbol="BTC", venue=Venue.BINANCE, mode=VenueMode.PERP)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    bars = pd.DataFrame(
        {
            "ts_open": pd.date_range(start, periods=80, freq="1h", tz="UTC"),
            "ts_close": pd.date_range(start + timedelta(hours=1), periods=80, freq="1h", tz="UTC"),
            "open": [float(100 + idx) for idx in range(80)],
            "high": [float(101 + idx) for idx in range(80)],
            "low": [float(99 + idx) for idx in range(80)],
            "close": [float(100 + idx) for idx in range(80)],
            "volume": [10.0] * 80,
            "volume_quote": [1_000_000.0] * 80,
            "trades": [5] * 80,
        }
    )
    storage.write_bars(inst, Timeframe.H1, bars)

    async def fake_funding(*args, **kwargs):
        return pd.DataFrame(
            {
                "ts": pd.date_range(start, periods=80, freq="1h", tz="UTC"),
                "rate": [(-1) ** idx * 0.001 * (1 + idx / 100) for idx in range(80)],
            }
        )

    async def fake_context(*args, **kwargs):
        return {
            "open_interest": pd.DataFrame(columns=["ts", "open_interest"]),
            "taker_flow": pd.DataFrame(columns=["ts", "taker_buy_volume", "taker_sell_volume"]),
            "liquidations": pd.DataFrame(columns=["ts", "liquidation_volume"]),
        }

    monkeypatch.setattr(service, "load_funding_like_series_async", fake_funding)
    monkeypatch.setattr(service, "fetch_market_context_series", fake_context)
    latest = service.latest_feature_bar(inst, Timeframe.H1)

    assert latest is not None
    assert abs(float(latest["funding_zscore"])) > 0


def test_builtin_registry_bootstrap_is_stable(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)

    registry.bootstrap_builtin_specs()
    first = registry.list_specs()
    second = registry.list_specs()

    assert len(first) == 3
    assert [item["spec_id"] for item in first] == [item["spec_id"] for item in second]

```

## `tests/test_engine.py`

```python
from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.backtest.engine import run_backtest
from backend.core.types import BacktestConfig, RuleBlock
from backend.strategy.engine import evaluate_rules
from backend.strategy.signals.momentum import build as build_momentum


def test_rule_evaluation_gt() -> None:
    rule = RuleBlock(feature="rsi_14", operator="gt", threshold=70)
    assert evaluate_rules([rule], {"rsi_14": 75}) is True
    assert evaluate_rules([rule], {"rsi_14": 65}) is False


def test_fees_and_backtest_runs() -> None:
    spec = build_momentum()
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(80):
        rows.append(
            {
                "ts_open": start + timedelta(hours=index),
                "open": 100 + index,
                "high": 101 + index,
                "low": 99 + index,
                "close": 100 + index,
                "volume": 10,
                "volume_quote": 1_000_000,
                "ret_4": 0.02 if index % 10 < 5 else -0.02,
                "vol_ratio": 1.5,
                "trend_signal": 1 if index % 10 < 5 else -1,
                "vol_20": 0.05,
            }
        )
    result = run_backtest(spec, pd.DataFrame(rows), BacktestConfig(start_date=start, end_date=start + timedelta(hours=80)))
    assert result.total_trades > 0
    assert result.avg_trade_pnl_usd != 0

```

## `tests/test_execution_hmac.py`

```python
import hashlib
import hmac
from urllib.parse import parse_qs, urlparse

from backend.execution.adapters import BinanceFuturesAdapter


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"ok": True}


def test_binance_signed_request_uses_hmac_signature(monkeypatch) -> None:
    captured = {"url": ""}

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def request(self, method: str, url: str):
            captured["url"] = url
            return _FakeResponse()

    monkeypatch.setattr("backend.execution.adapters.httpx.Client", _FakeClient)

    adapter = BinanceFuturesAdapter()
    adapter.api_key = "k"
    adapter.api_secret = "secret123"
    adapter.base_url = "https://example.com"
    adapter._signed_request("GET", "/fapi/v1/openOrders", {"timestamp": 12345, "recvWindow": 5000})

    query = parse_qs(urlparse(captured["url"]).query)
    signature = query["signature"][0]
    unsigned = "timestamp=12345&recvWindow=5000"
    expected = hmac.HMAC(b"secret123", unsigned.encode("utf-8"), hashlib.sha256).hexdigest()
    assert signature == expected

```

## `tests/test_execution_service.py`

```python
from backend.data import storage
from backend.execution.service import (
    approve_execution_ticket,
    create_execution_ticket,
    list_reconciliation,
    live_secrets_status,
    reconcile_venue,
)


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_create_execution_ticket_builds_preview(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)

    ticket = create_execution_ticket(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        direction="long",
        action="open",
        size_usd=1000.0,
    )

    assert ticket["status"] == "pending_approval"
    assert ticket["preview"]["approval_required"] is True
    assert ticket["preview"]["estimated_fee_usd"] > 0


def test_approve_execution_ticket_blocks_when_live_is_disabled(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)

    ticket = create_execution_ticket(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        direction="long",
        action="open",
        size_usd=1000.0,
    )
    approved = approve_execution_ticket(ticket["ticket_id"])

    assert approved["status"] == "blocked"


def test_reconcile_venue_persists_snapshot(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)

    result = reconcile_venue("binance")
    rows = list_reconciliation()

    assert result["venue"] == "binance"
    assert len(rows) == 1
    assert rows[0]["status"] == "approval_mode"


def test_live_secrets_status_defaults_missing() -> None:
    status = live_secrets_status()
    assert status["all_present"] is False

```

## `tests/test_ops_readiness.py`

```python
from datetime import datetime, timedelta, timezone

from backend.data import storage
from backend.ops.audit import record_audit_event
from backend.ops.readiness import readiness_snapshot
from backend.strategy import registry, targets


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_readiness_reports_live_blockers_when_live_is_disabled(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()
    now = datetime.now(timezone.utc)
    storage.upsert_dataset_health(
        [
            {
                "instrument_key": "binance:perp:BTC/USDT",
                "timeframe": "1h",
                "quality": "healthy",
                "last_bar_ts": (now - timedelta(minutes=30)).isoformat(),
                "gap_count": 0,
                "duplicate_count": 0,
                "coverage_days": 25.0,
                "checked_at": now.isoformat(),
            }
        ]
    )
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="promoted",
        paper_enabled=True,
    )
    record_audit_event("test.event", "system", "one", {"ok": True})

    snapshot = readiness_snapshot()

    assert snapshot["summary"]["data_ready"] is True
    assert snapshot["summary"]["live_ready"] is False
    assert "live_trading_disabled_by_config" in snapshot["summary"]["blockers"]
    assert snapshot["counts"]["audit_events"] >= 1

```

## `tests/test_paper_activity.py`

```python
from datetime import datetime, timezone

from backend.core.types import Instrument, Venue, VenueMode
from backend.data import storage
from backend.paper.activity import portfolio_snapshot
from backend.paper.broker import fill_order, open_position, submit_order
from backend.strategy import registry, targets


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_portfolio_snapshot_groups_activity_by_target(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="candidate",
        paper_enabled=True,
    )
    spec = registry.load_spec("builtin-range-breakout")
    assert spec is not None

    inst = Instrument(symbol="ETH", venue=Venue.BINANCE, mode=VenueMode.PERP)
    order = submit_order(spec, inst, "long", "open", 1_000.0, datetime.now(timezone.utc))
    fill_order(order, 101.0)
    open_position(order)

    snapshot = portfolio_snapshot()

    assert len(snapshot["active_targets"]) == 1
    assert snapshot["positions"][0]["symbol"] == "ETH"
    assert snapshot["orders"][0]["venue"] == "binance"
    assert snapshot["target_activity"][0]["recent_orders"] == 1
    assert snapshot["target_activity"][0]["open_positions"] == 1

```

## `tests/test_paper_runner.py`

```python
from datetime import datetime, timezone

from backend.data import storage
from backend.data.storage import fetch_all
from backend.paper.runner import run_bar
from backend.strategy import registry, targets


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_run_bar_logs_risk_block_event_for_low_volume(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="promoted",
        paper_enabled=True,
    )

    run_bar(
        {
            "timeframe": "1h",
            "symbol": "ETH",
            "venue": "binance",
            "ts": datetime.now(timezone.utc),
            "close": 2500.0,
            "volume_quote": 100.0,
            "pct_rank_20": 0.99,
            "vol_ratio": 2.1,
        }
    )

    rows = fetch_all("SELECT * FROM paper_cycle_events ORDER BY created_at DESC", [])

    assert len(rows) == 1
    assert rows[0]["event_type"] == "skipped"
    assert rows[0]["reason"] == "min_volume_not_met"


def test_run_bar_full_cycle_opens_and_closes_position(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="promoted",
        paper_enabled=True,
    )

    run_bar(
        {
            "timeframe": "1h",
            "symbol": "ETH",
            "venue": "binance",
            "ts": datetime.now(timezone.utc),
            "close": 2500.0,
            "volume_quote": 1_200_000.0,
            "pct_rank_20": 0.99,
            "vol_ratio": 2.1,
            "atr_14": 22.0,
            "vol_20": 0.04,
        }
    )
    run_bar(
        {
            "timeframe": "1h",
            "symbol": "ETH",
            "venue": "binance",
            "ts": datetime.now(timezone.utc),
            "close": 2475.0,
            "volume_quote": 1_400_000.0,
            "pct_rank_20": 0.01,
            "vol_ratio": 2.2,
            "atr_14": 25.0,
            "vol_20": 0.05,
        }
    )

    positions = fetch_all("SELECT * FROM paper_positions ORDER BY opened_at DESC", [])
    orders = fetch_all("SELECT * FROM paper_orders ORDER BY triggered_at DESC", [])
    events = fetch_all("SELECT * FROM paper_cycle_events ORDER BY created_at DESC", [])

    assert len(orders) >= 2
    assert len(positions) >= 1
    assert any(row["closed_at"] is not None for row in positions)
    assert any(row["event_type"] == "position_opened" for row in events)
    assert any(row["event_type"] == "position_closed" for row in events)

```

## `tests/test_pipeline_flow.py`

```python
from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.backtest import service as backtest_service
from backend.core.types import Instrument, Timeframe, Venue, VenueMode
from backend.data import storage
from backend.paper.runner import run_bar
from backend.strategy import registry, targets


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def _seed_bars(inst: Instrument) -> None:
    start = datetime.now(timezone.utc) - timedelta(hours=240)
    bars = pd.DataFrame(
        {
            "ts_open": pd.date_range(start, periods=240, freq="1h", tz="UTC"),
            "ts_close": pd.date_range(start + timedelta(hours=1), periods=240, freq="1h", tz="UTC"),
            "open": [float(100 + idx * 0.3) for idx in range(240)],
            "high": [float(101 + idx * 0.3) for idx in range(240)],
            "low": [float(99 + idx * 0.3) for idx in range(240)],
            "close": [float(100 + idx * 0.3) for idx in range(240)],
            "volume": [10.0] * 240,
            "volume_quote": [1_200_000.0] * 240,
            "trades": [5] * 240,
        }
    )
    storage.write_bars(inst, Timeframe.H1, bars)


def test_backtest_promote_paper_flow(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()
    instrument = Instrument(symbol="ETH", venue=Venue.BINANCE, mode=VenueMode.PERP)
    _seed_bars(instrument)

    monkeypatch.setattr(
        backtest_service,
        "load_funding_like_series",
        lambda *args, **kwargs: pd.DataFrame(columns=["ts", "rate"]),
    )

    result, decision = backtest_service.execute_backtest("builtin-range-breakout", "ETH", "binance", 30)
    target = targets.sync_target_with_backtest("builtin-range-breakout", "ETH", "binance", result, decision)
    targets.update_target_state("builtin-range-breakout", "ETH", "binance", status="promoted", paper_enabled=True)

    run_bar(
        {
            "timeframe": "1h",
            "symbol": "ETH",
            "venue": "binance",
            "ts": datetime.now(timezone.utc),
            "close": 2500.0,
            "volume_quote": 1_400_000.0,
            "pct_rank_20": 0.99,
            "vol_ratio": 2.0,
            "atr_14": 15.0,
            "vol_20": 0.04,
        }
    )

    open_positions = storage.fetch_all("SELECT * FROM paper_positions WHERE closed_at IS NULL", [])
    assert len(open_positions) >= 1

```

## `tests/test_quality.py`

```python
from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.core.types import DataQuality, Instrument, Timeframe, Venue, VenueMode
from backend.data.quality import check_dataset


def _instrument() -> Instrument:
    return Instrument(symbol="BTC", venue=Venue.BINANCE, mode=VenueMode.PERP)


def test_gap_detection() -> None:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    df = pd.DataFrame(
        {
            "ts_open": [start, start + timedelta(minutes=15), start + timedelta(hours=2, minutes=15)],
            "open": [1, 1, 1],
            "high": [1, 1, 1],
            "low": [1, 1, 1],
            "close": [1, 1, 1],
            "volume": [1, 1, 1],
            "volume_quote": [1, 1, 1],
        }
    )
    health = check_dataset(_instrument(), Timeframe.M15, df, now=start + timedelta(hours=3))
    assert health.gap_count == 1
    assert health.quality == DataQuality.GAPPED


def test_stale_detection() -> None:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    df = pd.DataFrame(
        {
            "ts_open": [start, start + timedelta(minutes=15), start + timedelta(minutes=30)],
            "open": [1, 1, 1],
            "high": [1, 1, 1],
            "low": [1, 1, 1],
            "close": [1, 1, 1],
            "volume": [1, 1, 1],
            "volume_quote": [1, 1, 1],
        }
    )
    health = check_dataset(_instrument(), Timeframe.M15, df, now=start + timedelta(hours=3))
    assert health.quality == DataQuality.STALE

```

## `tests/test_runner_state.py`

```python
from datetime import datetime, timedelta, timezone

from backend.data import service, storage


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_runner_state_dedupes_same_bar(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    ts = datetime(2025, 1, 1, tzinfo=timezone.utc)

    assert service.should_process_bar("paper:test", ts) is True
    service.mark_processed("paper:test", ts)
    assert service.should_process_bar("paper:test", ts) is False
    assert service.should_process_bar("paper:test", ts + timedelta(minutes=15)) is True

```

## `tests/test_spec_validator.py`

```python
from backend.core.types import RuleBlock
from backend.strategy.signals.momentum import build as build_momentum
from backend.strategy.validator import validate_spec


def test_rejects_empty_hypothesis() -> None:
    spec = build_momentum()
    spec.hypothesis = ""
    result = validate_spec(spec)
    assert result.valid is False


def test_rejects_unknown_feature() -> None:
    spec = build_momentum()
    spec.entry_long = [RuleBlock(feature="made_up_feature", operator="gt", threshold=1)]
    result = validate_spec(spec)
    assert result.valid is False

```

## `tests/test_targets.py`

```python
import json

from backend.data import storage
from backend.strategy import registry, targets


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_infer_target_status_promotes_strong_runs() -> None:
    status, note = targets.infer_target_status(
        {
            "sharpe": 1.36,
            "total_return_pct": 0.05,
            "total_trades": 57,
            "max_drawdown_pct": 0.03,
        },
        {"passed": False, "policy": {"min_trade_count": 30}},
    )

    assert status == "promoted"
    assert "Auto-promoted" in note


def test_sync_target_with_backtest_disables_rejected_paper_targets(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="candidate",
        paper_enabled=True,
    )

    synced = targets.sync_target_with_backtest(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        result={
            "run_id": "run-reject",
            "sharpe": -1.1,
            "total_return_pct": -3.0,
            "total_trades": 4,
            "max_drawdown_pct": 14.0,
        },
        decision={"passed": False, "policy": {"min_trade_count": 30}},
    )

    assert synced["status"] == "rejected"
    assert synced["paper_enabled"] == 0
    assert synced["last_backtest_run_id"] == "run-reject"


def test_best_target_snapshot_uses_latest_target_runs(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()

    storage.save_json_record(
        "backtest_runs",
        {
            "run_id": "run-eth",
            "spec_id": "builtin-range-breakout",
            "config_json": json.dumps({"instrument": {"symbol": "ETH", "venue": "binance"}}),
            "result_json": json.dumps({"sharpe": 1.36, "total_return_pct": 0.05, "total_trades": 57}),
            "ran_at": "2026-04-02T00:00:00+00:00",
        },
        "run_id",
    )
    storage.save_json_record(
        "backtest_runs",
        {
            "run_id": "run-btc",
            "spec_id": "builtin-funding-mean-reversion",
            "config_json": json.dumps({"instrument": {"symbol": "BTC", "venue": "binance"}}),
            "result_json": json.dumps({"sharpe": 0.37, "total_return_pct": 0.02, "total_trades": 23}),
            "ran_at": "2026-04-02T00:10:00+00:00",
        },
        "run_id",
    )
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="promoted",
        last_backtest_run_id="run-eth",
    )
    targets.update_target_state(
        spec_id="builtin-funding-mean-reversion",
        symbol="BTC",
        venue="binance",
        status="candidate",
        last_backtest_run_id="run-btc",
    )

    snapshot = targets.best_target_snapshot()

    assert snapshot is not None
    assert snapshot["spec_id"] == "builtin-range-breakout"
    assert snapshot["symbol"] == "ETH"
    assert snapshot["result"]["sharpe"] == 1.36

```

## `tests/test_vault_and_queue.py`

```python
import pytest

from backend.data import storage
from backend.secrets import vault
from backend.worker.jobs import enqueue_job
from backend.worker import service as worker_service


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()
    monkeypatch.setattr(
        vault,
        "settings",
        type("DummySettings", (), {"vault_file_path": tmp_path / "meta" / "secrets.vault", "vault_passphrase": "unit-test-passphrase"})(),
    )


def test_vault_round_trip(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)

    if not vault.CRYPTOGRAPHY_AVAILABLE:
        with pytest.raises(RuntimeError, match="vault_dependency_missing"):
            vault.set_secret("binance_api_key", "abc123")
        status = vault.vault_status()
        assert status["available"] is False
        return

    status = vault.set_secret("binance_api_key", "abc123")

    assert status["exists"] is True
    assert vault.get_secret("binance_api_key") == "abc123"


def test_process_next_job_completes_execution_submit(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(
        worker_service,
        "process_execution_job",
        lambda payload: {"ticket_id": payload["ticket_id"], "submission": {"status": "ok"}},
    )
    job = enqueue_job("execution_submit", {"ticket_id": "t-1"})

    completed = worker_service.process_next_job()

    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["job_id"] == job["job_id"]

```

