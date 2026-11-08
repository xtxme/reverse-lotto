# Corrections and limitations

1. ไม่มี target/ข้ามรอบขาด → None และ exclude แทน False; denominator จึงเปลี่ยน R06 686→663, R07 72→71, R08 738→730, R17 732→720 ฯลฯ
2. ข้อ 11 จากภาพใช้ next round เป็น primary; skip-one เป็น sensitivity เท่านั้น
3. permutation p คำนวณหลังรวมทุกวัน ไม่คืนค่าก่อนวันสุดท้ายที่ degenerate
4. trigger-dependent digit/triple targets สลับ future outcomes ทั้งก้อนแทนสลับ trigger labels; empirical null rate สำหรับกลุ่มนี้ใช้ permutation mean/triggers
5. uniform Brier รวมทั้ง 100 classes =0.99; bootstrap OOS ใช้ weighted estimand เดียวกับ LL
6. sparse 2×2 state tests ใช้ Fisher exact; conditional marginal ใช้ target ไม่ใช่ origin
7. แยก full outcome Bonferroni และ Holm; ไม่เรียกทุก hourly outcome null และไม่สรุปว่า top positive เป็น noise แน่นอน
8. แยก capture-match ออกจาก server verification และระบุ archive contradiction
9. run_all ใหม่สร้าง deliverables ทุกไฟล์และรายงานที่มาสคริปต์ ไม่อ้างว่า gitignore เดิมกัน data/ ทั้งหมด

ข้อจำกัดการออกแบบ: permutation ภายในวันสมมติ exchangeability; day bootstrap ยังสมมติ cross-day independence โดยประมาณ; exploratory families หลายชุดไม่ใช่ family เดียวที่ pre-register ก่อน dataset เกิด; ไม่ทดลองทุกความหมายแบบ combinatorial; ภาพไม่มี original publication timestamp และไม่มี edit history ของ LINE
