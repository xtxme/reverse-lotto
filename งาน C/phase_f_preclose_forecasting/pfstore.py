"""Phase F storage: append-only snapshot evidence and a frozen forecast ledger.

Two invariants are enforced by SQLite triggers, not by convention:
  * snapshot evidence (snapshots/page_reads/snapshot_rows) can never be updated
    or deleted, so a later run cannot rewrite history;
  * forecasts can never be updated or deleted, so a forecast cannot be re-fitted
    in place.

A repeated (day, round, horizon) capture gets `attempt = previous + 1` inside an
IMMEDIATE transaction, and daily order stays monotonic.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = Path(__file__).with_name('schema.sql')

SNAPSHOT_COLUMNS = [
    'attempt', 'trading_day', 'round_number', 'period_id', 'horizon_seconds', 'target_close_at',
    'target_close_monotonic_ns', 'scheduled_at_utc', 'scheduled_monotonic_ns', 'started_at_utc',
    'started_monotonic_ns', 'finished_at_utc', 'finished_monotonic_ns', 'saved_at_utc', 'lock_wait_ms',
    'status', 'error_category', 'pages_read', 'pages_available', 'rows_visible', 'displayed_total',
    'row16_number', 'row16_event_key', 'row16_seq_present', 'order_hash', 'reordered_from_previous',
    'seq_changes', 'content_hash', 'clock_offset_seconds', 'clock_source', 'notes',
]

PAGE_COLUMNS = [
    'page', 'url', 'request_started_utc', 'request_started_monotonic_ns', 'response_received_utc',
    'response_received_monotonic_ns', 'status_code', 'rows', 'more_pages_seen', 'content_hash',
    'budget_used_before', 'budget_ceiling', 'budget_checked',
]


def utcnow():
    return datetime.now(timezone.utc)


def utc(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


class PFStore:
    def __init__(self, path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(self.path, timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript(SCHEMA.read_text())
        self._migrate()
        self.db.execute('INSERT OR IGNORE INTO migrations VALUES(2,?)', (utcnow().isoformat(),))
        self.db.commit()
        os.chmod(self.path, 0o600)

    def _migrate(self):
        """Archive v1 evidence tables instead of deleting them."""
        columns = [row[1] for row in self.db.execute('PRAGMA table_info(snapshots)')]
        if 'attempt' in columns:
            return
        self.db.execute('PRAGMA foreign_keys=OFF')
        self.db.execute('PRAGMA legacy_alter_table=ON')
        for table in ('snapshots', 'page_reads', 'snapshot_rows', 'event_sequence', 'first_seen'):
            exists = self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if exists:
                self.db.execute(f'ALTER TABLE {table} RENAME TO {table}_v1')
        self.db.executescript(SCHEMA.read_text())
        self.db.execute('INSERT OR IGNORE INTO migrations VALUES(3,?)', (utcnow().isoformat(),))
        self.db.execute('PRAGMA legacy_alter_table=OFF')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.commit()

    def close(self):
        self.db.close()

    # ---- control -------------------------------------------------------
    def setting(self, key, default=None):
        row = self.db.execute('SELECT value FROM control WHERE key=?', (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO control(key,value) VALUES(?,?)', (key, str(value)))

    # ---- snapshots -----------------------------------------------------
    def insert_snapshot(self, record, pages, rows):
        """Append one capture attempt and its pages/rows atomically."""
        record = dict(record)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            attempt = self.db.execute(
                'SELECT COALESCE(MAX(attempt),0)+1 FROM snapshots WHERE trading_day=? AND round_number=? AND horizon_seconds=?',
                (record['trading_day'], record['round_number'], record['horizon_seconds'])).fetchone()[0]
            record['attempt'] = attempt
            columns = ['attempt'] + [c for c in SNAPSHOT_COLUMNS if c != 'attempt']
            placeholders = ','.join('?' for _ in columns)
            cur = self.db.execute(
                f"INSERT INTO snapshots({','.join(columns)}) VALUES({placeholders})",
                [record.get(c) for c in columns])
            sid = cur.lastrowid
            for page in pages:
                page = dict(page) if isinstance(page, dict) else dict(zip(PAGE_COLUMNS, page))
                self.db.execute(
                    f"INSERT INTO page_reads(snapshot_id,{','.join(PAGE_COLUMNS)}) "
                    f"VALUES(?{',' + ','.join('?' for _ in PAGE_COLUMNS)})",
                    [sid] + [page.get(c) for c in PAGE_COLUMNS])
            for row in rows:
                page, seq, number, created_at, display_hash, key = row
                self.db.execute('INSERT INTO snapshot_rows VALUES(?,?,?,?,?,?,?)',
                                (sid, page, seq, number, created_at, display_hash, key))
            if rows:
                self.db.executemany('INSERT INTO event_sequence(event_key,snapshot_id,observed_seq) VALUES(?,?,?)',
                                    [(r[5], sid, r[2]) for r in rows])
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return sid, attempt

    def previous_snapshot(self, day, rnd, before_monotonic_ns):
        return self.db.execute(
            '''SELECT * FROM snapshots WHERE trading_day=? AND round_number=?
               AND status IN ('OK','TRUNCATED') AND saved_at_utc<=target_close_at
               AND started_monotonic_ns<? ORDER BY started_monotonic_ns DESC, attempt DESC LIMIT 1''',
            (day, rnd, before_monotonic_ns)).fetchone()

    def latest_snapshot(self, day, rnd, horizon):
        return self.db.execute(
            '''SELECT * FROM snapshots WHERE trading_day=? AND round_number=? AND horizon_seconds=?
               ORDER BY attempt DESC LIMIT 1''', (day, rnd, horizon)).fetchone()

    def record_first_seen(self, snapshot_id, rows):
        """Insert first sightings only for events never seen before."""
        if not rows:
            return 0
        head = self.db.execute('SELECT trading_day,round_number,horizon_seconds FROM snapshots WHERE snapshot_id=?',
                               (snapshot_id,)).fetchone()
        day, rnd, horizon = head
        inserted = 0
        with self.db:
            for row in rows:
                page, seq, number, created_at, display_hash, key, seen_utc, seen_mono = row
                cur = self.db.execute(
                    '''INSERT OR IGNORE INTO first_seen(event_key,display_hash,five_digit_number,displayed_created_at,
                       first_snapshot_id,first_seen_utc,first_seen_monotonic_ns,first_seen_horizon,trading_day,
                       round_number,first_observed_seq) VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                    (key, display_hash, number, created_at, snapshot_id, seen_utc, seen_mono, horizon, day, rnd, seq))
                inserted += cur.rowcount
        return inserted

    # ---- ledger --------------------------------------------------------
    def insert_forecast(self, record):
        with self.db:
            self.db.execute(
                '''INSERT INTO forecasts(forecast_id,trading_day,round_number,horizon_seconds,attempt,model_version,
                   information_set,training_cutoff_utc,generated_at_utc,generated_monotonic_ns,snapshot_id,
                   snapshot_hash,snapshot_saved_at_utc,distribution_hash,distribution,distribution_dtype,modulus,
                   checksum,code_version,seed,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', record)

    def forecasts(self, day=None, rnd=None):
        query = 'SELECT * FROM forecasts WHERE 1=1'
        args = []
        if day:
            query += ' AND trading_day=?'
            args.append(day)
        if rnd:
            query += ' AND round_number=?'
            args.append(rnd)
        return self.db.execute(query + ' ORDER BY generated_monotonic_ns', args).fetchall()

    # ---- probes / audit ------------------------------------------------
    def insert_js_probe(self, record):
        with self.db:
            columns = list(record)
            placeholders = ','.join('?' for _ in columns)
            cur = self.db.execute(f"INSERT INTO js_probes({','.join(columns)}) VALUES({placeholders})",
                                  [record[c] for c in columns])
        return cur.lastrowid

    def write_audit(self, scope, passed, checks):
        with self.db:
            self.db.execute('INSERT INTO audit_runs(run_at_utc,scope,passed,checks_json) VALUES(?,?,?,?)',
                            (utc(utcnow()), scope, 1 if passed else 0, json.dumps(checks, ensure_ascii=False, sort_keys=True)))
