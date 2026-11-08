# OUT-OF-SAMPLE VALIDATION — การทดสอบแบบTrain/Validation/Test ตามเวลา

**คำถาม:** มี model ใดที่ทำนาย bottom2 ของรอบถัดไปได้ดีกว่า uniform บนข้อมูลที่ไม่ได้ใช้ fit หรือไม่?
**คำตอบสั้น:** ไม่มี; ทุก model แย่กว่า uniform บน test set

---

## 1. การแบ่งข้อมูล

แบ่งตาม **วันทำการ** (ไม่ใช่รายรอบ) เพื่อป้องกัน leakage:

| ช่วง | วันที่ | จำนวนวัน | จำนวนคู่รอบ |
|---|---|---:|---:|
| Train | 2026-08-13 → 2026-10-03 | 52 | 4,437 |
| Validation | 2026-10-04 → 2026-10-20 | 17 | 1,412 |
| Test | 2026-10-21 → 2026-11-07 | 18 | 1,503 |
| รวม | | 87 | 7,352 |

- Train ใช้ fit ทุก model
- Validation ใช้เลือก smoothing strength (alpha) เท่านั้น
- Test ถูกเปิด **ครั้งเดียว** หลังล็อก model/alpha
- ไม่มีวันใดอยู่ในสองช่วง; ไม่มีรอบใดถูกใช้ทั้ง fit และ test

---

## 2. Models ที่ทดสอบ

| Model | ตัวแปรต้น | จำนวน state |
|---|---|---:|
| Uniform | ไม่มี | 1 |
| Train marginal | ความถี่ของ bottom2 ใน train | 100 |
| Prev last digit | หลักหน่วยของ bottom2 ก่อนหน้า | 10 |
| Prev tens digit | หลักสิบของ bottom2 ก่อนหน้า | 10 |
| Prev bottom2 | bottom2 ก่อนหน้าทั้งหมด | 100 |
| Prev double | รอบก่อนเป็นเบิ้ลหรือไม่ | 2 |
| Prev sum bucket | ผลรวมหลักของ bottom2 ก่อนหน้า (4 buckets) | 4 |
| Prev top last | หลักหน่วยของ top3 ก่อนหน้า | 10 |
| Prev pair last | หลักหน่วยของ top3 + หลักหน่วยของ bottom2 | 100 |

**Smoothing:** ทุก model ใช้ Bayesian shrinkage ไปยัง train marginal:
`P(next | state) = (count(state,next) + alpha * P_marginal(next)) / (count(state) + alpha)`
เลือก alpha จาก `[1, 3, 10, 30, 100, 300, 1000]` บน validation

---

## 3. Metrics

- **Log loss** (multi-class, 100 classes): ยิ่งต่ำยิ่งดี; uniform = ln(100) = 4.60517
- **Brier score**: sum over 100 classes of `(p_i - y_i)^2`; ยิ่งต่ำยิ่งดี; uniform = 0.99
- **Top-1 accuracy**: ทำนายเลขที่มี probability สูงสุดถูกหรือไม่; uniform = 1%
- **Delta vs uniform** = model log loss − 4.60517 (ค่าบวก = แย่กว่า)
- **Day bootstrap 95% CI** ของ delta (resample 18 test days)

---

## 4. ผลบน Test set

| Model | alpha | Validation log loss | **Test log loss** | Delta vs uniform | 95% CI ของ delta | Brier | Top-1 |
|---|---:|---:|---:|---:|---|---:|---:|
| **Uniform** | — | 4.60517 | **4.60517** | 0.00000 | — | **0.9801** | **1.00%** |
| Train marginal | — | 4.61657 | 4.61214 | +0.00697 | [+0.00013, +0.01202] | 0.9901 | 0.47% |
| Prev last digit | 1000 | 4.62221 | 4.61644 | +0.01127 | [+0.00129, +0.01913] | 0.9902 | 1.06% |
| Prev tens digit | 1000 | 4.62738 | 4.62108 | +0.01591 | [+0.00360, +0.02573] | 0.9903 | 1.00% |
| Prev bottom2 | 1000 | 4.62097 | 4.61389 | +0.00872 | [+0.00088, +0.01439] | 0.9902 | 0.80% |
| Prev double | 1000 | 4.61923 | 4.61582 | +0.01065 | [−0.00017, +0.01761] | 0.9902 | 0.80% |
| Prev sum bucket | 1000 | 4.62543 | 4.61463 | +0.00946 | [+0.00164, +0.01685] | 0.9902 | 0.73% |
| Prev top last | 1000 | 4.62273 | 4.62153 | +0.01636 | [+0.00940, +0.02318] | 0.9903 | 1.06% |
| Prev pair last | 1000 | 4.61673 | 4.61174 | +0.00657 | [−0.00121, +0.01211] | 0.9901 | 0.73% |

**อ่านตาราง:**
- ไม่มี model ใดมี test log loss ต่ำกว่า 4.60517
- model ที่ดีที่สุด (prev pair last) ยังแย่กว่า +0.00657; CI คร่อม 0 → ไม่มีหลักฐานว่าแตกต่าง
- หลาย model แย่กว่าอย่างมีนัยสำคัญ (CI อยู่เหนือ 0 ทั้งช่วง)
- Brier ของทุก model > 0.9801 (uniform)
- Top-1 accuracy ใกล้ 1% ทุก model; บาง modelได้ 1.06% แต่ไม่ต่างจาก chance (1,503 แถว, SE ~0.26pp)
- alpha ที่เลือก = 1000 หมายถึง validation บอกให้ shrink เกือบทั้งหมดไปที่ marginal; นี่เป็นสัญญาณว่า conditional state ไม่มีข้อมูล

---

## 5. Data leakage / look-ahead checks

| การตรวจ | ผล |
|---|---|
| ใช้ข้อมูลอนาคตใน train? | ไม่; train จบ 2026-10-03 |
| ใช้ test เลือก model/alpha? | ไม่; alpha เลือกบน validation |
| ใช้ผลของ target ในการสร้าง feature? | ไม่; feature มาจากรอบก่อนหน้าเท่านั้น |
| ใช้ `first_result_posted` เป็นเวลา predict? | ไม่; ใช้ scheduled_close + round |
| ใช้ site-filled gaps ใน train/test? | ไม่; primary ใช้ LINE-only dataset |
| ตรวจซ้ำด้วย site-complete dataset? | ใช่ (sensitivity) ผลยังเป็น null |
| จำนวนรอบต่อวันไม่เท่ากัน? | ใช่; ใช้ pair ที่มีอยู่จริง ไม่เติมค่า |

---

## 6. Sensitivity: site-complete dataset

รัน image-rule backtest ซ้ำบน `site_complete_results_clean.csv` (7,466 รอบ; เติม 171 gaps จากเว็บ, ตัด 2 วันที่หน้าเว็บผิดปกติ):

| rule | LINE-only | site-complete |
|---|---|---|
| R01 | 5/81 (6.17%) | 5/79 (6.33%) |
| R06 (หาม) | 185/686 (26.97%) | 186/679 (27.39%) |
| R07 (ตอง) | 18/72 (25.00%) | 17/71 (23.94%) |
| R11 (หลังหาม) | 237/686 (34.55%) | 238/679 (35.05%) |
| R12 (หลังเบิ้ล 8) | 143/730 (19.59%) | 146/732 (19.95%) |
| R17 (4 ร้อยบน) | 205/732 (28.01%) | 208/743 (27.99%) |
| I1 (ชุดหลังเบิ้ล) | 49/730 (6.71%) | 47/732 (6.42%) |
| I2a (ชุดหลัง 69) | 5/75 (6.67%) | 6/77 (7.79%) |

**สรุป:** การเติม gaps ไม่เปลี่ยนข้อสรุป; ทุก rule ยัง null

---

## 7. ทำไม model ไม่ทำงาน

1. **ผลยี่กีถูกออกแบบให้เป็น deterministic จาก pool ที่ไม่รู้** — ผลรวมของเลขที่ผู้เล่นส่ง + การลบ row 16 ทำให้ผลขึ้นกับ input ที่ยังไม่เกิด ณ เวลาทำนาย
2. **ผลลัพธ์ใกล้ uniform** — marginal tests ไม่ reject uniformity; transition ไม่มี autocorrelation
3. **State ที่ลองเป็นข้อมูลอดีตที่หยาบเกินไป** — bottom2 100 state, last digit 10 state; sample ต่อ state ไม่พอ
4. **Smoothing ที่ validation เลือกสูงมาก** — บอกว่า conditional distribution ไม่ต่างจาก marginal
5. **Test set อยู่ในช่วงเวลาที่ต่างจาก train** — ถ้ามี regime change ก็จะทำให้แย่ลง

---

## 8. เกณฑ์ที่จะถือว่า “มี predictive skill” ในอนาคต

ถ้าจะทดสอบใหม่ ให้ล็อกก่อนเก็บข้อมูล:

1. **Primary metric:** log loss ของ bottom2 (หรือ digit-level ตามคำอ้าง)
2. **Baseline:** uniform + empirical marginal
3. **Success threshold:** test log loss ต่ำกว่า uniform อย่างมีนัยสำคัญ และ CI ของ delta ทั้งช่วงต่ำกว่า 0
4. **Sample size:** คำนวณ power สำหรับ effect ที่สนใจ; อย่างน้อย 5,000–10,000 รอบ
5. **Multiple testing:** จำนวน model/hypothesis ต้องถูกนับและแก้
6. **Prospective:** เก็บข้อมูลหลังล็อก; ห้ามใช้ test เลือก model
7. **รายงานทั้ง success และ failure** — รวมถึง model ที่ไม่ผ่าน

> **ข้อสรุป:** ข้อมูลชุดนี้และ model ที่ทดสอบไม่สนับสนุนความสามารถทำนายผลยี่กี; ค่า log loss ที่แย่กว่า uniform บน test set เป็นหลักฐานเชิงประจักษ์ว่า simple state models ไม่มีข้อมูล predictive ที่ใช้ได้
