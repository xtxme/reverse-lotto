# Chronological validation — retrospective reanalysis
ทั้งหมดเป็น retrospective reanalysis ของข้อมูลที่เคยถูกตรวจแล้ว ไม่มี untouched/prospective test ใหม่ การแบ่งเวลาและการล็อกโค้ดในรอบนี้ไม่สามารถทำให้ลืมผลที่เคยเห็นได้ อัตราเข้าเป็นสถิติของ outcome ที่นิยาม ไม่ใช่ผลกำไรหรือความสามารถรู้เลขทั้งชุด

สคริปต์ส่วนหนึ่งต่อยอดโครงสร้างจาก OpenCode หลังอ่านโค้ดทั้งหมดและแก้ข้อผิดพลาด พร้อม regression tests จึงไม่ใช่การยืนยันจาก analyst/dataset อิสระใหม่ทั้งหมด รายงานระบุสิ่งที่คำนวณซ้ำ สิ่งที่เป็นหลักฐานไฟล์ และสิ่งที่ยังไม่ทราบแยกกัน

Train ['2026-08-13', '2026-10-03'] = 4437 pairs; validation ['2026-10-04', '2026-10-20'] = 1412; test ['2026-10-21', '2026-11-07'] = 1503 pairs
แยกตาม trading day 52/17/18 วัน ปรับ alpha ด้วย validation เท่านั้น โมเดลใช้ feature ของรอบก่อน target; ไม่มีการ fill gaps จาก capture ใน primary
ชุด test นี้เคยถูกอ่านและวิเคราะห์แล้ว จึงตรวจ implementation ของ chronological split ได้ แต่ไม่รับรองว่าการพัฒนาสมมติฐานทั้งโครงการไม่เคยอาศัย test

| Model | Validation LL | Test LL | Brier | Top1 observed/reference |
|---|---|---|---|---|
| uniform | 4.60517 | 4.60517 | 0.9900000 | 1.00% theoretical |
| train_marginal | 4.61657 | 4.61214 | 0.9901452 | 0.47% |
| prev_lastdigit | 4.62221 | 4.61644 | 0.9902321 | 1.06% |
| prev_tensdigit | 4.62738 | 4.62108 | 0.9903364 | 1.00% |
| prev_bottom2 | 4.62097 | 4.61389 | 0.9901790 | 0.80% |
| prev_double | 4.61923 | 4.61582 | 0.9902136 | 0.80% |
| prev_sum_bucket | 4.62543 | 4.61463 | 0.9902055 | 0.73% |
| prev_top_last | 4.62273 | 4.62153 | 0.9903233 | 1.13% |
| prev_pair_last | 4.61673 | 4.61174 | 0.9901367 | 0.73% |

Uniform log loss = ln(100)=4.60517; Brier ที่ถูกต้อง = 0.99 ไม่ใช่ 0.9801
ผลทั้งหมดมี LL สูงกว่า uniform โมเดลดีที่สุดในชุดนี้อาจดีกว่า empirical marginal เพียงเล็กน้อย ไม่ใช่หลักฐานชนะทั้งสอง baseline
Paired day-cluster bootstrap CI (10,000) และ sign-flip diagnostics (20,000; สมมติ day errors independent/symmetric) เปรียบเทียบทั้ง uniform และ train marginal อยู่ OOS_PAIRED_COMPARISONS.csv ใช้ Holm across 15 comparisons
| Model | Baseline | Delta LL | 95% CI | Holm p improvement |
|---|---|---|---|---|
| train_marginal | uniform | 0.0069696 | [0.0012582,0.012708] | 1 |
| prev_lastdigit | uniform | 0.011266 | [0.002111,0.019592] | 1 |
| prev_lastdigit | train_marginal | 0.0042967 | [-0.0022418,0.010059] | 1 |
| prev_tensdigit | uniform | 0.015906 | [0.0047577,0.026762] | 1 |
| prev_tensdigit | train_marginal | 0.0089367 | [0.0012319,0.016799] | 1 |
| prev_bottom2 | uniform | 0.0087159 | [0.0020338,0.014744] | 1 |
| prev_bottom2 | train_marginal | 0.0017462 | [-0.0015022,0.0050117] | 1 |
| prev_double | uniform | 0.010652 | [0.0029994,0.017858] | 1 |
| prev_double | train_marginal | 0.0036823 | [0.00031165,0.0068307] | 1 |
| prev_sum_bucket | uniform | 0.0094586 | [0.0016262,0.017068] | 1 |
| prev_sum_bucket | train_marginal | 0.002489 | [-0.0029496,0.007788] | 1 |
| prev_top_last | uniform | 0.016365 | [0.0093579,0.023591] | 1 |
| prev_top_last | train_marginal | 0.0093952 | [0.0020814,0.017796] | 1 |
| prev_pair_last | uniform | 0.0065666 | [0.00015984,0.01261] | 1 |
| prev_pair_last | train_marginal | -0.000403 | [-0.0044355,0.0033935] | 1 |

CI resample day sums/counts เพื่อให้ตรงกับ observation-weighted headline LL มีเพียง 18 test days จึงจำกัดความแม่นของ interval
alpha=1000 คือค่าที่ดีที่สุดใน grid ที่ลอง ไม่พิสูจน์ว่า conditional state ไม่มีข้อมูลทุกชนิด
**ขอบเขต:** โมเดลเหล่านี้ทำนาย bottom2 รอบถัดไป ผลล้มเหลวของโมเดลนี้ไม่ใช่การหักล้างผู้ให้เลข top-digit รายชั่วโมงโดยตรง ดู late hourly diagnostic แยกใน HOURLY_FORECAST_AUDIT.md
