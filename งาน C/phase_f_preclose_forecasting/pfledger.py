"""Freeze a pre-close forecast into the append-only ledger.

Integrity rules:
  * a forecast may only be frozen while `now < betting_close_at`;
  * the snapshot must exist, be readable, and have started before now;
  * re-freezing the same (day, round, horizon, model) is rejected by the unique
    key, and the ledger triggers reject UPDATE/DELETE.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import models
import walkforward

MODULUS = models.MODULUS


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _parse(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def _training_rounds(cfg, day, rnd):
    db = Path(cfg['phase_d_state']) / 'research.sqlite3'
    rounds = walkforward.load_rounds(db)
    return [r for r in rounds if (r['trading_day'], r['round_number']) < (day, rnd)]


def _training_cutoff(cfg, day, rnd):
    db = Path(cfg['phase_d_state']) / 'research.sqlite3'
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    try:
        row = con.execute(
            '''SELECT MAX(betting_close_at) FROM rounds WHERE result_status='COMPLETE'
               AND (trading_day<? OR (trading_day=? AND round_number<?))''', (day, day, rnd)).fetchone()
    finally:
        con.close()
    return row[0] if row and row[0] else None


def build_distribution(cfg, store, snapshot, model_name):
    """Return (distribution, metadata) for the requested model."""
    day, rnd = snapshot['trading_day'], snapshot['round_number']
    if model_name == 'uniform':
        return models.uniform(), {'model': 'uniform', 'note': 'no information used'}
    training = _training_rounds(cfg, day, rnd)
    if model_name == 'historical':
        residues = np.fromiter((r['residue'] for r in training), dtype=np.int64, count=len(training))
        counts = np.bincount(residues, minlength=MODULUS).astype(np.float64)
        return models.historical(counts, 100.0), {'model': 'historical', 'training_rounds': len(training)}
    if model_name == 'partial':
        rows = store.db.execute(
            'SELECT five_digit_number FROM snapshot_rows WHERE snapshot_id=? ORDER BY observed_seq',
            (snapshot['snapshot_id'],)).fetchall()
        visible = [int(r[0]) for r in rows]
        k = len(visible)
        if k == 0:
            return models.uniform(), {'model': 'partial', 'visible_rows': 0,
                                      'note': 'no visible rows, uniform fallback'}
        deltas_by_k, all_deltas = {}, []
        for train in training:
            training_k = min(k, train['count'])
            delta = (train['residue'] - sum(train['numbers'][:training_k])) % MODULUS
            deltas_by_k.setdefault(training_k, []).append(delta)
            all_deltas.append(delta)
        fallback = models.delta_distribution(all_deltas, 20.0)
        delta_dist = models.conditional_delta(deltas_by_k, k, fallback, 20.0)
        return models.shift(delta_dist, sum(visible)), {'model': 'partial', 'visible_rows': k,
                                                        'observed_sum': sum(visible),
                                                        'training_rounds': len(training)}
    raise ValueError(f'unknown model: {model_name}')


def freeze(cfg, store, day, rnd, horizon, model_name, now=None):
    now = now or _now()
    snapshot = store.db.execute(
        'SELECT * FROM snapshots WHERE trading_day=? AND round_number=? AND horizon_seconds=?',
        (day, rnd, horizon)).fetchone()
    if snapshot is None:
        raise ValueError('snapshot_not_found')
    close = _parse(snapshot['target_close_at'])
    if now >= close:
        raise ValueError('refuse_post_close_freeze')
    if snapshot['status'] not in ('OK', 'TRUNCATED'):
        raise ValueError('snapshot_not_observable')
    if _parse(snapshot['started_at_utc']) > now:
        raise ValueError('snapshot_started_in_future')

    distribution, meta = build_distribution(cfg, store, snapshot, model_name)
    distribution = np.asarray(distribution, dtype=np.float64)
    if distribution.shape != (MODULUS,) or not np.isclose(float(distribution.sum()), 1.0, atol=1e-6):
        raise ValueError('invalid_distribution')

    payload = distribution.astype(np.float32).tobytes()
    distribution_hash = hashlib.sha256(payload).hexdigest()
    generated = _iso(now)
    digest = hashlib.sha256(json.dumps({
        'day': day, 'round': rnd, 'horizon': horizon, 'model': model_name,
        'snapshot': snapshot['content_hash'], 'generated': generated,
        'distribution': distribution_hash,
    }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    forecast_id = digest[:32]
    code_version = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]

    record = (forecast_id, day, rnd, horizon, model_name, 'PROSPECTIVE_PRE_CLOSE',
              _training_cutoff(cfg, day, rnd), generated, int(now.timestamp() * 1_000_000_000),
              snapshot['snapshot_id'], snapshot['content_hash'], distribution_hash, payload, 'float32',
              MODULUS, digest, code_version, None,
              json.dumps(meta, ensure_ascii=False, sort_keys=True))
    try:
        store.insert_forecast(record)
    except sqlite3.IntegrityError as error:
        raise ValueError('duplicate_forecast') from error
    return {
        'ok': True, 'forecast_id': forecast_id, 'trading_day': day, 'round_number': rnd,
        'horizon_seconds': horizon, 'model': model_name,
        'information_set': 'PROSPECTIVE_PRE_CLOSE',
        'snapshot_hash': snapshot['content_hash'], 'distribution_hash': distribution_hash,
        'checksum': digest, 'generated_at_utc': generated,
        'seconds_to_close': round((close - now).total_seconds(), 1), 'meta': meta,
    }
