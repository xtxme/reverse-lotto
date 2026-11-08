# Relationship to website research
อ่าน source จาก GitHub ที่ผู้ใช้ระบุผ่าน connector และเก็บ snapshot ใน evidence/ พร้อม source manifest ของเอกสารหลัก

| Claim | ระดับที่ยืนยันได้ในงานนี้ |
|---|---|
| 88 รอบ, close ทุก 15 นาที, shoot close+2 | รายงาน/หลักฐานงาน A ระบุไว้; ไม่ได้วัดเว็บใหม่ |
| R=Σx−x16, five-digit extraction | ตรวจเลขคณิตตัวอย่างในรายงานได้; production internals ยังไม่ทราบ |
| x16 เป็น display row ใหม่→เก่า | รายงานงาน A สนับสนุน; tie-break จาก timestamp อย่างเดียวไม่ทราบ |
| input final ยังไม่ครบก่อน close | งาน A/B/C รายงาน pool ยังเพิ่มหลัง close; ไม่พอคำนวณตรงล่วงหน้า |
| 60-second polling | Phase B แก้คำอ้าง Phase A: detail poll list/sum จริง แต่ไม่ใช่ result-state polling |
| archive ย้อนหลัง 88 รอบ | **ข้อขัดแย้งยังไม่คลี่คลาย**: Phase C บอก UI ไม่มี archive; Work B อ้างตรวจ 87 วัน |

## หลักฐานที่ต้องตรวจต่ออันดับแรก
เก็บ URL ที่ตัด credential แล้ว, capture timestamp, requested/effective date, product/category ID, heading และ DOM รอบข้างของข้อมูลผล เพื่อพิสูจน์ว่าเป็นสินค้า 88 รอบ วันตามที่อ้าง; ติด hash ไฟล์และเก็บผลจากคนละแหล่งที่เป็นอิสระ
ห้ามใช้ archive ของจับยี่กีทันใจ 264 รอบแทนสินค้า 88 รอบ แม้มีเลขรอบและชื่อคล้ายกัน
JSON เก่ามีหลายผลิตภัณฑ์อยู่ด้วยกันและไม่มี provenance metadata; การตรงกับ LINE ยังไม่ปิดข้อสงสัยนี้

การรู้สูตร deterministic เมื่อ pool final ไม่ใช่การรู้ final input ก่อนปิดเดิมพัน อย่างไรก็ดี input ไม่ครบไม่ใช่ข้อพิสูจน์ว่าไม่มี public statistical signal ใดเลย ต้องทดสอบตัวแปรที่มี timestamp ก่อน cutoff แยกต่างหาก ไม่ใช้ final sum/row16 หรือ first-seen หลังปิดเป็น feature
ไม่เข้าถึง Backend/DB/secret และไม่ใช้ REA กับ LINE ที่มีอยู่แล้ว

## Sources
- https://github.com/xtxme/reverse-lotto/blob/main/result_algorithm_research.md
- https://github.com/xtxme/reverse-lotto/blob/main/round_schedule.md
- https://github.com/xtxme/reverse-lotto/blob/main/submissions_analysis.md
- https://github.com/xtxme/reverse-lotto/blob/main/timing_analysis.md
- https://github.com/xtxme/reverse-lotto/blob/main/phase_b/PHASE_B_FINAL_REPORT.md
- https://github.com/xtxme/reverse-lotto/blob/main/phase_c/PHASE_C_FINAL_REPORT.md
