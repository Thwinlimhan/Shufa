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
    
    # Add _prev values for rule evaluator crossover/crossunder operators
    feature_cols = ["ret_1", "ret_4", "vol_20", "vol_ratio", "atr_14", "rsi_14", "pct_rank_20", "trend_signal", "close", "volume_quote"]
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
