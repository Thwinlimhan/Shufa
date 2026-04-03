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
