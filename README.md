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
