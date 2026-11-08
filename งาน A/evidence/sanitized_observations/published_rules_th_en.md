# Published rules — Yeekee (จับยี่กี), THLotto

Source: authenticated page `https://thlotto.com/member/lottery/yeekee/231`, `#modal-rule` ("กติกา"),
opened normally in the browser. Captured 2026-11-07 ~19:36 Asia/Bangkok.
Screenshot: `evidence/screenshots/rules_modal_round55.png`.

## Thai original (verbatim)

> เปิดรับแทงวันละ 88 รอบ ออกผลรางวัลทุกๆ 15 นาที
> รอบแรกเริ่มเวลา 06:00 น. (เริ่มทายผลได้ตั้งแต่ 05:00 น. ทายผลล่วงหน้าได้ทุกรอบ)
> ปิดรับแทงรอบสุดท้าย เวลา 03:45 น.
> สามารถส่งตัวเลขได้ฟรี ไม่จำกัดจำนวนครั้ง ด้วยกติกาที่ชัดเจนและสามารถตรวจสอบได้
> เลขวิ่งบน รับทายผล 3 ตัวบนเหมือนหวยรัฐบาล
> หากเลขที่สมาชิกร่วมทายผลมีไม่ถึง 20 ลำดับ ไม่ว่าในกรณีใดก็ตาม ทางระบบจะทำการคืนโพยและคืนยอดเงินที่แทงเข้ามาในรอบนั้นทันที
>
> **การออกผลรางวัล**
> ระบบจะให้สมาชิกทุกๆท่านร่วมส่งตัวเลขจำนวน 5 หลัก
> ทางบริษัทฯจะนำตัวเลขที่สมาชิกส่งเข้ามาทั้งหมดในรอบนั้นๆมารวมกัน แล้วเอาผลรวมที่ได้นำไปลบกับเลขลำดับที่ 16 ของรอบนั้น และจะนำผลที่ได้มาเป็นผลในการออกรางวัล
>
> **ตัวอย่างการออกผลรางวัล**
> ผลรวมการยิงเลขทั้งหมดได้ 2543565
> เลขลำดับที่ 16 คือเลข 34529
> นำผลรวมการยิงเลขทั้งหมดมาลบกับลำดับที่ 16 จะได้ 2543565-34529 = 2509036
> เลขที่ออก 3 ตัวบนคือ = 036 เลขที่ออก 2 ตัวล่างคือ = 09
>
> **โบนัสพิเศษ**
> สมาชิกที่ยิงเลขได้ลำดับที่ 1 จะได้รับเครดิต ฟรี 100 บาท
> สมาชิกที่ยิงเลขได้ลำดับที่ 16 จะได้รับเครดิต ฟรี 200 บาท
> สมาชิกที่ยิงเลขได้ลำดับที่ 100 จะได้รับเครดิต ฟรี 100 บาท
> หมายเหตุ: ต้องมียอดเดิมพันรอบนั้นๆ ขั้นต่ำ 100 บาทขึ้นไปถึงจะได้รับโบนัสพิเศษ; 1 บัญชี รับรางวัลได้เพียง 1 ครั้งต่อวัน
>
> **ขั้นตอนการออกผลรางวัล**
> หลังจากหวยยี่กีปิดรับแทงแต่ละรอบ ระบบยิงเลขจะเปิดให้ยิงอีก 2 นาที หลังจากระบบยิงเลขปิด อีก 1 นาที ระบบจะทำการตรวจโพย โดยใช้เวลาการจ่ายเงินประมาณ 2-5 นาที
> ตัวอย่าง เช่น ยี่กีรอบที่ 1 ระบบปิดรับแทงเวลา 06:00 น. ระบบยิงเลขจะสามารถยิงเลขได้จนถึงเวลา 06:02 น. ต่อไประบบจะทำการตรวจโพยในเวลา 06:03 น. และจะจ่ายเงินสมาชิกทั้งหมดเสร็จภายในเวลาไม่เกิน 06:08 น.
> หมายเหตุ โปรดตั้งเวลาของอุปกรณ์เข้าเล่นของท่านให้ตรงกับเวลาในเว็บ ... เวลาที่แสดงผลการส่งตัวเลขจะใช้เวลาจากเซิร์ฟเวอร์จริง

## English translation (analyst translation)

- Betting is accepted for 88 rounds per day; a result is published every 15 minutes.
- The first round starts at 06:00 (predictions/bets can begin at 05:00; advance betting is allowed for every round).
- The last round stops accepting bets at 03:45.
- Members may submit numbers free of charge, unlimited times, under explicit and verifiable rules.
- If a round has fewer than 20 submitted numbers, the system cancels and refunds that round’s bets immediately.
- **Result calculation:** every member submits a 5-digit number. The company sums all numbers submitted in that round, subtracts the number in **16th position**, and uses the difference as the result.
- **Worked example:** total 2,543,565; 16th number 34,529; 2,543,565 − 34,529 = 2,509,036; the 3-digit top prize is **036**, the 2-digit bottom prize is **09**.
- **Special bonuses:** 1st position gets 100 credit; 16th position gets 200 credit; 100th position gets 100 credit. Requires ≥100 THB of bets in that round; one bonus per account per day.
- **Processing:** after betting closes, the number-shooting system stays open for 2 more minutes. One minute after shooting closes, tickets are checked; payout takes about 2–5 minutes. Example: round 1 closes at 06:00, shooting until 06:02, checking at 06:03, payouts complete by 06:08.

## Digit-extraction interpretation (verified against live data)

Given the worked example and three live rounds, the mapping is:

- Let `R = sum(all submitted numbers) − 16th_number`.
- Take the last five decimal digits of `R` (equivalently `R mod 100000`, zero-padded).
- `bottom2` = the first two of those five digits.
- `top3` = the last three of those five digits.

The subtraction is not reduced modulo 100000 in the published text, but only the last five digits are used for the prizes, so modulo 100000 is observationally equivalent.
