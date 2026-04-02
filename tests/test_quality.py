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
