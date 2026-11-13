"""Pre-close snapshot capture.

Rules enforced here:
  * the browser profile is Phase D's, opened only while holding Phase D's
    worker.lock, so collection and snapshots can never run at the same time;
  * every document read is reserved in Phase D's own request ledger, and a
    headroom check keeps capacity free for round collection and recovery;
  * each page read keeps its own UTC and monotonic interval;
  * first-seen times come from the response that actually showed the row, never
    from displayed_created_at;
  * pagination bounds and sequence reordering are recorded per snapshot.
"""
from __future__ import annotations

import fcntl
import hashlib
import html as html_module
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

_MODULES = {}


def _pd(cfg):
    if _MODULES:
        return _MODULES
    root = cfg['phase_d_root']
    if root not in sys.path:
        sys.path.insert(0, root)
    from collector.core import Stop, allowed_url, close_at, day_for, digest, now, parse_time, pseudonym, stamp
    from collector.browser import Browser, check_response, parse_detail
    from storage import Store
    _MODULES.update(dict(Stop=Stop, allowed_url=allowed_url, close_at=close_at, day_for=day_for, digest=digest,
                         now=now, parse_time=parse_time, pseudonym=pseudonym, stamp=stamp, Browser=Browser,
                         check_response=check_response, parse_detail=parse_detail, Store=Store))
    return _MODULES


def utcnow():
    return datetime.now(timezone.utc)


def utc(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def read_identity(cfg, day, rnd):
    """Read the saved period/source identity from Phase D (read-only)."""
    db = Path(cfg['phase_d_state']) / 'research.sqlite3'
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute('SELECT period_id,source_url FROM rounds WHERE trading_day=? AND round_number=?',
                          (day, rnd)).fetchone()
        evidence = con.execute('SELECT * FROM round_identity_evidence WHERE trading_day=? AND round_number=?',
                               (day, rnd)).fetchone()
        halt = con.execute("SELECT value FROM control WHERE key='halt'").fetchone()
    finally:
        con.close()
    if not row or not row['period_id'] or not row['source_url']:
        return None
    identity = {'period_id': str(row['period_id']), 'source_url': row['source_url'],
                'round_number': int(rnd), 'trading_day': day}
    if evidence:
        identity.update({k: evidence[k] for k in ('period_id', 'source_url', 'index_close_at')})
        identity['period_id'] = str(identity['period_id'])
    identity['halt'] = halt[0] if halt else None
    return identity


def acquire_lock(path, timeout_seconds):
    """Blocking-with-deadline flock on Phase D's worker lock."""
    handle = Path(path).open('a')
    started = time.monotonic()
    while True:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle, int((time.monotonic() - started) * 1000)
        except BlockingIOError:
            if time.monotonic() - started >= timeout_seconds:
                handle.close()
                return None, int((time.monotonic() - started) * 1000)
            time.sleep(0.2)


def budget_headroom(pd_store, cfg_pd, reserve=4, cost=1):
    """Never consume the last `reserve` requests of Phase D's hourly ledger."""
    from collector.core import now as _now, stamp as _stamp
    used = pd_store.db.execute('SELECT COUNT(*) FROM requests WHERE requested_at>=?',
                               (_stamp(_now() - timedelta(hours=1)),)).fetchone()[0]
    budget = int(cfg_pd['hourly_request_budget'])
    ceiling = budget - int(reserve)
    return used + int(cost) <= ceiling, used, ceiling


def displayed_total(html, selectors):
    """Best-effort read of the page's own \"N of M\" counter (never used for first-seen)."""
    from bs4 import BeautifulSoup
    spec = (selectors or {}).get('total_submissions')
    if not spec:
        return None
    css = spec['css'] if isinstance(spec, dict) else spec
    extract = spec.get('extract') if isinstance(spec, dict) else None
    for node in BeautifulSoup(html, 'html.parser').select(css):
        text = node.get_text(' ', strip=True)
        match = re.fullmatch(extract, text) if extract else re.search(r'([0-9][0-9,]*)\s*$', text)
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except ValueError:
                return None
    return None


def event_key(display_hash, number, created_at, ordinal=0):
    base = hashlib.sha256(f'{display_hash}\x1f{number}\x1f{created_at}'.encode()).hexdigest()
    return base if ordinal == 0 else f'{base}#{ordinal}'


def fetch_page(browser, url, pd):
    """One document read with explicit UTC + monotonic bounds.

    Mirrors Phase D's Browser.get() guards; the route handler installed by
    Browser still enforces spacing and the shared request reservation.
    """
    path = urlparse(url).path
    detail = re.fullmatch(r'/member/lottery/yeekee/(\d+)', path)
    if not (pd['allowed_url'](url) or (detail and pd['allowed_url'](url, detail.group(1)))):
        raise pd['Stop']('ACCESS_BLOCKED', 'url_not_allowed')
    browser.failure = None
    started_utc = utcnow()
    started_mono = time.monotonic_ns()
    try:
        response = browser.page.goto(url, wait_until='domcontentloaded', timeout=30000)
        html = browser.page.content()
        status = response.status if response else 0
        headers = dict(response.headers) if response else {}
        pd['check_response'](status, browser.page.url, html)
    except pd['Stop']:
        raise
    except Exception:
        if browser.failure:
            raise browser.failure
        if 'login' in browser.page.url:
            raise pd['Stop']('AUTH_REQUIRED', 'login_required')
        raise pd['Stop']('COLLECTION_ERROR', 'navigation_failed')
    received_utc = utcnow()
    received_mono = time.monotonic_ns()
    return {
        'url': url,
        'html': html,
        'status': status,
        'headers': headers,
        'started_utc': started_utc,
        'started_mono': started_mono,
        'received_utc': received_utc,
        'received_mono': received_mono,
    }


def read_pages(cfg, pd, store_pd, browser, base_url, identity, close_at, deadline_mono):
    """Read page 1 and every same-round page link, within bounds and deadline."""
    pages = []
    rows = []
    links = set()
    read_urls = set()
    truncated = False
    queue = [base_url]
    seen_counts = {}
    captured_total = [None]
    page_state = [None]
    page_no = 0
    while queue:
        url = queue.pop(0)
        if url in read_urls:
            continue
        if time.monotonic() >= deadline_mono:
            truncated = True
            break
        page_no += 1
        fetched = fetch_page(browser, url, pd)
        parsed = parse_observation(cfg, fetched['html'], url, store_pd.key(), identity)
        if page_no == 1:
            page_state[0] = parsed.get('page_state')
            total = displayed_total(fetched['html'], cfg['phase_d']['selectors'])
            if total is not None:
                captured_total[0] = total
        links.update(parsed['links'])
        page_rows = []
        for item in parsed['rows']:
            base_key = event_key(item['display_hash'], item['number'], item['created_at'])
            ordinal = seen_counts.get(base_key, 0)
            seen_counts[base_key] = ordinal + 1
            key = event_key(item['display_hash'], item['number'], item['created_at'], ordinal)
            page_rows.append((item['page'], item['seq'], item['number'], item['created_at'], item['display_hash'], key))
        rows.extend(page_rows)
        read_urls.add(url)
        content_hash = hashlib.sha256(json.dumps(
            [[r[1], r[2], r[3], r[4]] for r in page_rows], ensure_ascii=False).encode()).hexdigest()
        pages.append((page_no, url, utc(fetched['started_utc']), fetched['started_mono'],
                      utc(fetched['received_utc']), fetched['received_mono'], fetched['status'],
                      len(page_rows), 1 if any(link not in read_urls and link != url for link in links) else 0,
                      content_hash))
        for link in sorted(links):
            if link not in read_urls and link not in queue:
                queue.append(link)
        if page_no >= cfg['max_pages']:
            truncated = truncated or bool(queue)
            break
    return pages, rows, len(links), truncated, captured_total[0], page_state[0]


def capture(cfg, store, day, rnd, horizon, live=False):
    """Capture one pre-close snapshot. Returns a JSON-serialisable report."""
    pd = _pd(cfg)
    close_at = pd['close_at'](day, rnd)
    scheduled = close_at - timedelta(seconds=horizon)
    started_utc = utcnow()
    started_mono = time.monotonic_ns()
    report = {
        'trading_day': day, 'round_number': rnd, 'horizon_seconds': horizon,
        'target_close_at': pd['stamp'](close_at), 'scheduled_at_utc': utc(scheduled),
        'started_at_utc': utc(started_utc),
    }
    record = [day, rnd, None, horizon, pd['stamp'](close_at), utc(scheduled), utc(started_utc), started_mono,
              None, None, None, 'FAILED', None, 0, 0, 0, None, None, None, None, None, None, None, None, None, None]
    if not live:
        report.update({'status': 'DRY_RUN', 'would_request': None})
        return report, None, [], []

    identity = read_identity(cfg, day, rnd)
    if not identity or not identity.get('period_id'):
        record[11] = 'NO_IDENTITY'
        record[12] = 'round_identity_missing'
        sid = store.insert_snapshot(record, [], [])
        report.update({'status': 'NO_IDENTITY', 'reason': 'round_identity_missing'})
        return report, sid, [], []
    if identity.get('halt'):
        record[11] = 'HALTED'
        record[12] = 'phase_d_halted'
        sid = store.insert_snapshot(record, [], [])
        report.update({'status': 'HALTED', 'reason': 'phase_d_halted'})
        return report, sid, [], []
    record[2] = identity['period_id']

    lock, wait_ms = acquire_lock(cfg['worker_lock'], cfg['lock_timeout_seconds'])
    record[10] = wait_ms
    if not lock:
        record[11] = 'LOCK_TIMEOUT'
        record[12] = 'worker_busy'
        record[8] = utc(utcnow())
        record[9] = time.monotonic_ns()
        sid = store.insert_snapshot(record, [], [])
        report.update({'status': 'LOCK_TIMEOUT', 'lock_wait_ms': wait_ms})
        return report, sid, [], []

    pages, rows, available, truncated, total_displayed = [], [], 0, False, None
    page_state = None
    status, error = 'OK', None
    try:
        store_pd = pd['Store'](Path(cfg['phase_d_state']) / 'research.sqlite3')
        try:
            allowed, used, ceiling = budget_headroom(store_pd, cfg['phase_d'], cfg.get('pf_reserve_requests', 4), cost=1)
            if not allowed:
                record[11] = 'BUDGET'
                record[12] = 'shared_hourly_budget_headroom'
                record[8] = utc(utcnow())
                record[9] = time.monotonic_ns()
                sid = store.insert_snapshot(record, [], [])
                report.update({'status': 'BUDGET', 'used_last_hour': used, 'ceiling': ceiling})
                return report, sid, [], []
            remaining = (close_at - pd['now']()).total_seconds() - cfg['deadline_safety_seconds']
            # Always leave at least a small budget for the first page: a snapshot that
            # starts inside the safety margin must still record what was visible.
            deadline_mono = time.monotonic() + max(2.0, remaining)
            with pd['Browser'](store_pd, cfg['phase_d']) as browser:
                pages, rows, available, truncated, total_displayed, page_state = read_pages(
                    cfg, pd, store_pd, browser, identity['source_url'], identity, close_at, deadline_mono)
        finally:
            store_pd.close()
        status = 'TRUNCATED' if truncated or (available + 1) > len(pages) else 'OK'
    except pd['Stop'] as exc:
        status, error = 'FAILED', exc.category
        report['error_category'] = exc.category
    except Exception as exc:  # noqa: BLE001 - category only, never a message with data
        status, error = 'FAILED', type(exc).__name__
        report['error_category'] = type(exc).__name__
    finally:
        if lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_UN)
            finally:
                lock.close()

    rows_by_seq = {}
    for row in rows:
        rows_by_seq.setdefault(row[1], row)
    row16 = rows_by_seq.get(16)
    order_payload = '\n'.join(f'{r[1]}:{r[5]}' for r in sorted(rows, key=lambda r: r[1]))
    order_hash = hashlib.sha256(order_payload.encode()).hexdigest() if rows else None
    content_hash = hashlib.sha256(json.dumps(
        [[p[0], p[1], p[7], p[9]] for p in pages] + [[r[1], r[2], r[3], r[4]] for r in rows],
        ensure_ascii=False).encode()).hexdigest() if rows else None

    previous = store.previous_snapshot(day, rnd, started_mono)
    reordered, seq_changes = None, None
    if previous is not None and rows:
        prior = {r['event_key']: r['observed_seq'] for r in store.db.execute(
            'SELECT event_key,observed_seq FROM snapshot_rows WHERE snapshot_id=?', (previous['snapshot_id'],))}
        moved = sum(1 for r in rows if r[5] in prior and prior[r[5]] != r[1])
        reordered, seq_changes = (1 if moved else 0), moved

    record[8] = utc(utcnow())
    record[9] = time.monotonic_ns()
    record[11], record[12] = status, error
    record[13], record[14], record[15] = len(pages), available + 1 if pages else 0, len(rows)
    record[16] = total_displayed
    record[17] = row16[2] if row16 else None
    record[18] = row16[5] if row16 else None
    record[19] = 1 if row16 else 0
    record[20], record[21], record[22], record[23] = order_hash, reordered, seq_changes, content_hash
    record[25] = json.dumps({'truncated': truncated, 'pages_unread': max(0, available + 1 - len(pages)),
                             'page_state': page_state}, ensure_ascii=False)

    notes = report.get('notes')
    sid = store.insert_snapshot(record, pages, rows)
    new = store.record_first_seen(sid, [(r[0], r[1], r[2], r[3], r[4], r[5],
                                         pages[min(r[0], len(pages)) - 1][4],
                                         pages[min(r[0], len(pages)) - 1][5]) for r in rows])
    report.update({
        'status': status,
        'snapshot_id': sid,
        'pages_read': len(pages),
        'pages_available': available + 1 if pages else 0,
        'rows_visible': len(rows),
        'row16_seq_present': bool(row16),
        'row16_number': row16[2] if row16 else None,
        'reordered_from_previous': reordered,
        'seq_changes': seq_changes,
        'first_seen_new': new,
        'lock_wait_ms': wait_ms,
        'truncated': truncated,
    })
    if notes:
        report['notes'] = notes
    return report, sid, pages, rows


def extract_betconfig(html):
    """Read betconfig from a script assignment or a Vue attribute, escaped or raw."""
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all(True):
        for name, value in (tag.attrs or {}).items():
            if 'betconfig' not in name.lower():
                continue
            raw_value = value if isinstance(value, str) else ' '.join(value)
            for candidate in (raw_value, html_module.unescape(raw_value)):
                try:
                    parsed = json.loads(candidate)
                except (ValueError, TypeError):
                    continue
                if isinstance(parsed, dict):
                    return parsed
    for script in soup.find_all('script'):
        text = script.string or script.get_text()
        match = re.search(r'betconfig\s*=\s*', text)
        if not match:
            continue
        raw = text[match.end():].lstrip()
        try:
            value, _ = json.JSONDecoder().raw_decode(raw)
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(html_module.unescape(value))
            except (ValueError, TypeError):
                continue
    return None


def parse_rows(html, url, key, pd):
    """Same row contract as Phase D's parser, reused for the pre-close shell."""
    soup = BeautifulSoup(html, 'html.parser')
    rows = []
    for item in soup.select('ul.number-key-list > li'):
        seq = item.select_one('.no')
        number = item.select_one('.key')
        mask = item.select_one('.username')
        timestamp = re.search(r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}', item.get_text(' ', strip=True))
        if not (seq and number and mask and timestamp):
            raise pd['Stop']('PARTIAL', 'row_layout_unknown')
        page = int(parse_qs(urlparse(url).query).get('page', ['1'])[0])
        rows.append(dict(seq=int(seq.get_text(strip=True).rstrip('.')), number=number.get_text('', strip=True),
                         created_at=pd['stamp'](pd['parse_time'](timestamp.group(0))),
                         display_hash=pd['pseudonym'](key, mask.get_text(strip=True)),
                         page=page))
    return rows


def parse_observation(cfg, html, url, key, identity):
    """Parse either a fully rendered page (Phase D path) or the pre-close shell.

    The pre-close shell has an HTML-escaped betconfig and no submission list; it is
    a valid observation of "page reachable, zero rows visible", not a failure.
    """
    pd = _pd(cfg)
    selectors = cfg['phase_d']['selectors']
    try:
        parsed = pd['parse_detail'](html, url, key, selectors, observation=True, index_identity=identity)
        parsed['page_state'] = 'PUBLISHED' if parsed.get('published') else 'ROWS_VISIBLE'
        return parsed
    except pd['Stop'] as exc:
        if exc.category != 'unrecognized_betconfig_layout':
            raise
    config = extract_betconfig(html)
    if not isinstance(config, dict):
        raise pd['Stop']('PARTIAL', 'no_betconfig_and_no_shell')
    title = str(config.get('title', ''))
    match = re.fullmatch(r'จับยี่กี\s+รอบที่\s+(\d+)', title)
    if not match or not 1 <= int(match.group(1)) <= 88:
        raise pd['Stop']('CONFLICT', 'wrong_product_title')
    close = pd['stamp'](pd['parse_time'](config['close_date']))
    period = str(config['id'])
    if not pd['allowed_url'](url, period):
        raise pd['Stop']('CONFLICT', 'unexpected_detail_url')
    if identity:
        if str(identity.get('period_id')) != period or int(match.group(1)) != int(identity.get('round_number', match.group(1))):
            raise pd['Stop']('CONFLICT', 'shell_identity_mismatch')
        if identity.get('index_close_at') and pd['stamp'](pd['parse_time'](identity['index_close_at'])) != close:
            raise pd['Stop']('CONFLICT', 'shell_close_mismatch')
    rows = parse_rows(html, url, key, pd)
    links = set()
    for anchor in BeautifulSoup(html, 'html.parser').select('a[href]'):
        target = urljoin(url, anchor['href'])
        if pd['allowed_url'](target, period):
            if parse_qs(urlparse(target).query).get('page') == ['1']:
                target = target.split('?')[0]
            links.add(target)
    return dict(product='yeekee88', period_id=period, round_number=int(match.group(1)), betting_close_at=close,
                published=False, total_submissions=None, total_sum=None, row16=None, rows=rows,
                links=sorted(links), observed_at=pd['stamp'](pd['now']()), page_state='PRE_CLOSE_SHELL')


def smoke(cfg, store, day, rnd):
    """One read-only page fetch through the shared lock/budget. Writes nothing."""
    pd = _pd(cfg)
    identity = read_identity(cfg, day, rnd)
    if not identity or not identity.get('period_id'):
        return {'status': 'NO_IDENTITY'}
    if identity.get('halt'):
        return {'status': 'HALTED', 'halt': identity['halt']}
    lock, wait_ms = acquire_lock(cfg['worker_lock'], cfg['lock_timeout_seconds'])
    if not lock:
        return {'status': 'LOCK_TIMEOUT', 'lock_wait_ms': wait_ms}
    try:
        store_pd = pd['Store'](Path(cfg['phase_d_state']) / 'research.sqlite3')
        try:
            allowed, used, ceiling = budget_headroom(store_pd, cfg['phase_d'], cfg.get('pf_reserve_requests', 4), cost=1)
            if not allowed:
                return {'status': 'BUDGET', 'used_last_hour': used, 'ceiling': ceiling}
            with pd['Browser'](store_pd, cfg['phase_d']) as browser:
                fetched = fetch_page(browser, identity['source_url'], pd)
                parsed = parse_observation(cfg, fetched['html'], identity['source_url'], store_pd.key(), identity)
        finally:
            store_pd.close()
        return {
            'status': 'OK',
            'period_id': parsed['period_id'],
            'round_number': parsed['round_number'],
            'betting_close_at': parsed['betting_close_at'],
            'published_at_read': parsed['published'],
            'rows_on_page': len(parsed['rows']),
            'page_links': len(parsed['links']),
            'first_seq': parsed['rows'][0]['seq'] if parsed['rows'] else None,
            'last_seq': parsed['rows'][-1]['seq'] if parsed['rows'] else None,
            'row16_visible': any(r['seq'] == 16 for r in parsed['rows']),
            'lock_wait_ms': wait_ms,
            'budget_used_last_hour': used,
            'budget_ceiling': ceiling,
            'request_interval_ms': int((fetched['received_mono'] - fetched['started_mono']) / 1e6),
        }
    except pd['Stop'] as exc:
        return {'status': 'FAILED', 'error_category': exc.category}
    except Exception as exc:  # noqa: BLE001
        return {'status': 'FAILED', 'error_category': type(exc).__name__}
    finally:
        try:
            fcntl.flock(lock, fcntl.LOCK_UN)
        finally:
            lock.close()


def plan(cfg, day, rnd, horizons=None):
    pd = _pd(cfg)
    close_at = pd['close_at'](day, rnd)
    now = pd['now']()
    items = []
    for horizon in (horizons or cfg['horizons']):
        due = close_at - timedelta(seconds=horizon)
        items.append({
            'horizon_seconds': horizon,
            'target_close_at': pd['stamp'](close_at),
            'scheduled_at_utc': utc(due),
            'scheduled_at_bangkok': pd['stamp'](due),
            'seconds_from_now': round((due - now).total_seconds(), 1),
            'missed': due < now - timedelta(seconds=5),
        })
    return items


def sleep_until(target):
    delta = (target - utcnow()).total_seconds()
    if delta > 0:
        time.sleep(delta)


def run_session(cfg, store, day, rnd, horizons=None, live=False, settle_seconds=1.0):
    pd = _pd(cfg)
    close_at = pd['close_at'](day, rnd)
    results = []
    if not live:
        return [{**item, 'status': 'DRY_RUN'} for item in plan(cfg, day, rnd, horizons)]
    for item in plan(cfg, day, rnd, horizons):
        horizon = item['horizon_seconds']
        due = close_at - timedelta(seconds=horizon)
        if due < utcnow() - timedelta(seconds=2):
            results.append({'horizon_seconds': horizon, 'status': 'SKIPPED_LATE'})
            continue
        sleep_until(due)
        if utcnow() >= close_at:
            results.append({'horizon_seconds': horizon, 'status': 'SKIPPED_AFTER_CLOSE'})
            continue
        report, _, _, _ = capture(cfg, store, day, rnd, horizon, live=live)
        results.append(report)
        if settle_seconds:
            time.sleep(settle_seconds)
    return results
