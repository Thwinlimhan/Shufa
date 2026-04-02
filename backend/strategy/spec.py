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
