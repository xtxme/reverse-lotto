# งาน B — LINE Pattern Discovery & Forecast Validation

โฟลเดอร์นี้รวมงาน B ทุกระยะไว้ใน repo เดียวกับงาน A แต่แยกขอบเขตชัดเจน
งาน B ศึกษาคำทำนายรายชั่วโมงและสูตรในภาพจาก LINE ส่วน phase_b/ และ phase_c/ ที่ระดับ root เป็นระยะวิจัยเว็บไซต์ของงาน A ไม่ใช่งาน B ของ LINE

## เริ่มอ่าน
**ฉบับล่าสุด:** [ผลตรวจอิสระและแก้ไข](03_independent_validation/FINAL_INDEPENDENT_REPORT_TH.md)

| ระยะงาน B | เนื้อหา | สถานะ |
|---|---|---|
| [01_initial_audit](01_initial_audit/) | Research starter และผลตรวจเริ่มต้น | เก็บเพื่อย้อนประวัติ; มีนิยาม/ข้อจำกัดเดิม |
| [02_opencode_review](02_opencode_review/) | รายงานและผลที่ OpenCode ส่งมอบ | เก็บฉบับเดิม; ไม่ใช่ผลแก้ไขล่าสุด |
| [03_independent_validation](03_independent_validation/) | ตรวจ raw ใหม่ แก้ backtest/Brier และตรวจ sensitivity | ใช้เป็นจุดอ้างอิงล่าสุด |

ฉบับเก่าอาจมีจำนวนตัวอย่าง นิยามสูตร และข้อสรุปต่างจากฉบับล่าสุด โปรดอ่าน [รายการแก้ไขและข้อจำกัด](03_independent_validation/CORRECTIONS_AND_LIMITATIONS.md)
ทุกระยะเป็น retrospective; ไม่ใช่หลักฐานทำนายอนาคตหรือคำแนะนำเดิมพัน ไม่มีการรับประกันผลรางวัล

## ข้อมูลส่วนตัว
ไม่รวม LINE ดิบ รูป/ข้อความแชตส่วนตัว cookie/token หรือ capture ที่ยังไม่ผ่านการคัดกรอง ชื่อผู้โพสต์ถูกแทนด้วย alias และคอลัมน์ชื่อถูกตัดจาก CSV ที่เผยแพร่
เก็บเฉพาะผลตัวเลข ตารางสถิติ รายงาน และโค้ดสำหรับตรวจซ้ำ Source line ใช้อ้างกลับไฟล์ส่วนตัวของเจ้าของข้อมูลเท่านั้น
การรัน parser ฉบับล่าสุดต้องกำหนด LINE_EXPORT_PATH และ LINE_SENDERS_FILE (JSON array รายชื่อผู้ส่งที่เก็บในเครื่อง) รวมถึง WORK_B_INPUT_DIR สำหรับ starter inputs; SITE_CAPTURE_DIR เป็นตัวเลือก
ตัวอย่าง: `LINE_EXPORT_PATH=/private/LINE.txt LINE_SENDERS_FILE=/private/senders.json WORK_B_INPUT_DIR=/private/starter ./03_independent_validation/REPRODUCIBLE_SCRIPTS/run_all.sh`
สคริปต์ประวัติใน 01/02 อาจใช้ path ของสภาพแวดล้อมเดิม ให้ใช้ 03 สำหรับการตรวจซ้ำที่แก้ไขแล้ว
