# Work B — corrected independent validation

เริ่มอ่าน FINAL_INDEPENDENT_REPORT_TH.md; ตัวเลขสูตรครบใน IMAGE_RULE_BACKTEST.csv; วิธีตีความจริงทุก variant ใน IMAGE_RULE_DEFINITIONS.csv; ภาพถอดคำใน IMAGE_TRANSCRIPTION.md
งานนี้แยกจาก `/path/to/private/work_b/` ของ OpenCode และ repo งานเว็บไซต์ ไม่มีการแก้หรืออัปโหลดข้อมูลต้นฉบับ

## Run
```bash
python3 -m pip install -r requirements.txt
LINE_EXPORT_PATH='/path/to/private/LINE.txt' WORK_B_INPUT_DIR='/path/to/original/downloads' SITE_CAPTURE_DIR='/path/to/optional/site_days' ./REPRODUCIBLE_SCRIPTS/run_all.sh
```
ค่า default ชี้ไฟล์ต้นฉบับบนเครื่องผู้ใช้ raw LINE ไม่อยู่ใน bundle; manifest บันทึก hashes และ paths เพื่อให้ตามกลับได้ ถ้าไม่มีกลุ่มไฟล์เว็บเก่าจะยังทำ primary LINE analyses ได้ แต่ capture comparison จะว่าง ไม่สร้างข้อมูลเว็บขึ้นเอง
รายงานสร้างใหม่จาก machine outputs; evidence/ เป็น snapshot หลักฐาน GitHub ไม่อ้างว่าเป็นการวัดเว็บใหม่
ดู CORRECTIONS_AND_LIMITATIONS.md และ WEBSITE_RELATIONSHIP_AUDIT.md สำหรับข้อจำกัดที่สำคัญ


## Public copy: private inputs required

Publication copies use `LINE_EXPORT_PATH`, `LINE_SENDERS_FILE` (a private JSON array of exact sender names), and `WORK_B_INPUT_DIR`. Set these explicitly; there is no bundled raw chat or default sender list. `SITE_CAPTURE_DIR` is optional. See [PUBLIC_INPUTS.md](PUBLIC_INPUTS.md) and [publication validation](PUBLICATION_VALIDATION.json). Historical local replay counts in VALIDATION.json precede privacy filtering.
