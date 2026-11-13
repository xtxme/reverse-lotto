# งาน C — Phase F: Pre-close Forecasting Research

โฟลเดอร์งานที่สามของ repository แยกจาก `งาน A/` และ `work_b/` ตามคำขอของผู้ใช้

โค้ดและเอกสารอยู่ใน [phase_f_preclose_forecasting](phase_f_preclose_forecasting/README_TH.md)
เป็นสำเนาเพื่อเผยแพร่ของ Phase F ที่พัฒนาโดย OpenCode; ตำแหน่งบริการในเครื่องยังคงเดิม

## สถานะ

- Research prototype: ยังไม่มีหลักฐาน prospective ว่าทำนายก่อนปิดเดิมพันได้ดีกว่าสุ่ม
- เส้นทาง SSR ที่ทดลองไม่แสดงรายการก่อนปิด; ยังไม่ได้พิสูจน์การมองเห็นทุกช่องทางของเว็บ
- ไม่ได้ติดตั้ง scheduler ของ Phase F ตามรายงานที่ส่งมอบ
- ตรวจ source และรันชุดทดสอบเดิมได้ 35/35 ข้อ เมื่อมี Phase D และสิทธิ์อ่าน SQLite ตามที่เทสต์ใช้
- ยังมีข้อค้นพบจาก code review ที่ต้องแก้ก่อนใช้ ledger เป็นหลักฐานล่วงหน้า ดู [REVIEW_STATUS_TH.md](REVIEW_STATUS_TH.md)

## การติดตั้งและขอบเขต

Phase F พึ่งพาโค้ด Phase D และ private configuration/session ที่มีอยู่ในเครื่อง
สำเนานี้ไม่ได้รวม Phase D runtime หรือข้อมูลส่วนตัว จึงไม่ใช่ระบบ standalone ที่ clone แล้วเปิดเก็บได้ทันที
ปรับ `phase_d_root`, `phase_d_config`, `state_dir` ตามเครื่องจริง; ตำแหน่ง `/Users/icy/...`
ในโค้ดเดิมเป็นตำแหน่งอ้างอิงของเครื่องพัฒนา ไม่ใช่ credential

เก็บเฉพาะ source, tests, schema, example config และรายงานสรุป
ไม่รวมฐานข้อมูล, snapshots, browser profile, keys, cookies, config จริง, LINE ดิบ หรือ virtual environment

