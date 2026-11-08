"""Declared diagnostic sensitivities; all data were previously inspected.
Not a new untouched test and not prospective validation.
"""
from pathlib import Path
from collections import defaultdict
import csv,json
import numpy as np
import audit_hourly_provider as a
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs';B=20000
def adjust(ps):
    order=np.argsort(ps);holm=np.ones(len(ps));last=0
    for j,i in enumerate(order):last=max(last,min(1,ps[i]*(len(ps)-j)));holm[i]=last
    return dict(bonferroni=[min(1,p*len(ps)) for p in ps],holm=holm.tolist())
def test(sub,seed=20261108):
    rng=np.random.default_rng(seed);groups=defaultdict(list)
    for i,r in enumerate(sub):groups[r['trading_day']].append(i)
    mat=np.array([[[int(str(d) in r[k+'_digits']) for k in ['top','bottom','either']] for d in range(10)] for r in sub])
    digits=np.array([int(r['digit']) for r in sub]);inds=np.arange(len(sub));obs=mat[inds,digits].sum(axis=0);sim=np.zeros((B,3),dtype=int)
    for b in range(B):
        v=digits.copy()
        for ix in groups.values():v[ix]=rng.permutation(v[ix])
        sim[b]=mat[inds,v].sum(axis=0)
    p=((1+(sim>=obs).sum(axis=0))/(B+1)).tolist()
    return dict(n=len(sub),days=len(groups),hits=obs.tolist(),p=p,correction=adjust(p),null_mean=sim.mean(axis=0).tolist())
def main():
    rec=list(csv.DictReader((OUT/'hourly_evaluated_hours.csv').open(encoding='utf-8-sig')))
    basic=json.loads((OUT/'hourly_audit_summary.json').read_text());ps=[basic['within_day_permutation_p'][k] for k in ['top','bottom','either']]
    report=dict(full_outcome_correction=adjust(ps),retrospective_late_diagnostic=test([r for r in rec if r['trading_day']>='2026-10-21']))
    # Preserve whole daily vectors and hour preference; permute vectors within
    # calendar month among complete 22-hour tables. Fixed original eligibility.
    tables,_=a.build_daily_tables(a.load_posts());days=sorted(d for d,v in tables.items() if len(v)==22);D={d:i for i,d in enumerate(days)};hours=sorted(next(iter(tables[d] for d in days)));H={h:i for i,h in enumerate(hours)}
    vectors=np.array([[tables[d][h]['digit'] for h in hours] for d in days]);membership=np.zeros((len(days),22,10,3),dtype=int);eligible=np.zeros((len(days),22),bool)
    for r in rec:
        if r['trading_day'] not in D:continue
        i,j=D[r['trading_day']],H[int(r['hour_label'])];eligible[i,j]=True
        for d in range(10):
            for k,field in enumerate(['top','bottom','either']):membership[i,j,d,k]=int(str(d) in r[field+'_digits'])
    di,hi=np.indices(vectors.shape);obs=membership[di,hi,vectors].sum(axis=(0,1));rng=np.random.default_rng(20261109);groups=defaultdict(list)
    for d,i in D.items():groups[d[:7]].append(i)
    sim=np.zeros((B,3),int)
    for b in range(B):
        perm=np.arange(len(days))
        for ix in groups.values():perm[ix]=rng.permutation(ix)
        sim[b]=membership[di,hi,vectors[perm]].sum(axis=(0,1))
    pp=((1+(sim>=obs).sum(axis=0))/(B+1)).tolist()
    report['month_stratified_whole_vector_null']=dict(days=len(days),n=int(eligible.sum()),hits=obs.tolist(),p=pp,correction=adjust(pp),null_mean=sim.mean(axis=0).tolist(),assumption='daily forecast vectors exchangeable within month; original eligibility fixed; incomplete vectors excluded')
    # Search-adjusted maximum surplus count over the EVALUABLE hours (21).
    hs=sorted({r['hour_label'] for r in rec});group=defaultdict(list)
    for i,r in enumerate(rec):group[r['trading_day']].append(i)
    members=np.array([[int(str(d) in r['top_digits']) for d in range(10)] for r in rec]);digits=np.array([int(r['digit']) for r in rec]);ix=np.arange(len(rec));hidx=[np.array([i for i,r in enumerate(rec) if r['hour_label']==h]) for h in hs];bases=np.array([sum(float(rec[i]['top_base']) for i in ids) for ids in hidx]);actual=members[ix,digits];obsmax=max(actual[ids].sum()-base for ids,base in zip(hidx,bases));rng=np.random.default_rng(20261110);mx=[]
    for b in range(B):
        dd=digits.copy()
        for ids in group.values():dd[ids]=rng.permutation(dd[ids])
        y=members[ix,dd];mx.append(max(y[ids].sum()-base for ids,base in zip(hidx,bases)))
    report['max_hour_top_surplus']=dict(hours_tested=len(hs),observed=float(obsmax),p=(1+sum(v>=obsmax for v in mx))/(B+1),B=B)
    report['seed_and_B']=dict(base=20261108,vector=20261109,hourmax=20261110,B=B)
    report['warning']='All retrospective; sensitivity families descriptive. No prospective claim. Do not choose a null model or correction based on which gives significance.'
    (OUT/'HOURLY_SENSITIVITY.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
