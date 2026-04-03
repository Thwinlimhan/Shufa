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
