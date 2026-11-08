#!/usr/bin/env python3
"""Read-only research of already-exported LINE chat. Generates deduplicated round results and preregistered screenshot-rule tests.
Uses no network requests and no betting interactions. Adapt for local exported chats as needed.
"""
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict,Counter
import re,csv,json,math

root=Path('/mnt/data')
file=next(x for x in root.glob('*(10).txt') if 'VIP' in x.name)
lines=file.read_text(encoding='utf-8-sig').splitlines()
DATE=re.compile(r'^(20\d{2})\.(\d{2})\.(\d{2})\b')
HEADER=re.compile(r'^(\d{2}):(\d{2}) (.+)$')
ROUND=re.compile(r'จับยี่กี\s*รอบที่\s*(\d+)')
PAIR=re.compile(r'^\s*(\d{3})\s*-\s*(\d{2})\s*$')
INLINE=re.compile(r'^(\d{1,2}):\s*(\d{2}):(\d{2})\s*➡️\s*(\d{3})\s*-\s*(\d{2})')
current_date=None;msg_ts=None;msg_author=None
result_posts=[];shortrow=[];forecast_posts=[]; forecast_re=re.compile(r'^\s*(\d{2})\.00\s*=\s*([0-9])(?:=|\s|$)')
for i,s in enumerate(lines):
 m=DATE.match(s)
 if m:current_date=date(*map(int,m.groups())); msg_ts=None;continue
 m=HEADER.match(s)
 if m and current_date:
  h,mi,author=m.groups()
  msg_ts=datetime.combine(current_date,datetime.min.time())+timedelta(hours=int(h),minutes=int(mi))
  msg_author=author
 if not msg_ts:continue
 m=ROUND.search(s)
 if m and i+1<len(lines):
  n=int(m.group(1));q=PAIR.match(lines[i+1]);
  if 1<=n<=88 and q:
   top,bot=q.groups();d=msg_ts.date();
   # round 1..72 scheduled 06:00 -> 23:45 same day; 73..88 00:00..03:45 next calendar day
   hh,mm=((6*60+(n-1)*15) if n<=72 else ((n-73)*15))//60,((6*60+(n-1)*15) if n<=72 else ((n-73)*15))%60
   close=datetime.combine(d,datetime.min.time())+timedelta(hours=hh,minutes=mm)
   # date of close <= message timestamp, allow +15 minutes posting delay typical
   if close>msg_ts:close-=timedelta(days=1)
   result_posts.append(dict(close=close,round=n,top=top,bottom=bot,posted=msg_ts,author=msg_author,line=i+1))
 m=INLINE.match(s)
 if m:
  n=int(m.group(1));m2,m3,top,bot=m.groups()[1:]
  shortrow.append((n,m2,m3,top,bot,msg_ts))
 if 'เลขนิ่ง' in s and msg_author and msg_ts:
  # scan body until next header or day, collecting h.00=d lines
  cur=[]
  for j in range(i+1,min(i+48,len(lines))):
   st=lines[j]
   if DATE.match(st) or HEADER.match(st): break
   k=forecast_re.match(st)
   if k:cur.append((k.group(1),k.group(2)))
  if cur:forecast_posts.append(dict(posted=msg_ts,author=msg_author,line=i+1,entries=cur))

byclose=defaultdict(list)
for r in result_posts:byclose[r['close']].append(r)
results=[];conflicts=[]
for dt,parts in sorted(byclose.items()):
 c=Counter((p['top'],p['bottom']) for p in parts)
 if len(c)>1:conflicts.append(dict(close=dt.isoformat(),counts={f'{a}-{b}':v for (a,b),v in c.items()},samples=[p['line'] for p in parts[:5]]))
 (top,bot),freq=c.most_common(1)[0]
 earliest=min((p['posted'] for p in parts if p['top']==top and p['bottom']==bot))
 results.append(dict(close=dt,day=dt.date(),round=parts[0]['round'],top=top,bottom=bot,first_posted=earliest,n_posts=len(parts),source_line=min(p['line'] for p in parts)))

with open(root/'line_B_results_dedup.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['close_datetime','draw_day','round','top3','bottom2','first_result_posted','repeated_post_count','source_line']);w.writeheader()
 for r in results:w.writerow(dict(close_datetime=r['close'].isoformat(sep=' '),draw_day=r['day'].isoformat(),round=r['round'],top3=r['top'],bottom2=r['bottom'],first_result_posted=r['first_posted'].isoformat(sep=' '),repeated_post_count=r['n_posts'],source_line=r['source_line']))

# draw gaps & quality
for j,r in enumerate(results):
 r['prev'] = results[j-1] if j else None
 r['next'] = results[j+1] if j<len(results)-1 else None
 r['next_is_contig'] = bool(r['next'] and (r['next']['close']-r['close'])==timedelta(minutes=15))

# Screenshot rules: bottom2 after double and after 69/65. Exact next 15 minute draw, not skip.
doubles={f'{k}{k}' for k in range(10)}
img1_targets=set('85 97 94 95 74 96 75'.split())
img2_targets=set('56 58 59 68 69 76 78 79 89'.split())
N=[r for r in results if r['next_is_contig']]
# only trigger draw is bottom2; target next is bottom2; non-overlapping boundary within same calendar not needed

def stats(where,targets,output='bottom',label=''):
 triggered=[r for r in N if where(r)]
 def val(r):return r['next']['bottom'] if output=='bottom' else r['next']['top'][-2:]
 hit=sum(val(r) in targets for r in triggered)
 bg=sum(val(r) in targets for r in N);q=bg/len(N) if N else None
 p=len(targets)/100
 # binomial CDF upper null with p = baseline empirical; independent approximation only
 def binom_upper(n,k,p):
  if n==0:return None
  if k==0:return 1.
  if p==0:return 0.
  if p==1:return 1.
  return sum(math.exp(math.lgamma(n+1)-math.lgamma(i+1)-math.lgamma(n-i+1)+i*math.log(p)+(n-i)*math.log1p(-p)) for i in range(k,n+1))
 return dict(label=label,triggers=len(triggered),hits=hit,hit_rate=round(hit/len(triggered),4) if triggered else None,target_count=len(targets),uniform_baseline=p,empirical_baseline=round(q,4),binomial_upper_uniform=round(binom_upper(len(triggered),hit,p),6) if triggered else None,first10=[dict(date=x['close'].isoformat(),before=x['bottom'],after=x['next']['bottom'],hit=val(x) in targets) for x in triggered[:10]])

stats_output=[
 stats(lambda r:r['bottom'] in doubles,img1_targets,'bottom','Photo1: next bottom 2 after bottom double'),
 stats(lambda r:r['bottom'] in doubles,img1_targets,'toplast2','Photo1: next top last2 after bottom double'),
 stats(lambda r:r['bottom']=='69',img2_targets,'bottom','Photo2: next bottom2 after 69'),
 stats(lambda r:r['bottom']=='65',img2_targets,'bottom','Photo2: next bottom2 after 65'),
 stats(lambda r:r['bottom'] in {'69','65'},img2_targets,'bottom','Photo2: next bottom2 after 69 OR 65'),
 stats(lambda r:r['bottom']=='69',img2_targets,'toplast2','Photo2: next top last2 after 69'),
 stats(lambda r:r['bottom'] in {'69','65'},img2_targets,'toplast2','Photo2: next top last2 after 69 OR 65'),
]
# adjacent category (phee-nong) & after double -> digit 8 in next lower as additional ambiguity
siblings={"01","12","23","34","45","56","67","78","89","90","10","21","32","43","54","65","76","87","98","09"}
# picture 3 rule #8 "เบิ้ลล่างตาม 0 กับ พี่น้อง" measured next lower contains 0 OR is sibling
stats_output.append(stats(lambda r:r['bottom'] in doubles,{f'{i:02d}' for i in range(100) if '0' in f'{i:02d}' or f'{i:02d}' in siblings},'bottom','Photo3 #8: after bottom double, next bottom contains 0 or adjacent digits'))
stats_output.append(stats(lambda r:r['bottom'] in doubles,{f'{i:02d}' for i in range(100) if '8' in f'{i:02d}'},'bottom','Photo3 #12: after bottom double, next bottom contains digit 8'))
# three test values only after top3 triple? 'ตองมารอบต่อไปตามตัวมันเอง': if prior top triple then next top3 contains repeated digit
triple=set(f'{d}'*3 for d in range(10))
stats_output.append(dict(label='Photo3 #7: top3 triple then next top contains that digit',triggers=sum(1 for r in N if r['top'] in triple),hits=sum(1 for r in N if r['top'] in triple and r['top'][0] in r['next']['top']),comment='Alternative outcomes include exact triple repeat; requires rule definition before formal test'))

summary={
 'file':file.name,'line_count':len(lines),'first_date':str(results[0]['close']) if results else None,'last_date':str(results[-1]['close']) if results else None,
 'result_post_count':len(result_posts),'unique_rounds_by_close':len(results),'conflicting_posted_rounds':len(conflicts),'first_conflicts':conflicts[:8],
 'contiguous_pairs':len(N),'forecast_message_count':len(forecast_posts),'forecast_dates':len({p['posted'].date() for p in forecast_posts}),
 'all_result_days':len({r['close'].date() for r in results}),
 'test_results':stats_output,
 'quality_note':'Messages lack seconds, and screenshot rule dates/original publication times are not established. Baseline p-values are exploratory independence approximations and should not be used as conclusive tests.'
}
(root/'line_B_picture_rule_tests.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2,default=str)[:24000])
