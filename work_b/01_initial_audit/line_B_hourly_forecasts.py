#!/usr/bin/env python3
"""Extract first-seen hourly forecasts and compare only against complete, future hourly results."""
from pathlib import Path
import re,csv,json,random,math,statistics
from datetime import datetime,timedelta,date
from collections import defaultdict,Counter
ROOT=Path('/mnt/data')
file=next(x for x in ROOT.glob('*(10).txt') if 'VIP' in x.name)
lines=file.read_text(encoding='utf-8-sig').splitlines()
DATE=re.compile(r'^(20\d{2})\.(\d{2})\.(\d{2})\b')
HEADER=re.compile(r'^(\d{2}):(\d{2}) (.+)$')
F=re.compile(r'^\s*(\d{2})\.00\s*=\s*([0-9])(?:=|\s|$)')
current=None;ts=None;items=[];postcount=0
for i,s in enumerate(lines):
 m=DATE.match(s)
 if m:current=date(*map(int,m.groups()));continue
 m=HEADER.match(s)
 if m and current:
  hh,mm,auth=m.groups();ts=datetime.combine(current,datetime.min.time())+timedelta(hours=int(hh),minutes=int(mm))
 if not (ts and 'เลขนิ่ง' in s):continue
 postcount+=1
 trading_day=ts.date() if ts.hour>=5 else ts.date()-timedelta(days=1)
 for j in range(i+1,min(i+52,len(lines))):
  st=lines[j]
  if DATE.match(st) or HEADER.match(st):break
  k=F.match(st)
  if k:
   h=int(k.group(1));digit=k.group(2)
   if h>=6 and h<=23: target=datetime.combine(trading_day,datetime.min.time())+timedelta(hours=h)
   elif h in (0,24):target=datetime.combine(trading_day,datetime.min.time())+timedelta(days=1)
   elif 1<=h<=3:target=datetime.combine(trading_day,datetime.min.time())+timedelta(days=1,hours=h)
   else: continue
   items.append(dict(target=target,posted=ts,digit=digit,author=auth,line=i+1,raw=st))

tables=defaultdict(list)
for row in items:tables[row['target']].append(row)
for t in tables:tables[t].sort(key=lambda x:(x['posted'],x['line']))
raw=list(csv.DictReader(open(ROOT/'line_B_results_dedup.csv',encoding='utf-8-sig')))
rr={datetime.strptime(row['close_datetime'],'%Y-%m-%d %H:%M:%S'):row for row in raw}
out=[];valid=0
for target,entries in sorted(tables.items()):
 eligible=[x for x in entries if x['posted'] < target]
 if not eligible:continue
 first=eligible[0]
 draws=[rr.get(target+timedelta(minutes=15*i)) for i in range(4)]
 if any(d is None for d in draws):continue
 hits_top=any(first['digit'] in x['top3'] for x in draws)
 hits_bottom=any(first['digit'] in x['bottom2'] for x in draws)
 topdigits=set(''.join(x['top3'] for x in draws));botdigits=set(''.join(x['bottom2'] for x in draws))
 baseline_top=len(topdigits)/10;baseline_bot=len(botdigits)/10;baseline_union=len(topdigits|botdigits)/10
 out.append({
  'hour_start':target.isoformat(sep=' '),'first_posted':first['posted'].isoformat(sep=' '),'digit':first['digit'],'source_line':first['line'],
  'author':first['author'],'top_hit':int(hits_top),'bottom_hit':int(hits_bottom),'either_hit':int(hits_top or hits_bottom),
  'baseline_top':baseline_top,'baseline_bottom':baseline_bot,'baseline_either':baseline_union,
  'n_eligible_versions':len(eligible)
 })
with open(ROOT/'line_B_hourly_first_seen.csv','w',encoding='utf-8-sig',newline='') as f:
 fields=out[0].keys() if out else []
 w=csv.DictWriter(f,fields);w.writeheader();w.writerows(out)
summary={'forecast_messages':postcount,'forecast_hour_entries':len(items),'all_target_hours':len(tables),'evaluated_before_hour_complete_4draws':len(out),'date_range':[out[0]['hour_start'],out[-1]['hour_start']] if out else [],'metrics':{}}
for k,base in [('top_hit','baseline_top'),('bottom_hit','baseline_bottom'),('either_hit','baseline_either')]:
 hits=sum(x[k] for x in out);n=len(out);prob=sum(x[base] for x in out)/n
 # Poisson binomial approximate standardized deviation (not strict inference, hours correlated)
 variance=sum(x[base]*(1-x[base]) for x in out);z=(hits-sum(x[base] for x in out))/math.sqrt(variance) if variance else 0
 summary['metrics'][k]={'hits':hits,'n':n,'hit_rate':hits/n,'random_digit_avg_probability':prob,'difference_points':100*(hits/n-prob),'rough_z':z}
# early holdout 75% train vs 25% test for raw hit-rate check
split=int(.75*len(out))
for i,chunk in [('historical_first75pct',out[:split]),('later25pct',out[split:])]:
 summary[i]={k:dict(rate=sum(x[k] for x in chunk)/len(chunk),rand=sum(x[b] for x in chunk)/len(chunk),n=len(chunk)) for k,b in [('top_hit','baseline_top'),('bottom_hit','baseline_bottom'),('either_hit','baseline_either')]}
(ROOT/'line_B_hourly_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
