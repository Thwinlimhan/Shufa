import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet, apiPost } from "../api/client";

type StrategyUniverseItem = {
  symbol: string;
  venue: string;
};

type StrategyRow = {
  spec_id: string;
  name: string;
  version: number;
  status: string;
  created_at: string;
  paper_enabled_count: number;
  targets: Array<{
    target_id: string;
    spec_id: string;
    symbol: string;
    venue: string;
    status: string;
    paper_enabled: number;
    notes?: string | null;
    last_backtest_run_id?: string | null;
  }>;
  spec: {
    hypothesis: string;
    universe: StrategyUniverseItem[];
  };
};

type BacktestRow = {
  run_id: string;
  spec_id: string;
  ran_at: string;
  config: {
    start_date: string;
    end_date: string;
    instrument?: {
      symbol: string;
      venue: string;
      mode: string;
      quote: string;
    };
  };
  result: {
    sharpe: number;
    total_trades: number;
    total_return_pct: number;
    max_drawdown_pct: number;
    diagnostics?: {
      bars_seen?: number;
      signal_counts?: Record<string, number>;
      feature_ranges?: Record<string, { min: number; max: number }>;
    };
    equity_curve: Array<[string, number] | { ts: string; equity: number }>;
    trades: Array<{
      trade_id: string;
      direction: string;
      entry_ts: string;
      exit_ts: string;
      pnl_usd: number;
      exit_reason: string;
    }>;
  };
};

type CompareRow = {
  symbol: string;
  venue: string;
  sharpe: number | null;
  total_return_pct: number | null;
  total_trades: number;
  passed: boolean;
};

type SweepRow = {
  label: string;
  sharpe: number;
  return_pct: number;
  trades: number;
  drawdown_pct: number;
};

type TargetSnapshot = {
  spec_id: string;
  name: string;
  symbol: string;
  venue: string;
  status: string;
  paper_enabled: number;
  notes?: string | null;
  run?: BacktestRow;
};

const LOOKBACK_OPTIONS = [60, 120, 180, 365];
const BUILDER_FEATURES = [
  "ret_4",
  "vol_ratio",
  "trend_signal",
  "funding_zscore",
  "rsi_14",
  "pct_rank_20",
  "oi_change_pct",
  "buy_sell_ratio",
  "liquidation_intensity",
  "btc_ret_1",
  "rel_strength_20",
  "beta_btc_20",
  "onchain_pressure"
];
const STATUS_PRIORITY: Record<string, number> = {
  rejected: 0,
  proposed: 1,
  shortlist: 2,
  candidate: 3,
  promoted: 4
};

export function StrategyRegistryPage() {
  const [selectedSpecId, setSelectedSpecId] = useState<string>("");
  const [selectedSymbol, setSelectedSymbol] = useState<string>("BTC");
  const [selectedVenue, setSelectedVenue] = useState<string>("binance");
  const [lookbackDays, setLookbackDays] = useState<number>(180);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [compareRows, setCompareRows] = useState<CompareRow[]>([]);
  const [sweepRows, setSweepRows] = useState<SweepRow[]>([]);
  const [builderName, setBuilderName] = useState<string>("Custom Signal");
  const [builderHypothesis, setBuilderHypothesis] = useState<string>("User-defined strategy idea.");
  const [builderFeature, setBuilderFeature] = useState<string>("ret_4");
  const [builderOperator, setBuilderOperator] = useState<string>("gt");
  const [builderThreshold, setBuilderThreshold] = useState<number>(0.01);

  const strategies = useQuery({
    queryKey: ["strategies"],
    queryFn: () => apiGet<StrategyRow[]>("/strategies"),
    refetchInterval: 30_000,
    refetchIntervalInBackground: true
  });
  const backtests = useQuery({
    queryKey: ["backtests"],
    queryFn: () => apiGet<BacktestRow[]>("/backtests"),
    refetchInterval: 30_000,
    refetchIntervalInBackground: true
  });

  useEffect(() => {
    if (!selectedSpecId && strategies.data?.length) {
      setSelectedSpecId(strategies.data[0].spec_id);
    }
  }, [selectedSpecId, strategies.data]);

  const selectedStrategy = strategies.data?.find((row) => row.spec_id === selectedSpecId) ?? strategies.data?.[0];
  const availableSymbols = Array.from(new Set((selectedStrategy?.spec.universe ?? []).map((item) => item.symbol)));
  const availableVenues = Array.from(
    new Set(
      (selectedStrategy?.spec.universe ?? [])
        .filter((item) => item.symbol === selectedSymbol)
        .map((item) => item.venue)
    )
  );

  useEffect(() => {
    if (!availableSymbols.includes(selectedSymbol)) {
      setSelectedSymbol(availableSymbols[0] ?? "BTC");
    }
  }, [availableSymbols, selectedSymbol]);

  useEffect(() => {
    if (!availableVenues.includes(selectedVenue)) {
      setSelectedVenue(availableVenues[0] ?? "binance");
    }
  }, [availableVenues, selectedVenue]);

  const latestBySpec = new Map<string, BacktestRow>();
  for (const run of backtests.data ?? []) {
    if (!latestBySpec.has(run.spec_id)) {
      latestBySpec.set(run.spec_id, run);
    }
  }

  const selectedRun =
    (backtests.data ?? []).find(
      (run) =>
        run.spec_id === selectedStrategy?.spec_id &&
        run.config.instrument?.symbol === selectedSymbol &&
        run.config.instrument?.venue === selectedVenue
    ) ??
    (selectedStrategy ? latestBySpec.get(selectedStrategy.spec_id) : undefined);
  const selectedTarget =
    selectedStrategy?.targets?.find((target) => target.symbol === selectedSymbol && target.venue === selectedVenue) ?? null;
  const diagnostics = selectedRun?.result.diagnostics;
  const targetSnapshots = useMemo<TargetSnapshot[]>(
    () =>
      (strategies.data ?? [])
        .flatMap((strategy) =>
          (strategy.targets ?? []).map((target) => ({
            spec_id: strategy.spec_id,
            name: strategy.name,
            symbol: target.symbol,
            venue: target.venue,
            status: target.status,
            paper_enabled: target.paper_enabled,
            notes: target.notes,
            run: (backtests.data ?? []).find((item) => item.run_id === target.last_backtest_run_id)
          }))
        )
        .filter((item) => item.run)
        .sort((left, right) => {
          const leftScore = STATUS_PRIORITY[left.status] ?? 0;
          const rightScore = STATUS_PRIORITY[right.status] ?? 0;
          if (leftScore !== rightScore) return rightScore - leftScore;
          if ((right.run?.result.sharpe ?? 0) !== (left.run?.result.sharpe ?? 0)) {
            return (right.run?.result.sharpe ?? 0) - (left.run?.result.sharpe ?? 0);
          }
          if ((right.run?.result.total_return_pct ?? 0) !== (left.run?.result.total_return_pct ?? 0)) {
            return (right.run?.result.total_return_pct ?? 0) - (left.run?.result.total_return_pct ?? 0);
          }
          return (right.run?.result.total_trades ?? 0) - (left.run?.result.total_trades ?? 0);
        }),
    [backtests.data, strategies.data]
  );
  const bestTarget = targetSnapshots[0];
  const equityData = useMemo(
    () =>
      (selectedRun?.result.equity_curve ?? []).map((point) => {
        const ts = Array.isArray(point) ? point[0] : point.ts;
        const value = Array.isArray(point) ? point[1] : point.equity;
        return {
          ts,
          tsLabel: new Date(ts).toLocaleDateString(),
          equity: Number(Number(value).toFixed(2))
        };
      }),
    [selectedRun]
  );
  const comparisonChartData = useMemo(
    () =>
      targetSnapshots
        .slice(0, 5)
        .map((item) => ({
          label: `${item.symbol}/${item.venue}`,
          sharpe: Number(item.run?.result.sharpe?.toFixed(2) ?? 0),
          returnPct: Number(item.run?.result.total_return_pct?.toFixed(2) ?? 0)
        })),
    [targetSnapshots]
  );

  async function runBacktest(specId: string, symbol: string, venue: string) {
    setSelectedSpecId(specId);
    setSelectedSymbol(symbol);
    setSelectedVenue(venue);
    setStatusMessage(`Running ${symbol} on ${venue}...`);
    try {
      const response = await apiPost<{ target?: { status?: string } }>("/backtests", {
        spec_id: specId,
        symbol,
        venue,
        lookback_days: lookbackDays
      });
      setStatusMessage(
        response.target?.status ? `Backtest completed. Target is now ${response.target.status}.` : "Backtest completed."
      );
      await Promise.all([backtests.refetch(), strategies.refetch()]);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Backtest failed.");
    }
  }

  async function runCompare() {
    if (!selectedStrategy) return;
    setStatusMessage("Running symbol and venue comparison...");
    try {
      const response = await apiPost<{ comparisons: CompareRow[] }>("/backtests/compare", {
        spec_id: selectedStrategy.spec_id,
        lookback_days: lookbackDays
      });
      setCompareRows(response.comparisons);
      setStatusMessage("Comparison completed.");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Comparison failed.");
    }
  }

  async function runSweep() {
    if (!selectedStrategy) return;
    setStatusMessage("Running parameter sweep...");
    try {
      const response = await apiPost<{ results: SweepRow[] }>("/backtests/sweep", {
        spec_id: selectedStrategy.spec_id,
        symbol: selectedSymbol,
        venue: selectedVenue,
        lookback_days: lookbackDays
      });
      setSweepRows(response.results.slice(0, 6));
      setStatusMessage("Sweep completed.");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Sweep failed.");
    }
  }

  async function setTargetState(status: string | null, paperEnabled: boolean | null) {
    if (!selectedStrategy) return;
    setStatusMessage("Updating target...");
    try {
      await apiPost(`/strategies/${selectedStrategy.spec_id}/targets`, {
        symbol: selectedSymbol,
        venue: selectedVenue,
        status: status ?? selectedTarget?.status ?? "shortlist",
        paper_enabled: paperEnabled ?? Boolean(selectedTarget?.paper_enabled),
        last_backtest_run_id: selectedRun?.run_id
      });
      await strategies.refetch();
      setStatusMessage("Target updated.");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Target update failed.");
    }
  }

  async function createStrategyFromBuilder() {
    const specId = `custom-${builderName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "")}`;
    const payload = {
      spec_id: specId,
      name: builderName,
      version: 1,
      created_at: new Date().toISOString(),
      universe: [{ symbol: selectedSymbol, venue: selectedVenue, mode: "perp", quote: "USDT" }],
      primary_timeframe: "1h",
      feature_inputs: [builderFeature],
      entry_long: [{ feature: builderFeature, operator: builderOperator, threshold: builderThreshold }],
      entry_short: [{ feature: builderFeature, operator: builderOperator === "gt" ? "lt" : "gt", threshold: builderThreshold }],
      sizing: { method: "fixed_notional", fixed_notional_usd: 1000 },
      risk_limits: { max_open_positions: 4 },
      execution: { bar_close_only: true, min_volume_usd: 500000, max_spread_bps: 10 },
      hypothesis: builderHypothesis,
      tags: ["custom", "ui-builder"]
    };
    setStatusMessage("Creating strategy from builder...");
    try {
      await apiPost("/strategies", payload);
      await strategies.refetch();
      setSelectedSpecId(specId);
      setStatusMessage(`Created ${specId}.`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Builder create failed.");
    }
  }

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (!selectedStrategy) return;
      if (event.altKey && event.key.toLowerCase() === "b") {
        void runBacktest(selectedStrategy.spec_id, selectedSymbol, selectedVenue);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedStrategy, selectedSymbol, selectedVenue, lookbackDays]);

  if (strategies.isLoading || backtests.isLoading) {
    return <section className="panel skeleton-block">Loading strategy registry...</section>;
  }
  if (strategies.isError || backtests.isError) {
    return <section className="panel">Failed to load strategy registry.</section>;
  }

  return (
    <section className="stack">
      <div className="panel strategy-hero compact-hero">
        <div>
          <div className="eyebrow dark">Strategy Registry</div>
          <h2 className="hero-title compact">Run, compare, and reject with evidence.</h2>
          <p className="hero-copy">
            Choose symbol, venue, and lookback. Then inspect the latest run, compare markets, and sweep thresholds.
          </p>
        </div>
        <div className="run-controls">
          <div className="control-grid">
            <label className="field">
              <span>Lookback</span>
              <select value={lookbackDays} onChange={(event) => setLookbackDays(Number(event.target.value))}>
                {LOOKBACK_OPTIONS.map((days) => (
                  <option key={days} value={days}>
                    {days} days
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Symbol</span>
              <select value={selectedSymbol} onChange={(event) => setSelectedSymbol(event.target.value)}>
                {availableSymbols.map((symbol) => (
                  <option key={symbol} value={symbol}>
                    {symbol}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Venue</span>
              <select value={selectedVenue} onChange={(event) => setSelectedVenue(event.target.value)}>
                {availableVenues.map((venue) => (
                  <option key={venue} value={venue}>
                    {venue}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="button-row">
            <button disabled={!selectedStrategy} onClick={() => selectedStrategy && runBacktest(selectedStrategy.spec_id, selectedSymbol, selectedVenue)}>
              Run Selected
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={runCompare}>
              Compare Markets
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={runSweep}>
              Sweep Params
            </button>
          </div>
          <div className="button-row">
            <button className="secondary-button" disabled={!selectedStrategy} onClick={() => setTargetState("shortlist", null)}>
              Shortlist
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={() => setTargetState("candidate", null)}>
              Candidate
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={() => setTargetState("promoted", null)}>
              Promote
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={() => setTargetState("rejected", false)}>
              Reject
            </button>
            <button className="secondary-button" disabled={!selectedStrategy} onClick={() => setTargetState(null, !Boolean(selectedTarget?.paper_enabled))}>
              {selectedTarget?.paper_enabled ? "Disable Paper" : "Enable Paper"}
            </button>
          </div>
        </div>
        <div className="status-strip">{statusMessage || "Select a strategy to inspect the latest run."}</div>
      </div>

      {bestTarget ? (
        <div className="panel target-summary-strip">
          <div>
            <div className="eyebrow dark">Best Current Target</div>
            <div className="target-summary-title">
              {bestTarget.name} on {bestTarget.symbol} / {bestTarget.venue}
            </div>
            <p className="muted target-summary-copy">
              {bestTarget.notes || "This target currently has the strongest evidence-adjusted score in the registry."}
            </p>
          </div>
          <div className="target-summary-metrics">
            <span className={`status-pill ${bestTarget.status}`}>{bestTarget.status}</span>
            <span>Sharpe {bestTarget.run?.result.sharpe.toFixed(2)}</span>
            <span>Return {bestTarget.run ? `${bestTarget.run.result.total_return_pct.toFixed(2)}%` : "n/a"}</span>
            <span>Trades {bestTarget.run?.result.total_trades ?? "n/a"}</span>
            <span>Paper {bestTarget.paper_enabled ? "enabled" : "off"}</span>
          </div>
          <div className="button-row">
            <button
              className="secondary-button"
              onClick={() => {
                setSelectedSpecId(bestTarget.spec_id);
                setSelectedSymbol(bestTarget.symbol);
                setSelectedVenue(bestTarget.venue);
                setStatusMessage(`Focused ${bestTarget.name} on ${bestTarget.symbol} / ${bestTarget.venue}.`);
              }}
            >
              Inspect Best
            </button>
            <button onClick={() => runBacktest(bestTarget.spec_id, bestTarget.symbol, bestTarget.venue)}>Run Best Again</button>
          </div>
        </div>
      ) : null}

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Strategy Builder</h2>
            <p>Create a rule-based strategy without editing Python.</p>
          </div>
        </div>
        <div className="control-grid">
          <label className="field">
            <span>Name</span>
            <input value={builderName} onChange={(event) => setBuilderName(event.target.value)} />
          </label>
          <label className="field">
            <span>Feature</span>
            <select value={builderFeature} onChange={(event) => setBuilderFeature(event.target.value)}>
              {BUILDER_FEATURES.map((feature) => (
                <option key={feature} value={feature}>
                  {feature}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Operator</span>
            <select value={builderOperator} onChange={(event) => setBuilderOperator(event.target.value)}>
              <option value="gt">gt</option>
              <option value="lt">lt</option>
            </select>
          </label>
          <label className="field">
            <span>Threshold</span>
            <input type="number" value={builderThreshold} onChange={(event) => setBuilderThreshold(Number(event.target.value))} />
          </label>
        </div>
        <label className="field">
          <span>Hypothesis</span>
          <input value={builderHypothesis} onChange={(event) => setBuilderHypothesis(event.target.value)} />
        </label>
        <div className="button-row">
          <button onClick={createStrategyFromBuilder}>Save Strategy</button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Strategy Table</h2>
            <p>Built-in specs stay proposed until the evidence is good enough to promote them.</p>
          </div>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Version</th>
              <th>Status</th>
              <th>Hypothesis</th>
              <th>Latest Backtest</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {(strategies.data ?? []).map((row) => (
              <tr
                key={row.spec_id}
                className={row.spec_id === selectedSpecId ? "selected-row" : undefined}
                onClick={() => setSelectedSpecId(row.spec_id)}
              >
                <td>{row.name}</td>
                <td>{row.version}</td>
                <td>{row.status}</td>
                <td>{row.spec.hypothesis}</td>
                <td>
                  {latestBySpec.has(row.spec_id)
                    ? `Sharpe ${latestBySpec.get(row.spec_id)!.result.sharpe.toFixed(2)} | Trades ${latestBySpec.get(row.spec_id)!.result.total_trades}`
                    : "No run yet"}
                </td>
                <td>
                  <button
                    onClick={(event) => {
                      event.stopPropagation();
                      runBacktest(row.spec_id, selectedSymbol, selectedVenue);
                    }}
                  >
                    Run Backtest
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="inspector-grid">
        <div className="panel inspector-main">
          <div className="panel-header">
            <div>
              <h2>{selectedStrategy?.name ?? "Selected Run"}</h2>
              <p>{selectedRun ? `Latest run at ${new Date(selectedRun.ran_at).toLocaleString()}` : "Run a backtest to inspect details."}</p>
            </div>
          </div>

          <div className="metrics-grid">
            <div className="metric-card warm">
              <div className="metric-label">Sharpe</div>
              <div className="metric-value">{selectedRun?.result.sharpe?.toFixed(2) ?? "n/a"}</div>
            </div>
            <div className="metric-card warm">
              <div className="metric-label">Return</div>
              <div className="metric-value">{selectedRun ? `${selectedRun.result.total_return_pct.toFixed(2)}%` : "n/a"}</div>
            </div>
            <div className="metric-card warm">
              <div className="metric-label">Trades</div>
              <div className="metric-value">{selectedRun?.result.total_trades ?? "n/a"}</div>
            </div>
            <div className="metric-card warm">
              <div className="metric-label">Max Drawdown</div>
              <div className="metric-value">{selectedRun ? `${selectedRun.result.max_drawdown_pct.toFixed(2)}%` : "n/a"}</div>
            </div>
          </div>

          <div className="run-meta">
            <span>Target Status: {selectedTarget?.status ?? "proposed"}</span>
            <span>Paper: {selectedTarget?.paper_enabled ? "enabled" : "off"}</span>
            <span>Venue: {selectedRun?.config.instrument?.venue ?? "n/a"}</span>
            <span>Symbol: {selectedRun?.config.instrument?.symbol ?? "n/a"}</span>
            <span>
              Window:{" "}
              {selectedRun
                ? `${new Date(selectedRun.config.start_date).toLocaleDateString()} - ${new Date(selectedRun.config.end_date).toLocaleDateString()}`
                : "n/a"}
            </span>
          </div>

          <div className="chart-shell">
            {equityData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={equityData}>
                  <XAxis dataKey="tsLabel" minTickGap={30} />
                  <YAxis domain={["dataMin", "dataMax"]} width={84} />
                  <Tooltip labelFormatter={(value) => String(value)} />
                  <Line type="monotone" dataKey="equity" stroke="#ff8f00" strokeWidth={3} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state">No equity curve yet. Run a backtest first.</div>
            )}
          </div>

          <div className="chart-shell">
            {comparisonChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={comparisonChartData}>
                  <XAxis dataKey="label" />
                  <YAxis yAxisId="left" width={62} />
                  <YAxis yAxisId="right" orientation="right" width={72} />
                  <Tooltip />
                  <Line yAxisId="left" type="monotone" dataKey="sharpe" stroke="#00adb5" strokeWidth={2} dot />
                  <Line yAxisId="right" type="monotone" dataKey="returnPct" stroke="#ff8f00" strokeWidth={2} dot />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state">No comparison data yet.</div>
            )}
          </div>

          <div className="trade-log">
            <div className="section-title">Latest Trades</div>
            <table className="table compact-table">
              <thead>
                <tr>
                  <th>Direction</th>
                  <th>Entry</th>
                  <th>Exit</th>
                  <th>PnL USD</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {(selectedRun?.result.trades ?? []).slice(0, 8).map((trade) => (
                  <tr key={trade.trade_id}>
                    <td>{trade.direction}</td>
                    <td>{new Date(trade.entry_ts).toLocaleString()}</td>
                    <td>{new Date(trade.exit_ts).toLocaleString()}</td>
                    <td>{trade.pnl_usd.toFixed(2)}</td>
                    <td>{trade.exit_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel inspector-side">
          <div className="section-title">Target Note</div>
          <p className="muted">
            {selectedTarget?.notes || "Run a target-specific backtest to let the app classify this market pair automatically."}
          </p>

          <div className="section-title">Funding Debug Note</div>
          <p className="muted">
            Funding reversion now runs with funding features merged into the bar frame. Use the compare and sweep tools below to see whether the idea fails everywhere or only on certain venue-symbol pairs.
          </p>

          <div className="section-title">Signal Diagnostics</div>
          <div className="diagnostics-list">
            <div>
              <strong>Bars Seen</strong>
              <span>{diagnostics?.bars_seen ?? "n/a"}</span>
            </div>
            <div>
              <strong>Long Signals</strong>
              <span>{diagnostics?.signal_counts?.long ?? 0}</span>
            </div>
            <div>
              <strong>Short Signals</strong>
              <span>{diagnostics?.signal_counts?.short ?? 0}</span>
            </div>
            <div>
              <strong>Flat Bars</strong>
              <span>{diagnostics?.signal_counts?.flat ?? 0}</span>
            </div>
          </div>

          <div className="section-title">Feature Ranges</div>
          <div className="range-list">
            {Object.entries(diagnostics?.feature_ranges ?? {}).map(([feature, range]) => (
              <div key={feature}>
                <strong>{feature}</strong>
                <span>
                  {range.min.toFixed(4)} to {range.max.toFixed(4)}
                </span>
              </div>
            ))}
          </div>

          <div className="section-title">Market Compare</div>
          <div className="range-list">
            {compareRows.map((row) => (
              <div key={`${row.symbol}-${row.venue}`}>
                <strong>
                  {row.symbol} / {row.venue}
                </strong>
                <span>{row.sharpe === null ? "no data" : `Sharpe ${row.sharpe.toFixed(2)} | Trades ${row.total_trades}`}</span>
              </div>
            ))}
          </div>

          <div className="section-title">Top Sweep Results</div>
          <div className="range-list">
            {sweepRows.map((row) => (
              <div key={row.label}>
                <strong>{row.label}</strong>
                <span>Sharpe {row.sharpe.toFixed(2)} | Trades {row.trades}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
