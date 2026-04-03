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
