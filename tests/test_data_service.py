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
