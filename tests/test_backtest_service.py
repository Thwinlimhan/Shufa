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
