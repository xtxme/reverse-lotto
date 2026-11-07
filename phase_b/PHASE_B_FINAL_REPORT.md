# PHASE B — Final Report
## THLotto Yeekee: Five Unresolved Anomalies

วันที่: 2026-11-07 (Asia/Bangkok, UTC+7)
ขอบเขต: ต่อยอด Phase A, ตรวจสอบ 5 ประเด็น, ไม่สร้าง replica, ไม่แตะ LINE dataset
สถานะ: **เสร็จสิ้นทั้ง 5 investigations** (มีข้อจำกัดที่ระบุไว้)

---

## บทสรุปผู้บริหาร (Thai)

Phase B เก็บข้อมูลดิบใหม่ 7 รอบ (period 229–235 = รอบ 53–59) จำนวน **1,097 แถว** และ audit ข้อสรุป Phase A ทั้งหมด ผลสำคัญมีดังนี้:

1. **98.91% ของเลขถูกส่งหลังเวลาปิดรับแทง** และ **84.14% มาภายใน 20 วินาทีสุดท้าย** ก่อนปิดรับเลข ข้อกล่าวอ้าง Phase A ที่ว่ารอบ 55 มี 5 เลขก่อนปิด และ 146 เลขหลังปิด **ถูกต้องตรงเป๊ะ**
2. การที่ 49–51 เลขมี timestamp เดียวกัน ไม่ใช่ bot ตัวเดียว เพราะ burst เหล่านั้นมี **ผู้ใช้ต่างกัน 49–65 คน** และเลขส่วนใหญ่ไม่ซ้ำ แต่เกิดที่ **offset เดียวกันทุกรอบ คือ +103s และ +119s** จากเวลาปิดรับ รวมกัน 63.08% ของทุกแถว ยังแยกไม่ได้ว่าเป็น server batch/queue หรือ synchronized multi-account automation
3. เลขซ้ำ (duplicates) ไม่ได้มาจากคนจำนวนมากเลือกเลขเดียวกัน แต่มาจาก **ผู้ใช้คนเดิมส่งเลขเดิมซ้ำหลายครั้ง** — 39/44 กลุ่มเป็น same-user, 0/44 กลุ่มอยู่ในวินาทีเดียวกัน, 59/61 คู่ต่างวินาที
4. **60-second polling มีจริง** ในหน้า round-detail: `setInterval(getYeekeeNumberList, 60000)` วัด runtime ได้ที่ +59.991s และ +119.991s แต่ polling นี้更新เฉพาะ **รายการเลขและ sum** ไม่ได้ update ผลรางวัลหรือ round state หน้า list/result ไม่ poll; grid ผลรางวัล refresh ที่ **ขอบ 15 นาที** (21:00, 21:15, 21:30) ทำให้ grid ล่าช้ากว่า detail ได้ถึง ~15 นาที
5. Monte Carlo p=0.1208 ของ Phase A reproduce ได้เฉพาะเมื่อ replay RNG state เท่านั้น ถ้า seed ใหม่จะได้ p ต่างกันมาก (0.27–0.91) และ 64 configurations มีเพียง 4/64 ที่ p<0.05 หลัง multiple-testing correction **ไม่มีผลใดมีนัยสำคัญ**

**ข้อสรุปหลัก:** ไม่มีหลักฐานที่ผ่านการ validate ว่าตัวแปร public ใดก่อน cutoff ทำนายผลลัพธ์อนาคตได้ และในทางโครงสร้าง ณ เวลาปิดรับPool มีเพียง **0–5 เลข** ซึ่งน้อยกว่า 16 ทำให้ "row 16" ยังไม่ถูกนิยามด้วยซ้ำ ดังนั้นการคำนวณผลก่อน cutoff จึงเป็นไปไม่ได้จากข้อมูล public

---

## 1. วิธีวิจัยและขอบเขต

- Audit รายงาน Phase A ทั้ง 11 ไฟล์, CSV/JSON, screenshots, JS ที่ดาวน์โหลดไว้ และรันสคริปต์ reproducibility เดิม
- เก็บข้อมูลใหม่จากหน้าเว็บปกติ (authorized account) เฉพาะ GET/read-only:
  - หน้า round detail ของ period 229–235
  - หน้า list และ result
  - betconfig ที่ server ฝังใน HTML
- ไม่มีการส่งเลข, ไม่มีการแทง, ไม่มีการเดิมพัน, ไม่มีการ probe endpoint ที่ไม่มีเอกสารรองรับ, ไม่มีการเก็บ username ดิบ
- ข้อมูลใหม่ถูก sanitize เหลือ `round, period_id, seq, number, timestamp` เท่านั้น
- ที่เก็บ: `phase_b/evidence/`, สคริปต์: `phase_b/scripts/`, กราฟ: `phase_b/charts/`

ข้อจำกัดด้าน session: เว็บบังคับ single active session และตัด session ซ้ำ ๆ ระหว่างเก็บข้อมูล ต้อง login ใหม่หลายครั้ง ทุกครั้งที่หลุดได้ re-authenticate และเก็บต่อ ไม่มีการเดาข้อมูลในช่องว่าง

Phase B ใช้ direct browser runtime/JS และ server-rendered HTML เป็นหลัก เพราะให้ granularity ของ timestamp/network ที่ต้องการ; REA ยังพร้อมใช้แต่ไม่ได้เพิ่มหลักฐานใหม่ที่จำเป็นเกิน direct runtime ในรอบนี้

เครื่องมือ: REA ไม่ได้หยุดหรือ timeout ระหว่างงานหลัก; มี agent-browser daemon socket error `Resource temporarily unavailable (os error 35)` หนึ่งครั้งจาก long-running eval (~3 นาที) ตัว browser ยังทำงานอยู่ จึงทิ้ง run นั้นและเปลี่ยนเป็น short/non-blocking reads — ไม่มีข้อมูลจาก run ที่ล้มเหลวถูกนำมาใช้

---

## 2. Audit ผลลัพธ์ Phase A

| ข้อกล่าวอ้าง Phase A | ผล audit Phase B | สถานะ |
|---|---|---|
| รอบ 55: 5 เลขก่อนปิด, 146 หลังปิด | 5 และ 146 ตรงเป๊ะ | **VERIFIED** |
| รอบ 55: 51 @ 19:31:59, 49 @ 19:31:43 | 51 และ 49 ตรงเป๊ะ | **VERIFIED** |
| Pool Monte Carlo 337 เลข = 173+164 | 337 ตรง, เป็น list เต็ม ไม่ใช่ sample | **VERIFIED** |
| สูตร sum − row16, 5 หลักสุดท้าย → top3/bottom2 | ตรง 3 รอบ (53/54/55), 7 รอบ top/bottom | **VERIFIED** |
| row16 คือ display row 16 (newest-first) | counter-test ปฏิเสธ 16th chronological | **VERIFIED** |
| "ไม่มี polling ของ round state" | หน้า grid/result ไม่ poll จริง แต่หน้า detail poll ทุก 60s | **CONTRADICTED (detail)** / ถูกต้องสำหรับ grid/result |
| Duplicate เกิดจาก human preference / independent users | 39/44 กลุ่มเป็น same-user, 3/44 all-different | **REFINED** |
| Monte Carlo p≈0.12 เป็นผลที่ stable | p เปลี่ยนตาม RNG state/seed มาก | **REFINED / UNSTABLE** |
| ผลรางวัลแสดงภายใน ≤18s | หน้า detail ใช่ (≤18s) แต่ grid ล่าช้าถึง ~15 นาที | **VERIFIED (detail) / NEW (grid)** |
| `created_at` เป็น server time | การ deliver เป็น server-side จริง แต่ความหมาย creation/acceptance/commit ยัง UNKNOWN | **VERIFIED (delivery) / UNKNOWN (semantics)** |

---

## 3. Investigation 1 — ทำไมเลขส่วนใหญ่มาหลังปิดรับ?

### 3.1 นิยาม

- **Betting close** = `close_date` ของรอบ (server betconfig)
- **Shoot close** = `close_date + 2 นาที` (`closeDateYeekee`)
- **ก่อนปิด** = `created_at < close_date`
- **หลังปิด** = `created_at >= close_date`

### 3.2 ผลรายรอบ

| รอบ | Period | n | ก่อนปิด | หลังปิด | % ก่อน | % หลัง |
|---|---:|---:|---:|---:|---:|---:|
| 53 | 229 | 173 | 2 | 171 | 1.16% | 98.84% |
| 54 | 230 | 164 | 1 | 163 | 0.61% | 99.39% |
| 55 | 231 | 151 | 5 | 146 | 3.31% | 96.69% |
| 56 | 232 | 146 | 1 | 145 | 0.68% | 99.32% |
| 57 | 233 | 145 | 2 | 143 | 1.38% | 98.62% |
| 58 | 234 | 150 | 1 | 149 | 0.67% | 99.33% |
| 59 | 235 | 168 | 0 | 168 | 0.00% | 100.00% |
| **รวม** | — | **1,097** | **12** | **1,085** | **1.09%** | **98.91%** |

### 3.3 การกระจาย 20 วินาที

| ช่วง | จำนวน | สัดส่วน |
|---|---:|---:|
| ก่อนปิด | 12 | 1.09% |
| 0–20s | 10 | 0.91% |
| 20–40s | 12 | 1.09% |
| 40–60s | 12 | 1.09% |
| 60–80s | 68 | 6.20% |
| 80–100s | 60 | 5.47% |
| **100–120s** | **923** | **84.14%** |
| หลัง 120s | 0 | 0.00% |

ต่อรอบ final-20s อยู่ที่ 77.5%–88.7% ดังนั้นเป็น pattern ที่เสถียร ไม่ใช่รอบเดียว

### 3.4 `created_at` หมายถึงอะไร?

- **OBSERVED:** เป็น timestamp จาก server, ความละเอียด 1 วินาที, ไม่มี milliseconds, แสดงใน HTML และ JSON
- **OBSERVED:** ไม่ใช่เวลาที่ browser render; การ fetch ช้าไม่เปลี่ยนค่า
- **INFERRED:** น่าจะเป็น DB insert/commit time
- **UNKNOWN:** เป็น creation, acceptance, หรือ processing time กันแน่; ต้องมี server logs
- **OBSERVED:** ผลรวม `sum` ตรงกับผลรวมของทุกแถว ณ เวลาที่ fetch (ตรวจ 3 รอบ) และเพิ่มขึ้นตามจำนวนแถว

### 3.5 ตัดสมมติฐาน rendering delay

การ delay ของ browser/network ไม่สามารถอธิบาย pattern นี้ได้ เพราะ timestamp ถูกเก็บมากับแถวแล้ว และ pattern ปรากฏในข้อมูลดิบทั้ง 7 รอบ

### 3.6 ข้อสรุป Investigation 1

- **OBSERVED:** 98.91% หลังปิด, 84.14% ใน 20 วินาทีสุดท้าย, 7/7 รอบ
- **INFERRED:** การเปิดรับเลขก่อนปิดมีเพียง 0–5 คน; ผู้ใช้ส่วนใหญ่ส่งหลังปิด
- **HYPOTHESIS:** server batch/queue หรือ synchronized clients (ดู Investigation 2)
- **UNKNOWN:** ความหมายแท้จริงของ `created_at`

ไฟล์: `01_submission_timeline.md`, `submission_timeline.csv`, `charts/submission_timing_distribution.png`

---

## 4. Investigation 2 — ทำไม 49–51 เลขมี timestamp เดียวกัน?

### 4.1 Precision

- แสดง `YYYY-MM-DD HH:mm:ss` → **1 วินาที**
- **ไม่มี milliseconds** ใน UI/JSON ปกติ
- ภายในวินาทีเดียวกัน ลำดับถูกกำหนดจาก server; เราเห็น row sequence ที่เสถียร แต่ไม่รู้ tie-break key

### 4.2 สถิติต่อรอบ

| รอบ | n | Distinct seconds | Max/s | Timestamp ของ max | Tied timestamps | Rows in ties | Collision pairs |
|---|---:|---:|---:|---|---:|---:|---:|
| 53 | 173 | 44 | 51 | 19:01:43 | 12 | 141 | 2,468 |
| 54 | 164 | 36 | 49 | 19:16:43 | 10 | 138 | 2,457 |
| 55 | 151 | 23 | 51 | 19:31:59 | 11 | 139 | 2,552 |
| 56 | 146 | 27 | 53 | 19:46:43 | 9 | 128 | 2,341 |
| 57 | 145 | 23 | 49 | 20:01:43 | 11 | 133 | 2,055 |
| 58 | 150 | 21 | 50 | 20:16:43 | 11 | 140 | 2,519 |
| 59 | 168 | 23 | 65 | 20:31:59 | 10 | 155 | 3,444 |

### 4.3 สอง burst ที่ offset เดียวกันทุกรอบ

| รอบ | Burst +103s | จำนวน | Burst +119s | จำนวน |
|---|---|---:|---|---:|
| 53 | 19:01:43 | 51 | 19:01:59 | 47 |
| 54 | 19:16:43 | 49 | 19:16:59 | 48 |
| 55 | 19:31:43 | 49 | 19:31:59 | 51 |
| 56 | 19:46:43 | 53 | 19:46:59 | 42 |
| 57 | 20:01:43 | 49 | 20:01:59 | 38 |
| 58 | 20:16:43 | 50 | 20:16:59 | 49 |
| 59 | 20:31:43 | 51 | 20:31:59 | 65 |

สองวินาทีนี้รวม **692/1,097 = 63.08%** ของทุกแถว

### 4.4 องค์ประกอบของ burst

- largest burst: 49–65 แถว; **distinct users = 49–65**; unique numbers = 49–65 (ยกเว้นรอบ 59 มี 2 แถวของผู้ใช้คนเดียว)
- +103 และ +119 bursts มี user overlap 12–41 คน (Jaccard 0.16–0.55) → มีผู้ใช้บางส่วนส่งทั้งสอง wave
- ไม่ใช่ bot ตัวเดียว เพราะแต่ละแถวเป็นคนละ masked user และเลขต่างกัน

### 4.5 Ordering

- fetch หน้า 1 ซ้ำ 2 ครั้ง → ลำดับ 50 แถวเหมือนเดิมทุกตัว
- page 1 จบ seq 50; page 2 เริ่ม seq 51 → ไม่มี gap/overlap
- API `limit=200&offset=0` คืน 20 แถวแรก ตรงกับ HTML page 1
- **OBSERVED:** ordering stable; **UNKNOWN:** tie-break ภายในวินาทีเดียวกัน

### 4.6 Duplicate vs collision

- 44 duplicate groups, 96 rows
- **0/44** groups อยู่ในวินาทีเดียวกัน
- **59/61** colliding pairs อยู่ต่างวินาที
- ดังนั้น timestamp collision กับ duplicate number เป็นคนละ phenomenon

### 4.7 Models

- Uniform arrival over 120s: max/s ~5–6, observed 49–65 → ปฏิเสธชัดเจน
- Smooth deadline rush: อธิบาย tail ได้ แต่ไม่อธิบาย two one-second spikes ที่ offset เดิมทุกรอบ
- Two-point mass + background: อธิบาย descriptive ได้ แต่ไม่บอกสาเหตุ
- One automated client: ปฏิเสธสำหรับ top burst (distinct users/numbers)

### 4.8 Hypotheses

- **H1:** server batch/queue commit at fixed ticks → timestamps เป็น commit time
- **H2:** synchronized multi-account automation
- **H3:** deadline rush + server load/batch commit

ยังแยก H1–H3 ไม่ได้ด้วยข้อมูล public; ต้องมี server request-arrival logs vs DB commit logs, queue metrics, IP/device/session data

### 4.9 ข้อสรุป Investigation 2

- **OBSERVED:** 51/49 ตรงเป๊ะ; +103/+119 ทุกรอบ; 63.08% ของแถว; multi-user/multi-number
- **REJECTED:** "one bot submitted 51 numbers"; "duplicates caused collisions"
- **HYPOTHESIS:** batch/queue หรือ synchronized automation
- **UNKNOWN:** สาเหตุที่แท้จริง

ไฟล์: `02_timestamp_collision_analysis.md`, `timestamp_collisions.csv`, `charts/timestamp_burst_analysis.png`

---

## 5. Investigation 3 — ทำไมเลข 5 หลักซ้ำบ่อย?

### 5.1 นิยาม

- **Duplicate entry** = `n − unique` (แถวส่วนเกิน)
- **Colliding pair** = `Σ C(freq,2)` (คู่ของแถวที่เลขเดียวกัน)

ตัวเลข 9 และ 13 ของ Phase A เป็น **duplicate entries** ไม่ใช่ pairs; 9 entries → 11 pairs (รอบ 53), 13 entries → 18 pairs (รอบ 54)

### 5.2 ผลรายรอบ

| รอบ | n | Unique | Dup entries | Rate | Colliding pairs | Max freq |
|---|---:|---:|---:|---:|---:|---:|
| 53 | 173 | 164 | 9 | 5.20% | 11 | 3 |
| 54 | 164 | 151 | 13 | 7.93% | 18 | 4 |
| 55 | 151 | 146 | 5 | 3.31% | 5 | 2 |
| 56 | 146 | 142 | 4 | 2.74% | 5 | 3 |
| 57 | 145 | 142 | 3 | 2.07% | 3 | 2 |
| 58 | 150 | 141 | 9 | 6.00% | 9 | 2 |
| 59 | 168 | 159 | 9 | 5.36% | 10 | 3 |
| **รวม** | **1,097** | **1,023** | **52** | **4.74%** | **61** | — |

### 5.3 Same-user structure

| รอบ | Dup groups | All same user | Mixed | All different |
|---|---:|---:|---:|---:|
| 53 | 7 | 6 | 0 | 1 |
| 54 | 9 | 7 | 1 | 1 |
| 55 | 5 | 5 | 0 | 0 |
| 56 | 3 | 2 | 1 | 0 |
| 57 | 3 | 2 | 0 | 1 |
| 58 | 9 | 9 | 0 | 0 |
| 59 | 8 | 8 | 0 | 0 |
| **รวม** | **44** | **39** | **2** | **3** |

- 37 pairs, 6 triples, 1 quadruple
- Top: `37553` ×3 (รอบ 53, 1 user), ×4 (รอบ 54, 1 user); `66666` ×3 (รอบ 56, 2 users); `55359` ×3 (รอบ 59, 1 user)
- Max rows/user: 8 (53), 7 (54), 6 (55), 5 (56/59), 4 (57), 3 (58)

### 5.4 Timing

- **0/44** groups มีทุก copy ในวินาทีเดียวกัน
- **59/61** pairs อยู่ต่างวินาที
- Duplicate เป็นการส่งเลขเดิมซ้ำ **คนละเวลา** โดยผู้ใช้คนเดิม ไม่ใช่ batch insert

### 5.5 Cross-round

- Pairwise intersection: observed 34, uniform expected 5.15 → **6.6×**
- 18/21 pairs มีเลขร่วมกัน
- Top recurring: `37553` 8 ครั้ง (3 รอบ), `66666` 8 (4 รอบ), `55014` 6 (2 รอบ), `85858` 5 (5 รอบ), `88888` 5 (3 รอบ), `00000` 4 (3 รอบ)
- Family-wise p ของ top values < 1e-6; แต่เป็นการเลือก post-hoc และเป็น same-user repeat

### 5.6 Pattern frequencies

| Pattern | Observed | Uniform expected | Ratio |
|---|---:|---:|---:|
| All five same | 23 | 0.11 | 209.7× |
| Exactly four same | 9 | 4.94 | 1.8× |
| Palindrome | 46 | 1.10 | 41.9× |
| At least one repeated digit | 795 | 765.27 | 1.04× |

### 5.7 Null models

| Model | Mean duplicate entries | 95% interval | Observed 52 | Verdict |
|---|---:|---|---:|---|
| A uniform | 0.86 | 0–3 | 52 | Rejected |
| B finite-pool other rounds | 102.3 | 85–120 | 52 | Over-predicts; not credible |
| C smoothed ε=0.5 | 27.4 | 18–38 | 52 | Rejected |
| C smoothed ε=0.9 | 1.95 | 0–5 | 52 | Rejected |
| D positional digits | 0.90 | 0–3 | 52 | Rejected |
| E pooled in-sample | 90.0 | 73–107 | 52 | Over-predicts |

**No population-level number distribution that can generate unseen numbers comes close to 52 duplicates.** A finite-pool model can be tuned to match the count, but cannot explain the same-user grouping or the different-second structure.

### 5.8 ข้อสรุป Investigation 3

- **OBSERVED:** 52 duplicate entries, 61 pairs, 44 groups; 39/44 all-same-user; 0/44 same-second
- **OBSERVED:** cross-round overlap 6.6× uniform; pattern excess
- **INFERRED:** duplicates are mostly one account repeating its own number
- **HYPOTHESIS:** automation/scripted number sets may explain some repeats, but not proven
- **REJECTED:** "many independent users chose the same favorite number" as the main cause
- **NOT PREDICTIVE:** duplicates say nothing about the sum modulo 100,000 or row 16

ไฟล์: `03_duplicate_number_analysis.md`, `number_frequency.csv`, `duplicate_simulation.py`, `charts/duplicate_distribution.png`

---

## 6. Investigation 4 — Polling และ Frontend Update

### 6.1 Code

ใน `main.js`:

```js
this.isYeekee && this.yeekeeCountdownTimer &&
  setInterval(function () { t.getYeekeeNumberList(); }, 6e4)
```

`getYeekeeNumberList()` เรียก:

```
GET /member/lottery/yeekee-list-number?id={id}&limit=19&offset=0
```

แล้ว update `yeekeeLists` และ `sumYeekee`

### 6.2 Runtime

หน้า `/member/lottery/yeekee/238` (รอบ 62) โหลด 21:03:28.278:

| เวลา | Request | Interval |
|---|---|---:|
| 21:03:28.278 | list-number | 0 |
| 21:03:28.278 | chart | 0 |
| 21:04:28.269 | list-number | **59,991 ms** |
| 21:05:28.269 | list-number | **119,991 ms** |

- chart fetched once
- list-number polled every ~60s
- ไม่มี result/round-state request

### 6.3 หน้า list/result ไม่ poll

- หน้า `/member/lottery/yeekee`: 70 วินาที ไม่มี round-data XHR
- หน้า `/member/lottery/yeekee/228`: 72 วินาที ไม่มี round-data XHR

### 6.4 Grid refresh ทุก 15 นาที

| เหตุการณ์ | เวลา | Boundary |
|---|---|---|
| รอบ 60 detail มีผล | 20:57:41 | — |
| รอบ 60 ปรากฏใน grid | 21:00:56 | 21:00 (รอบ 61 ปิด) |
| รอบ 61 ปรากฏใน grid | 21:16:23 | 21:15 (รอบ 62 ปิด) |
| รอบ 62 detail มีผล | 21:17:16 | — |
| รอบ 62 ปรากฏใน grid | 21:30:28 | 21:30 (รอบ 63 ปิด) |

- **OBSERVED:** grid เพิ่มผลที่ boundary 21:00, 21:15, 21:30
- **INFERRED:** grid refresh ทุก 15 นาที (server-side job/cache)
- **UNKNOWN:** กลไกจริง (job/cache/materialized table)

ผลคือ grid ล่าช้ากว่า detail ได้ถึง ~15 นาที แม้ detail จะมีผลภายใน ~16–18 วินาทีหลัง shoot close

### 6.5 Auto-reload

เมื่อ countdown ถึง `close+2m` ติดลบ:

```js
window.location.reload()
```

ดังนั้นผลจะถูกเห็นผ่านการ reload หน้า detail ไม่ใช่ polling ของ result

### 6.6 สรุปความขัดแย้ง Codex vs OpenCode

- **Codex ถูก** ที่พบ 60-second timer ใน code
- **OpenCode ถูก** ที่ grid/result ไม่ poll
- ทั้งสองฝ่ายไม่ครบ: 60s timer เป็นของ **detail list/sum**; grid ใช้ **15-minute boundary**; result ใช้ **page reload**
- Phase A “no polling” ต้องแก้เป็น “no polling of round state/result on grid/result pages”

ไฟล์: `04_polling_and_frontend_runtime.md`, `frontend_timers.csv`, `runtime_network_timeline.csv`

---

## 7. Investigation 5 — Audit Monte Carlo

### 7.1 Reproduction

- Phase A p=0.1208, χ²=14.044, counts [1953, 2084, 1967, 1923, 1983, 1980, 2008, 2086, 2050, 1966] reproduce ได้ **เฉพาะเมื่อ replay RNG state** (test 2 consume 20,000×53 draws ก่อน test 6)
- Fresh Python seed: χ²=4.027, p=0.9096
- Fresh NumPy seed: χ²=11.082, p=0.2701
- 200,000 iterations: χ²=8.849, p=0.4513

### 7.2 p-value distribution

100 seeds (main config):

```
mean 0.4816, median 0.4995, 5th 0.0334, 95th 0.9543, P(p<0.05)=0.070
```

→ p-values เป็น uniform ภายใต้ simulation null; p=0.12 เป็นเพียง draw เดียว

### 7.3 Sensitivity 64 configs

- 4/64 p<0.05 (expected 3.2)
- mean p=0.4836
- ไม่มี pool/n/rule ใด bias เป็นระบบ
- หลัง multiple-testing correction ไม่มี config ใด significant

### 7.4 Effect sizes

| Quantity | Estimate | Interval / note |
|---|---|---|
| Last-digit Cramér’s V | 0.132 | bootstrap 0.116–0.267; null ≈0.137 |
| Runs z | 0.419 | p=0.6753 |
| Lag-1 autocorr | −0.1205 | bootstrap −0.285..0.247; perm p=0.3805 |
| Hot digit | 13.0% (3/23) | Wilson 4.5%–32.1% |
| Bottom-2 distinct | 39/100 | expected 41.3 |
| Split-half homogeneity | χ²=8.127, df=9 | p=0.5214 |

### 7.5 Multiple testing

7 exploratory p-values; Holm-adjusted min 0.8456; BH min 0.7031 → ไม่มีผลใด significant

### 7.6 ข้อสรุป Investigation 5

- **OBSERVED:** Phase A script reproducible, arithmetic correct
- **OBSERVED:** p=0.12 ไม่ stable; 64 configs ไม่มี bias
- **OBSERVED:** no effect survives correction
- **NOT DEMONSTRATED:** validated prospective prediction
- **LIMITATION:** n=53, 3-digit power แทบเป็นศูนย์; simulation ไม่จำลอง ordering/same-user/timestamps

ไฟล์: `05_monte_carlo_audit.md`, `monte_carlo_reproduction.py`, `simulation_comparison.csv`, `statistical_validation.md`

---

## 8. Cross-cutting — ข้อมูลอะไรรู้ได้ก่อน cutoff?

### 8.1 ข้อค้นพบเชิงโครงสร้าง

ณ เวลาปิดรับ (cutoff) ข้อมูล 7 รอบแสดง:

| รอบ | partial_n (ก่อน close) | partial_row16 |
|---|---:|---|
| 53 | 2 | ไม่มี |
| 54 | 1 | ไม่มี |
| 55 | 5 | ไม่มี |
| 56 | 1 | ไม่มี |
| 57 | 2 | ไม่มี |
| 58 | 1 | ไม่มี |
| 59 | 0 | ไม่มี |

**ทุกครั้ง partial_n < 16** → row 16 ยังไม่ถูกนิยาม → ไม่สามารถใช้สูตรที่ประกาศได้ก่อน cutoff

### 8.2 Pre-cutoff predictive test

- partial_sum vs final_sum: r = 0.09 (แทบไม่สัมพันธ์)
- partial_sum (raw) vs final_result: r = 0.233; permutation p = 0.613
- partial_sum (mod 100k) vs final_result: r = 0.156; permutation p = 0.724
- Leave-one-out prediction (partial_sum + mean future sum): mean circular error 22,694 vs uniform ~25,000; top3 hits 0/7; bottom2 hits 0/7

แม้ใช้ค่าเฉลี่ย future sum จากรอบอื่น (ซึ่งไม่ใช่ข้อมูลที่รู้จริง ณ cutoff) ก็ยังไม่ชนะ random

### 8.3 ตัวแปรที่ legitimate สำหรับ pre-cutoff test

- round number, close_date, shoot_close, server_time, current grid: ใช้เป็น time features ได้
- partial pool/sum: ใช้ได้ แต่ต้อง label ว่า partial และห้ามตีความเป็น final
- final pool/sum/row16/result/top3/bottom2: **ห้ามใช้** เป็น pre-cutoff
- list page result count: stale, ห้ามใช้
- is_open: ไม่ reliable (ยังเป็น 1 หลัง close)
- masked username: ไม่เก็บ/ไม่ใช้
- per-second burst/duplicate history: ใช้เป็น historical covariate ได้ แต่ไม่ใช่ outcome

Matrix: `06_pre_cutoff_information_matrix.csv`

### 8.4 คำตอบ

**ไม่มีหลักฐานว่า public pre-cutoff variable ใดมี validated predictive relationship กับผลอนาคต** และในทางโครงสร้าง row 16 ยังไม่เกิด ณ cutoff

---

## 9. Verified facts vs hypotheses

| ID | Finding | Class | Confidence | Evidence |
|---|---|---|---|---|
| PB-01 | 98.91% ของ 1,097 แถวมาหลังปิดรับ | OBSERVED | High | PB-TIME-01 |
| PB-02 | 84.14% อยู่ใน 20 วินาทีสุดท้าย | OBSERVED | High | PB-TIME-01 |
| PB-03 | Burst +103s/+119s ทุกรอบ; 63.08% ของแถว | OBSERVED | High | PB-BURST-01 |
| PB-04 | Burst เป็น multi-user/multi-number | OBSERVED | High | PB-BURST-02 |
| PB-05 | 52 duplicate entries, 61 pairs | OBSERVED | High | PB-DUP-01 |
| PB-06 | 39/44 duplicate groups เป็น same-user | OBSERVED | High | PB-USER-01 |
| PB-07 | 0/44 duplicate groups อยู่ในวินาทีเดียวกัน | OBSERVED | High | PB-DUP-01 |
| PB-08 | Cross-round overlap 6.6× uniform | OBSERVED | Medium | PB-DUP-03 |
| PB-09 | Pattern all-same/palindrome สูงกว่า uniform มาก | OBSERVED | High | PB-DUP-02 |
| PB-10 | Detail page poll list-number ทุก 60s | OBSERVED | High | PB-POLL-02 |
| PB-11 | Grid refresh ที่ boundary 15 นาที | OBSERVED/INFERRED | Medium-High | PB-GRID-01 |
| PB-12 | Grid/result page ไม่ poll | OBSERVED | High | PB-POLL-02 |
| PB-13 | Phase A “no polling” ผิดสำหรับ detail | CONTRADICTED | High | PB-POLL-03 |
| PB-14 | Phase A p=0.12 ไม่ stable | OBSERVED | High | PB-MC-01/02 |
| PB-15 | ไม่มีผล significant หลัง correction | OBSERVED | High | PB-MC-01 |
| PB-16 | ณ cutoff pool มี 0–5 เลข; row16 ไม่มี | OBSERVED | High | PB-PRECUT-01 |
| PB-17 | ไม่มี validated pre-cutoff prediction | OBSERVED/INFERRED | Medium | PB-PRECUT-02 |
| PB-18 | `created_at` semantics = creation/acceptance/commit | UNKNOWN | — | — |
| PB-19 | สาเหตุ +103/+119 = batch vs sync automation | HYPOTHESIS | Low-Medium | PB-BURST-01 |
| PB-20 | Tie-break ภายในวินาที | UNKNOWN | — | — |
| PB-21 | สูตร deterministic สำหรับรอบที่จบแล้ว | OBSERVED | High | PB-FORMULA-01 |
| PB-22 | Grid ล่าช้ากว่า detail ได้ถึง ~15 นาที | OBSERVED/INFERRED | Medium-High | PB-GRID-01 |

---

## 10. Codex vs OpenCode — ความขัดแย้งที่ยืนยันได้

### 10.1 60-second update interval

- **Codex:** พบ code ที่มี 60-second interval → ถูกต้อง
- **OpenCode Phase A:** ไม่พบ polling ใน idle observation → ถูกต้องสำหรับหน้า grid/result และช่วง observation 5–15 วินาที แต่ไม่ครอบคลุมหน้า detail ที่มี timer 60s
- **Resolution:** timer 60s เป็นของ `getYeekeeNumberList` บนหน้า detail; ไม่อัปเดต result/round state; grid ใช้ 15-minute boundary; result ใช้ reload

### 10.2 ไม่มีความขัดแย้งอื่นที่ยืนยันได้

Phase A claims อื่นถูก verify หรือ refine ตามตาราง Section 2

---

## 11. คำถามที่ยังไม่ได้คำตอบ (Exact unresolved)

1. `created_at` คือ creation, acceptance, หรือ DB commit time?
2. ทำไม burst อยู่ที่ +103s และ +119s พอดีทุกรอบ?
3. เป็น server batch/queue หรือ synchronized multi-account automation?
4. Tie-break ภายในวินาทีเดียวกันใช้ field ใด?
5. ทำไม grid refresh ที่ 15-minute boundary และมีกลไกอะไร?
6. ผลลัพธ์ระยะยาว (multi-day) เป็น uniform จริงหรือไม่?
7. Server-side rate limit / anti-automation มีหรือไม่?
8. Late bet หลัง close_date ถูก reject หรือไม่ (ไม่ได้ทดสอบเพราะผิดกฎ)?
9. Duplicate/same-user pattern คงอยู่ข้ามวันหรือไม่?
10. Round ที่มี <20 submissions ถูก cancel/refund อย่างไร?
11. Negative/underflow result handling?
12. Backend framework/DB schema แท้จริง?
13. ทำไม is_open ยังเป็น 1 หลัง close?
14. ทำไมผลรวม partial sum ณ cutoff แทบไม่สัมพันธ์กับ final sum?

---

## 12. งานวิจัยเพิ่มเติมที่ควรทำ (เรียงตามคุณค่า)

1. **Operator-side logs/audit** — request arrival vs DB commit, queue metrics, grid refresh job; ตอบ H1/H2/H3 และ tie-break
2. **Multi-day/Multi-week archive** — อย่างน้อยหลายพันรอบ สำหรับ 3-digit uniformity/power และ cross-day persistence
3. **Per-user repeat model** — เก็บ user hash แบบ privacy-preserving เพื่อ simulate same-user repeats และวัดว่าอธิบาย duplicate ได้ทั้งหมดหรือไม่
4. **Grid refresh mechanism** — ตรวจ server-side cache/job/materialized view; อธิบาย lag 15 นาที
5. **Pre-registered prospective test** — กำหนด model ล่วงหน้าและทดสอบกับรอบอนาคตจริง (ไม่ใช่ same-day)
6. **Cross-product comparison** — Yeekee264/จับยี่กีทันใจ มี pattern เดียวกันหรือไม่

---

## 13. สิ่งที่ไม่สามารถยืนยันได้จากหลักฐานที่มี

### 13.1 ACCESS BLOCKED

- **Historical period archive:** period IDs 83, 84, 170, 171 returned HTTP 404 in the authorized session. Only current-day periods (172–264 at capture) were reachable.
- **Server-side logs/metrics:** request-arrival logs, queue metrics, DB commit logs, admin interface — not available and not sought. This is the main blocker for resolving batch-vs-automation and `created_at` semantics.
- **Continuous publication timing:** for some rounds only an upper bound is known (e.g., round 60 result present by 20:57:41). Round 55 and 62 have tight bounds.
- **Late-bet enforcement:** not tested, because placing a late bet is outside the research rules. `is_open` remained 1 after close, so it is not a usable proxy.


- Backend language/framework version, DB schema, table names, indexes
- ความหมายแท้จริงของ `created_at`
- สาเหตุของ +103/+119 bursts
- Tie-break ภายในวินาทีเดียวกัน
- Server-side validation, rate limit, anti-automation
- การ reject late bets
- กลไก grid refresh
- Long-run uniformity / predictability
- ผลของ round ที่ <20 submissions หรือ cancelled
- Negative/underflow handling

ทั้งหมดนี้ต้องใช้ operator-side data หรือ authorized audit; ไม่สามารถอนุมานจาก client/public evidence ได้

---

## 14. ข้อจำกัดทางสถิติ

- n=53 results (one day) — insufficient for 3-digit tests; underpowered for subtle digit bias
- 7 rounds of full pool (one evening) — insufficient for day-of-week/time-of-day analysis
- Monte Carlo p=0.12 เป็น single draw; p distribution mean ~0.48
- Multiple testing: 7 exploratory tests; no significant after Holm/BH
- Simulation not faithful to real ordering/same-user/timestamps
- Cross-round overlap p-values post-hoc; family-wise correction marginal
- No prospective validation on unseen future rounds
- Failure to reject randomness ≠ proof of perfect randomness

---

## 15. ข้อสรุปสุดท้าย

1. **สูตร deterministic** สำหรับรอบที่จบแล้ว: ยืนยันแล้ว
2. **ข้อมูลก่อน cutoff** ไม่พอจะคำนวณผล: ณ cutoff มี 0–5 เลข, row16 ยังไม่เกิด
3. **ไม่มี validated predictive relationship** จาก public pre-cutoff data
4. **60s polling มีจริง** แต่เป็นเพียง list/sum บน detail; grid ใช้ 15-min boundary; result ใช้ reload
5. **Duplicates** มาจาก same-user repeats เป็นหลัก ไม่ใช่ population preference
6. **Bursts** เป็น multi-user/multi-number ที่ offset คงที่; ยังแยก batch vs automation ไม่ได้
7. **Monte Carlo p=0.12** ไม่ stable และไม่ใช่หลักฐาน predictability

**คำตอบต่อคำถามหลัก:** ข้อมูล public ก่อน betting close **ไม่สนับสนุนความสัมพันธ์เชิงทำนายที่ผ่านการ validate** และไม่ควรใช้สร้างสูตรทำนายผลยี่กี

---

## 16. Evidence index

ดู `phase_b/evidence_index.csv` และไฟล์:

- `01_submission_timeline.md`
- `submission_timeline.csv`
- `charts/submission_timing_distribution.png`
- `02_timestamp_collision_analysis.md`
- `timestamp_collisions.csv`
- `charts/timestamp_burst_analysis.png`
- `03_duplicate_number_analysis.md`
- `number_frequency.csv`
- `duplicate_simulation.py`
- `charts/duplicate_distribution.png`
- `04_polling_and_frontend_runtime.md`
- `frontend_timers.csv`
- `runtime_network_timeline.csv`
- `05_monte_carlo_audit.md`
- `monte_carlo_reproduction.py`
- `simulation_comparison.csv`
- `statistical_validation.md`
- `06_pre_cutoff_information_matrix.csv`
- `evidence/` (raw sanitized rows, summaries, per-second, user concentration, partial-vs-final)

---

## 17. Ethical statement

- ไม่มีการส่งเลข/แทง/เดิมพัน
- ไม่มีการ bypass authentication/authorization
- ไม่มีการ probe endpoint ที่ไม่มีเอกสารรองรับ
- ไม่มีการเก็บ username ดิบ, password, token, cookie
- ข้อมูลทั้งหมดเป็น public/authorized member view
- ผลลัพธ์ที่มีความอ่อนไหว (ถ้ามี) รายงานเพื่อ remediation ไม่ใช่ exploitation
