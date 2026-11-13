#!/usr/bin/env python3
"""Phase F CLI — pre-close snapshot capture, audit, and forecast ledger.

Usage:
  pf.py --config <phase_f.yaml> init
  pf.py --config <phase_f.yaml> status
  pf.py --config <phase_f.yaml> schedule --round 70
  pf.py --config <phase_f.yaml> snapshot --round 70 --horizon 120 --dry-run
  pf.py --config <phase_f.yaml> snapshot --round 70 --horizon 120 --live --authorized
  pf.py --config <phase_f.yaml> session  --round 70 --live --authorized
  pf.py --config <phase_f.yaml> audit --round 70
  pf.py --config <phase_f.yaml> test --offline
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pfconfig
import pfaudit
import pfsession
from pfstore import PFStore


def _store(cfg):
    return PFStore(Path(cfg['state_dir']) / 'phase_f.sqlite3')


def _day(cfg, value):
    if value:
        return value
    pd = pfsession._pd(cfg)
    return pd['day_for'](pd['now']())


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('init')
    sub.add_parser('status')
    sub.add_parser('test').add_argument('--offline', action='store_true', required=True)

    fc = sub.add_parser('forecast')
    fc.add_argument('--round', type=int, required=True)
    fc.add_argument('--day')
    fc.add_argument('--horizon', type=int, required=True)
    fc.add_argument('--model', choices=['uniform', 'historical', 'partial'], required=True)

    smoke = sub.add_parser('smoke')
    smoke.add_argument('--round', type=int, required=True)
    smoke.add_argument('--day')
    smoke.add_argument('--live', action='store_true')
    smoke.add_argument('--authorized', action='store_true')

    for name in ('schedule', 'snapshot', 'session', 'audit'):
        item = sub.add_parser(name)
        item.add_argument('--round', type=int, required=True)
        item.add_argument('--day')
        if name in ('schedule', 'session'):
            item.add_argument('--horizons', help='comma separated seconds, default from config')
        if name in ('snapshot', 'session'):
            item.add_argument('--live', action='store_true')
            item.add_argument('--authorized', action='store_true')
            item.add_argument('--dry-run', action='store_true')
        if name == 'snapshot':
            item.add_argument('--horizon', type=int, required=True)

    args = parser.parse_args(argv)

    if args.command == 'test':
        return subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT / 'tests'), '-v'],
                              cwd=ROOT).returncode

    cfg = pfconfig.load(args.config)
    store = _store(cfg)
    try:
        if args.command == 'init':
            print(json.dumps({'ok': True, 'database': str(store.path), 'horizons': cfg['horizons']}, indent=2))
            return 0

        if args.command == 'status':
            counts = {row[0]: row[1] for row in store.db.execute('SELECT status,COUNT(*) FROM snapshots GROUP BY status')}
            first_seen = store.db.execute('SELECT COUNT(*) FROM first_seen').fetchone()[0]
            forecasts = store.db.execute('SELECT COUNT(*) FROM forecasts').fetchone()[0]
            print(json.dumps({
                'database': str(store.path),
                'snapshots_by_status': counts,
                'first_seen_events': first_seen,
                'forecasts': forecasts,
                'horizons': cfg['horizons'],
                'phase_d_state': str(cfg['phase_d_state']),
                'profile_shared': str(cfg['profile_dir']),
                'worker_lock': str(cfg['worker_lock']),
            }, ensure_ascii=False, indent=2))
            return 0

        day = _day(cfg, args.day)
        if not 1 <= args.round <= 88:
            raise ValueError('round must be 1..88')

        if args.command == 'forecast':
            import pfledger
            try:
                print(json.dumps(pfledger.freeze(cfg, store, day, args.round, args.horizon, args.model),
                                 ensure_ascii=False, indent=2))
                return 0
            except ValueError as error:
                print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False, indent=2))
                return 2

        if args.command == 'smoke':
            if not (args.live and args.authorized):
                raise ValueError('smoke requires --live --authorized (it performs one page read)')
            if not cfg.get('automated_access_permitted'):
                raise ValueError('automated_access_permitted must be true in the phase_f config')
            print(json.dumps(pfsession.smoke(cfg, store, day, args.round), ensure_ascii=False, indent=2))
            return 0

        if args.command == 'schedule':
            print(json.dumps(pfsession.plan(cfg, day, args.round), ensure_ascii=False, indent=2))
            return 0

        if args.command == 'audit':
            result = pfaudit.audit(store, day=day, rnd=args.round)
            store.write_audit(f'{day}/R{args.round}', result['passed'],
                              {'failed_checks': result['failed_checks'], 'snapshots': result['snapshots']})
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result['passed'] else 2

        live = bool(args.live and not args.dry_run)
        if live:
            if not cfg.get('automated_access_permitted'):
                raise ValueError('automated_access_permitted must be true in the phase_f config')
            if not args.authorized:
                raise ValueError('--authorized is required for live capture')

        if args.command == 'snapshot':
            report, _, _, _ = pfsession.capture(cfg, store, day, args.round, args.horizon, live=live)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report.get('status') in ('OK', 'TRUNCATED', 'DRY_RUN') else 2

        horizons = None
        if args.horizons:
            horizons = [int(x) for x in args.horizons.split(',') if x.strip()]
        results = pfsession.run_session(cfg, store, day, args.round, horizons=horizons, live=live)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    finally:
        store.close()


if __name__ == '__main__':
    sys.exit(main())
