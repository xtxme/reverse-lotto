# Pattern discovery
ทั้งหมดเป็น retrospective reanalysis ของข้อมูลที่เคยถูกตรวจแล้ว ไม่มี untouched/prospective test ใหม่ การแบ่งเวลาและการล็อกโค้ดในรอบนี้ไม่สามารถทำให้ลืมผลที่เคยเห็นได้ อัตราเข้าเป็นสถิติของ outcome ที่นิยาม ไม่ใช่ผลกำไรหรือความสามารถรู้เลขทั้งชุด

สคริปต์ส่วนหนึ่งต่อยอดโครงสร้างจาก OpenCode หลังอ่านโค้ดทั้งหมดและแก้ข้อผิดพลาด พร้อม regression tests จึงไม่ใช่การยืนยันจาก analyst/dataset อิสระใหม่ทั้งหมด รายงานระบุสิ่งที่คำนวณซ้ำ สิ่งที่เป็นหลักฐานไฟล์ และสิ่งที่ยังไม่ทราบแยกกัน

| Family | Tests |
|---|---|
| A_marginal | 2 |
| B_lag | 12 |
| C_position | 20 |
| D_state | 20 |
| E_time | 10 |
| F_same_round | 8 |
| G_conditional | 4 |

ผลใหม่ 76 tests, 7,469 ผล, 7,352 คู่ติดกัน; nominal p<0.05 = 5; BH q<0.05 = 0; smallest q=0.72803

| Test | n | p | BH q | effect |
|---|---|---|---|---|
| after_69 | 75 | 0.013986 | 0.72803 | TVD=0.5287 |
| bottom_units_lag3 | 7127 | 0.034782 | 0.72803 | 0.0406 |
| top_hundreds_eq_bottom_tens | 7469 | 0.039034 | 0.72803 | 0.007243272191725797 |
| after_double | 730 | 0.043956 | 0.72803 | TVD=0.1601 |
| top_tens_lag1 | 7352 | 0.047897 | 0.72803 | 0.0395 |
| bottom_units_lag2 | 7239 | 0.071371 | 0.90403 | 0.0392 |
| even_bottom_lag2 | 7239 | 0.086148 | 0.93532 | 0.0204 |
| top_units_eq_bottom_tens | 7469 | 0.15916 | 0.93968 | -0.004940420404337939 |
| top_tens_lag4 | 7017 | 0.16493 | 0.93968 | 0.0384 |
| top3_pos1_by_weekday | 7469 | 0.1785 | 0.93968 | 0.0376 |
| bottom_tens_lag1 | 7352 | 0.18029 | 0.93968 | 0.0374 |
| double_lag2 | 7239 | 0.18884 | 0.93968 | 0.0162 |

รายงานทุกสมมติฐานรวมผลล้มเหลวใน outputs/PATTERN_DISCOVERY_TESTS.csv
Marginal ใช้ Monte Carlo 500 ครั้ง; 100×100 transition ใช้ within-day permutation 5,000 ครั้ง; position/time ใช้ chi-square; rare 2×2 states ใช้ Fisher exact แทน chi-square sparse; conditional distribution ใช้ target marginal จริงและ permutation 1,000 ครั้ง
lag 1–4 ต้องมี round ต่อกันจริง ไม่ข้าม missing rows หรือข้าม trading day
binomial/chi-square/Fisher และ permutation ยังมี independence/exchangeability assumptions ไม่ใช่หลักฐานว่าทุก time-series dependence ถูกกำจัดแล้ว

## ข้อสรุปที่อนุญาต
ยังไม่พบ predictive pattern ที่ผ่าน family นี้ ไม่ใช่พิสูจน์ว่าผลสุ่มสมบูรณ์ หรือว่าทุก nominal finding เป็นความบังเอิญแน่นอน
after-69 distribution test กับการทดสอบชุด 9 ตัวหลัง 69 เป็นคนละสมมติฐาน ต้องไม่ยกผลข้อหนึ่งไปรับรองอีกข้อ
ไม่ได้ค้นโมเดลเพิ่มหลังดู test เพื่อสร้างเลขที่ดูแม่น
