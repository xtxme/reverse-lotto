"""Read-only input audit; no network access or raw LINE in deliverables."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timedelta
import csv,json,hashlib,os,re,sys

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs'
DOWNLOADS=Path(os.environ['WORK_B_INPUT_DIR'])
CAPTURES=Path(os.environ.get('SITE_CAPTURE_DIR',str(ROOT/'data/site_days')))
def read(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def write(p,rows,fields=None):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    results=read(OUT/'results_dedup_independent.csv')
    byclose={r['scheduled_close']:(r['top3'],r['bottom2']) for r in results}
    inventory=[]; starter=[]
    paths=[DOWNLOADS/'line_B_results_dedup.csv',DOWNLOADS/'line_B_results_dedup (1).csv',DOWNLOADS/'work_B_initial_audit_th.md',Path(os.environ['LINE_EXPORT_PATH'])]
    paths+=sorted((DOWNLOADS/'work_B_analysis_starter').glob('*'))
    paths+=[DOWNLOADS/f'LINE_ALBUM_2142019_261107_{i}.jpg' for i in [1,2,3]]
    for p in paths:
        b=p.read_bytes();inventory.append(dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
        if p.suffix=='.json':
            d=json.loads(b);starter.append(dict(file=p.name,type='json',keys=list(d) if isinstance(d,dict) else len(d)))
        elif p.suffix in {'.py','.md','.csv'}: b.decode('utf-8-sig')
    old=read(DOWNLOADS/'line_B_results_dedup.csv')
    agree=sum(byclose.get(r['close_datetime'])==(r['top3'],r['bottom2']) for r in old)
    site={}; ignored=[];capture_inventory=[]
    for p in sorted(CAPTURES.glob('*.json')):
        b=p.read_bytes();capture_inventory.append(dict(file=p.name,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)))
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',p.stem):ignored.append(p.name);continue
        d=json.loads(b);d=json.loads(d) if isinstance(d,str) else d
        for title,vs in d.items():
            m=re.fullmatch(r'จับยี่กี รอบที่ (\d+)',title)
            if not m:continue
            kv={x['key']:x.get('val') for x in vs};a,b=kv.get('สามตัวบน'),kv.get('สองตัวล่าง')
            if a and b:site[(p.stem,int(m[1]))]=(a,b)
    statuses=Counter(); unreliable={'2026-09-08','2026-10-08'}
    for r in results:
        vals=site.get((r['trading_day'],int(r['round'])))
        status='capture_date_unreliable' if r['trading_day'] in unreliable else ('capture_values_match_origin_unverified' if vals==(r['top3'],r['bottom2']) else 'not_matched')
        r['capture_comparison']=status;statuses[status]+=1
    write(ROOT/'DEDUPLICATED_RESULTS.csv',results)
    h=read(OUT/'hourly_evaluated_hours.csv');errors=[]
    raw=Path(os.environ.get('LINE_EXPORT_PATH',str(Path(os.environ['LINE_EXPORT_PATH'])))).read_text(encoding='utf-8-sig').splitlines()
    # Use first source line of the forecast itself, not a later annotated table.
    posts=json.loads((OUT/'hourly_forecast_posts.json').read_text())
    first={}
    for p in posts:
        for e in p['entries']:
            if p['posted']>=e['target']:continue
            k=e['target'];v=(p['posted'],p['line'])
            if k not in first or v<first[k]:first[k]=v
    for r in h:
        r['source_line']=first[r['target_hour']][1]
        r.pop('first_author',None)  # keep personal names out of deliverable CSV
        t=datetime.fromisoformat(r['target_hour']);ds=[byclose.get((t+timedelta(minutes=15*i)).isoformat(sep=' ')) for i in range(4)]
        assert all(ds)
        sets=[set(''.join(d[j] for d in ds)) for j in [0,1]]
        for k,s in [('top',sets[0]),('bottom',sets[1]),('either',sets[0]|sets[1])]:
            if int(r[k+'_hit'])!=int(r['digit'] in s) or abs(float(r[k+'_base'])-len(s)/10)>1e-12:errors.append(r['target_hour'])
        assert r['first_posted']<r['target_hour']
    write(ROOT/'FIRST_SEEN_FORECASTS.csv',h)
    assert not errors and agree==len(old)==len(results)
    assert len({(r['trading_day'],r['round']) for r in results})==len(results)
    assert all(1<=int(r['source_line'])<=len(raw) for r in results)
    # Validate source lines really begin a message and values occur in its body.
    source_bad=0
    for r in results:
        i=int(r['source_line'])-1;body='\n'.join(raw[i:i+65])
        if not re.match(r'\d{2}:\d{2} ',raw[i]) or not re.search(r'จับยี่กี\s*รอบที่\s*'+str(r['round'])+r'\b',body) or not re.search(r'(?<!\d)'+r['top3']+r'\s*-\s*'+r['bottom2']+r'(?!\d)',body):source_bad+=1
    assert source_bad==0
    check=Counter()
    for (day,rnd),v in site.items():
        if day in unreliable:continue
        c=(datetime.fromisoformat(day)+timedelta(hours=6,minutes=15*(rnd-1))).isoformat(sep=' ')
        if c in byclose:check['match' if byclose[c]==v else 'mismatch']+=1
        else:check['line_missing_capture_present']+=1
    summary=dict(line_csv_agreement=agree,result_rows=len(results),forecast_rows=len(h),source_line_errors=source_bad,forecast_recalculation_errors=len(errors),capture_statuses=dict(statuses),capture_comparison_after_exclusions=dict(check),excluded_capture_dates=sorted(unreliable),ignored_non_date_filenames=ignored,website_verification_status='UNVERIFIED PROVENANCE: saved result JSONs have no capture URL/time/product identity; contradict current GitHub Phase C archive claim. Matches are file-to-file, not independent server verification.',starter_json_inventory=starter)
    (OUT/'INPUT_AUDIT.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    write(ROOT/'INPUT_MANIFEST.csv',inventory)
    write(ROOT/'evidence/CAPTURE_MANIFEST.csv',capture_inventory)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
