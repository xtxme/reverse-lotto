PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);

-- Append-only: one row per capture attempt. A repeated horizon creates attempt 2,
-- never an overwrite. UTC and monotonic readings are stored side by side.
CREATE TABLE IF NOT EXISTS snapshots(
  snapshot_id INTEGER PRIMARY KEY,
  attempt INTEGER NOT NULL,
  trading_day TEXT NOT NULL,
  round_number INTEGER NOT NULL,
  period_id TEXT,
  horizon_seconds INTEGER NOT NULL,
  target_close_at TEXT NOT NULL,
  target_close_monotonic_ns INTEGER,
  scheduled_at_utc TEXT,
  scheduled_monotonic_ns INTEGER,
  started_at_utc TEXT NOT NULL,
  started_monotonic_ns INTEGER NOT NULL,
  finished_at_utc TEXT,
  finished_monotonic_ns INTEGER,
  saved_at_utc TEXT NOT NULL,
  lock_wait_ms INTEGER,
  status TEXT NOT NULL,
  error_category TEXT,
  pages_read INTEGER NOT NULL DEFAULT 0,
  pages_available INTEGER NOT NULL DEFAULT 0,
  rows_visible INTEGER NOT NULL DEFAULT 0,
  displayed_total INTEGER,
  row16_number TEXT,
  row16_event_key TEXT,
  row16_seq_present INTEGER,
  order_hash TEXT,
  reordered_from_previous INTEGER,
  seq_changes INTEGER,
  content_hash TEXT,
  clock_offset_seconds REAL,
  clock_source TEXT,
  notes TEXT,
  UNIQUE(trading_day, round_number, horizon_seconds, attempt)
);
CREATE INDEX IF NOT EXISTS snapshots_day ON snapshots(trading_day, round_number, horizon_seconds, attempt);
CREATE INDEX IF NOT EXISTS snapshots_status ON snapshots(status);

-- Every document read, its observation interval, and the budget state that was
-- checked immediately before the request was issued.
CREATE TABLE IF NOT EXISTS page_reads(
  snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id),
  page INTEGER NOT NULL,
  url TEXT NOT NULL,
  request_started_utc TEXT NOT NULL,
  request_started_monotonic_ns INTEGER NOT NULL,
  response_received_utc TEXT NOT NULL,
  response_received_monotonic_ns INTEGER NOT NULL,
  status_code INTEGER,
  rows INTEGER,
  more_pages_seen INTEGER,
  content_hash TEXT,
  budget_used_before INTEGER,
  budget_ceiling INTEGER,
  budget_checked INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(snapshot_id, page)
);

CREATE TABLE IF NOT EXISTS snapshot_rows(
  snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id),
  page INTEGER NOT NULL,
  observed_seq INTEGER NOT NULL,
  five_digit_number TEXT NOT NULL CHECK(length(five_digit_number)=5 AND five_digit_number NOT GLOB '*[^0-9]*'),
  displayed_created_at TEXT NOT NULL,
  display_hash TEXT NOT NULL,
  event_key TEXT NOT NULL,
  PRIMARY KEY(snapshot_id, event_key)
);
CREATE INDEX IF NOT EXISTS snapshot_rows_seq ON snapshot_rows(snapshot_id, observed_seq);

CREATE TABLE IF NOT EXISTS event_sequence(
  event_key TEXT NOT NULL,
  snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id),
  observed_seq INTEGER NOT NULL,
  PRIMARY KEY(event_key, snapshot_id)
);

CREATE TABLE IF NOT EXISTS first_seen(
  event_key TEXT PRIMARY KEY,
  display_hash TEXT NOT NULL,
  five_digit_number TEXT NOT NULL,
  displayed_created_at TEXT NOT NULL,
  first_snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id),
  first_seen_utc TEXT NOT NULL,
  first_seen_monotonic_ns INTEGER NOT NULL,
  first_seen_horizon INTEGER NOT NULL,
  trading_day TEXT NOT NULL,
  round_number INTEGER NOT NULL,
  first_observed_seq INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS first_seen_round ON first_seen(trading_day, round_number);

CREATE TABLE IF NOT EXISTS forecasts(
  forecast_id TEXT PRIMARY KEY,
  trading_day TEXT NOT NULL,
  round_number INTEGER NOT NULL,
  horizon_seconds INTEGER NOT NULL,
  attempt INTEGER NOT NULL DEFAULT 1,
  model_version TEXT NOT NULL,
  information_set TEXT NOT NULL,
  training_cutoff_utc TEXT,
  generated_at_utc TEXT NOT NULL,
  generated_monotonic_ns INTEGER NOT NULL,
  snapshot_id INTEGER,
  snapshot_hash TEXT,
  snapshot_saved_at_utc TEXT,
  distribution_hash TEXT NOT NULL,
  distribution BLOB NOT NULL,
  distribution_dtype TEXT NOT NULL,
  modulus INTEGER NOT NULL DEFAULT 100000,
  checksum TEXT NOT NULL,
  code_version TEXT,
  seed INTEGER,
  notes TEXT,
  UNIQUE(trading_day, round_number, horizon_seconds, model_version, attempt)
);
CREATE INDEX IF NOT EXISTS forecasts_round ON forecasts(trading_day, round_number);

CREATE TRIGGER IF NOT EXISTS forecasts_no_update BEFORE UPDATE ON forecasts
BEGIN SELECT RAISE(ABORT,'forecast_ledger_is_immutable'); END;
CREATE TRIGGER IF NOT EXISTS forecasts_no_delete BEFORE DELETE ON forecasts
BEGIN SELECT RAISE(ABORT,'forecast_ledger_is_immutable'); END;

-- A snapshot row may never be rewritten either: evidence must survive.
CREATE TRIGGER IF NOT EXISTS snapshots_no_update BEFORE UPDATE ON snapshots
BEGIN SELECT RAISE(ABORT,'snapshot_evidence_is_append_only'); END;
CREATE TRIGGER IF NOT EXISTS snapshots_no_delete BEFORE DELETE ON snapshots
BEGIN SELECT RAISE(ABORT,'snapshot_evidence_is_append_only'); END;
CREATE TRIGGER IF NOT EXISTS page_reads_no_update BEFORE UPDATE ON page_reads
BEGIN SELECT RAISE(ABORT,'snapshot_evidence_is_append_only'); END;
CREATE TRIGGER IF NOT EXISTS page_reads_no_delete BEFORE DELETE ON page_reads
BEGIN SELECT RAISE(ABORT,'snapshot_evidence_is_append_only'); END;
CREATE TRIGGER IF NOT EXISTS snapshot_rows_no_update BEFORE UPDATE ON snapshot_rows
BEGIN SELECT RAISE(ABORT,'snapshot_evidence_is_append_only'); END;
CREATE TRIGGER IF NOT EXISTS snapshot_rows_no_delete BEFORE DELETE ON snapshot_rows
BEGIN SELECT RAISE(ABORT,'snapshot_evidence_is_append_only'); END;

CREATE TABLE IF NOT EXISTS audit_runs(
  audit_id INTEGER PRIMARY KEY,
  run_at_utc TEXT NOT NULL,
  scope TEXT NOT NULL,
  passed INTEGER NOT NULL,
  checks_json TEXT NOT NULL
);

-- JavaScript-enabled visibility probes. Diagnostic only: counts and request
-- metadata, never response bodies.
CREATE TABLE IF NOT EXISTS js_probes(
  probe_id INTEGER PRIMARY KEY,
  trading_day TEXT NOT NULL,
  round_number INTEGER NOT NULL,
  period_id TEXT,
  target_close_at TEXT NOT NULL,
  started_at_utc TEXT NOT NULL,
  started_monotonic_ns INTEGER NOT NULL,
  finished_at_utc TEXT,
  finished_monotonic_ns INTEGER,
  saved_at_utc TEXT NOT NULL,
  status TEXT NOT NULL,
  error_category TEXT,
  dom_rows INTEGER,
  dom_row16 INTEGER,
  doc_requests INTEGER,
  xhr_requests INTEGER,
  asset_requests INTEGER,
  blocked_requests INTEGER,
  budget_used_before INTEGER,
  budget_ceiling INTEGER,
  rows_visible INTEGER,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS control(key TEXT PRIMARY KEY, value TEXT NOT NULL);
