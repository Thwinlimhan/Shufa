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
