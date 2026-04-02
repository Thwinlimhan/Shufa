import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "../api/client";

type HealthRow = {
  instrument_key: string;
  timeframe: string;
  quality: string;
  last_bar_ts: string | null;
  gap_count: number;
  duplicate_count: number;
  coverage_days: number;
};

export function DataHealthPage() {
  const query = useQuery({
    queryKey: ["data-health"],
    queryFn: () => apiGet<HealthRow[]>("/data/health")
  });

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Data Health</h2>
          <p>Quality checks for each instrument and timeframe.</p>
        </div>
        <div className="button-row">
          <button onClick={() => apiPost("/data/ingest", { lookback_days: 30 }).then(() => query.refetch())}>
            Ingest 30d
          </button>
          <button onClick={() => apiPost("/data/refresh-health").then(() => query.refetch())}>Refresh</button>
        </div>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Instrument</th>
            <th>Timeframe</th>
            <th>Quality</th>
            <th>Last Bar</th>
            <th>Gaps</th>
            <th>Duplicates</th>
            <th>Coverage (days)</th>
          </tr>
        </thead>
        <tbody>
          {(query.data ?? []).map((row) => (
            <tr key={`${row.instrument_key}-${row.timeframe}`}>
              <td>{row.instrument_key}</td>
              <td>{row.timeframe}</td>
              <td>{row.quality}</td>
              <td>{row.last_bar_ts ?? "n/a"}</td>
              <td>{row.gap_count}</td>
              <td>{row.duplicate_count}</td>
              <td>{row.coverage_days}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
