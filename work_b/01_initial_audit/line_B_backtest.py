#!/usr/bin/env python3
"""Predefined out-of-sample transition analysis, distinct from wagering advice."""
import csv,json,math
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timedelta
ROOT=Path('/mnt/data')
r=list(csv.DictReader(open(ROOT/'line_B_results_dedup.csv',encoding='utf-8-sig')))
for x in r:x['close']=datetime.strptime(x['close_datetime'],'%Y-%m-%d %H:%M:%S')
pairs=[(a,b) for a,b in zip(r,r[1:]) if b['close']-a['close']==timedelta(minutes=15)]
n=len(pairs)
# fixed, chronological 60/20/20 split. ML baselines: next lower digit uniform, empirical prior without context, Markov context.
train=pairs[:int(n*.6)];valid=pairs[int(n*.6):int(n*.8)];test=pairs[int(n*.8):]

def key(a,kind):
 if kind=='prev_bottom2':return a['bottom2']
 if kind=='prev_lastdigit':return a['bottom2'][-1]
 if kind=='prev_double':return str(a['bottom2'][0]==a['bottom2'][1])
 if kind=='prev_toplastdigit':return a['top3'][-1]
 if kind=='prev_hour':return str(a['close'].hour)

def prepare(rows,kind):
 base=Counter(b['bottom2'] for a,b in rows)
 conditional=defaultdict(Counter)
 for a,b in rows:conditional[key(a,kind)][b['bottom2']]+=1
 return base,conditional

def predict(a,base,conditional,kind,alpha):
 # bayesian shrink towards smoothed marginal, alpha prior concentration
 p0={f'{j:02d}':(base[f'{j:02d}']+1)/(sum(base.values())+100) for j in range(100)}
 c=conditional[key(a,kind)];z=sum(c.values())+alpha
 return {k:(c[k]+alpha*v)/z for k,v in p0.items()}

def score(rows,base,conditional,kind,alpha):
 loss=0.;hits=0
 for a,b in rows:
  prob=predict(a,base,conditional,kind,alpha) if kind else {f'{j:02d}':(base[f'{j:02d}']+1)/(sum(base.values())+100) for j in range(100)}
  loss-=math.log(prob[b['bottom2']]);hits+=int(max(prob,key=prob.get)==b['bottom2'])
 return round(loss/len(rows),5),hits,len(rows)
alpha_grid=[1.,10.,30.,100.,300.,1000.,3000.]
out=[]
base,_=prepare(train,'prev_bottom2')
uniform_logloss=math.log(100)
plain_valid=score(valid,base,None,None,None)
plain_test=score(test,base,None,None,None)
out.append({'model':'uniform','validation_log_loss':round(uniform_logloss,5),'test_log_loss':round(uniform_logloss,5),'test_top1_hits':None,'test_n':len(test),'note':'uniform 1/100'})
out.append({'model':'global_smoothed_frequency','validation_log_loss':plain_valid[0],'test_log_loss':plain_test[0],'test_top1_hits':plain_test[1],'test_n':plain_test[2],'note':'no conditional pattern'})
for kind in ['prev_lastdigit','prev_bottom2','prev_double','prev_toplastdigit','prev_hour']:
 base,conds=prepare(train,kind)
 configs=[(score(valid,base,conds,kind,alpha)[0],alpha) for alpha in alpha_grid];lv,alpha=min(configs)
 ts=score(test,base,conds,kind,alpha)
 out.append({'model':kind,'selected_alpha':alpha,'validation_log_loss':lv,'test_log_loss':ts[0],'test_top1_hits':ts[1],'test_n':ts[2],'note':'alpha selected on validation; single held-out test'})
(ROOT/'line_B_transition_holdout.json').write_text(json.dumps({'total_contiguous_pairs':n,'train_pairs':len(train),'validation_pairs':len(valid),'test_pairs':len(test),'train_dates':[str(train[0][0]['close'].date()),str(train[-1][1]['close'].date())],'test_dates':[str(test[0][0]['close'].date()),str(test[-1][1]['close'].date())],'models':out},indent=2,ensure_ascii=False))
print(json.dumps(out,indent=2,ensure_ascii=False))
