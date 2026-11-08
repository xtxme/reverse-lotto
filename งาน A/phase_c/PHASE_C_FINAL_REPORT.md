# PHASE C — Final Report
## THLotto Yeekee: Historical Access & Submission Pattern Audit

วันที่: 2026-11-07/08 (Asia/Bangkok)
Target: `https://thlotto.com/member/lottery/yeekee`
Repo ปลายทาง: `https://github.com/xtxme/reverse-lotto` → `phase_c/`

---

## บทสรุปผู้บริหาร (Thai)

Phase C ตรวจ 5 เรื่องต่อจาก Phase A/B และเก็บข้อมูลเพิ่มเป็น **16 รอบ (period 229–244, rounds 53–68) จำนวน 2,474 แถว** โดยเก็บเฉพาะ hash ของ masked username ไม่เก็บชื่อดิบ

ผลสำคัญ:

1. **53-result dataset เป็น snapshot แน่นอน** — grid เดียวกันแสดง 51 ผลเวลา 18:58, 53 เวลา 19:23, 59 เวลา 20:55, 62 เวลา 21:30, 71 เวลา 23:49 และ 72 เวลา 00:00:37
2. **สินค้า 88 รอบไม่มี historical archive ใน UI ปกติ** — หน้า main ไม่มี date filter; หน้า result มี date filter แต่สินค้า 88 รอบแสดงเพียงรอบล่าสุด (รอบ 72) ทุกวันที่ที่ทดสอบ; สินค้า 264 รอบ (จับยี่กีทันใจ) มี history ตามวันที่ แต่เป็นคนละสินค้า
3. **Oldest date ที่ยืนยันได้:** 88 รอบ = 2026-11-07 (current day เท่านั้น); 264 รอบ = 2026-01-01 (comparison only) — **ห้ามใช้แทน retention ของ 88 รอบ**
4. **13 inversions ที่รายงานเดิมยืนยันครบ** — เพิ่มอีก 5 รวมเป็น 18 ใน 16 รอบ; ทุกอันเป็น +1 วินาที; ลำดับไม่ใช่ timestamp strictly desc และไม่ใช่เลข ascending/descending ภายในวินาที
5. **Row 16 อยู่ในกลุ่ม +119s ทั้ง 16/16 รอบ** — ความน่าจะเป็นแบบสุ่มประมาณ 4.3×10^-9
6. **Duplicate groups เป็น same-user 94/104 (90.4%)** — permutation p<1e-4; ไม่ใช่ same-second (0/104)
7. **Burst +103/+119 เป็น multi-user/multi-number** — user overlap ระหว่างสอง burst ไม่เกิน chance ใน 15/16 รอบ; round 59 p=0.011 ไม่รอด multiple-testing correction
8. **REA ยืนยัน runtime:** หน้า detail มี list-number request 1 ครั้งใน 65s; หน้า list ไม่มี network request ใน 70s; main.js hash ตรงกับ Phase B
9. **Cross-day persistence: UNTESTABLE** — ไม่มี historical 88-round data; ต้องรายงานเป็น UNKNOWN/ACCESS BLOCKED ไม่ใช่ “persistent” หรือ “manipulated”
10. **ไม่มีหลักฐานว่า account repetition หรือ bursts บ่งชี้ manipulation หรือทำนายผลได้**

---

## 1. วิธีวิจัยและขอบเขต

- Audit หลักฐาน Phase A/B และรันสคริปต์ reproducibility เดิม
- เก็บข้อมูลใหม่ read-only จากหน้าเว็บปกติ:
  - main grid `/member/lottery/yeekee`
  - round detail `/member/lottery/yeekee/{periodId}` (period 229–244)
  - results page `/member/lottery/result?date=...`
- เก็บเฉพาะ `round, period_id, seq, number, timestamp, user_hash`; `user_hash` = SHA-256 ของ masked display name พร้อม prefix คงที่ `phase_c:` ตัด 16 hex
- ไม่เก็บ username ดิบ, password, token, cookie
- ไม่ส่งเลข, ไม่แทง, ไม่เดิมพัน, ไม่ bypass auth, ไม่ probe endpoint ที่ไม่มีเอกสาร
- 16 รอบ: 53–68 (period 229–244); 2,474 แถว
- วันที่: 2026-11-07 ต่อเนื่องถึง 2026-11-08 00:00 (lottery day ยังไม่จบ)

ข้อจำกัด session: single active session; session หลุดหลายครั้ง; re-login ทุกครั้ง ไม่มีการเดาข้อมูล

---

## 2. Task 1 — Historical Data Availability

### 2.1 53-result dataset เป็น snapshot

| เวลา | จำนวนผล | รอบล่าสุด |
|---|---:|---|
| 18:58 | 51 | 51 |
| 19:23 | 53 | 53 |
| 20:55 | 59 | 59 |
| 21:30 | 62 | 62 |
| 23:49 | 71 | 71 |
| 00:00:37 (8 พ.ย.) | 72 | 72 |

**OBSERVED:** 53 เป็น snapshot ของเวลานั้น ไม่ใช่ชุดคงที่

### 2.2 หน้า main 88 รอบ

- ไม่มี date input, ไม่มี archive/history link
- `?date=01/11/2569` หรือ `?date=06/11/2569` ให้ผลเหมือนเดิม (71 ผล ณ ตอนทดสอบ) — parameter ถูก ignore
- ณ 00:00:37 ยังแสดง 72 ผล (รอบ 1–72) และ pending รอบ 73–75 → **ไม่ reset ตอนเที่ยงคืน**; lottery day ต่อเนื่อง

### 2.3 หน้า results และ date filter

ทดสอบ `07/11/2569`, `06/11/2569`, `01/11/2569`, `01/10/2569`, `01/01/2569`:

- **88 รอบ:** แสดงเพียง `จับยี่กี รอบที่ 72` (latest) ทุกวันที่ → **ไม่มี per-date archive**
- **264 รอบ (จับยี่กีทันใจ):** เปลี่ยนตามวันที่ และแสดง 355 บรรทัด รวม rounds 1–214 → มี history แต่เป็นคนละสินค้า

**OBSERVED:** date filter มีอยู่จริง แต่ไม่ให้ history ของ 88 รอบ

### 2.4 Datepicker

```js
$('.input-group.date').datepicker({
  format: "dd/mm/yyyy", thaiyear: true, language: "th",
  todayHighlight: true, endDate: '+1d', autoclose: true,
  todayBtn: "linked"
});
```

- ไม่มี `startDate`
- `endDate: '+1d'`
- UI รับวันที่ย้อนหลังได้ แต่ไม่เปิดเผย retention

### 2.5 Oldest/newest ที่ยืนยันได้

| Product | Oldest verified | Newest verified | Meaning |
|---|---|---|---|
| 88 รอบ | 2026-11-07 | 2026-11-07 | current day only |
| 264 รอบ (comparison) | 2026-01-01 | 2026-11-07 | per-date history, คนละสินค้า |

**สำคัญ:** 2026-01-01 เป็นของ 264 รอบ ไม่ใช่ 88 รอบ; **actual database retention ของ 88 รอบ = UNKNOWN**

### 2.6 404 และประวัติ submission

- period เก่า 83, 84, 170, 171 → **HTTP 404**
- period ปัจจุบัน 236–244, 249 → 200 และเข้าถึง submission list ได้
- route มีอยู่จริง; สาเหตุ 404 เป็น **UNKNOWN** (pruning/retention/access scope)
- สำหรับ 88 รอบ: result history และ submission history ถูกจำกัดที่ **current day เท่ากัน**

### 2.7 All 88 หลังจบวัน?

- ณ 00:00:37 มี 72/88; รอบ 73–88 ยังไม่จบ
- คาดว่าจะครบ 88 ตอน 03:45 แต่ **ไม่ได้ observe โดยตรง**
- ไม่มี archive ให้ตรวจหลัง reset
- สถานะ: **INFERRED / UNKNOWN** (ไม่ใช่ OBSERVED)

### 2.8 ACCESS BLOCKED

- ไม่มี completed-day snapshot
- ไม่มี historical 88-round submission list
- ไม่มี retention metadata
- ไม่มี server-side archive route (ไม่เดา/ไม่ probe)

ไฟล์: `HISTORICAL_AVAILABILITY.md`, `HISTORICAL_ACCESS_MATRIX.csv`

---

## 3. Task 2 — Masked Account Pattern Audit

### 3.1 ข้อมูล

- 16 รอบ, 2,474 แถว
- **469 distinct masked hashes**
- **286/469 (61.0%) ปรากฏใน ≥2 รอบ**
- 2 hashes ปรากฏใน 16/16 รอบ; 1 ใน 15; 1 ใน 14
- 19 same-hash + same-number pairs ปรากฏใน ≥2 รอบ:
  - `85858` 6 รอบ, `11111` 6 รอบ, `52525` 5 รอบ, `37553` 4 รอบ, `55014` 4 รอบ

### 3.2 Within-round repetition

- ทุกรอบมี 38–68 ผู้ใช้ที่ส่ง ≥2 แถว
- max rows/user: 2–8 ในรอบปกติ; **16 แถวในรอบ 62**
- distinct hashes/รอบ: 88–104 (mean 95.7)

### 3.3 Duplicate ownership

| Metric | Value |
|---|---:|
| Duplicate groups | 104 |
| Duplicate entries | 120 |
| Colliding pairs | 138 |
| Same-user groups | **94 (90.4%)** |
| Mixed | 4 |
| All-different | 6 |
| Groups all in same second | **0/104** |
| Pairs same second | 3/138 (2.2%) |

Permutation test (shuffle user labels within each round, preserve numbers and user row counts):

- Observed same-user groups: **94**
- Null mean: **0.56**, SD 0.74, max 6 (10,000 permutations)
- **P(null ≥ 94) < 1e-4**

**OBSERVED:** same-user duplicate repetition is far above chance; it is not a byproduct of high-volume users.

### 3.4 Burst composition

- +103 burst: rows = distinct users in **16/16** rounds
- +119 burst: rows = distinct users in **14/16** (rounds 59, 64 have one user with 2 rows)
- Number intersection between bursts: 0–2
- User overlap: 12–41; Jaccard 0.16–0.554

Hypergeometric test per round:

- Only round 59 p=0.011
- Other 15 rounds p>0.2 (many near 1.0)
- After 16-test correction: **not significant**

**Negative finding:** the two bursts are generally **not** the same users more than chance. The overlap is mostly explained by the large active-user base.

### 3.5 Outlier round 62

One masked hash submitted **16 rows**:

- 14 unique numbers, 2 duplicate entries
- Includes `66666` ×3, `77777`, `55555`, `88888`, `99999`
- Timestamps every ~16–18 seconds (some 30/64s gaps), from 21:11:15 to 21:16:59
- One row in +103, one in +119

Consistent with a scripted cadence, but one identifier/one round → **HYPOTHESIS**, not proof. No identification attempted.

### 3.6 Masked-name collisions

- Mask format preserves prefix/suffix; different accounts can render the same mask
- 469 = distinct masked display identifiers, not verified persons
- True account count ≥469; exact UNKNOWN
- No reversal/de-anonymization attempted

### 3.7 Cross-date

- Phase C has only one lottery day
- 88-round history unavailable
- Cross-date comparison: **UNTESTABLE / ACCESS BLOCKED**
- 264-round history not used as a proxy

### 3.8 Reproducibility

```bash
cd phase_c
python3 scripts/build_c_dataset.py
python3 scripts/account_pattern_audit.py
```

Input: `evidence/combined_events.csv` (hash-only). Output: `evidence/c_account_patterns.json`, `c_account_summary.csv`, `c_same_user_duplicates.csv`, `evidence/c_burst_overlap.csv`.

ไฟล์: `MASKED_ACCOUNT_PATTERN_AUDIT.md`

---

## 4. Task 3 — Submission Ordering

### 4.1 13 inversions

Phase B 7-round dataset: **13 adjacent pairs** where the next row is **newer** by 1 second. **VERIFIED exactly.**

Additional rounds 60–68 add **5** more; total 16 rounds = **18 inversions**, all **+1 s**.

Rate: 18 / 2,458 adjacent pairs = **0.73%**.

### 4.2 Pattern

- All inversions are +1 second; none are 2+ seconds.
- Timestamps cluster at **19→20** and **39→40** second boundaries; one **42→43** (round 56).
- Inversion pairs have **different users** and **different numbers**.
- Not explained by a user or numeric tie.

### 4.3 Is order consistent with an observable field?

| Candidate | Evidence | Verdict |
|---|---|---|
| `created_at` desc | 18 one-second inversions | **Almost**, not strict |
| Number asc/desc within a second | 164 groups: 28 asc, 28 desc, **108 neither** | **Rejected** |
| Masked user | Inversion pairs differ | **Rejected** |
| Seq/row number | Contiguous and stable | Trivial |
| Internal ID/batch sequence | Not exposed | **UNKNOWN** |

Ordering is stable across repeated fetches and pagination is contiguous, but the internal tie-break key is **UNKNOWN**.

### 4.4 Row 16 = +119s group

Across **16/16** rounds, display row 16 is in the **+119-second** group.

If row 16 were random, probability ≈ **4.3×10^-9**.

This confirms: the “16th number” is chosen from the final-second batch, not known before the final second.

### 4.5 Implication

- Row 16 is not the 16th chronological submission; it is the 16th row of the newest-first table.
- At betting close, the pool has only 0–5 rows (Phase B), so row 16 does not exist.
- Pre-cutoff computation remains impossible.

ไฟล์: `SUBMISSION_ORDERING_AUDIT.md`

---

## 5. Task 4 — Independent REA Verification

### 5.1 Operations and evidence IDs

| ID | Operation | Evidence ID | Confirmed |
|---|---|---|---|
| REA-C01 | `list_browser_targets` | `ev_f36b5417bcbc318aefdf575c28184557d2a00ed03b78a358318a39be4a2c7a1d` | live page target on `https://thlotto.com` |
| REA-C02 | `inspect_web_page` 65s on `/member/lottery/yeekee/249` | `ev_942135b8ad6c196646ea89acb139556bdce4f33389bd9b27a87996868c9005da` | one `yeekee-list-number` request during 65s; no WebSocket; storage key `pusherTransportTLS` |
| REA-C03 | `analyze_web_bundle` | `ev_84dfc67f4d52f13250f877cf030712a949d5db99edf74ee7a9d38731fc3637db` | 12 scripts; `main.js` 1,042,206 bytes SHA-256 `74ed...`; POST `/member/lottery/yeekee` candidate; route family |
| REA-C04 | `capture_web_screenshot` | `ev_f38aea83b8cf8d9a1f7ad902128a61ee30d309750d97e72a1739e4a64282088c` | visible round page viewport |
| REA-C05 | `list_browser_targets` | `ev_869c097d56a22e137a7754e09ad08faf93a23d63c30107d33e40f47f0bd49b50` | live target on `/member/lottery/yeekee` |
| REA-C06 | `inspect_web_page` 70s on main list | `ev_1113b5a09f78f11e9666d6225c583bad29b5d1b151aa252a4b4b2356790499f1` | **zero allowed-origin network requests** during 70s |

### 5.2 What REA confirmed

- exact origin/routes;
- round-detail page performs a sparse XHR poll (one request in 65s), not per-second polling;
- list page performs no allowed-origin network requests over 70s;
- `main.js` hash matches Phase B’s static copy;
- endpoint `/member/lottery/yeekee` is present in the bundle.

### 5.3 What REA did not confirm

- Exact 60s interval (agent-browser measured **59,991 ms** and **119,991 ms**).
- Initial page-load list+chart requests (REA attached after load).
- Grid count/row-level timestamps (agent-browser/derived).
- Historical date-filter behavior (agent-browser).
- Formula verification (saved CSVs + `verify_formula.py`).

### 5.4 REA limitations

- Observation starts at attach; prior activity unavailable.
- Raw headers/bodies/cookies/storage values/WS payloads not retained.
- Source maps not fetched; scripts/accessibility policy-filtered.
- `analyze_web_bundle` does not execute JS; endpoint candidates low-confidence; it does not enumerate `setInterval`.
- Screenshot viewport-only.

ไฟล์: `REA_EVIDENCE_VERIFICATION.md`

---

## 6. Task 5 — Statistical Validity

### 6.1 Predefined hypotheses

| ID | Hypothesis | Result | Verdict |
|---|---|---|---|
| H1 | +103/+119 bursts in every round | 16/16 | **SUPPORTED (within day)** |
| H2 | Row 16 in +119 group | 16/16; random p≈4.3e-9 | **SUPPORTED** |
| H3 | Duplicate groups are same-user | 94/104; permutation p<1e-4 | **SUPPORTED** |
| H4 | Bursts share more users than chance | Only 1/16 nominal; not after correction | **NOT SUPPORTED** |
| H5 | Patterns persist across days | No 88-round historical data | **UNTESTABLE / ACCESS BLOCKED** |
| H6 | Account recurrence across days | No 88-round historical data | **UNTESTABLE / ACCESS BLOCKED** |

### 6.2 Negative findings

- No evidence that bursts are coordinated groups; overlap is generally ≤ chance.
- No evidence that account repetition implies manipulation/collusion/automation.
- No evidence that account repetition predicts results.
- No cross-day evidence at all for the 88-round product.
- Round-62 16-row cadence is a HYPOTHESIS, not proof.

### 6.3 Power

- 16 rounds, one lottery day; enough for within-day regularity, not cross-day persistence.
- 469 display identifiers, not verified people; mask collisions possible.
- No prospective prediction test; no betting recommendation.

ไฟล์: `STATISTICAL_VALIDITY_C.md`

---

## 7. Verified facts vs hypotheses

| ID | Finding | Class | Confidence | Evidence |
|---|---|---|---|---|
| PC-01 | 53-result dataset was a snapshot | OBSERVED | High | grid counts 51→72; PC-HIST-01 |
| PC-02 | 88-round product has no UI history archive | OBSERVED | High | main page/date filter; PC-HIST-02 |
| PC-03 | 264-round product has per-date history; not target | OBSERVED | High | date filter; PC-HIST-02 |
| PC-04 | Oldest 88-round date = current day only | OBSERVED | High | PC-HIST-01/02 |
| PC-05 | Old period IDs 404; current IDs 200 | OBSERVED | High | PC-HIST-04 |
| PC-06 | 13 inversions in 7 rounds; 18 in 16 rounds | OBSERVED | High | PC-ORDER-01 |
| PC-07 | All inversions +1s; order not strictly timestamp | OBSERVED | High | PC-ORDER-01 |
| PC-08 | Within-tie order not numeric | OBSERVED | High | PC-ORDER-02 |
| PC-09 | Row16 in +119 group 16/16 | OBSERVED | High | PC-ORDER-02 |
| PC-10 | 94/104 duplicate groups same-user | OBSERVED | High | PC-ACCT-01 |
| PC-11 | 0/104 duplicate groups same-second | OBSERVED | High | PC-ACCT-01 |
| PC-12 | Same-user duplicates far above chance (p<1e-4) | OBSERVED | High | PC-ACCT-02 |
| PC-13 | +103/+119 bursts multi-user/multi-number | OBSERVED | High | PC-ACCT-03 |
| PC-14 | Burst user overlap not above chance | OBSERVED (negative) | Medium | PC-ACCT-04 |
| PC-15 | 286/469 hashes recur in ≥2 rounds | OBSERVED | Medium-High | PC-ACCT-05 |
| PC-16 | One 16-row user in round 62 | OBSERVED | High | PC-ACCT-06 |
| PC-17 | Scripted cadence for that user | HYPOTHESIS | Low-Medium | PC-ACCT-06 |
| PC-18 | Masked-name collisions can distort counts | UNKNOWN | — | PC-ACCT-07 |
| PC-19 | Cross-day persistence | UNTESTABLE | — | PC-HIST-05 |
| PC-20 | REA confirms sparse detail poll + no list poll | OBSERVED | High | PC-REA-01/02 |
| PC-21 | Exact 60s interval | OBSERVED | High | runtime 59,991/119,991 ms |
| PC-22 | All 88 results visible after complete day | UNKNOWN/INFERRED | Low | 72/88 at 00:00; not observed |
| PC-23 | Actual DB retention | UNKNOWN | — | no UI metadata |

---

## 8. Exact unresolved questions

1. Does the 88-round grid show all 88 at 03:45, and for how long before the next day reset?
2. What is the actual database retention for 88-round periods?
3. Why do old period IDs return 404 while current ones work?
4. What internal field orders rows within the same second?
5. Why do one-second inversions cluster at 19→20 and 39→40?
6. What causes the +103/+119 bursts — batch commit or synchronized clients?
7. What is the true account count after masked-name collisions?
8. Do account/burst patterns persist on other days?
9. Is `created_at` creation, acceptance, or commit time?
10. Are late bets rejected server-side? (not tested)
11. Why does the 88-round block ignore the results-page date filter?
12. What is the grid refresh mechanism (job/cache/materialized view)?

---

## 9. Additional investigations ranked

1. **Operator-side logs/audit** — request arrival vs commit, batch vs client, tie-break, grid refresh.
2. **Completed-day observation at 03:50** — confirm 88/88 and reset behavior.
3. **Multi-day archive via operator** — test cross-day persistence and retention.
4. **Mask-collision analysis with operator help** — true account count; no deanonymization.
5. **Per-user cadence model** — quantify scripted vs human inter-arrival patterns.
6. **264-round comparison** — only as a different product; not a substitute.

---

## 10. ACCESS BLOCKED / cannot be established

- No completed-day 88-round snapshot.
- No historical 88-round submission lists.
- No actual retention period.
- No server logs/queue metrics/DB/admin.
- No cross-day comparison.
- No internal ordering key.
- No proof of batch vs synchronized automation.
- No true account count due to mask collisions.
- No late-bet enforcement test.

---

## 11. Deliverables

```text
phase_c/
├── HISTORICAL_AVAILABILITY.md
├── HISTORICAL_ACCESS_MATRIX.csv
├── MASKED_ACCOUNT_PATTERN_AUDIT.md
├── SUBMISSION_ORDERING_AUDIT.md
├── REA_EVIDENCE_VERIFICATION.md
├── STATISTICAL_VALIDITY_C.md
├── PHASE_C_FINAL_REPORT.md
├── c_round_summary.csv
├── c_ordering_inversions.csv
├── charts/ (screenshots)
├── scripts/
│   ├── build_c_dataset.py
│   ├── account_pattern_audit.py
│   └── collect_round_hash.js
└── evidence/
    ├── combined_events.csv
    ├── raw_rounds_hash/ (16 rounds, hash-only)
    ├── c_burst_overlap.csv
    ├── c_same_user_duplicates.csv
    ├── c_account_summary.csv
    └── c_account_patterns.json
```

---

## 12. Ethical statement

- ไม่มีการส่งเลข/แทง/เดิมพัน
- ไม่มี authentication bypass, ไม่ probe endpoint ที่ไม่มีเอกสาร
- ไม่เก็บ username ดิบ, password, token, cookie
- Account identifiers เป็น hash ของ masked display name; ไม่พยายาม reverse/identify
- ข้อมูลทั้งหมดเป็น public/authorized member view
- รายงานพฤติกรรมเป็นสถิติ ไม่กล่าวหาบุคคลหรือสรุปว่าเป็นการทุจริต
- ไม่มีคำแนะนำการเดิมพันหรือสูตรทำนาย
