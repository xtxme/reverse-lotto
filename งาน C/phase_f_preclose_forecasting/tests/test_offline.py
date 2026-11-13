import hashlib
import json
import sqlite3
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pfconfig
import pfaudit
import pfsession
from pfstore import PFStore


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def page_html(numbers, close='13/11/2569 22:30:00', period='243', page=None, with_result=False):
    url = f'https://thlotto.com/member/lottery/yeekee/{period}'
    config = {'id': period, 'title': 'จับยี่กี รอบที่ 67', 'close_date': close, 'result_state': 'none'}
    if with_result:
        config['result_state'] = 'published'
    head = '<script>var betconfig = ' + json.dumps(config) + ';</script>'
    if with_result:
        head += '<b class="top3">123</b><b class="bottom2">45</b>'
    items = []
    for seq, number in numbers:
        items.append(f'<li><span class="no">{seq}.</span><span class="key">{number}</span>'
                     f'<span class="username">ab***cd</span>13/11/2569 22:29:5{seq % 10}</li>')
    link = f'<a href="/member/lottery/yeekee/{period}?page={page}">next</a>' if page else ''
    return f'{head}<ul class="number-key-list">{"".join(items)}</ul>{link}'


def synthetic(store, close_at, started_mono, status='OK', pages=1, unread=0, rows=None,
              horizon=120, started_offset=120, started_at=None, reordered=None, seq_changes=None):
    """Insert a synthetic snapshot directly, bypassing the browser."""
    rows = rows or []
    day, rnd = '2026-11-13', 67
    started = started_at or (close_at - timedelta(seconds=started_offset))
    finished = started + timedelta(seconds=3)
    row16 = next((r for r in rows if r[1] == 16), None)
    order = '\n'.join(f'{r[1]}:{r[5]}' for r in sorted(rows, key=lambda r: r[1]))
    record = [day, rnd, '243', horizon, iso(close_at), iso(started), iso(started), started_mono,
              iso(finished), started_mono + 3_000_000_000, 10, status, None, pages, pages + unread,
              len(rows), None, row16[2] if row16 else None, row16[5] if row16 else None,
              1 if row16 else 0, hashlib.sha256(order.encode()).hexdigest() if rows else None,
              reordered, seq_changes, None, None,
              json.dumps({'truncated': bool(unread), 'pages_unread': unread})]
    page_records = []
    for number in range(1, pages + 1):
        page_rows = [r for r in rows if r[0] == number]
        page_records.append((number, f'https://thlotto.com/member/lottery/yeekee/243?page={number}',
                             iso(started), started_mono, iso(started + timedelta(seconds=1)),
                             started_mono + 1_000_000_000, 200, len(page_rows), 1 if unread else 0,
                             hashlib.sha256(str(number).encode()).hexdigest()))
    return store.insert_snapshot(record, page_records, rows)


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name)
        self.config_path = self.state / 'phase_f.yaml'
        self.config_path.write_text(
            'phase_d_root: /Users/icy/reverse-lotto/งาน A/phase_d_account_monitoring\n'
            'phase_d_config: ' + str(Path.home() / 'Library/Application Support/ThlottoResearch/phase_d/config.yaml') + '\n'
            'state_dir: ' + str(self.state) + '\n'
            'automated_access_permitted: true\n'
            'horizons: [120, 60]\n'
            'pf_hourly_headroom: 8\n',
            encoding='utf-8')
        self.cfg = pfconfig.load(str(self.config_path))
        self.store = PFStore(self.state / 'phase_f.sqlite3')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_event_keys_are_stable_and_duplicates_get_ordinals(self):
        a = pfsession.event_key('hmac-v1:abc', '12345', '2026-11-13T22:29:50+07:00')
        b = pfsession.event_key('hmac-v1:abc', '12345', '2026-11-13T22:29:50+07:00')
        c = pfsession.event_key('hmac-v1:abc', '12345', '2026-11-13T22:29:50+07:00', 1)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(a, pfsession.event_key('hmac-v1:abc', '12346', '2026-11-13T22:29:50+07:00'))

    def test_parse_preclose_page_yields_rows_without_results(self):
        pd = pfsession._pd(self.cfg)
        html = page_html([(1, '12345'), (2, '00007'), (16, '99999')], page=2)
        parsed = pd['parse_detail'](html, 'https://thlotto.com/member/lottery/yeekee/243',
                                    b'k' * 32, self.cfg['phase_d']['selectors'], observation=True)
        self.assertFalse(parsed['published'])
        self.assertIsNone(parsed['top3'])
        self.assertIsNone(parsed['total_submissions'])
        self.assertEqual([r['seq'] for r in parsed['rows']], [1, 2, 16])
        self.assertEqual(parsed['rows'][1]['number'], '00007')
        self.assertTrue(any('page=2' in link for link in parsed['links']))

    def test_shell_parser_handles_escaped_betconfig_and_zero_rows(self):
        import html as html_module
        config = {'id': '243', 'main_type': 1, 'title': 'จับยี่กี รอบที่ 67', 'close_date': '13/11/2569 22:30:00'}
        literal = json.dumps(config, ensure_ascii=False).replace('"', '&quot;')
        shell = f'<script>var betconfig = "{literal}";</script><div class="card-title">รอบที่ 67</div>'
        parsed = pfsession.parse_observation(
            self.cfg, shell, 'https://thlotto.com/member/lottery/yeekee/243', b'k' * 32,
            {'period_id': '243', 'round_number': 67, 'index_close_at': '2026-11-13T22:30:00+07:00'})
        self.assertEqual(parsed['page_state'], 'PRE_CLOSE_SHELL')
        self.assertEqual(parsed['rows'], [])
        self.assertEqual(parsed['period_id'], '243')
        self.assertEqual(parsed['round_number'], 67)
        self.assertFalse(parsed['published'])

    def test_shell_parser_rejects_identity_mismatch(self):
        config = {'id': '243', 'title': 'จับยี่กี รอบที่ 67', 'close_date': '13/11/2569 22:30:00'}
        literal = json.dumps(config, ensure_ascii=False).replace('"', '&quot;')
        shell = f'<script>var betconfig = "{literal}";</script>'
        with self.assertRaises(Exception):
            pfsession.parse_observation(
                self.cfg, shell, 'https://thlotto.com/member/lottery/yeekee/243', b'k' * 32,
                {'period_id': '244', 'round_number': 67, 'index_close_at': '2026-11-13T22:30:00+07:00'})

    def test_snapshot_insert_and_first_seen_is_idempotent(self):
        close = datetime(2026, 11, 13, 15, 30, tzinfo=timezone.utc)
        rows = [(1, 1, '11111', '2026-11-13T22:29:50+07:00', 'hmac-v1:a', 'k1'),
                (1, 16, '99999', '2026-11-13T22:29:51+07:00', 'hmac-v1:b', 'k2')]
        sid = synthetic(self.store, close, time.monotonic_ns(), rows=rows)
        new = self.store.record_first_seen(sid, [(r[0], r[1], r[2], r[3], r[4], r[5],
                                                  '2026-11-13T15:28:01.000000Z', 1000) for r in rows])
        self.assertEqual(new, 2)
        again = self.store.record_first_seen(sid, [(r[0], r[1], r[2], r[3], r[4], r[5],
                                                    '2026-11-13T15:28:01.000000Z', 1000) for r in rows])
        self.assertEqual(again, 0)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM first_seen').fetchone()[0], 2)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM event_sequence').fetchone()[0], 2)

    def test_audit_passes_clean_snapshot(self):
        close = datetime(2026, 11, 13, 15, 30, tzinfo=timezone.utc)
        rows = [(1, seq, f'{seq:05d}', f'2026-11-13T22:29:{50 + seq % 9}+07:00', f'hmac-v1:{seq}', f'k{seq}')
                for seq in range(1, 17)]
        sid = synthetic(self.store, close, time.monotonic_ns(), rows=rows)
        self.store.record_first_seen(sid, [(r[0], r[1], r[2], r[3], r[4], r[5],
                                            '2026-11-13T15:28:01.000000Z', 1000) for r in rows])
        result = pfaudit.audit(self.store, day='2026-11-13', rnd=67)
        self.assertTrue(result['passed'], json.dumps(result, ensure_ascii=False, indent=1))

    def test_visibility_gate_blocks_pre_close_claims_with_zero_rows(self):
        close = datetime(2026, 11, 13, 15, 30, tzinfo=timezone.utc)
        synthetic(self.store, close, time.monotonic_ns(), status='OK', pages=1, rows=[])
        result = pfaudit.audit(self.store, day='2026-11-13', rnd=67)
        self.assertTrue(result['passed'], json.dumps(result['visibility'], ensure_ascii=False))
        self.assertFalse(result['pre_close_ready'])
        self.assertEqual(result['visibility']['reason'], 'no_rows_visible_before_close')

    def test_visibility_gate_allows_claims_when_rows_are_visible(self):
        close = datetime(2026, 11, 13, 15, 30, tzinfo=timezone.utc)
        rows = [(1, seq, f'{seq:05d}', f'2026-11-13T22:29:{50 + seq % 9}+07:00', f'hmac-v1:{seq}', f'k{seq}')
                for seq in range(1, 17)]
        sid = synthetic(self.store, close, time.monotonic_ns(), rows=rows)
        self.store.record_first_seen(sid, [(r[0], r[1], r[2], r[3], r[4], r[5],
                                            '2026-11-13T15:28:01.000000Z', 1000) for r in rows])
        result = pfaudit.audit(self.store, day='2026-11-13', rnd=67)
        self.assertTrue(result['passed'])
        self.assertTrue(result['pre_close_ready'])

    def test_audit_rejects_snapshot_started_after_close(self):
        close = datetime(2026, 11, 13, 15, 30, tzinfo=timezone.utc)
        sid = synthetic(self.store, close, time.monotonic_ns(), rows=[])
        self.store.db.execute("UPDATE snapshots SET started_at_utc=?, target_close_at=? WHERE snapshot_id=?",
                              (iso(close + timedelta(seconds=5)), iso(close), sid))
        self.store.db.commit()
        result = pfaudit.audit(self.store, day='2026-11-13', rnd=67)
        self.assertFalse(result['passed'])
        self.assertIn('pre_close_bound', result['failed_checks'])

    def test_audit_rejects_backdated_first_seen(self):
        close = datetime(2026, 11, 13, 15, 30, tzinfo=timezone.utc)
        rows = [(1, 1, '11111', '2026-11-13T22:29:50+07:00', 'hmac-v1:a', 'k1')]
        sid = synthetic(self.store, close, time.monotonic_ns(), rows=rows)
        self.store.record_first_seen(sid, [(1, 1, '11111', '2026-11-13T22:29:50+07:00', 'hmac-v1:a', 'k1',
                                            '2026-11-13T15:00:00.000000Z', 1)])
        result = pfaudit.audit(self.store, day='2026-11-13', rnd=67)
        self.assertFalse(result['passed'])
        self.assertIn('first_seen_prospective', result['failed_checks'])

    def test_audit_detects_unmarked_truncation_and_order_hash_drift(self):
        close = datetime(2026, 11, 13, 15, 30, tzinfo=timezone.utc)
        rows = [(1, 1, '11111', '2026-11-13T22:29:50+07:00', 'hmac-v1:a', 'k1')]
        sid = synthetic(self.store, close, time.monotonic_ns(), status='OK', pages=1, unread=2, rows=rows)
        result = pfaudit.audit(self.store, day='2026-11-13', rnd=67)
        self.assertIn('pagination_bounds', result['failed_checks'])
        self.store.db.execute("UPDATE snapshots SET status='TRUNCATED', order_hash='broken' WHERE snapshot_id=?", (sid,))
        self.store.db.commit()
        result = pfaudit.audit(self.store, day='2026-11-13', rnd=67)
        self.assertIn('order_reproducible', result['failed_checks'])

    def test_reorder_counter_is_recomputable(self):
        close = datetime(2026, 11, 13, 15, 30, tzinfo=timezone.utc)
        base = time.monotonic_ns()
        first = [(1, 1, '11111', '2026-11-13T22:29:50+07:00', 'hmac-v1:a', 'k1'),
                 (1, 2, '22222', '2026-11-13T22:29:51+07:00', 'hmac-v1:b', 'k2')]
        synthetic(self.store, close, base, rows=first, horizon=120)
        # Same events, swapped sequence numbers: a reorder, not new submissions.
        second = [(1, 2, '11111', '2026-11-13T22:29:50+07:00', 'hmac-v1:a', 'k1'),
                  (1, 1, '22222', '2026-11-13T22:29:51+07:00', 'hmac-v1:b', 'k2')]
        synthetic(self.store, close, base + 60_000_000_000, rows=second, horizon=60,
                  started_offset=60, reordered=1, seq_changes=2)
        result = pfaudit.audit(self.store, day='2026-11-13', rnd=67)
        self.assertTrue(result['passed'], json.dumps(result, ensure_ascii=False, indent=1))
        detail = next(c for c in result['checks'] if c['name'] == 'reorder_recomputable')
        self.assertTrue(detail['passed'], detail)
        stored = self.store.db.execute('SELECT seq_changes FROM snapshots WHERE horizon_seconds=60').fetchone()[0]
        self.assertEqual(stored, 2)

    def test_forecast_ledger_is_immutable(self):
        record = ('f1', '2026-11-13', 67, 120, 'A-uniform', 'PROSPECTIVE_PRE_CLOSE', None,
                  iso(datetime.now(timezone.utc)), time.monotonic_ns(), None, None, 'd' * 64, b'\x00' * 16,
                  'float32', 100000, 'c' * 64, 'dev', None, 'test')
        self.store.insert_forecast(record)
        with self.assertRaises(sqlite3.DatabaseError):
            with self.store.db:
                self.store.db.execute("UPDATE forecasts SET model_version='tampered' WHERE forecast_id='f1'")
        with self.assertRaises(sqlite3.DatabaseError):
            with self.store.db:
                self.store.db.execute("DELETE FROM forecasts WHERE forecast_id='f1'")
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM forecasts').fetchone()[0], 1)

    def test_plan_marks_missed_horizons(self):
        items = pfsession.plan(self.cfg, '2026-11-13', 67)
        self.assertEqual([i['horizon_seconds'] for i in items], [120, 60])
        for item in items:
            self.assertIn('scheduled_at_utc', item)
            self.assertIn('missed', item)

    def test_config_rejects_state_inside_repository(self):
        bad = self.state / 'bad.yaml'
        bad.write_text('phase_d_root: /Users/icy/reverse-lotto/งาน A/phase_d_account_monitoring\n'
                       'phase_d_config: ' + str(Path.home() / 'Library/Application Support/ThlottoResearch/phase_d/config.yaml') + '\n'
                       f'state_dir: {ROOT}/private\n', encoding='utf-8')
        with self.assertRaises(pfconfig.ConfigError):
            pfconfig.load(str(bad))


if __name__ == '__main__':
    unittest.main()
