from __future__ import annotations

from backend.core.types import BacktestResult, PromotionDecision, PromotionPolicy, utc_now


def compute_max_drawdown(equity_curve: list[tuple]) -> tuple[float, float]:
    if not equity_curve:
        return 0.0, 0.0
    peak = equity_curve[0][1]
    peak_time = equity_curve[0][0]
    max_dd = 0.0
    max_duration = 0.0
    for ts, value in equity_curve:
        if value >= peak:
            peak = value
            peak_time = ts
        drawdown = (peak - value) / peak if peak else 0.0
        if drawdown > max_dd:
            max_dd = drawdown
            max_duration = max(max_duration, (ts - peak_time).total_seconds() / 86400)
    return max_dd * 100, max_duration


def annualized_return(total_return_pct: float, days: float) -> float:
    if days <= 0:
        return 0.0
    total = 1 + total_return_pct / 100
    return (total ** (365 / days) - 1) * 100 if total > 0 else -100.0


def evaluate_promotion(result: BacktestResult, policy: PromotionPolicy | None = None) -> PromotionDecision:
    policy = policy or PromotionPolicy()
    failures: list[str] = []
    if result.avg_trade_pnl_usd < policy.min_net_expectancy_usd:
        failures.append("avg_trade_pnl_below_min")
    if result.oos_sharpe < policy.min_oos_sharpe:
        failures.append("oos_sharpe_below_min")
    if result.max_drawdown_pct > policy.max_drawdown_pct * 100:
        failures.append("max_drawdown_above_limit")
    if result.total_trades < policy.min_trade_count:
        failures.append("trade_count_below_min")
    if result.perturbation_sharpe_mean < policy.min_perturbation_sharpe:
        failures.append("perturbation_sharpe_below_min")

    return PromotionDecision(
        spec_id=result.spec_id,
        backtest_run_id=result.run_id,
        policy=policy,
        passed=not failures,
        failures=failures,
        decided_at=utc_now(),
        approved_by="auto" if not failures else None,
    )
