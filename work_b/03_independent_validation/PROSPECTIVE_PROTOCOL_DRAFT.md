# ร่างวิธีทดสอบใหม่ก่อนเก็บผลอนาคต

เอกสารนี้ยังไม่ใช่การ pre-register ที่มี timestamp สาธารณะหรือหลักฐาน commitment และยังไม่ได้เริ่มเก็บข้อมูลใหม่

1. ระบุต้นทางตารางและสินค้า 88 รอบให้แน่นอน ไม่รวมผลิตภัณฑ์ชื่อคล้ายกัน ล็อกนิยามเวลา Asia/Bangkok, trading_day และ cutoff
2. เลือก primary outcome ก่อนเริ่ม เช่น digit ที่ให้ปรากฏใน top3 อย่างน้อยหนึ่งครั้งในผล 4 รอบของชั่วโมงทั้งวัน หากต้องการยืนยัน top/bottom/either พร้อมกัน ให้ล็อกทั้งสามและวิธี Holm หรือ Bonferroni ก่อน ไม่เลือกหลังเห็นผล
3. บันทึกข้อความครั้งแรกก่อนเริ่มชั่วโมงพร้อม original message ID, timestamp ระดับวินาทีเมื่อทำได้, hash ของ export/ภาพและหลักฐาน edits การโพสต์ที่ timestamp ตรงเวลาเริ่มหรือระบุไม่ได้ชัดให้ excluded ตามกติกาล่วงหน้า
4. เก็บผลจากแหล่งที่พิสูจน์ product/date/URL/capture time ได้แยกจากแหล่งคำทำนาย ห้ามใช้ final input หลัง cutoff เป็น feature
5. วิเคราะห์ทุกชั่วโมงที่เข้าเกณฑ์ครบ 4 รอบ กำหนดการจัด missing/delayed/cancelled rounds ล่วงหน้า รวมคนโพสต์ตารางเดียวกันเป็นแหล่งเดียว ไม่ขยาย n ด้วย repost
6. กำหนด effect ขั้นต่ำที่สนใจ เช่น +2 จุดเปอร์เซ็นต์ และ sample size ด้วย simulation ที่รักษาโครงสร้างตาราง/ภายในวัน รวม sensitivity ต่อ cross-day dependence ไม่รับรองว่า 60 วันเพียงพอโดยไม่มี power calculation
7. ล็อก null models: conditional uniform digit benchmark, within-day permutation และ whole-vector/hour-preserving sensitivity พร้อม assumptions และ family ของการแก้ multiple testing การสลับข้อมูลต้องไม่สร้างข้อมูลที่มาจากอนาคตให้คำทำนายจริง
8. ล็อก statistic หลัก, ขนาด simulation, seeds หรือวิธีสุ่ม seed, confidence intervals และค่า alpha; หากผลอยู่ใกล้ threshold ต้องรายงาน Monte Carlo uncertainty และห้าม rerun seed จนได้ p ที่ชอบ
9. จบตามจำนวนวัน/ตัวอย่างที่ล็อกแล้ววิเคราะห์ครั้งเดียว การดู dashboard ระหว่างทางต้องไม่มีการเปลี่ยนสูตร/เลือกช่วง หากต้องการตัดสินก่อนครบให้วาง sequential design และ alpha spending ก่อน
10. รายงานทั้งผลบวก ผลลบ และข้อมูลถูกตัด พร้อมเหตุผล ห้ามตีความ non-significance เป็น proof of no effect หรือ hit rate เป็นผลกำไร
11. ทำ replication ในอีกช่วงใหม่หรือโดยผู้ตรวจอื่นก่อนอ้าง predictive skill ไม่มีเลขเดิมพันหรือการรับประกันผลรางวัลในงานนี้

สำหรับการตรวจย้อนหลังครั้งปัจจุบัน late segment 18 วัน/312 ชั่วโมงเป็นเพียง diagnostic ที่เคยเห็นข้อมูลแล้ว ไม่สามารถใช้แทนการศึกษานี้ได้
