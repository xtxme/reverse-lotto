"""Audit for prospective snapshots.

The audit is deliberately adversarial: it recomputes ordering, pagination bounds
and first-seen consistency from stored rows instead of trusting the snapshot row.
Any FAIL blocks using the snapshot for pre-close claims.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

TOLERANCE_SECONDS = 2.0


def _parse(value):
    if value is None:
        return None
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _check(name, failures, detail):
    return {'name': name, 'passed': not failures, 'failures': failures[:20], 'count': len(failures), 'detail': detail}


def audit(store, day=None, rnd=None):
    db = store.db
    query = "SELECT * FROM snapshots WHERE 1=1"
    args = []
    if day:
        query += ' AND trading_day=?'
        args.append(day)
    if rnd is not None:
        query += ' AND round_number=?'
        args.append(rnd)
    snapshots = [dict(r) for r in db.execute(query + ' ORDER BY started_monotonic_ns', args)]
    checks = []

    # 1. UTC and monotonic ordering agree inside every snapshot.
    failures = []
    for snap in snapshots:
        started, finished = _parse(snap['started_at_utc']), _parse(snap['finished_at_utc'])
        if snap['status'] in ('OK', 'TRUNCATED', 'FAILED') and (not started or not finished):
            failures.append({'snapshot': snap['snapshot_id'], 'reason': 'missing_bounds'})
            continue
        pages = [dict(r) for r in db.execute('SELECT * FROM page_reads WHERE snapshot_id=? ORDER BY page', (snap['snapshot_id'],))]
        prev_mono = snap['started_monotonic_ns']
        prev_utc = started
        for page in pages:
            start_u, end_u = _parse(page['request_started_utc']), _parse(page['response_received_utc'])
            if not (start_u and end_u):
                failures.append({'snapshot': snap['snapshot_id'], 'page': page['page'], 'reason': 'missing_page_bounds'})
                continue
            if page['request_started_monotonic_ns'] < prev_mono or end_u < start_u:
                failures.append({'snapshot': snap['snapshot_id'], 'page': page['page'], 'reason': 'monotonic_or_utc_regression'})
            if prev_utc and start_u < prev_utc:
                failures.append({'snapshot': snap['snapshot_id'], 'page': page['page'], 'reason': 'utc_regression'})
            prev_mono = page['response_received_monotonic_ns']
            prev_utc = end_u
        if finished and prev_utc and finished < prev_utc:
            failures.append({'snapshot': snap['snapshot_id'], 'reason': 'finished_before_last_response'})
    checks.append(_check('clock_ordering', failures, f'{len(snapshots)} snapshots checked'))

    # 2. Monotonic elapsed time must roughly match UTC elapsed time.
    failures = []
    for snap in snapshots:
        for page in db.execute('SELECT * FROM page_reads WHERE snapshot_id=? ORDER BY page', (snap['snapshot_id'],)):
            start_u, end_u = _parse(page['request_started_utc']), _parse(page['response_received_utc'])
            if not (start_u and end_u):
                continue
            utc_delta = (end_u - start_u).total_seconds()
            mono_delta = (page['response_received_monotonic_ns'] - page['request_started_monotonic_ns']) / 1e9
            if abs(utc_delta - mono_delta) > TOLERANCE_SECONDS:
                failures.append({'snapshot': snap['snapshot_id'], 'page': page['page'],
                                 'utc_delta': round(utc_delta, 3), 'monotonic_delta': round(mono_delta, 3)})
    checks.append(_check('clock_agreement', failures, f'tolerance {TOLERANCE_SECONDS}s; mismatch is a warning-level clock jump'))

    # 3. Every snapshot must start strictly before its betting close.
    failures = []
    for snap in snapshots:
        started = _parse(snap['started_at_utc'])
        close = _parse(snap['target_close_at'])
        if started and close and started >= close:
            failures.append({'snapshot': snap['snapshot_id'], 'started': snap['started_at_utc'],
                             'close': snap['target_close_at'], 'reason': 'started_at_or_after_close'})
    checks.append(_check('pre_close_bound', failures, 'no snapshot may start at/after betting close'))

    # 4. First-seen must be prospective: inside its own snapshot window and before close.
    failures = []
    for row in db.execute('''SELECT f.*, s.started_at_utc, s.target_close_at FROM first_seen f
                             JOIN snapshots s ON s.snapshot_id=f.first_snapshot_id'''):
        seen, started, close = _parse(row['first_seen_utc']), _parse(row['started_at_utc']), _parse(row['target_close_at'])
        if seen and started and seen < started:
            failures.append({'event': row['event_key'][:16], 'reason': 'first_seen_before_snapshot_start',
                             'seen': row['first_seen_utc'], 'snapshot_start': row['started_at_utc']})
        if seen and close and seen >= close:
            failures.append({'event': row['event_key'][:16], 'reason': 'first_seen_after_close', 'seen': row['first_seen_utc']})
    checks.append(_check('first_seen_prospective', failures, 'first_seen must come from a pre-close response'))

    # 5. First-seen must be the earliest snapshot that contains the event.
    failures = []
    for row in db.execute('''SELECT f.event_key, f.first_snapshot_id, f.first_seen_monotonic_ns
                             FROM first_seen f'''):
        earlier = db.execute('''SELECT e.snapshot_id, s.started_monotonic_ns FROM event_sequence e
                                JOIN snapshots s ON s.snapshot_id=e.snapshot_id
                                WHERE e.event_key=? AND s.status IN ('OK','TRUNCATED')
                                ORDER BY s.started_monotonic_ns LIMIT 1''', (row['event_key'],)).fetchone()
        if earlier and earlier[0] != row['first_snapshot_id']:
            failures.append({'event': row['event_key'][:16], 'stored': row['first_snapshot_id'], 'earliest': earlier[0]})
    checks.append(_check('first_seen_is_earliest', failures, 'no later snapshot may claim a first sighting'))

    # 6. first_seen must never equal displayed_created_at by construction.
    failures, warnings = [], []
    for row in db.execute('SELECT event_key, first_seen_utc, displayed_created_at FROM first_seen'):
        if row['first_seen_utc'] == row['displayed_created_at']:
            warnings.append({'event': row['event_key'][:16], 'reason': 'identical_to_displayed_timestamp'})
    checks.append(_check('first_seen_not_displayed_time', warnings,
                         'displayed_created_at is never used as first_seen (identical values are suspicious, not proof)'))

    # 7. Pagination bounds must be internally consistent.
    failures = []
    for snap in snapshots:
        if snap['status'] not in ('OK', 'TRUNCATED'):
            continue
        available = snap['pages_available'] or 0
        read = snap['pages_read'] or 0
        unread = max(0, available - read)
        if read > available:
            failures.append({'snapshot': snap['snapshot_id'], 'reason': 'read_more_than_available', 'read': read, 'available': available})
        if unread and snap['status'] != 'TRUNCATED':
            failures.append({'snapshot': snap['snapshot_id'], 'reason': 'unread_pages_not_marked_truncated', 'unread': unread})
        actual = db.execute('SELECT COUNT(*) FROM page_reads WHERE snapshot_id=?', (snap['snapshot_id'],)).fetchone()[0]
        if actual != read:
            failures.append({'snapshot': snap['snapshot_id'], 'reason': 'page_rows_mismatch', 'recorded': read, 'stored': actual})
    checks.append(_check('pagination_bounds', failures, 'pages_read + unread must equal pages_available'))

    # 8. No duplicate event keys, no duplicate sequences inside a snapshot.
    failures = []
    for snap in snapshots:
        dup = db.execute('''SELECT observed_seq, COUNT(*) n FROM snapshot_rows WHERE snapshot_id=?
                            GROUP BY observed_seq HAVING n>1''', (snap['snapshot_id'],)).fetchall()
        if dup:
            failures.append({'snapshot': snap['snapshot_id'], 'duplicate_sequences': [d[0] for d in dup][:10]})
        counted = db.execute('SELECT COUNT(*) FROM snapshot_rows WHERE snapshot_id=?', (snap['snapshot_id'],)).fetchone()[0]
        distinct = db.execute('SELECT COUNT(DISTINCT event_key) FROM snapshot_rows WHERE snapshot_id=?', (snap['snapshot_id'],)).fetchone()[0]
        if counted != distinct:
            failures.append({'snapshot': snap['snapshot_id'], 'reason': 'duplicate_event_key'})
        if snap['status'] in ('OK', 'TRUNCATED') and counted != (snap['rows_visible'] or 0):
            failures.append({'snapshot': snap['snapshot_id'], 'reason': 'rows_visible_mismatch'})
    checks.append(_check('row_integrity', failures, 'unique sequence and event keys per snapshot'))

    # 9. Order hash and row-16 fields must be reproducible from stored rows.
    failures = []
    for snap in snapshots:
        if snap['status'] not in ('OK', 'TRUNCATED'):
            continue
        rows = db.execute('SELECT observed_seq,five_digit_number,event_key FROM snapshot_rows WHERE snapshot_id=? ORDER BY observed_seq',
                          (snap['snapshot_id'],)).fetchall()
        payload = '\n'.join(f'{r[0]}:{r[2]}' for r in rows)
        expected = hashlib.sha256(payload.encode()).hexdigest() if rows else None
        if expected != snap['order_hash']:
            failures.append({'snapshot': snap['snapshot_id'], 'reason': 'order_hash_mismatch'})
        row16 = next((r for r in rows if r[0] == 16), None)
        if (row16 is not None) != bool(snap['row16_seq_present']):
            failures.append({'snapshot': snap['snapshot_id'], 'reason': 'row16_presence_mismatch'})
        if row16 and row16[1] != snap['row16_number']:
            failures.append({'snapshot': snap['snapshot_id'], 'reason': 'row16_number_mismatch'})
    checks.append(_check('order_reproducible', failures, 'order_hash and row-16 fields recomputed from rows'))

    # 10. Reorder counters must match a recomputation against the previous snapshot.
    failures = []
    for snap in snapshots:
        previous = db.execute('''SELECT snapshot_id FROM snapshots WHERE trading_day=? AND round_number=?
                                 AND status IN ('OK','TRUNCATED') AND started_monotonic_ns<?
                                 ORDER BY started_monotonic_ns DESC LIMIT 1''',
                              (snap['trading_day'], snap['round_number'], snap['started_monotonic_ns'])).fetchone()
        if not previous:
            continue
        prior = {r[0]: r[1] for r in db.execute('SELECT event_key,observed_seq FROM snapshot_rows WHERE snapshot_id=?', (previous[0],))}
        current = {r[0]: r[1] for r in db.execute('SELECT event_key,observed_seq FROM snapshot_rows WHERE snapshot_id=?', (snap['snapshot_id'],))}
        moved = sum(1 for key, seq in current.items() if key in prior and prior[key] != seq)
        if (snap['seq_changes'] or 0) != moved:
            failures.append({'snapshot': snap['snapshot_id'], 'recorded': snap['seq_changes'], 'recomputed': moved})
        expected_flag = 1 if moved else 0
        if snap['reordered_from_previous'] is not None and int(snap['reordered_from_previous']) != expected_flag:
            failures.append({'snapshot': snap['snapshot_id'], 'reason': 'reorder_flag_mismatch'})
    checks.append(_check('reorder_recomputable', failures, 'sequence moves recomputed against the previous snapshot'))

    checks.insert(0, _check('has_snapshots', [] if snapshots else [{'reason': 'no_snapshots_for_scope'}],
                            f'{len(snapshots)} snapshots in scope'))
    passed = all(c['passed'] for c in checks)
    pre_close = [s for s in snapshots if s['status'] in ('OK', 'TRUNCATED') and (s['horizon_seconds'] or 0) > 0]
    with_rows = [s for s in pre_close if (s['rows_visible'] or 0) > 0]
    visibility = {
        'pre_close_snapshots': len(pre_close),
        'pre_close_snapshots_with_rows': len(with_rows),
        'pre_close_claims_allowed': bool(with_rows),
        'reason': None if with_rows else 'no_rows_visible_before_close',
    }
    return {'passed': passed, 'pre_close_ready': bool(passed and with_rows),
            'snapshots': len(snapshots), 'visibility': visibility, 'checks': checks,
            'failed_checks': [c['name'] for c in checks if not c['passed']]}
