# Phase F — รายงานผลรอบแรก (13 พ.ย. 2026)

## 1. สิ่งที่สร้าง

`งาน A/phase_f_preclose_forecasting/` แยกจาก Phase D โดยสมบูรณ์:

| ไฟล์ | หน้าที่ |
|---|---|
| `schema.sql` / `pfstore.py` | snapshot, page_reads, snapshot_rows, event_sequence, first_seen, forecasts (append-only), audit_runs |
| `pfsession.py` | ล็อก/ бюджет ร่วมกับ Phase D, อ่านหน้า, parse shell + published, capture, plan/session/smoke |
| `pfaudit.py` | audit 11 ข้อ + visibility gate |
| `pf.py` | CLI: init/status/schedule/smoke/session/audit/test |
| `models.py`, `scoring.py`, `walkforward.py` | baseline A/B/C, proper scoring, walk-forward |
| `baseline_run.py` | harness พิมพ์ JSON (ไม่เขียนไฟล์รายงาน) |
| `tests/` | 30 tests ผ่านทั้งหมด |

**ไม่แก้โค้ดบริการของ Phase D** — ใช้ `worker.lock`, `requests` ledger, `browser_profile`
และ `hmac.key` เดิมร่วมกัน ไฟล์เดียวที่แตะใน Phase D คือ `tests/test_stats_push.py`
เพื่อเลิก hardcode วันที่ 2026-11-10 (เทสต์พังตามเวลาที่ผ่านไป ไม่ใช่บั๊กของบริการ)

## 2. หลักฐานการมองเห็นก่อนปิด (Stage-1 gate)

ทดลองจริงกับเว็บ (อ่านอย่างเดียว ตามสิทธิ์เดิม):

| เวลา / เป้าหมาย | ผล |
|---|---|
| R66 T−5 นาที (22:10) | หน้าโหลดได้ แต่ **0 แถว** |
| R66 T+36 วินาที (22:15:36) | **0 แถว** |
| R67 T−13 นาที (มี/ไม่มี `?page=1`) | **0 แถว** |
| R68 T−25 นาที (smoke) | **0 แถว** (period 244, close 22:45 ตรง) |
| R65 (published) | **50 แถว** หน้าแรก + 3 หน้าเชื่อมโยง |

หน้า pre-close เป็น "shell" ที่มี `betconfig` (escape ใน attribute) + title + close time
แต่ไม่มี `ul.number-key-list` เลย. รายการเลขจะปรากฏเมื่อรอบถูก publish (Phase D เก็บที่
`submission_close + 10s`)

**สรุป:** เส้นทาง SSR ที่ได้รับอนุญาตไม่เปิดเผยรายการส่งเลขก่อนปิดเดิมพัน ⇒
**ห้ามอ้างผลก่อนปิด** จากข้อมูลชุดนี้ ตัวเก็บ snapshot บันทึกสถานะนี้เป็น
`PRE_CLOSE_SHELL` (ไม่ใช่ error) เพื่อให้ audit ตรวจสอบได้

## 3.ผล audit R68 (snapshot จริง)

รอบ 68 (close 22:45:00) เก็บได้ 3/5 จุด. T−30 และ T−1 ถูก **budget guard** บล็อก
(Phase D ใช้ 76/80 คำขอในชั่วโมงนั้น) — เป็นพฤติกรรมที่ออกแบบไว้เพื่อไม่ให้กระทบการเก็บผลรายรอบ

| horizon | UTC start | สถานะ | pages | rows |
|---:|---|---|---:|---:|
| 120s | 15:43:00.009Z | OK | 1 | 0 |
| 60s | 15:44:00.005Z | OK | 1 | 0 |
| 30s | 15:44:30.010Z | BUDGET (76/80) | 0 | 0 |
| 10s | 15:44:50.009Z | OK | 1 | 0 |
| 1s | 15:44:59.010Z | BUDGET (76/80) | 0 | 0 |

Audit: `passed: true` ทุกข้อ (clock ordering/agreement, pre-close bound, first-seen
prospective/earliest, pagination bounds, row integrity, order reproducible,
reorder recomputable) และ `pre_close_ready: false` เพราะ
`pre_close_snapshots_with_rows = 0`

`page_reads` เก็บ UTC + monotonic ของทุกหน้า และ import latency จริง ~170–320 ms

## 4. Baseline A/B/C + walk-forward (retrospective)

ข้อมูล: Phase D 470 รอบ COMPLETE / 6 วัน (8–13 พ.ย.), ประเมิน 440 รอบแรกหลัง `min_train=30`
ทุก forecast ใช้เฉพาะรอบก่อนหน้าเท่านั้น (strict walk-forward)

| model | log-loss | Brier | bottom2 exact | top3 exact |
|---|---:|---:|---:|---:|
| A uniform | **11.512925** | **0.999990** | 4/440 (0.91%) | 0/440 |
| B historical | 12.688423 | 1.002009 | 5/440 | 1/440 |
| C_k16 | 13.949005 | 1.004373 | 5/440 | 0/440 |
| C_k50 | 13.949005 | 1.004373 | 8/440 | 0/440 |

ด้วย shrinkage ที่เหมาะสม (prior 5000 / delta 20000) ทุกโมเดลลู่เข้าหา uniform:
B = 11.5613, C = 11.5212 (ยังแย่กว่า uniform)

**ข้อสรุป:** ไม่มีโมเดลใดชนะ uniform บน proper score; B/C แย่กว่าเพราะความเบาบาง
ของ residue 100,000 คลาส (delta ส่วนใหญ่ไม่เคยเกิดซ้ำ) การที่ C_k50 ได้ bottom2 8/440
(1.82%, p≈0.078 แบบไม่ปรับ multiple testing) เป็น noise และขัดกับ log-loss ที่แย่กว่า
(overconfident) — ไม่ใช่หลักฐาน edge

ป้ายที่แนบมากับผลทุกครั้ง:
`information_set = RETROSPECTIVE_POST_CLOSE_SIMULATION`
(ใช้ข้อมูลรอบที่ปิดแล้ว + synthetic truncation ไม่ใช่หลักฐานก่อนปิด)

## 4b. Forecast ledger

`pf.py forecast --round N --horizon H --model uniform|historical|partial` จะ freeze
คำพยากรณ์ลงตาราง `forecasts` (append-only, trigger ห้าม UPDATE/DELETE) พร้อม
snapshot hash, training cutoff, distribution float32 + hash, checksum, UTC + monotonic

กฎที่บังคับในโค้ด: **freeze ได้เฉพาะตอน `now < betting_close_at`** ถ้าเลย close แล้วจะถูก
ปฏิเสธ (`refuse_post_close_freeze`) จึงไม่มีทางเขียนคำพยากรณ์ย้อนหลัง

R68 ไม่มี forecast ถูก freeze เพราะ ณ เวลาที่ระบบพร้อม รอบปิดไปแล้ว — การ freeze ตอนนี้
จะเป็นการเขียนย้อนหลังซึ่งผิดกติกา (ledger ว่างโดยเจตนา; เทสต์ปิดช่องนี้ไว้แล้ว)

## 5. ข้อจำกัด

1. **Visibility:** ไม่สามารถเก็บ first-seen ของแถวได้จากหน้า SSR ที่อนุญาต — เป็นข้อจำกัดของเว็บ ไม่ใช่ของ collector
2. **Budget:** snapshot อาจถูกข้ามเมื่อ Phase D ใช้ budget สูง (R68 ขาด T−30/T−1)
3. **Synthetic truncation:** การตัดแถวตาม `display_sequence` ไม่เท่ากับสิ่งที่ผู้ใช้เห็นตามเวลา
4. **Sample size:** 440 รอบเพียงพอ detect เฉพาะ bottom2 edge ใหญ่ (>~1.5%); top3 ต้องการหลักพันรอบ
5. **Calibration:** ใช้ confidence calibration (max prob vs hit rate) ไม่ใช่ reliability รายคลาส
6. **Ledger:** โครงสร้าง + immutability พร้อมแล้ว แต่ยังไม่มี forecast ถูก freeze เพราะไม่มีข้อมูล
   pre-close ให้ใช้ (ห้าม freeze ย้อนหลังหลังรอบจบ)

## 6. ขั้นต่อไปที่สมเหตุสมผล

- ถ้าต้องการ pre-close จริง: ต้องหาช่องทางที่ผู้ใช้ได้รับอนุญาตและเว็บเปิดเผยจริง (เช่น export ที่เป็นทางการ)
  แล้วนำเข้าเป็น snapshot source ใหม่ — ห้ามใช้ hidden API หรือเพิ่ม rate
- คงระบบ snapshot ไว้ตรวจซ้ำเมื่อเว็บเปลี่ยนพฤติกรรม (เช่น ถ้าเริ่มแสดงรายการก่อนปิด)
- ก่อนขยายโมเดล: ยืนยันด้วย prospective lockbox หลังมี first-seen จริงหลายพันรอบ
