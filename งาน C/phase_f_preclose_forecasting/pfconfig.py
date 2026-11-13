"""Phase F configuration.

Phase F deliberately shares Phase D's identity, browser profile, HMAC key, and
request ledger. It loads Phase D's own config through Phase D's own validator so
budgets and selectors can never drift, and keeps its own state directory outside
the repository.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

PHASE_D_ROOT = Path('/Users/icy/reverse-lotto/งาน A/phase_d_account_monitoring')
PHASE_D_CONFIG = Path.home() / 'Library/Application Support/ThlottoResearch/phase_d/config.yaml'
PHASE_F_STATE = Path.home() / 'Library/Application Support/ThlottoResearch/phase_f'

DEFAULTS = {
    'phase_d_root': str(PHASE_D_ROOT),
    'phase_d_config': str(PHASE_D_CONFIG),
    'state_dir': str(PHASE_F_STATE),
    'horizons': [120, 60, 30, 10],
    'max_pages': 12,
    'deadline_safety_seconds': 8,
    'lock_timeout_seconds': 25,
    'snapshot_window_seconds': 130,
    'automated_access_permitted': False,
}


class ConfigError(ValueError):
    pass


def load(path):
    """Load Phase F settings and the validated Phase D settings they depend on."""
    raw = {}
    if path:
        raw = yaml.safe_load(Path(path).expanduser().read_text(encoding='utf-8')) or {}
    if not isinstance(raw, dict):
        raise ConfigError('config must be a mapping')
    cfg = {**DEFAULTS, **raw}

    root = Path(cfg['phase_d_root']).expanduser().resolve()
    if not (root / 'cli.py').is_file():
        raise ConfigError(f'phase_d_root does not contain cli.py: {root}')
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import cli as phase_d_cli  # Phase D's own validator (state dir, budgets, selectors)

    phase_d_cfg = phase_d_cli.config(str(Path(cfg['phase_d_config']).expanduser()))
    cfg['phase_d_root'] = str(root)
    cfg['phase_d'] = phase_d_cfg
    cfg['phase_d_state'] = Path(phase_d_cfg['state_dir'])
    cfg['profile_dir'] = cfg['phase_d_state'] / 'browser_profile'
    cfg['worker_lock'] = cfg['phase_d_state'] / 'worker.lock'
    cfg['hmac_key'] = cfg['phase_d_state'] / 'hmac.key'

    state = Path(cfg['state_dir']).expanduser().resolve()
    repo = next((p for p in Path(__file__).resolve().parents if (p / '.git').exists()), None)
    if repo and (state == repo or repo in state.parents):
        raise ConfigError('private state must stay outside the repository')
    if state == root or state in root.parents:
        raise ConfigError('phase_f state must not be inside the phase_d tree')
    cfg['state_dir'] = str(state)

    horizons = cfg['horizons']
    if not isinstance(horizons, list) or not horizons:
        raise ConfigError('horizons must be a non-empty list')
    horizons = sorted({int(h) for h in horizons}, reverse=True)
    if any(h <= 0 or h > 600 for h in horizons):
        raise ConfigError('horizons must be between 1 and 600 seconds')
    if horizons != sorted(set(horizons), reverse=True):
        raise ConfigError('horizons must be unique')
    cfg['horizons'] = horizons

    for key, low, high in (('max_pages', 1, 32), ('deadline_safety_seconds', 1, 60),
                           ('lock_timeout_seconds', 1, 120), ('snapshot_window_seconds', 10, 600)):
        value = cfg[key]
        if not isinstance(value, int) or not low <= value <= high:
            raise ConfigError(f'{key} must be an integer in [{low}, {high}]')
    if cfg['max_pages'] < 1:
        raise ConfigError('max_pages must be >= 1')
    return cfg


def example():
    return {
        'phase_d_root': str(PHASE_D_ROOT),
        'phase_d_config': str(PHASE_D_CONFIG),
        'state_dir': str(PHASE_F_STATE),
        'horizons': [120, 60, 30, 10],
        'max_pages': 12,
        'deadline_safety_seconds': 8,
        'lock_timeout_seconds': 25,
        'snapshot_window_seconds': 130,
        'automated_access_permitted': False,
    }
