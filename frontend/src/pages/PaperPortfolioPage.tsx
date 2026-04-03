import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { apiGet, apiPost } from "../api/client";
import { MetricCard } from "../components/MetricCard";

type PortfolioResponse = {
  positions: Array<Record<string, string | number | null>>;
  orders: Array<Record<string, string | number | null>>;
  active_targets: Array<Record<string, string | number | null>>;
  target_activity: Array<Record<string, string | number | null>>;
  total_unrealized_pnl_usd: number;
};

export function PaperPortfolioPage() {
  const query = useQuery({
    queryKey: ["paper-portfolio"],
    queryFn: () => apiGet<PortfolioResponse>("/paper/portfolio"),
    refetchInterval: 10_000,
    refetchIntervalInBackground: true
  });
  async function runPaperCycle() {
    await apiPost("/paper/run-once");
    await query.refetch();
  }

  async function runKillSwitch() {
    await apiPost("/paper/kill");
    await query.refetch();
  }

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.altKey && event.key.toLowerCase() === "r") {
        void runPaperCycle();
      }
      if (event.altKey && event.key.toLowerCase() === "k") {
        void runKillSwitch();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (query.isLoading) {
    return <section className="panel skeleton-block">Loading paper portfolio...</section>;
  }
  if (query.isError) {
    return <section className="panel">Failed to load paper portfolio.</section>;
  }

  const data = query.data;

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Paper Portfolio</h2>
          <p>Open positions, recent fills, and emergency controls.</p>
        </div>
        <div className="button-row">
          <button onClick={() => void runPaperCycle()}>Run Paper Cycle</button>
          <button onClick={() => void runKillSwitch()}>Kill Switch</button>
        </div>
      </div>

      <div className="metrics-grid">
        <MetricCard label="Open Positions" value={data?.positions.length ?? 0} />
        <MetricCard label="Recent Orders" value={data?.orders.length ?? 0} />
        <MetricCard label="Active Targets" value={data?.active_targets.length ?? 0} />
        <MetricCard label="Unrealized PnL" value={`$${(data?.total_unrealized_pnl_usd ?? 0).toFixed(2)}`} />
      </div>

      <h3>Active Paper Targets</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Spec</th>
            <th>Symbol</th>
            <th>Venue</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {(data?.active_targets ?? []).map((row) => (
            <tr key={`${row.spec_id}-${row.symbol}-${row.venue}`}>
              <td>{row.name}</td>
              <td>{row.spec_id}</td>
              <td>{row.symbol}</td>
              <td>{row.venue}</td>
              <td>{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Target Activity</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Market</th>
            <th>Open Positions</th>
            <th>Recent Orders</th>
            <th>Last Activity</th>
            <th>Last Order</th>
            <th>Realized PnL</th>
          </tr>
        </thead>
        <tbody>
          {(data?.target_activity ?? []).map((row) => (
            <tr key={`${row.spec_id}-${row.symbol}-${row.venue}`}>
              <td>{row.name}</td>
              <td>
                {row.symbol} / {row.venue}
              </td>
              <td>{row.open_positions}</td>
              <td>{row.recent_orders}</td>
              <td>{row.last_event_at ? new Date(String(row.last_event_at)).toLocaleString() : "No activity yet"}</td>
              <td>
                {row.last_order_action
                  ? `${row.last_order_action} ${row.last_direction ?? ""} (${row.last_order_status ?? "n/a"})`
                  : "No orders yet"}
              </td>
              <td>${Number(row.realized_pnl_usd ?? 0).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Recent Orders</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Spec</th>
            <th>Market</th>
            <th>Action</th>
            <th>Status</th>
            <th>Triggered</th>
            <th>Fill</th>
            <th>Size USD</th>
          </tr>
        </thead>
        <tbody>
          {(data?.orders ?? []).map((row) => (
            <tr key={String(row.order_id)}>
              <td>{row.spec_id}</td>
              <td>
                {row.symbol} / {row.venue}
              </td>
              <td>
                {row.action} {row.direction}
              </td>
              <td>{row.status}</td>
              <td>{row.triggered_at ? new Date(String(row.triggered_at)).toLocaleString() : "n/a"}</td>
              <td>{row.fill_price ?? "n/a"}</td>
              <td>{row.size_usd}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Open Positions</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Spec</th>
            <th>Market</th>
            <th>Direction</th>
            <th>Opened</th>
            <th>Entry</th>
            <th>Mark</th>
            <th>Unrealized</th>
            <th>Size USD</th>
          </tr>
        </thead>
        <tbody>
          {(data?.positions ?? []).map((row) => (
            <tr key={String(row.position_id)}>
              <td>{row.spec_id}</td>
              <td>
                {row.symbol} / {row.venue}
              </td>
              <td>{row.direction}</td>
              <td>{row.opened_at ? new Date(String(row.opened_at)).toLocaleString() : "n/a"}</td>
              <td>{row.entry_price}</td>
              <td>{row.mark_price ?? "n/a"}</td>
              <td>${Number(row.unrealized_pnl_usd ?? 0).toFixed(2)}</td>
              <td>{row.size_usd}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
