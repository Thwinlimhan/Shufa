import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "../api/client";

type StrategyRow = {
  spec_id: string;
  name: string;
  targets: Array<{
    symbol: string;
    venue: string;
    status: string;
    paper_enabled: number;
  }>;
};

type TicketRow = {
  ticket_id: string;
  spec_id: string;
  symbol: string;
  venue: string;
  direction: string;
  action: string;
  size_usd: number;
  status: string;
  approval_mode: string;
  rationale?: string | null;
  preview: {
    estimated_fee_usd: number;
    estimated_slippage_bps: number;
    notional_limit_ok: boolean;
    approval_required: boolean;
  };
  created_at: string;
  approved_at?: string | null;
  submitted_at?: string | null;
};

type ReconciliationRow = {
  reconciliation_id: string;
  venue: string;
  status: string;
  created_at: string;
  summary: {
    notes?: string;
  };
};

type SecretsResponse = {
  all_present: boolean;
  venues: Record<string, boolean>;
};

type JobRow = {
  job_id: string;
  job_type: string;
  status: string;
  created_at: string;
  payload: {
    ticket_id?: string;
    venue?: string;
    symbol?: string;
  };
  result?: Record<string, unknown> | null;
};

type JobMetrics = {
  queued: number;
  claimed: number;
  completed: number;
  failed: number;
};

export function ExecutionPage() {
  const [selectedSpecId, setSelectedSpecId] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("ETH");
  const [selectedVenue, setSelectedVenue] = useState("binance");
  const [direction, setDirection] = useState("long");
  const [sizeUsd, setSizeUsd] = useState(1000);
  const [message, setMessage] = useState("");

  const strategies = useQuery({
    queryKey: ["execution-strategies"],
    queryFn: () => apiGet<StrategyRow[]>("/strategies")
  });
  const tickets = useQuery({
    queryKey: ["execution-tickets"],
    queryFn: () => apiGet<TicketRow[]>("/execution/tickets")
  });
  const reconciliation = useQuery({
    queryKey: ["execution-reconciliation"],
    queryFn: () => apiGet<ReconciliationRow[]>("/execution/reconciliation")
  });
  const secrets = useQuery({
    queryKey: ["execution-secrets"],
    queryFn: () => apiGet<SecretsResponse>("/execution/secrets")
  });
  const jobs = useQuery({
    queryKey: ["execution-jobs"],
    queryFn: () => apiGet<JobRow[]>("/execution/jobs")
  });
  const jobMetrics = useQuery({
    queryKey: ["execution-job-metrics"],
    queryFn: () => apiGet<JobMetrics>("/execution/jobs/metrics")
  });

  useEffect(() => {
    if (!selectedSpecId && strategies.data?.length) {
      setSelectedSpecId(strategies.data[0].spec_id);
    }
  }, [selectedSpecId, strategies.data]);

  const selectedStrategy = strategies.data?.find((item) => item.spec_id === selectedSpecId) ?? strategies.data?.[0];
  const targetOptions = selectedStrategy?.targets ?? [];

  useEffect(() => {
    const match = targetOptions.find((item) => item.symbol === selectedSymbol && item.venue === selectedVenue);
    if (!match && targetOptions[0]) {
      setSelectedSymbol(targetOptions[0].symbol);
      setSelectedVenue(targetOptions[0].venue);
    }
  }, [selectedSymbol, selectedVenue, targetOptions]);

  const pendingTickets = useMemo(
    () => (tickets.data ?? []).filter((item) => item.status === "pending_approval"),
    [tickets.data]
  );

  async function createTicket() {
    if (!selectedStrategy) return;
    setMessage("Creating execution ticket...");
    try {
      await apiPost("/execution/tickets", {
        spec_id: selectedStrategy.spec_id,
        symbol: selectedSymbol,
        venue: selectedVenue,
        direction,
        action: "open",
        size_usd: sizeUsd,
        rationale: "Operator requested approval-mode live ticket"
      });
      await tickets.refetch();
      await jobs.refetch();
      await jobMetrics.refetch();
      setMessage("Execution ticket created.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to create ticket.");
    }
  }

  async function approve(ticketId: string) {
    setMessage("Approving ticket...");
    try {
      await apiPost(`/execution/tickets/${ticketId}/approve`, {});
      await Promise.all([tickets.refetch(), reconciliation.refetch(), jobs.refetch(), jobMetrics.refetch()]);
      setMessage("Ticket processed.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Approval failed.");
    }
  }

  async function reject(ticketId: string) {
    setMessage("Rejecting ticket...");
    try {
      await apiPost(`/execution/tickets/${ticketId}/reject`, { reason: "operator_rejected" });
      await tickets.refetch();
      await jobs.refetch();
      await jobMetrics.refetch();
      setMessage("Ticket rejected.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Reject failed.");
    }
  }

  async function reconcileVenue(venue: string) {
    setMessage(`Reconciling ${venue}...`);
    try {
      await apiPost("/execution/reconciliation/run", { venue });
      await reconciliation.refetch();
      setMessage(`Reconciliation completed for ${venue}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Reconciliation failed.");
    }
  }

  async function processQueue() {
    setMessage("Processing next worker job...");
    try {
      await apiPost("/execution/jobs/process", { job_type: "execution_submit" });
      await Promise.all([tickets.refetch(), jobs.refetch(), jobMetrics.refetch()]);
      setMessage("Processed next queued job.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Job processing failed.");
    }
  }

  return (
    <section className="stack">
      <div className="panel strategy-hero compact-hero">
        <div>
          <div className="eyebrow dark">Execution Control</div>
          <h2 className="hero-title compact">Gate live orders through approval and reconciliation.</h2>
          <p className="hero-copy">
            This stays in approval mode until data, paper evidence, secrets, and reconciliation are all strong enough.
          </p>
        </div>
        <div className="run-controls">
          <div className="control-grid">
            <label className="field">
              <span>Strategy</span>
              <select value={selectedSpecId} onChange={(event) => setSelectedSpecId(event.target.value)}>
                {(strategies.data ?? []).map((item) => (
                  <option key={item.spec_id} value={item.spec_id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Target</span>
              <select
                value={`${selectedSymbol}:${selectedVenue}`}
                onChange={(event) => {
                  const [symbol, venue] = event.target.value.split(":");
                  setSelectedSymbol(symbol);
                  setSelectedVenue(venue);
                }}
              >
                {targetOptions.map((item) => (
                  <option key={`${item.symbol}:${item.venue}`} value={`${item.symbol}:${item.venue}`}>
                    {item.symbol} / {item.venue} ({item.status})
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Direction</span>
              <select value={direction} onChange={(event) => setDirection(event.target.value)}>
                <option value="long">long</option>
                <option value="short">short</option>
              </select>
            </label>
          </div>
          <div className="control-grid">
            <label className="field">
              <span>Size USD</span>
              <input
                type="number"
                min={100}
                step={100}
                value={sizeUsd}
                onChange={(event) => setSizeUsd(Number(event.target.value))}
              />
            </label>
          </div>
          <div className="button-row">
            <button onClick={createTicket}>Create Ticket</button>
            <button className="secondary-button" onClick={() => reconcileVenue("binance")}>
              Reconcile Binance
            </button>
            <button className="secondary-button" onClick={() => reconcileVenue("hyperliquid")}>
              Reconcile Hyperliquid
            </button>
          </div>
        </div>
        <div className="status-strip">{message || "Create approval-mode execution tickets instead of sending live orders directly."}</div>
      </div>

      <div className="metrics-grid">
        <div className="metric-card warm">
          <div className="metric-label">Pending Tickets</div>
          <div className="metric-value">{pendingTickets.length}</div>
        </div>
        <div className="metric-card warm">
          <div className="metric-label">Queued Jobs</div>
          <div className="metric-value">{jobMetrics.data?.queued ?? 0}</div>
        </div>
        <div className="metric-card warm">
          <div className="metric-label">Reconciliation Runs</div>
          <div className="metric-value">{reconciliation.data?.length ?? 0}</div>
        </div>
        <div className="metric-card warm">
          <div className="metric-label">Secrets Ready</div>
          <div className="metric-value">{secrets.data?.all_present ? "yes" : "no"}</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Execution Tickets</h2>
            <p>Every live intent becomes an approval artifact first.</p>
          </div>
          <div className="button-row">
            <button className="secondary-button" onClick={processQueue}>
              Process Queue
            </button>
          </div>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Market</th>
              <th>Side</th>
              <th>Preview</th>
              <th>Status</th>
              <th>When</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {(tickets.data ?? []).map((ticket) => (
              <tr key={ticket.ticket_id}>
                <td>{ticket.spec_id}</td>
                <td>
                  {ticket.symbol} / {ticket.venue}
                </td>
                <td>
                  {ticket.action} {ticket.direction}
                </td>
                <td>
                  Fee ${ticket.preview.estimated_fee_usd.toFixed(2)} | Slip {ticket.preview.estimated_slippage_bps}bps
                </td>
                <td>{ticket.status}</td>
                <td>{new Date(ticket.created_at).toLocaleString()}</td>
                <td className="button-row">
                  <button className="secondary-button" disabled={ticket.status !== "pending_approval"} onClick={() => approve(ticket.ticket_id)}>
                    Approve
                  </button>
                  <button className="secondary-button" disabled={ticket.status !== "pending_approval"} onClick={() => reject(ticket.ticket_id)}>
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="inspector-grid">
        <div className="panel inspector-main">
          <div className="section-title">Worker Queue</div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Job</th>
                <th>Status</th>
                <th>Payload</th>
              </tr>
            </thead>
            <tbody>
              {(jobs.data ?? []).map((job) => (
                <tr key={job.job_id}>
                  <td>{job.job_type}</td>
                  <td>{job.status}</td>
                  <td>{job.payload.ticket_id ?? `${job.payload.symbol ?? ""} ${job.payload.venue ?? ""}`.trim()}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="section-title">Venue Secrets</div>
          <div className="range-list">
            {Object.entries(secrets.data?.venues ?? {}).map(([venue, ready]) => (
              <div key={venue}>
                <strong>{venue}</strong>
                <span>{ready ? "configured" : "missing"}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="panel inspector-side">
          <div className="section-title">Reconciliation</div>
          <div className="range-list">
            {(reconciliation.data ?? []).map((item) => (
              <div key={item.reconciliation_id}>
                <strong>{item.venue}</strong>
                <span>
                  {item.status} | {new Date(item.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
