from __future__ import annotations

import math

import pandas as pd


def compute_features(bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return bars.copy()

    df = bars.copy().sort_values("ts_open").reset_index(drop=True)
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume_quote = df["volume_quote"].astype(float)

    df["ret_1"] = close.pct_change()
    df["ret_4"] = close.pct_change(4)
    df["vol_20"] = df["ret_1"].rolling(20).std().fillna(0.0) * math.sqrt(20)
    df["vol_ratio"] = volume_quote / volume_quote.rolling(20).mean()
    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean().fillna(0.0)
    delta = close.diff().fillna(0.0)
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, pd.NA)
    rs = gain / loss
    df["rsi_14"] = (100 - (100 / (1 + rs))).fillna(50.0)
    range_high = close.rolling(20).max()
    range_low = close.rolling(20).min()
    width = (range_high - range_low).replace(0, pd.NA)
    df["pct_rank_20"] = ((close - range_low) / width).fillna(0.5)
    trend_fast = close.rolling(10).mean()
    trend_slow = close.rolling(30).mean()
    df["trend_signal"] = (trend_fast > trend_slow).astype(int) - (trend_fast < trend_slow).astype(int)
    df["oi_change_pct"] = df.get("open_interest", pd.Series([0.0] * len(df))).astype(float).pct_change().fillna(0.0)
    buy_vol = df.get("taker_buy_volume", pd.Series([0.0] * len(df))).astype(float)
    sell_vol = df.get("taker_sell_volume", pd.Series([0.0] * len(df))).astype(float)
    denom = (buy_vol + sell_vol).replace(0, pd.NA)
    df["buy_sell_ratio"] = ((buy_vol - sell_vol) / denom).fillna(0.0)
    liquidation = df.get("liquidation_volume", pd.Series([0.0] * len(df))).astype(float)
    base_liq = liquidation.rolling(20).mean().replace(0, pd.NA)
    df["liquidation_intensity"] = (liquidation / base_liq).fillna(0.0)
    df["spread_bps"] = df.get("spread_bps", pd.Series([0.0] * len(df))).astype(float)
    df["orderbook_imbalance"] = df.get("orderbook_imbalance", pd.Series([0.0] * len(df))).astype(float)
    btc_close = df.get("btc_close", close).astype(float)
    df["btc_ret_1"] = btc_close.pct_change().fillna(0.0)
    rel = (close / btc_close.replace(0, pd.NA)).astype(float)
    df["rel_strength_20"] = rel.pct_change(20).fillna(0.0)
    btc_var = df["btc_ret_1"].rolling(20).var().replace(0, pd.NA)
    cov = df["ret_1"].rolling(20).cov(df["btc_ret_1"])
    df["beta_btc_20"] = (cov / btc_var).fillna(0.0)
    df["exchange_netflow"] = df.get("exchange_netflow", pd.Series([0.0] * len(df))).astype(float)
    df["whale_txn_count"] = df.get("whale_txn_count", pd.Series([0.0] * len(df))).astype(float)
    df["miner_outflow"] = df.get("miner_outflow", pd.Series([0.0] * len(df))).astype(float)
    netflow_std = df["exchange_netflow"].rolling(30).std().replace(0, pd.NA)
    netflow_mean = df["exchange_netflow"].rolling(30).mean()
    df["onchain_pressure"] = ((df["exchange_netflow"] - netflow_mean) / netflow_std).fillna(0.0)
    
    # Add _prev values for rule evaluator crossover/crossunder operators
    feature_cols = [
        "ret_1",
        "ret_4",
        "vol_20",
        "vol_ratio",
        "atr_14",
        "rsi_14",
        "pct_rank_20",
        "trend_signal",
        "oi_change_pct",
        "buy_sell_ratio",
        "liquidation_intensity",
        "spread_bps",
        "orderbook_imbalance",
        "btc_ret_1",
        "rel_strength_20",
        "beta_btc_20",
        "exchange_netflow",
        "whale_txn_count",
        "miner_outflow",
        "onchain_pressure",
        "close",
        "volume_quote",
    ]
    for col in feature_cols:
        df[f"{col}_prev"] = df[col].shift(1)

    return df.fillna(0.0)


def add_funding_features(features: pd.DataFrame, funding: pd.DataFrame | None) -> pd.DataFrame:
    if funding is None or funding.empty or features.empty:
        out = features.copy()
        out["funding_rate"] = out.get("funding_rate", 0.0)
        out["funding_zscore"] = out.get("funding_zscore", 0.0)
        return out

    bars = features.copy()
    bars["ts_open"] = pd.to_datetime(bars["ts_open"], utc=True)
    rates = funding.copy()
    rates["ts"] = pd.to_datetime(rates["ts"], utc=True)
    rates = rates.sort_values("ts")
    merged = pd.merge_asof(bars.sort_values("ts_open"), rates, left_on="ts_open", right_on="ts", direction="backward")
    merged["funding_rate"] = merged["rate"].fillna(0.0).astype(float)
    rolling_mean = merged["funding_rate"].rolling(30).mean()
    rolling_std = merged["funding_rate"].rolling(30).std().replace(0, pd.NA)
    merged["funding_zscore"] = ((merged["funding_rate"] - rolling_mean) / rolling_std).fillna(0.0)
    return merged.drop(columns=[col for col in ("ts", "rate") if col in merged.columns])
