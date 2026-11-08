"""Paired day-cluster CIs and sign-flip diagnostics vs both baselines.
Sign flips assume symmetric independent day errors; retrospective only.
"""
from pathlib import Path
from collections import defaultdict
import csv,json,math
import numpy as np
import oos_validation as o
from hourly_sensitivity import adjust
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs'
def main():
    summary=json.loads((OUT/'OUT_OF_SAMPLE_RESULTS.json').read_text());pairs=o.load_pairs();td,vd,ed,days=o.days_split(pairs);train=[p for p in pairs if p['day'] in td];test=[p for p in pairs if p['day'] in ed]
    p0,_=o.fit(train,None,1);marg=o.evaluate(test,p0,None,None,1)['per_row_logloss'];rng=np.random.default_rng(20261111);results=[]
    for model in summary['models']:
        if model['model']=='uniform':continue
        kind=None if model['model']=='train_marginal' else model['model'];alpha=model['selected_alpha'] or 1
        p0,cond=o.fit(train,kind,alpha);loss=o.evaluate(test,p0,cond,kind,alpha)['per_row_logloss']
        for label,base in [('uniform',[math.log(100)]*len(test)),('train_marginal',marg)]:
            if label=='train_marginal' and kind is None:continue
            ds=defaultdict(list)
            for p,a,b in zip(test,loss,base):ds[p['day']].append(a-b)
            sums=np.array([sum(x) for x in ds.values()]);ns=np.array([len(x) for x in ds.values()]);delta=float(sums.sum()/ns.sum());pick=rng.integers(0,len(ns),(10000,len(ns)));boot=sums[pick].sum(axis=1)/ns[pick].sum(axis=1)
            signs=rng.choice([-1,1],(20000,len(ns)));null=(signs*sums).sum(axis=1)/ns.sum();p=(1+int((null<=delta+1e-15).sum()))/20001
            results.append(dict(model=model['model'],baseline=label,delta=delta,ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),p_one_sided_improvement=p,days=len(ns),n=len(test)))
    cor=adjust([r['p_one_sided_improvement'] for r in results])
    for i,r in enumerate(results):r['holm_across_comparisons']=cor['holm'][i]
    with (OUT/'OOS_PAIRED_COMPARISONS.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    print(json.dumps(results,indent=2))
if __name__=='__main__':main()
