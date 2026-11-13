import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (str(ROOT), str(ROOT / 'tests')):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import pfconfig
import pfledger
from pfstore import PFStore
from test_offline import synthetic


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name)
        config_path = self.state / 'phase_f.yaml'
        config_path.write_text(
            'phase_d_root: /Users/icy/reverse-lotto/งาน A/phase_d_account_monitoring\n'
            'phase_d_config: ' + str(Path.home() / 'Library/Application Support/ThlottoResearch/phase_d/config.yaml') + '\n'
            'state_dir: ' + str(self.state) + '\n'
            'automated_access_permitted: false\n', encoding='utf-8')
        self.cfg = pfconfig.load(str(config_path))
        self.store = PFStore(self.state / 'phase_f.sqlite3')
        self.close = datetime(2026, 11, 13, 15, 30, tzinfo=timezone.utc)
        rows = [(1, seq, f'{seq:05d}', f'2026-11-13T22:29:{50 + seq % 9}+07:00', f'hmac-v1:{seq}', f'k{seq}')
                for seq in range(1, 17)]
        self.snapshot_id = synthetic(self.store, self.close, 1_000_000, rows=rows)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_uniform_freeze_before_close_is_recorded_and_immutable(self):
        now = self.close - timedelta(seconds=5)
        result = pfledger.freeze(self.cfg, self.store, '2026-11-13', 67, 120, 'uniform', now=now)
        self.assertTrue(result['ok'])
        self.assertEqual(result['information_set'], 'PROSPECTIVE_PRE_CLOSE')
        self.assertGreater(result['seconds_to_close'], 0)
        stored = self.store.db.execute('SELECT * FROM forecasts WHERE forecast_id=?', (result['forecast_id'],)).fetchone()
        self.assertEqual(stored['model_version'], 'uniform')
        self.assertEqual(stored['distribution_dtype'], 'float32')
        self.assertEqual(len(stored['distribution']), 400000)
        with self.assertRaises(Exception):
            with self.store.db:
                self.store.db.execute("UPDATE forecasts SET model_version='x' WHERE forecast_id=?", (result['forecast_id'],))

    def test_duplicate_freeze_is_rejected(self):
        now = self.close - timedelta(seconds=5)
        pfledger.freeze(self.cfg, self.store, '2026-11-13', 67, 120, 'uniform', now=now)
        with self.assertRaises(ValueError):
            pfledger.freeze(self.cfg, self.store, '2026-11-13', 67, 120, 'uniform', now=now)

    def test_post_close_freeze_is_refused(self):
        with self.assertRaises(ValueError) as context:
            pfledger.freeze(self.cfg, self.store, '2026-11-13', 67, 120, 'uniform',
                            now=self.close + timedelta(seconds=1))
        self.assertIn('refuse_post_close', str(context.exception))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM forecasts').fetchone()[0], 0)

    def test_partial_with_visible_rows_is_not_uniform(self):
        now = self.close - timedelta(seconds=5)
        result = pfledger.freeze(self.cfg, self.store, '2026-11-13', 67, 120, 'partial', now=now)
        self.assertTrue(result['ok'])
        self.assertEqual(result['meta']['model'], 'partial')
        self.assertGreater(result['meta'].get('visible_rows', 0), 0)

    def test_missing_snapshot_is_rejected(self):
        with self.assertRaises(ValueError):
            pfledger.freeze(self.cfg, self.store, '2026-11-13', 67, 999, 'uniform',
                            now=self.close - timedelta(seconds=5))


if __name__ == '__main__':
    unittest.main()
