CREATE TABLE IF NOT EXISTS market_marks (
    instrument_key TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    venue TEXT NOT NULL,
    price REAL NOT NULL,
    ts TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_marks_ts ON market_marks(ts);
