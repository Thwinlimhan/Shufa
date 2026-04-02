from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlencode

import httpx

from backend.core.config import settings
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
        response = httpx.get(
            f"{self.base_url}/fapi/v1/premiumIndex",
            params={"symbol": instrument.venue_symbol},
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        return Decimal(str(payload["markPrice"]))

    def _quantity_for_notional(self, instrument: Instrument, size_usd: float, mark_price: Decimal) -> str:
        info = httpx.get(f"{self.base_url}/fapi/v1/exchangeInfo", timeout=10.0)
        info.raise_for_status()
        symbol_info = next(item for item in info.json()["symbols"] if item["symbol"] == instrument.venue_symbol)
        quantity_precision = int(symbol_info.get("quantityPrecision", 3))
        raw_quantity = Decimal(str(size_usd)) / mark_price
        quantum = Decimal("1").scaleb(-quantity_precision)
        quantity = raw_quantity.quantize(quantum, rounding=ROUND_DOWN)
        return format(quantity, "f")

    def _signed_request(self, method: str, path: str, params: dict) -> dict:
        query = urlencode(params, doseq=True)
        signature = hmac.new(self.api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        headers = {"X-MBX-APIKEY": self.api_key}
        with httpx.Client(base_url=self.base_url, timeout=15.0, headers=headers) as client:
            response = client.request(method, f"{path}?{query}&signature={signature}")
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
