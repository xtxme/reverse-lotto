from pathlib import Path
import csv,random,json
from collections import defaultdict
from datetime import datetime,date,timedelta
import numpy as np
R=Path('/mnt/data')
r=list(csv.DictReader(open(R/'line_B_results_dedup.csv',encoding='utf-8-sig')))
lookup={datetime.fromisoformat(a['close_datetime']):(a['top3'],a['bottom2']) for a in r}
f=list(csv.DictReader(open(R/'line_B_hourly_first_seen.csv',encoding='utf-8-sig')))
bytes_mask=[]; days=[];digits=[]
for item in f:
 dt=datetime.fromisoformat(item['hour_start']); vals=[lookup[dt+timedelta(minutes=15*i)] for i in range(4)]
 t=set(''.join(v[0] for v in vals));b=set(''.join(v[1] for v in vals));
 bytes_mask.append([ [int(str(j) in t),int(str(j) in b),int(str(j) in t|b)] for j in range(10)])
 days.append((dt.date() if dt.hour>=6 else dt.date()-timedelta(days=1)).isoformat());digits.append(int(item['digit']))
a=np.array(bytes_mask,dtype=np.int16);digits=np.array(digits);idx=np.arange(len(digits));
observed=a[idx,digits].sum(axis=0)
B=10000;rng=np.random.default_rng(20261107)
groups=list(defaultdict(list).items())
day_index=defaultdict(list)
for i,k in enumerate(days):day_index[k].append(i)
groups=list(day_index.values());sim=np.zeros((B,3),np.int16)
for k in range(B):
 d=digits.copy()
 for group in groups:
  group=np.asarray(group,dtype=int)
  d[group]=rng.permutation(d[group])
 sim[k]=a[idx,d].sum(axis=0)
p=(1+(sim>=observed).sum(axis=0))/(B+1)
summary={'observed_counts':observed.tolist(),'n':len(digits),'within_day_permutation_trials':B,'permutation_means':sim.mean(axis=0).round(2).tolist(),'permutation_sd':sim.std(axis=0).round(2).tolist(),'permutation_one_sided_p':p.tolist(),'scores':['top','bottom','either']}
(R/'line_B_forecast_permutation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
