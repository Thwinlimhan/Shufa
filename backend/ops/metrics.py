from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "workbench_http_requests_total",
    "Total HTTP requests by path and method.",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "workbench_http_request_latency_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)
PAPER_POSITION_GAUGE = Gauge("workbench_open_positions", "Current open paper positions.")
WORKER_QUEUE_GAUGE = Gauge("workbench_worker_queue_depth", "Current queued jobs.")
TRADE_EVENTS = Counter(
    "workbench_trade_events_total",
    "Paper trade events.",
    ["event_type", "spec_id"],
)


def prometheus_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
