# PATTERN DISCOVERY REPORT — การค้นหา pattern ที่ตรวจซ้ำได้

**คำถาม:** มีความสัมพันธ์ใดระหว่างผลรอบก่อนกับรอบถัดไป ที่ตรวจซ้ำได้และไม่ใช่ความบังเอิญหรือไม่?
**คำตอบสั้น:** ไม่พบ pattern ใดที่รอดจากการแก้ multiple testing; มี 4 การทดสอบที่ nominal p < 0.05 จาก 76 การทดสอบ แต่ smallest BH q = 0.805 และ effect size เล็กมาก

---

## 1. ข้อมูลและหน่วยวิเคราะห์

| รายการ | ค่า |
|---|---:|
| ผลไม่ซ้ำ | 7,469 รอบ |
| วันทำการ | 87 วัน |
| คู่รอบติดกัน (15 นาที, วันเดียวกัน) | 7,352 คู่ |
| ช่วงวันที่ | 2026-08-13 ถึง 2026-11-07 |
| หน่วยของ lag | รอบ (15 นาที) ไม่ใช่วัน |
| การจัดการวันข้ามเที่ยงคืน | ใช้ trading_day + round; ไม่ให้ lag ข้ามวัน |

**ข้อสำคัญ:** การทดสอบ lag 1–4 ใช้เฉพาะคู่ที่อยู่ติดกันจริงในวันเดียวกัน; จำนวน n จึงลดลงตาม lag (7,352 → 7,017)

---

## 2. Family ของการทดสอบ (76 tests)

| Family | จำนวน tests | สิ่งที่ทดสอบ |
|---|---:|---|
| A_marginal | 2 | bottom2, top3 uniform |
| B_lag | 12 | repeat ของ bottom2 / หลักหน่วย, transition 100×100, lag 1–4 |
| C_position | 20 | transition ของ 5 ตำแหน่ง (บน 3, ล่าง 2) × lag 1–4 |
| D_state | 20 | double, triple, sibling, sum10, even × lag 1–4 |
| E_time | 10 | digit frequency ตามชั่วโมง/วันในสัปดาห์ |
| F_same_round | 8 | ความสัมพันธ์บน–ล่างในรอบเดียวกัน |
| G_conditional | 4 | การกระจายของ bottom2 ถัดไปหลัง trigger ที่ชื่อ |

### 2.1 วิธีทดสอบ

- **Chi-square / permutation:** สำหรับตาราง transition 100×100 หรือ 10×10 ใช้ chi-square statistic และ permutation ภายในวัน (รักษาการกระจายของ target ต่อวัน)
- **Binomial:** สำหรับ repeat rate เทียบกับ 1/100 หรือ 1/10
- **TVD permutation:** สำหรับ conditional distribution เทียบกับ marginal
- **Multiple testing:** Benjamini–Hochberg (BH) q-value across all 76 tests
- **Effect size:** Cramér's V, mutual information, TVD, lift

---

## 3. ผลรวม

| ตัวชี้วัด | ค่า |
|---|---:|
| จำนวน tests | 76 |
| p < 0.05 (nominal) | 4 |
| q < 0.05 (BH) | **0** |
| smallest p | 0.0140 |
| smallest q | **0.805** |

> **แปลความ:** ถ้ามี 76 tests และไม่มี signal จริง เราคาดว่าจะเห็น p<0.05 ประมาณ 3–4 ครั้งจาก chance; จำนวนที่เห็น (4) จึงตรงกับ null มาก

---

## 4. ผลของแต่ละ family

### 4.1 A — Marginal uniformity

| test | n | statistic | p | q |
|---|---:|---:|---:|---:|
| bottom2 uniform (100 ช่อง) | 7,469 | 84.82 | 0.838 | 0.966 |
| top3 uniform (1,000 ช่อง) | 7,469 | 1,019.28 | 0.327 | 0.965 |

- bottom2 ทั้ง 100 เลขปรากฏครบ; min 54 ครั้ง, max 96 ครั้ง, expected 74.7
- top3 ปรากฏ 999 จาก 1,000 ค่า
- **สรุป:** ผลรวม-level distribution สอดคล้องกับ uniform มาก

### 4.2 B — Lag repeats / transitions

| test | n | observed | expected | p | q |
|---|---:|---:|---:|---:|---:|
| bottom2 exact repeat lag1 | 7,352 | 69 | 73.52 | 0.639 | 0.966 |
| bottom2 exact repeat lag2 | 7,239 | 81 | 72.39 | 0.315 | 0.965 |
| bottom2 exact repeat lag3 | 7,127 | 63 | 71.27 | 0.371 | 0.965 |
| bottom2 exact repeat lag4 | 7,017 | 71 | 70.17 | 0.904 | 0.966 |
| last-digit repeat lag1 | 7,352 | 708 | 735.2 | 0.303 | 0.965 |
| last-digit repeat lag2 | 7,239 | 703 | 723.9 | 0.422 | 0.965 |
| last-digit repeat lag3 | 7,127 | 692 | 712.7 | 0.430 | 0.965 |
| last-digit repeat lag4 | 7,017 | 677 | 701.7 | 0.340 | 0.965 |

- transition 100×100: Cramér's V ≈ 0.114–0.119, ใกล้ค่าสุ่ม (random V สำหรับ 100×100, n=7,352 คือ ~0.116)
- **สรุป:** ไม่มี autocorrelation ที่ใช้ได้; การ repeat เกิดใกล้ค่าคาดหวัง

### 4.3 C — Position transitions

20 tests (5 positions × 4 lags). Nominal ที่เล็กที่สุด:

| test | n | chi2 | p | q | Cramér's V |
|---|---:|---:|---:|---:|---:|
| bottom_units lag3 | 7,127 | 105.57 | 0.0348 | 0.805 | 0.0406 |
| top_tens lag1 | 7,352 | 103.32 | 0.0479 | 0.805 | 0.0395 |
| bottom_units lag2 | 7,239 | 100.36 | 0.0714 | 0.903 | 0.0392 |
| top_tens lag4 | 7,017 | 93.32 | 0.165 | 0.965 | 0.0384 |

- Cramér's V ~0.04 = effect เล็กมาก (อธิบาย variance ได้ <0.2%)
- หลัง BH ไม่มีตัวใดรอด
- **สรุป:** ไม่มี position-based transition ที่ reproducibly ใช้ได้

### 4.4 D — State transitions

| state | lag1 p | lag2 p | lag3 p | lag4 p | หมายเหตุ |
|---|---:|---:|---:|---:|---|
| double | 0.926 | 0.168 | 0.402 | 0.828 | ไม่มี clustering |
| triple top | 0.691 | 0.420 | 0.615 | 0.615 | sample น้อย |
| sibling bottom | 0.815 | 0.895 | 0.426 | 0.662 | ไม่มี |
| sum10 | 0.925 | 0.521 | 0.700 | 0.457 | ไม่มี |
| even bottom | 0.399 | 0.083 | 0.949 | 0.750 | ไม่มี |

- หลัง double แล้ว double อีก: อัตรา ~10% ตาม baseline
- หลัง triple แล้ว triple อีก: แทบไม่เกิด
- **สรุป:** state ไม่มี memory ที่ใช้ทำนายได้

### 4.5 E — Time-of-day / day-of-week

- 10 tests (5 positions × 2 มิติ)
- ไม่มีตัวใดมี q < 0.9
- digit frequency ตามชั่วโมงส่วนใหญ่ใกล้ uniform; chi2 รายชั่วโมงอยู่ที่ 3–20 (df=9) และไม่มีตัวใดรอดหลังแก้ 22 ชั่วโมง
- **สรุป:** ไม่มี time-of-day bias ที่ reproducibly ใช้ได้

### 4.6 F — Same-round relations

| test | n | observed | expected | p | q | effect |
|---|---:|---:|---:|---:|---:|---:|
| top hundreds = bottom tens | 7,469 | 801 | 746.9 | 0.039 | 0.805 | +0.72 pp |
| top units = bottom tens | 7,469 | 710 | 746.9 | 0.159 | 0.965 | −0.49 pp |
| top3 has duplicate | 7,469 | 2,093 | 2,091 | 0.969 | 0.982 | +0.02 pp |
| top3 triple | 7,469 | 72 | 74.7 | 0.816 | 0.966 | −0.04 pp |

- ความสัมพันธ์เดียวที่ nominal คือ top hundreds = bottom tens (10.72% vs 10%)
- effect +0.72 pp; q=0.805; ไม่ใช่หลักฐานที่ใช้ได้
- **สรุป:** บน–ล่างในรอบเดียวกันเกือบ independent

### 4.7 G — Conditional distributions

| trigger | n | TVD vs marginal | p | q | หมายเหตุ |
|---|---:|---:|---:|---:|---|
| after 69 | 75 | 0.530 | 0.014 | 0.805 | sample เล็ก; ชุด 9 ตัวที่อ้างไม่ significant |
| after double | 730 | 0.159 | 0.053 | 0.805 | ชุด 7 ตัวที่อ้างไม่ significant |
| after 65 | 78 | — | >0.05 | — | sample เล็ก |
| after sum10 | 686 | — | >0.05 | — | ไม่มี |

- `after 69` มี TVD สูงเพราะ n=75 กับ 100 categories; การทดสอบชุดเฉพาะ (56,58,59,68,69,76,78,79,89) ได้ 5/75 = 6.67% vs 9% (p=0.82)
- `after double` TVD 0.159 (เล็ก) และชุด 7 ตัวได้ 49/730 = 6.71% vs 7% (p=0.64)
- **สรุป:** การกระจายอาจดูต่างจาก marginal เล็กน้อย แต่เมื่อทดสอบชุดที่อ้างจริง กลับไม่ต่างจากสุ่ม

---

## 5. Pattern ที่ “ดูเหมือนมี” แต่เป็นความบังเอิญ

| pattern | หลักฐาน nominal | ทำไมไม่ควรเชื่อ |
|---|---|---|
| หลัง 69 แล้ว bottom2 กระจายต่าง | p=0.014 | n=75; 100 categories; ชุดที่อ้าง 5/75 vs 9% p=0.82; q=0.805 |
| top tens lag1 | p=0.048 | V=0.039; ไม่มี mechanism; q=0.805 |
| bottom units lag3 | p=0.035 | V=0.041; lag 3 ไม่มี rationale; q=0.805 |
| top hundreds = bottom tens | p=0.039 | +0.72 pp; q=0.805; อาจเป็น sampling noise |
| after double distribution | p=0.053 | TVD 0.159; ชุดที่อ้าง null |

**หลักคิด:** เมื่อทดสอบ 76 ครั้ง ค่า p ที่เล็กที่สุดควรอยู่ราว 1/76 ≈ 0.013 ถ้า null จริง; ค่าที่เห็น 0.014 จึงแทบ будет perfect null expectation

---

## 6. Pattern ที่ “ตรวจซ้ำได้” ในความหมายที่แคบ

มีเพียงสิ่งเหล่านี้ที่ “เสถียร” และควรถือเป็นข้อเท็จจริงเชิงพรรณนา ไม่ใช่ predictive edge:

1. **ผลรวม-level distribution ใกล้ uniform** — bottom2 ครบ 100 เลข, top3 เกือบครบ 1,000
2. **ไม่มี autocorrelation ที่ lag 1–4** — repeat rate ใกล้ 1/100 และ 1/10
3. **ไม่มี state clustering** — double/triple/sibling/sum10 ไม่ทำนายรอบถัดไป
4. **บน–ล่างเกือบ independent** — ยกเว้น top hundreds = bottom tens ที่ +0.72 pp (ไม่ significant)
5. **ตารางเลขนิ่งรายชั่วโมงมี human digit preference** — 1/9 บ่อย, 6 เลี่ยง; ไม่ได้ derive จากผล

---

## 7. ข้อจำกัด

| ข้อจำกัด | ผล |
|---|---|
| ข้อมูล retrospective | ไม่ใช่ prospective test |
| 7,469 รอบอาจไม่พอสำหรับ effect <1 pp | power ต่ำสำหรับ effect เล็กมาก |
| หลาย hypothesis | ต้องแก้ multiple testing; ทำแล้ว |
| ผลอาจไม่ independent ภายในวัน | ใช้ permutation ภายในวัน |
| ไม่มี covariate อื่น (pool, เวลา, ผู้เล่น) | ไม่สามารถแยก mechanism |
| ผลรวมถูกกำหนดจาก pool ที่ไม่รู้ | การทำนายเชิงสาเหตุเป็นไปไม่ได้จากข้อมูลนี้ |

---

## 8. สิ่งที่ต้องทำเพื่อพิสูจน์ pattern ในอนาคต

1. **Pre-register** hypothesis ก่อนเก็บ data: ระบุ field, lag, target, ทิศทาง, จำนวนตัวอย่างขั้นต่ำ
2. **เก็บ prospective** อย่างน้อย 30–60 วันหลังล็อกสมมติฐาน
3. **Hold-out** แบบ chronological; ห้ามใช้ test เลือกสูตร
4. **แก้ multiple testing** ตามจำนวน tests ที่วางแผนไว้
5. **รายงาน effect size + CI** ไม่ใช่แค่ p-value
6. **ทดสอบกับข้อมูลใหม่ที่ไม่มีอยู่ใน dataset นี้** (เช่น หลัง 2026-11-07)
7. **ถ้าจะอ้าง predictive skill** ต้องเทียบกับ uniform และ empirical baseline, และต้องมี log loss/Brier ที่ดีกว่าอย่างมีนัยสำคัญ

> **ข้อสรุป:** ข้อมูลชุดนี้ไม่สนับสนุน pattern ที่ใช้ทำนายผลยี่กีได้จริง; สิ่งที่เห็นเป็นความบังเอิญหรือ effect เล็กมากที่ยังไม่ reproducible
