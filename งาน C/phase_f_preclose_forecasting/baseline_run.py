#!/usr/bin/env python3
"""Retrospective baseline harness (A/B/C) with strict walk-forward.

Prints JSON to stdout and writes nothing. Every result carries the
RETROSPECTIVE_POST_CLOSE_SIMULATION label: rows are taken from completed rounds
and truncated synthetically by display sequence, which is NOT pre-close evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import walkforward


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=str(Path.home() / 'Library/Application Support/ThlottoResearch/phase_d/research.sqlite3'))
    parser.add_argument('--k', default='16,50', help='visible prefix lengths for model C')
    parser.add_argument('--min-train', type=int, default=30)
    parser.add_argument('--prior-strength', type=float, default=100.0)
    parser.add_argument('--delta-prior', type=float, default=20.0)
    parser.add_argument('--compact', action='store_true')
    args = parser.parse_args(argv)

    k_values = tuple(int(x) for x in args.k.split(',') if x.strip())
    result = walkforward.run(args.db, k_values=k_values, min_train=args.min_train,
                             prior_strength=args.prior_strength, delta_prior=args.delta_prior)

    if args.compact:
        summary = {
            'data': result['data'],
            'labels': result['labels'],
            'models': {name: {key: value for key, value in stats.items() if key != 'calibration'}
                       for name, stats in result['models'].items()},
            'per_day': result['per_day'],
            'paired_vs_A': result['paired_vs_A'],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=1))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
