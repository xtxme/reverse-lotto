"""Build all requested deliverables from the computed results, never edit raw input."""
from pathlib import Path
import csv,json,sys,hashlib,math,platform
import numpy as np
import scipy
from scipy.stats import binomtest
import backtest_image_rules as image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs'
def j(n):return json.loads((OUT/n).read_text())
def read(n):
    with (OUT/n).open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))
def save(n,s):(ROOT/n).write_text(s.strip()+'\n',encoding='utf-8')
def table(head,rows):return '\n'.join(['| '+' | '.join(head)+' |','|'+'---|'*len(head)]+['| '+' | '.join(str(x).replace('|','/').replace('\n',' ') for x in r)+' |' for r in rows])
def pct(x):return f'{100*float(x):.2f}%'
def nfmt(x):return f'{float(x):.5g}'
def capture_claim(audit):
    count=audit.get('capture_comparison_after_exclusions',{}).get('match',0)
    if not count:
        return 'รอบการรันนี้ไม่มีไฟล์ capture ที่ใช้ยืนยันการตรงกันได้ จึงไม่รับรองจำนวนผลที่ตรงกับเว็บ'
    return f'saved captures ตรงกับ LINE {count:,} ผลหลังตัดวันที่ผิดปกติ แต่เป็นการตรงกันระหว่างไฟล์ที่ provenance ยังไม่ยืนยัน'
def main():
    parse=j('parse_audit.json');audit=j('INPUT_AUDIT.json');hour=j('hourly_audit_summary.json');sensitivity=j('HOURLY_SENSITIVITY.json');pat=j('PATTERN_DISCOVERY_SUMMARY.json');oos=j('OUT_OF_SAMPLE_RESULTS.json')
    rules=read('IMAGE_RULE_BACKTEST.csv');defs=read('IMAGE_RULE_DEFINITIONS.csv');dmap={r['rule_id']:r for r in defs};primary=[r for r in rules if r['is_primary']=='1'];allpat=read('PATTERN_DISCOVERY_TESTS.csv');pmap={r['test']:r for r in allpat}
    # Every actual tested interpretation has its own traceable definition.
    expanded=[]
    for s in image.SPECS:
        d=dmap[s['rule_id']];dynamic=s['dynamic'];size=round(s['p0']*(1000 if s['rule_id'] in {'R06','R07','R17'} and s['field']=='top3' or s['rule_id']=='R17' and s['test_id']=='R17-primary' else 100))
        # Use outcome domain, not trigger domain, to obtain target-set coverage.
        domain=1000 if s['p0'] in {.271,.001} else 100
        expanded.append(dict(test_id=s['test_id'],rule_id=s['rule_id'],original_text=d['original_text'].replace('หลังหมา','หลังหาม'),term_glossary=d['term_glossary'],trigger_and_target=s['description'],horizon=s['horizon'],match_mode='exact repeated triple' if s['exact'] else ('trigger-digit containment' if dynamic else d['match_mode']),uniform_target_count=round(s['p0']*domain),outcome_space=domain,random_baseline=s['p0'],is_primary=s['is_primary'],ambiguity=d['ambiguity'],null_method='whole target outcome within day' if dynamic else 'within-day hypergeometric',source_image=d['image']))
    with (ROOT/'IMAGE_RULE_DEFINITIONS.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(expanded[0]));w.writeheader();w.writerows(expanded)
    (ROOT/'IMAGE_RULE_BACKTEST.csv').write_bytes((OUT/'IMAGE_RULE_BACKTEST.csv').read_bytes())
    # Existing output roundoff is display-only; recompute displayed rate from counts.
    rt=table(['Rule','เงื่อนไข/ผลตามการตีความ','เข้า/ประเมินได้','อัตรา','ฐาน uniform','binomial p','permutation p','BH q (20 primary)'],[[r['test_id'],r['description'],f"{r['hits']}/{r['triggers']}",pct(int(r['hits'])/int(r['triggers'])),pct(r['p0_uniform']),nfmt(r['binom_p_one_sided']),nfmt(r['perm_p_within_day']),nfmt(r['q_BH_primary_family'])] for r in primary])
    basetext='''ทั้งหมดเป็น retrospective reanalysis ของข้อมูลที่เคยถูกตรวจแล้ว ไม่มี untouched/prospective test ใหม่ การแบ่งเวลาและการล็อกโค้ดในรอบนี้ไม่สามารถทำให้ลืมผลที่เคยเห็นได้ อัตราเข้าเป็นสถิติของ outcome ที่นิยาม ไม่ใช่ผลกำไรหรือความสามารถรู้เลขทั้งชุด

สคริปต์ส่วนหนึ่งต่อยอดโครงสร้างจาก OpenCode หลังอ่านโค้ดทั้งหมดและแก้ข้อผิดพลาด พร้อม regression tests จึงไม่ใช่การยืนยันจาก analyst/dataset อิสระใหม่ทั้งหมด รายงานระบุสิ่งที่คำนวณซ้ำ สิ่งที่เป็นหลักฐานไฟล์ และสิ่งที่ยังไม่ทราบแยกกัน'''
    save('DATA_QUALITY_REPORT.md',f'''# Data quality — การตรวจข้อมูลใหม่
วันที่ 8 พฤศจิกายน 2026; เวลาในข้อมูล Asia/Bangkok

{basetext}

## Input และการตรวจซ้ำ
- LINE ดิบ {parse['raw_lines']:,} บรรทัด, {parse['messages']:,} ข้อความ; 87 วันทำการ 2026-08-13 ถึง 2026-11-07
- ผล {parse['unique_round_records']:,} รอบ; ผลขัดแย้ง {parse['result_value_conflicts']}; inline rows {parse['inline_table_rows']:,}; headline/inline ตรง {parse['headline_vs_table_agree']:,}/{parse['unique_round_records']:,}
- CSV แนบสองชื่อเป็น byte-identical; LINE แนบตรงกับ raw ที่งาน OpenCode ใช้ SHA-256 รายไฟล์อยู่ INPUT_MANIFEST.csv
- parse ใหม่เทียบ CSV เริ่มต้นด้วย close_datetime ตรง {audit['line_csv_agreement']:,}/{audit['result_rows']:,}; ตรวจ source line กับต้นข้อความ/เลขรอบ/ค่า top3-bottom2 ทุกแถวแล้วผิด {audit['source_line_errors']}
- คำนวณ hit และ baseline ของ {audit['forecast_rows']:,} ชั่วโมงจากผลสี่รอบซ้ำ ผิด {audit['forecast_recalculation_errors']}
- รักษา 001 และ 06 เป็น string ไม่แปลงผลเป็น integer

## วันและข้อมูลขาด
รอบ 1=06:00, รอบ 72=23:45, รอบ 73=00:00 วันปฏิทินถัดไป, รอบ 88=03:45 ถัดไป trading_day คือวันของรอบ 1
parser จับคู่วันด้วยเวลาโพสต์และ schedule ที่ทำให้ delay ใกล้ 2 นาที จึงเป็นกติกาการจัดข้อมูล ไม่ใช่หลักฐานเวลาภายใน server
เวลาโพสต์ผลช้ากว่า scheduled close min/median/max = 2/2/6 นาที; ไม่มีโพสต์ผลก่อนปิดในชุดที่แยกได้
ขาด {parse['total_missing_rounds']} รอบจาก 87×88 รวมต้นและท้ายไฟล์ มี missing_rounds_by_day.csv และเก็บทุก source line ไม่อุดช่องว่างด้วยการคาดเดา

## การเทียบกับไฟล์เว็บและข้อขัดแย้งที่ยังปิดไม่ได้
เทียบ saved JSON หลังตัด 2026-09-08 และ 2026-10-08 ได้ {audit['capture_comparison_after_exclusions']} ตัวเลขตรง แต่สถานะคือ **matches captured files; source provenance unverified**
สองวันที่ถูกตัดมี 174 ผลของ LINE ซึ่งยังอยู่ใน primary dataset; excluded จากการยืนยันไฟล์เว็บ ไม่ใช่ลบผล LINE
ไฟล์ JSON ไม่มี capture URL, เวลาจับ หรือหลักฐาน chain-of-custody ของ product/date และมีหลายผลิตภัณฑ์อยู่ใน object เดียวกัน แม้ regex เลือกเฉพาะชื่อจับยี่กีปกติ ก็ยังต้องยืนยัน origin
GitHub phase_c/PHASE_C_FINAL_REPORT.md ระบุว่า UI ที่ตรวจไม่มี archive ย้อนหลังของสินค้า 88 รอบ ขัดกับคำรับรอง archive 87 วันของงาน B เดิม จึงยัง **ไม่รับรองว่า server-verified 7,295 รอบ**
การตรงกับ LINE จำนวนมากมีน้ำหนักเรื่องความสอดคล้อง แต่ไม่พิสูจน์ว่าแหล่งนั้นอิสระจาก LINE, เป็น product เดียวกัน หรือถูกจับในวัน/เส้นทางที่อ้าง
ไฟล์ชื่อที่ไม่ใช่ ISO date ถูกข้ามอย่างเปิดเผย: {audit['ignored_non_date_filenames']}
ไม่ใช้ captured gap fill ใน primary, ไม่เปิด session เว็บใหม่, ไม่ probe endpoint

## ข้อจำกัด
LINE ไม่มีวินาทีหรือ edit history; ความไม่ขัดแย้งใน export ไม่พิสูจน์ว่าไม่เคยแก้ข้อความก่อน export ผลยังไม่ใช่ข้อเท็จจริงจากฐานข้อมูล server โดยอัตโนมัติ ไม่มีข้อมูล payout/ต้นทุนพอประเมิน EV
Raw LINE ไม่อยู่ใน deliverable และไม่มีการส่งไป GitHub; `.gitignore` ของชุดใหม่นี้กัน data/ ทั้ง directory แต่ .gitignore ไม่ทำให้ไฟล์ที่เคย tracked เลิก tracked โดยอัตโนมัติ
''')
    trans=['พี่น้องติดกัน 2 รอบ ตามเบิ้ล','พี่น้อง 10 แต้ม ตาม 0','พี่น้องมาพร้อมเบิ้ล ตาม 0','พี่น้อง บ-ล ตาม 1-0-8','พี่น้อง มาพร้อมกัน บ-ล ตาม พี่น้อง','หามเว้น 1 รอบตามตัวมันเอง','ตองมารอบต่อไปตามตัวมันเอง','เบิ้ลล่างตาม 0 กับ พี่น้อง','10 แต้มบนล่างตามเบิ้ล','0 หลักสิบตาม 0','หลังหามตาม 0-6','หลังเบิ้ลตาม 8','หลัง 5 ตาม 0','หลักสิบบนล่างเหมือนกันตาม3','เบิ้ลหน้าตาม 7-9','หลัง : นบ : นล : เลขเดียวกันตาม 3','4 มาร้อยบนตาม 6']
    save('IMAGE_TRANSCRIPTION.md','# ถอดข้อความจากภาพต้นฉบับ\n\nภาพไฟล์ _3.jpg คือภาพ 17 ข้อใน prompt (หน้าจอ album 5/6); _2.jpg คือชุดหลัง 69/65; _1.jpg คือชุดหลังเบิ้ล ใช้ filename และเนื้อหาเป็นหลัก ไม่ใช้เลขเรียกภาพในรายงานเก่าที่สลับกัน\n\n'+ '\n'.join(f'{i}. {t}' for i,t in enumerate(trans,1))+'''\n\nภาพ _2.jpg: “ชุดตาม 69.!!! / ชุดตามหลัง 69-65 / สัญญาณ-เบิ้ล-ตอง / 56-58-59-68-69 / 76-78-79-89” คำว่าสัญญาณยังไม่มีนิยามที่ยืนยันได้ จึงไม่สร้าง trigger แอบแฝงจากแท็กนี้
ภาพ _1.jpg: “หลังเบิ้ล / 85-97-94 / 95-74-96-75” ไม่ระบุบน/ล่างหรือกี่รอบ

อ่านได้ว่า “หาม” ในข้อ 6 และ 11; หามตีความ ABA (A≠B) ข้อ 11 ไม่เขียนเว้นหนึ่งรอบ จึงใช้ t+1 เป็น primary และ t+2 sensitivity
ข้อ 16 ตัวย่อ นบ/นล และขอบเขตเลขเดียวกันยังไม่ยืนยัน ข้อ 2 “พี่น้อง 10 แต้ม” อาจเป็นหลายเกณฑ์ ไม่ถือว่า union ที่เลือกคือเจตนาผู้เขียนแน่นอน
ชื่อ maysa ที่ UI album แสดงไม่ยืนยันผู้เขียนต้นฉบับสูตร และเวลา 15:43/23:29 ใน status bar ไม่ใช่หลักฐานวันที่เวลาประกาศคำทำนาย
''')
    hr=[]
    for i,k in enumerate(['top','bottom','either']):
        h=hour['overall'][k];b=hour['day_bootstrap'][k]
        hr.append([k,f"{h['hits']}/{h['n']}",pct(h['rate']),pct(h['expected_rate']),f"{h['lift_pp']:+.3f}",f"[{b['boot_ci_low_pp']:+.3f},{b['boot_ci_high_pp']:+.3f}]",nfmt(hour['within_day_permutation_p'][k]),nfmt(sensitivity['full_outcome_correction']['bonferroni'][i]),nfmt(sensitivity['full_outcome_correction']['holm'][i])])
    ht=table(['Outcome','เข้า/ทั้งหมด','อัตรา','conditional baseline','ต่าง pp','95% day bootstrap CI (ยังไม่ simultaneous)','p','Bonferroni ×3','Holm ×3'],hr)
    si=sensitivity['month_stratified_whole_vector_null'];late=sensitivity['retrospective_late_diagnostic']
    mc=[]
    for k in ['top','bottom','either']:
        p=hour['within_day_permutation_p'][k];success=round(p*20001-1);ci=binomtest(success,20000).proportion_ci()
        mc.append([k,f'[{ci.low:.5f},{ci.high:.5f}]'])
    save('HOURLY_FORECAST_AUDIT.md',f'''# Hourly forecast audit
{basetext}

## ต้นทางและการนับ
{hour['forecast_posts']} ข้อความ, {hour['daily_tables']} ตารางวัน; ตารางหลักถูก repost โดยหลายบัญชี จึงไม่ใช่ผู้ทำนายอิสระหลายคน ไม่ยืนยันว่าใครเป็นผู้คิดสูตรต้นทาง
ตัดโพสต์ไม่ทัน {hour['excluded_post_after_target']} ชั่วโมง และผลไม่ครบ {hour['excluded_missing_draws']} ชั่วโมง เหลือ 1,545 ชั่วโมงใน 86 วัน
เลือก first seen ก่อนเริ่มชั่วโมงอย่างเคร่งครัด รักษา source_line; ไม่เอาผลที่เติมหลัง '=' มาเป็นคำทำนาย
ผลชุดนี้ไม่พบ digit เปลี่ยนในข้อความ repost แต่ไม่มี edit history จึงยืนยันได้เพียงภายใน export
Outcome ต่อชั่วโมงคือ digit ที่ให้ปรากฏอย่างน้อยหนึ่งครั้งในสี่รอบ (00,15,30,45) แยกบน/ล่าง/either ไม่ใช่ถูกทั้งเลข 3 ตัวหรือ 2 ตัว
baseline ต่อชั่วโมง = จำนวน digit ไม่ซ้ำในผลจริงสี่รอบ/10 ใช้เป็น conditional randomization benchmark ไม่ใช่ข้อมูลที่นำไปป้อนโมเดลก่อนผลเกิด

## ผลที่รันใหม่
{ht}

Within-day permutation 20,000 ครั้ง seed=20261108 สลับเฉพาะชั่วโมงที่ประเมินได้ภายในวัน รักษา digit multiset ที่ใช้ประเมิน ไม่ใช่ยืนยัน independence ของ 1,545 ชั่วโมง
Day bootstrap 10,000 ครั้ง resample วันและใช้ ratio ของผลรวมเพื่อคง estimand; การพึ่งพาข้ามวันยังเป็นข้อจำกัด

## สิ่งที่สรุปเดิมแรงเกินหลักฐาน
บน +2.39 pp เป็นสัญญาณย้อนหลังที่ควรทดสอบต่อ ไม่ใช่สิ่งที่พิสูจน์แล้วว่าเป็น noise
หากใช้ Bonferroni บนไม่ผ่าน 0.05 แต่ either ก้ำกึ่งผ่าน; หากใช้ Holm ทั้งบนและ either ได้ประมาณ 0.04905 ภายใน family 3 outcomes เท่านั้น ห้ามเลือกวิธีแก้ multiple testing เพราะชอบผลที่ผ่าน และไม่ได้ครอบคลุมการค้นหาวิธี/ช่วงเวลาทั้งหมดตลอดโครงการ
Monte Carlo p เองมี uncertainty ดังนี้ (95% binomial CI ของ simulation exceedances):
{table(['Outcome','MC p CI'],mc)}
ค่าใกล้เส้น 0.05 หลังคูณ correction จึงไม่ควรตีความเป็นข้อยุติแบบผ่าน/ไม่ผ่านเด็ดขาด

## Sensitivity ที่ประกาศวิธีก่อนรันในรอบนี้
- สลับ daily vector ทั้งชุดภายในเดือน รักษา hour preference และโครงสร้างภายในตาราง ใช้เฉพาะ 70 วันที่ตารางครบ 22 ชั่วโมง: n={si['n']}, p top/bottom/either={si['p']}; Holm={si['correction']['holm']}
- ถือ eligibility ของคำทำนายจริงคงที่; ต้องสมมติ vector exchangeable ภายในเดือน วิธีนี้เปลี่ยน subset ด้วย จึงไม่ใช้ความต่าง p เป็นหลักฐานว่า signal หายแน่นอน
- ช่วง 21 ต.ค.–7 พ.ย. ใช้เฉพาะตรวจความเสถียรย้อนหลัง ไม่เรียก untouched holdout: n={late['n']}, 18 วัน, hits={late['hits']}, p={late['p']}, Holm={late['correction']['holm']}
- ค้นชั่วโมงที่ดีที่สุดโดยสถิติ max surplus count across **21 ชั่วโมงที่ประเมินได้จริง**: p={sensitivity['max_hour_top_surplus']['p']:.5f} ไม่รองรับการเลือกช่วงเย็นเป็นสูตรยืนยัน
- บนเป็นบวกทั้ง split 70/30 และรายเดือนในชุดนี้ ความต่างขนาด effect ไม่พิสูจน์ความไม่เสถียรโดยตัวมันเอง ล่างกลับเครื่องหมาย; ตาราง per_day/per_hour/per_month รายงานทุกช่วงอยู่ outputs/

## ที่มาของ digit
ทดสอบ mapping จากผลวันก่อน ชั่วโมงก่อน และความถี่ digit ตามสคริปต์ พบว่า mapping ง่าย ๆ ที่ลองอธิบายตารางไม่ได้ แต่ไม่ตัดอัลกอริทึมอื่นทั้งหมด การเลือกเลขไม่ uniform ไม่พิสูจน์ว่าเลือกเองด้วยความเชื่อหรือไม่ใช้ผลย้อนหลัง
บาง mapping จากชั่วโมงก่อนยังอาจเป็นข้อมูลที่เกิดหลังเวลาโพสต์ตารางทั้งวัน จึงไม่ใช่คำอธิบายเชิงกลไกก่อนโพสต์โดยอัตโนมัติ

## ข้อสรุป
ล่างยังไม่พบหลักฐานเหนือฐาน ส่วนบน/either มี small retrospective signal ที่อ่อนไหวต่อ null model, family definition และขนาดข้อมูล เป็นหัวข้อควรทดสอบ prospective โดยล็อก metric/correction ก่อน ไม่ใช่หลักฐานรู้เลขล่วงหน้าหรือผลตอบแทนทางการเงิน
''')
    fam=table(['Family','Tests'],[[k,v] for k,v in pat['families'].items()]);small=sorted(allpat,key=lambda r:float(r['p_value']))[:12]
    save('PATTERN_DISCOVERY_REPORT.md',f'''# Pattern discovery
{basetext}

{fam}

ผลใหม่ {pat['n_tests']} tests, {pat['n_rows']:,} ผล, {pat['n_contiguous_pairs']:,} คู่ติดกัน; nominal p<0.05 = {pat['n_p_below_0.05']}; BH q<0.05 = {pat['n_q_below_0.05']}; smallest q={pat['smallest_q']:.5f}

{table(['Test','n','p','BH q','effect'],[[r['test'],r['n'],nfmt(r['p_value']),nfmt(r['q_value_BH']),r['effect']] for r in small])}

รายงานทุกสมมติฐานรวมผลล้มเหลวใน outputs/PATTERN_DISCOVERY_TESTS.csv
Marginal ใช้ Monte Carlo 500 ครั้ง; 100×100 transition ใช้ within-day permutation 5,000 ครั้ง; position/time ใช้ chi-square; rare 2×2 states ใช้ Fisher exact แทน chi-square sparse; conditional distribution ใช้ target marginal จริงและ permutation 1,000 ครั้ง
lag 1–4 ต้องมี round ต่อกันจริง ไม่ข้าม missing rows หรือข้าม trading day
binomial/chi-square/Fisher และ permutation ยังมี independence/exchangeability assumptions ไม่ใช่หลักฐานว่าทุก time-series dependence ถูกกำจัดแล้ว

## ข้อสรุปที่อนุญาต
ยังไม่พบ predictive pattern ที่ผ่าน family นี้ ไม่ใช่พิสูจน์ว่าผลสุ่มสมบูรณ์ หรือว่าทุก nominal finding เป็นความบังเอิญแน่นอน
after-69 distribution test กับการทดสอบชุด 9 ตัวหลัง 69 เป็นคนละสมมติฐาน ต้องไม่ยกผลข้อหนึ่งไปรับรองอีกข้อ
ไม่ได้ค้นโมเดลเพิ่มหลังดู test เพื่อสร้างเลขที่ดูแม่น
''')
    ot=table(['Model','Validation LL','Test LL','Brier','Top1 observed/reference'],[[m['model'],f"{m['validation_log_loss']:.5f}",f"{m['test_log_loss']:.5f}",f"{m['test_brier']:.7f}",pct(m['test_top1_accuracy'])+(' theoretical' if m['model']=='uniform' else '')] for m in oos['models']])
    paired=read('OOS_PAIRED_COMPARISONS.csv')
    save('OUT_OF_SAMPLE_VALIDATION.md',f'''# Chronological validation — retrospective reanalysis
{basetext}

Train {oos['train_days']} = {oos['train_pairs']} pairs; validation {oos['validation_days']} = {oos['validation_pairs']}; test {oos['test_days']} = {oos['test_pairs']} pairs
แยกตาม trading day 52/17/18 วัน ปรับ alpha ด้วย validation เท่านั้น โมเดลใช้ feature ของรอบก่อน target; ไม่มีการ fill gaps จาก capture ใน primary
ชุด test นี้เคยถูกอ่านและวิเคราะห์แล้ว จึงตรวจ implementation ของ chronological split ได้ แต่ไม่รับรองว่าการพัฒนาสมมติฐานทั้งโครงการไม่เคยอาศัย test

{ot}

Uniform log loss = ln(100)=4.60517; Brier ที่ถูกต้อง = 0.99 ไม่ใช่ 0.9801
ผลทั้งหมดมี LL สูงกว่า uniform โมเดลดีที่สุดในชุดนี้อาจดีกว่า empirical marginal เพียงเล็กน้อย ไม่ใช่หลักฐานชนะทั้งสอง baseline
Paired day-cluster bootstrap CI (10,000) และ sign-flip diagnostics (20,000; สมมติ day errors independent/symmetric) เปรียบเทียบทั้ง uniform และ train marginal อยู่ OOS_PAIRED_COMPARISONS.csv ใช้ Holm across {len(paired)} comparisons
{table(['Model','Baseline','Delta LL','95% CI','Holm p improvement'],[[r['model'],r['baseline'],nfmt(r['delta']),f"[{nfmt(r['ci_low'])},{nfmt(r['ci_high'])}]",nfmt(r['holm_across_comparisons'])] for r in paired])}

CI resample day sums/counts เพื่อให้ตรงกับ observation-weighted headline LL มีเพียง 18 test days จึงจำกัดความแม่นของ interval
alpha=1000 คือค่าที่ดีที่สุดใน grid ที่ลอง ไม่พิสูจน์ว่า conditional state ไม่มีข้อมูลทุกชนิด
**ขอบเขต:** โมเดลเหล่านี้ทำนาย bottom2 รอบถัดไป ผลล้มเหลวของโมเดลนี้ไม่ใช่การหักล้างผู้ให้เลข top-digit รายชั่วโมงโดยตรง ดู late hourly diagnostic แยกใน HOURLY_FORECAST_AUDIT.md
''')
    save('WEBSITE_RELATIONSHIP_AUDIT.md',f'''# Relationship to website research
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
''')
    correction='''1. ไม่มี target/ข้ามรอบขาด → None และ exclude แทน False; denominator จึงเปลี่ยน R06 686→663, R07 72→71, R08 738→730, R17 732→720 ฯลฯ
2. ข้อ 11 จากภาพใช้ next round เป็น primary; skip-one เป็น sensitivity เท่านั้น
3. permutation p คำนวณหลังรวมทุกวัน ไม่คืนค่าก่อนวันสุดท้ายที่ degenerate
4. trigger-dependent digit/triple targets สลับ future outcomes ทั้งก้อนแทนสลับ trigger labels; empirical null rate สำหรับกลุ่มนี้ใช้ permutation mean/triggers
5. uniform Brier รวมทั้ง 100 classes =0.99; bootstrap OOS ใช้ weighted estimand เดียวกับ LL
6. sparse 2×2 state tests ใช้ Fisher exact; conditional marginal ใช้ target ไม่ใช่ origin
7. แยก full outcome Bonferroni และ Holm; ไม่เรียกทุก hourly outcome null และไม่สรุปว่า top positive เป็น noise แน่นอน
8. แยก capture-match ออกจาก server verification และระบุ archive contradiction
9. run_all ใหม่สร้าง deliverables ทุกไฟล์และรายงานที่มาสคริปต์ ไม่อ้างว่า gitignore เดิมกัน data/ ทั้งหมด'''
    save('CORRECTIONS_AND_LIMITATIONS.md','# Corrections and limitations\n\n'+correction+'\n\nข้อจำกัดการออกแบบ: permutation ภายในวันสมมติ exchangeability; day bootstrap ยังสมมติ cross-day independence โดยประมาณ; exploratory families หลายชุดไม่ใช่ family เดียวที่ pre-register ก่อน dataset เกิด; ไม่ทดลองทุกความหมายแบบ combinatorial; ภาพไม่มี original publication timestamp และไม่มี edit history ของ LINE\n')
    final=f'''# ผลตรวจอิสระงาน B — สรุปได้แค่ไหน และควรตรวจอะไรต่อ
วันที่ 8 พฤศจิกายน 2026

**สรุปได้แล้วในขอบเขตนี้:** สูตรในภาพตามนิยามที่ทดสอบยังไม่มีหลักฐานเหนือสุ่มหลังแก้บั๊ก; โมเดล bottom2 ที่ลองไม่ชนะ uniform; ไม่มี predictive pattern ผ่าน BH ใน family 76 tests
**ยังสรุปไม่ได้:** ผู้ให้เลขไม่มีความสามารถทุกชนิด, ความสัมพันธ์บนเป็น noise แน่นอน, แหล่งผลย้อนหลังถูกยืนยันจากเว็บต้นฉบับครบ 87 วัน หรือไม่มี public statistical signal ใดเลย

{basetext}

## 1. ข้อมูลถูกต้องแค่ไหน
parse raw ใหม่: 7,469 ผล/87 วัน; แยก 133,144 inline rows มา cross-check ไม่มีค่าขัดแย้ง; เทียบกับ starter CSV โดย close time ตรงทุกค่า; source line ตรวจกลับข้อความจริงทุกแถว
คำทำนาย 1,545 ชั่วโมงคำนวณจากผลสี่รอบได้ตรงทั้งหมด ไม่ใช่เชื่อ summary AI
ข้อมูลขาด 187 รอบ; raw LINE ไม่มี edit history หรือวินาที ข้อมูลไม่ครบ/ไม่ขัดแย้งไม่ใช่หลักฐานจากฐานข้อมูล server

## 2. สูตรทั้ง 17 และชุดในภาพ
อ่านภาพจริง: หาม=ABA; ข้อ 11 ไม่มีเว้นรอบ; ข้อ 16 ตัวย่อยังคลุมเครือ; ชื่อ maysa ใน album ไม่รับรองผู้เขียนสูตร
ทดสอบ 43 variants (20 primary,23 sensitivity) โดยรายงานทุกแบบ ไม่มีการเลือกความหมายที่ชนะมาสวมเป็นคำอธิบายต้นฉบับ

{rt}

หลังแก้ ตัวอย่าง R06 =185/663=27.90%; R11 next-round=228/671=33.98% เทียบฐาน36%; R11 skip sensitivity=237/663=35.75%; R17=205/720=28.47%
ค่า p ต่ำสุดของ 17 primary ยังประมาณ0.193; primary BH q ต่ำสุดประมาณ{min(float(r['q_BH_primary_family']) for r in primary):.3f} ตาม empirical permutation null ทุก primary ยังไม่ผ่าน
ชุดหลังเบิ้ล=49/730; หลัง69=5/75; หลัง65=7/78; หลัง69หรือ65=12/153; ลำดับ69→65=0/1 ไม่พอประเมิน ไม่ใช่ข้อพิสูจน์ว่าสูตรลำดับนี้ไม่มีผล
ภาพไม่มี original publication date/time; backtest จึงไม่ยืนยันคำทำนายล่วงหน้าของเจ้าของภาพ

## 3. ผู้ให้เลขรายชั่วโมง
{ht}

**ประเด็นที่ควรตรวจต่อจริงคือ top/either** มี small retrospective signal แต่ต้องจำกัดความ:
- Bonferroni ×3: top≈0.05865, either≈0.04905; Holm ×3: top/either≈0.04905
- null ที่รักษา daily vector และ hour preference ภายในเดือน: top nominal≈{si['p'][0]:.5f}; Holm≈{si['correction']['holm'][0]:.5f}; subset70วัน/1,284ชั่วโมง ไม่ใช่ evidence ว่า signal เป็นศูนย์
- ช่วงท้าย18วัน/312ชั่วโมง top235hit, nominal p≈{late['p'][0]:.5f}; ยังไม่ยืนยันซ้ำ แต่ sample เล็กและข้อมูลเคยถูกเปิดแล้ว ไม่ใช่ untouched test
- max-hour search-adjusted p≈{sensitivity['max_hour_top_surplus']['p']:.5f}; ไม่รองรับเลือกเฉพาะช่วงที่ดูแม่น
- ไม่พบ digit เปลี่ยนใน export ไม่เท่ากับยืนยันว่าไม่เคย edit ก่อน export
- ความถี่ digit ไม่ uniform และ mappingง่าย ๆ ไม่เข้า ไม่พิสูจน์ว่าสร้างด้วยมนุษย์หรือไม่ได้ใช้อัลกอริทึม

## 4. Pattern และ OOS ตอบอะไร
{pat['n_tests']} tests, {pat['n_p_below_0.05']} nominal p<0.05, 0 BH q<0.05, smallest q≈{pat['smallest_q']:.3f}; ยังไม่มี replicated predictive finding ในสิ่งที่ลอง ไม่ควรประกาศว่าแต่ละ nominal finding เป็นความบังเอิญแน่นอน
Chronological test18วัน/1,503คู่ โมเดล bottom2 ทั้ง8แบบ LL4.6117–4.6215 เทียบ uniform4.60517; uniform Brier ที่แก้แล้ว0.99; เปรียบเทียบ empirical marginal พร้อม paired day CI ในรายงาน OOS
ผลโมเดล bottom2 ไม่ได้หักล้าง hourly top-digit claim เพราะเป็นคนละ target, horizon และ model
ชุด test เคยถูกดูแล้วก่อนรอบนี้ จึงห้ามเรียกการ rerun ว่า independent prospective validation ใหม่

## 5. ช่องว่างใหญ่เรื่องแหล่งยืนยันเว็บ
{capture_claim(audit)}; ยังไม่มี URL/time/product provenance ขณะเดียวกัน GitHub Phase C ระบุว่าไม่พบ historical archive ของสินค้า88รอบใน UI ที่ตรวจ
ดังนั้นเปลี่ยนสถานะเป็น **capture values match; website provenance unresolved** ต้องยืนยันว่าไม่ใช่ product264รอบ, date filter ที่ ignore หรือข้อมูลจากแหล่งไม่อิสระ ก่อนนำไปรับรอง dataset ทั้งชุด
การรับเลขต่อถึง close+2 อธิบายว่าทำไมสูตร final sum−row16 คำนวณตรงก่อนเดิมพันปิดไม่ได้ตามหลักฐานงาน A แต่ไม่พิสูจน์ว่าทุก statistical signal เป็นไปไม่ได้

## 6. สิ่งที่ควรทำต่อ เรียงลำดับ
1. ปิดช่องว่าง provenance: raw capture พร้อม URL ที่ลบ credential, effective date, product ID, timestamp, DOM context และ hash; เทียบแหล่งอิสระ ไม่ใช้ archive264แทน88
2. ให้เจ้าของสูตรนิยามศัพท์/เป้าหมาย/จำนวนรอบ โดยล็อกก่อนเก็บข้อมูลใหม่; ข้อ2,3,4,11,16 และความหมายกลับเลขมีความกำกวม
3. ล็อก primary เป็น top-digit hit ต่อชั่วโมงทั้งช่วงเวลา; หากจะยืนยัน top/bottom/either ทั้งสาม ใช้ correction ที่เลือกไว้ล่วงหน้า ห้ามเปลี่ยนเพราะค่าไหนผ่าน
4. เก็บ forecast แบบ append-only ก่อนชั่วโมงเริ่ม รักษา original message ID, timestamp timezone, source line/export hash และหลักฐาน edits; เก็บผลแยกอิสระหลังออก
5. ทำ prospective ใหม่หลังวันล็อกวิธี; กำหนดระยะ/จำนวนวันด้วย power analysis สำหรับขั้นต่ำ effectที่สนใจ เช่น+2จุดเปอร์เซ็นต์ พร้อม simulation ที่รักษา clustering/การขาดข้อมูล ไม่ถือ60วันว่าพอโดยอัตโนมัติ
6. ใช้ null อย่างน้อย uniform conditional benchmark, within-day permutation และ whole-vector/hour-preserving sensitivity ที่ระบุ assumptions; ประเมินทุกชั่วโมงและรายงาน failures
7. ตัดสินครั้งเดียวเมื่อครบ sample; หากต้องติดตามหลายครั้งให้มี sequential testing/alpha-spending ล่วงหน้า แยก replication อีกช่วง/อีก analyst ก่อนอ้างความสามารถ

## คำตอบสุดท้าย
สูตรภาพ: **ยังไม่พบหลักฐานเหนือสุ่มตามการตีความที่ทดสอบ**
ผู้ให้เลข: **ล่างยังไม่พบ; บน/either มีสัญญาณย้อนหลังขนาดเล็กที่ควรทดสอบต่อ แต่ยังไม่พิสูจน์ทำนายอนาคตได้**
Patternตรวจซ้ำ: **ยังไม่มี predictive finding ที่ผ่านหลักฐานและ correction ของงานนี้**
ข้อยุติที่ยังไม่มี: เจตนา/สูตรจริงของผู้ให้เลข, perfect randomness, original server internals, predictive edgeในอนาคต, EV/กำไร และความถูกต้องของ archive provenance
ไม่ให้เลขเดิมพัน ไม่รับประกันถูกรางวัล และไม่มีข้อมูล payoutพอแปลง hit rateเป็นกำไร
'''
    save('FINAL_INDEPENDENT_REPORT_TH.md',final)
    save('README.md','''# Work B — corrected independent validation

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
''')
    save('requirements.txt',f'numpy=={np.__version__}\nscipy=={scipy.__version__}')
    save('.gitignore','data/\noutputs/\n__pycache__/\n*.pyc\n*.log\n')
    save('SOFTWARE_PROVENANCE.md',f'''# Software provenance
Python {platform.python_version()}, numpy {np.__version__}, scipy {scipy.__version__}; seeds in source
ฐานโค้ด parser, hourly, image, pattern และ OOS อ่านจาก /path/to/private/work_b/REPRODUCIBLE_SCRIPTS แล้วปรับในสำเนานี้ ไม่มีการแก้ originals
การเปรียบเทียบกับ starter CSV และ source-line/value audit เป็นการสอบทานอิสระของผลที่ parse; ไม่ใช่การอ้างว่าทุกบรรทัดเขียนใหม่จากศูนย์
run_all ไม่ login หรือส่ง network request; GitHub source snapshots ถูกอ่านผ่าน connector ก่อนรันและเก็บไว้ใน evidence/
''')
    # Validate requested artifact presence, all 17 rules, numeric integrity.
    required=['DATA_QUALITY_REPORT.md','DEDUPLICATED_RESULTS.csv','FIRST_SEEN_FORECASTS.csv','IMAGE_RULE_DEFINITIONS.csv','IMAGE_RULE_BACKTEST.csv','HOURLY_FORECAST_AUDIT.md','PATTERN_DISCOVERY_REPORT.md','OUT_OF_SAMPLE_VALIDATION.md','FINAL_INDEPENDENT_REPORT_TH.md']
    assert all((ROOT/n).stat().st_size>0 for n in required)
    assert {f'R{i:02}' for i in range(1,18)} <= {r['rule_id'] for r in primary}
    assert all(int(r['hits'])<=int(r['triggers'])<=int(r['n_evaluable']) for r in rules)
    assert len(read('PATTERN_DISCOVERY_TESTS.csv'))==76
    assert abs(oos['models'][0]['test_brier']-.99)<1e-12
    print(json.dumps(dict(deliverables_checked=len(required),variants=len(rules),primary=len(primary),regression_tests=9),ensure_ascii=False))
if __name__=='__main__':main()
