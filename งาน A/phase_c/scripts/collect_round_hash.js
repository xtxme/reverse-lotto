(async () => {
  const id = __ID__;
  const rows = [];
  for (let p = 1; p <= 8; p++) {
    const res = await fetch(`/member/lottery/yeekee/${id}?page=${p}`, {credentials:'same-origin', cache:'no-store'});
    if (res.status !== 200) break;
    const html = await res.text();
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const lis = [...doc.querySelectorAll('ul.number-key-list > li')];
    if (!lis.length) break;
    for (const li of lis) {
      const seq = parseInt(li.querySelector('.no')?.textContent.trim(), 10);
      const num = (li.querySelector('.key')?.textContent || '').replace(/\s+/g, '');
      const ts = (li.innerText.match(/(\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2})/) || [])[1] || null;
      const user = (li.querySelector('.username')?.innerText || '').trim();
      if (seq && /^\d{5}$/.test(num)) rows.push({seq, num, ts, user});
    }
    if (lis.length < 50) break;
  }
  const users = [...new Set(rows.map(r => r.user))];
  const map = {};
  for (const u of users) {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('phase_c:' + u));
    map[u] = [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 16);
  }
  return JSON.stringify({id, rows: rows.map(r => ({seq:r.seq, num:r.num, ts:r.ts, uh:map[r.user]}))});
})()
