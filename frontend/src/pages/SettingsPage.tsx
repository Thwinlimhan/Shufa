import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiGet, apiPost } from "../api/client";

type ReadinessResponse = {
  generated_at: string;
  summary: {
    data_ready: boolean;
    paper_ready: boolean;
    live_ready: boolean;
    blockers: string[];
  };
  counts: {
    datasets: number;
    healthy_datasets: number;
    fresh_datasets: number;
    audit_events: number;
    paper_cycle_events: number;
    reconciliation_runs: number;
    promoted_targets: number;
    active_paper_targets: number;
    open_positions: number;
  };
  risk: {
    paper_trading_enabled: boolean;
    live_trading_enabled: boolean;
    live_approval_mode: boolean;
    paper_max_open_positions: number;
    paper_max_gross_exposure_usd: number;
    paper_daily_loss_limit_usd: number;
    live_secrets: {
      all_present: boolean;
      venues: Record<string, boolean>;
    };
  };
  best_target?: {
    name: string;
    symbol: string;
    venue: string;
    status: string;
    result: {
      sharpe: number;
      total_return_pct: number;
      total_trades: number;
    };
  } | null;
  recent_health_issues: string[];
};

type AuditRow = {
  event_id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  created_at: string;
};

type PaperEventRow = {
  event_id: string;
  spec_id: string;
  symbol: string;
  venue: string;
  timeframe: string;
  event_type: string;
  reason: string;
  created_at: string;
};

type VaultStatus = {
  path: string;
  exists: boolean;
  unlocked: boolean;
  configured_keys: string[];
  required_keys: string[];
};

type WorkerHealth = {
  healthy: boolean;
  workers: Array<{ worker_id: string; healthy: boolean; last_seen: string; status: string }>;
};

function statusText(value: boolean) {
  return value ? "Ready" : "Blocked";
}

export function SettingsPage() {
  const [vaultPassphrase, setVaultPassphrase] = useState("");
  const [vaultName, setVaultName] = useState("binance_api_key");
  const [vaultValue, setVaultValue] = useState("");
  const [vaultMessage, setVaultMessage] = useState("");
  const readiness = useQuery({
    queryKey: ["ops-readiness"],
    queryFn: () => apiGet<ReadinessResponse>("/ops/readiness"),
    refetchInterval: 20_000,
    refetchIntervalInBackground: true
  });
  const audit = useQuery({
    queryKey: ["ops-audit"],
    queryFn: () => apiGet<AuditRow[]>("/ops/audit?limit=20"),
    refetchInterval: 20_000,
    refetchIntervalInBackground: true
  });
  const paperEvents = useQuery({
    queryKey: ["ops-paper-events"],
    queryFn: () => apiGet<PaperEventRow[]>("/ops/paper-events?limit=20"),
    refetchInterval: 20_000,
    refetchIntervalInBackground: true
  });
  const vault = useQuery({
    queryKey: ["vault-status"],
    queryFn: () => apiGet<VaultStatus>("/vault/status"),
    retry: false
  });
  const workerHealth = useQuery({
    queryKey: ["ops-worker-health"],
    queryFn: () => apiGet<WorkerHealth>("/ops/worker-health"),
    refetchInterval: 15_000,
    refetchIntervalInBackground: true
  });
  if (readiness.isLoading || audit.isLoading || paperEvents.isLoading) {
    return <section className="panel skeleton-block">Loading operations snapshot...</section>;
  }
  if (readiness.isError || audit.isError || paperEvents.isError) {
    return <section className="panel">Failed to load operations snapshot.</section>;
  }

  const data = readiness.data;

  async function saveVaultSecret() {
    setVaultMessage("Saving vault secret...");
    try {
      const response = await apiPost<VaultStatus>("/vault/secrets", {
        name: vaultName,
        value: vaultValue,
        passphrase: vaultPassphrase
      });
      await vault.refetch();
      setVaultValue("");
      setVaultMessage(`Vault updated. ${response.configured_keys.length} keys configured.`);
    } catch (error) {
      setVaultMessage(error instanceof Error ? error.message : "Vault update failed.");
    }
  }

  return (
    <section className="stack">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Operations</h2>
            <p>Readiness, guardrails, and audit surfaces for production hardening.</p>
          </div>
          <div className="muted">
            {data ? `Snapshot ${new Date(data.generated_at).toLocaleString()}` : "Loading readiness snapshot..."}
          </div>
        </div>

        <div className="settings-grid">
          <div className="setting-card">
            <div className="metric-label">Data Readiness</div>
            <div className="metric-value">{statusText(Boolean(data?.summary.data_ready))}</div>
          </div>
          <div className="setting-card">
            <div className="metric-label">Paper Readiness</div>
            <div className="metric-value">{statusText(Boolean(data?.summary.paper_ready))}</div>
          </div>
          <div className="setting-card">
            <div className="metric-label">Live Readiness</div>
            <div className="metric-value">{statusText(Boolean(data?.summary.live_ready))}</div>
          </div>
          <div className="setting-card">
            <div className="metric-label">Audit Events</div>
            <div className="metric-value">{data?.counts.audit_events ?? 0}</div>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Blockers</h2>
            <p>The system should stay conservative until these are cleared.</p>
          </div>
        </div>
        <div className="range-list">
          {(data?.summary.blockers ?? []).length > 0 ? (
            (data?.summary.blockers ?? []).map((blocker) => (
              <div key={blocker}>
                <strong>{blocker}</strong>
                <span>Needs operator attention</span>
              </div>
            ))
          ) : (
            <div>
              <strong>No blockers</strong>
              <span>The current snapshot passed all active checks.</span>
            </div>
          )}
        </div>
      </div>

      <div className="inspector-grid">
        <div className="panel inspector-main">
          <div className="panel-header">
            <div>
              <h2>Readiness Counters</h2>
              <p>Coverage across data, strategy promotion, and paper history.</p>
            </div>
          </div>
          <div className="metrics-grid">
            <div className="metric-card warm">
              <div className="metric-label">Datasets</div>
              <div className="metric-value">{data?.counts.datasets ?? 0}</div>
            </div>
            <div className="metric-card warm">
              <div className="metric-label">Healthy</div>
              <div className="metric-value">{data?.counts.healthy_datasets ?? 0}</div>
            </div>
            <div className="metric-card warm">
            <div className="metric-label">Paper Events</div>
            <div className="metric-value">{data?.counts.paper_cycle_events ?? 0}</div>
          </div>
          <div className="metric-card warm">
            <div className="metric-label">Recon Runs</div>
            <div className="metric-value">{data?.counts.reconciliation_runs ?? 0}</div>
          </div>
          </div>

          <div className="section-title">Best Current Target</div>
          <div className="range-list">
            {data?.best_target ? (
              <div>
                <strong>
                  {data.best_target.name} on {data.best_target.symbol} / {data.best_target.venue}
                </strong>
                <span>
                  {data.best_target.status} | Sharpe {data.best_target.result.sharpe.toFixed(2)} | Trades{" "}
                  {data.best_target.result.total_trades}
                </span>
              </div>
            ) : (
              <div>
                <strong>No best target yet</strong>
                <span>Run more backtests before promoting anything.</span>
              </div>
            )}
          </div>

          <div className="section-title">Recent Audit</div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Entity</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {(audit.data ?? []).map((row) => (
                <tr key={row.event_id}>
                  <td>{row.event_type}</td>
                  <td>
                    {row.entity_type} / {row.entity_id}
                  </td>
                  <td>{new Date(row.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel inspector-side">
          <div className="section-title">Risk Controls</div>
          <div className="range-list">
            <div>
              <strong>Paper Trading</strong>
              <span>{data?.risk.paper_trading_enabled ? "enabled" : "disabled"}</span>
            </div>
            <div>
              <strong>Live Trading</strong>
              <span>{data?.risk.live_trading_enabled ? "enabled" : "forced off"}</span>
            </div>
            <div>
              <strong>Approval Mode</strong>
              <span>{data?.risk.live_approval_mode ? "manual" : "direct"}</span>
            </div>
            <div>
              <strong>Max Open Positions</strong>
              <span>{data?.risk.paper_max_open_positions ?? 0}</span>
            </div>
            <div>
              <strong>Daily Loss Limit</strong>
              <span>${Number(data?.risk.paper_daily_loss_limit_usd ?? 0).toFixed(0)}</span>
            </div>
            <div>
              <strong>Gross Exposure Cap</strong>
              <span>${Number(data?.risk.paper_max_gross_exposure_usd ?? 0).toFixed(0)}</span>
            </div>
            <div>
              <strong>Live Secrets</strong>
              <span>{data?.risk.live_secrets?.all_present ? "ready" : "missing"}</span>
            </div>
            <div>
              <strong>Worker Health</strong>
              <span>{workerHealth.data?.healthy ? "healthy" : "degraded"}</span>
            </div>
          </div>

          <div className="section-title">Health Issues</div>
          <div className="range-list">
            {(data?.recent_health_issues ?? []).slice(0, 8).map((issue) => (
              <div key={issue}>
                <strong>{issue}</strong>
                <span>Investigate before live enablement</span>
              </div>
            ))}
            {(data?.recent_health_issues ?? []).length === 0 ? (
              <div>
                <strong>No current health issues</strong>
                <span>The last health pass came back clean.</span>
              </div>
            ) : null}
          </div>

          <div className="section-title">Paper Cycle Feed</div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Market</th>
                <th>Event</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {(paperEvents.data ?? []).map((row) => (
                <tr key={row.event_id}>
                  <td>
                    {row.symbol} / {row.venue}
                  </td>
                  <td>
                    {row.event_type} / {row.reason}
                  </td>
                  <td>{new Date(row.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="section-title">Vault</div>
          <div className="range-list">
            <div>
              <strong>Status</strong>
              <span>{vault.data ? (vault.data.unlocked ? "unlocked" : "locked") : "admin only"}</span>
            </div>
            <div>
              <strong>Configured</strong>
              <span>{vault.data?.configured_keys.join(", ") || "none"}</span>
            </div>
          </div>
          <div className="field">
            <span>Vault Passphrase</span>
            <input type="password" value={vaultPassphrase} onChange={(event) => setVaultPassphrase(event.target.value)} />
          </div>
          <div className="field">
            <span>Secret Name</span>
            <select value={vaultName} onChange={(event) => setVaultName(event.target.value)}>
              <option value="binance_api_key">binance_api_key</option>
              <option value="binance_api_secret">binance_api_secret</option>
              <option value="hyperliquid_private_key">hyperliquid_private_key</option>
              <option value="hyperliquid_account_address">hyperliquid_account_address</option>
            </select>
          </div>
          <div className="field">
            <span>Secret Value</span>
            <input value={vaultValue} onChange={(event) => setVaultValue(event.target.value)} />
          </div>
          <div className="button-row">
            <button className="secondary-button" onClick={saveVaultSecret}>
              Save To Vault
            </button>
          </div>
          <div className="muted">{vaultMessage}</div>
        </div>
      </div>
    </section>
  );
}
