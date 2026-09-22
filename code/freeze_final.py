#!/usr/bin/env python3
"""Every number the manuscript cites, recomputed from the 240-run set."""
import os
import numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); SEED,NPERM,EQ=20260921,200_000,0.75
DATA = os.path.join(HERE,'..','results') if os.path.isdir(os.path.join(HERE,'..','results','free_ext')) else os.path.join(HERE,'models')

out=[]
def P(s=''): out.append(s); print(s)
def load(f,c='rlf_rate'):
    return np.array([float(pd.read_csv(os.path.join(DATA,f,'model_s%d_metrics.csv'%s)).iloc[0][c]) for s in range(20,100)])
def perm(d,seed=SEED,n=NPERM):
    o=d.mean(); r=np.random.default_rng(seed); c=0
    for _ in range(n):
        if abs((d*r.choice([-1.,1.],size=len(d))).mean())>=abs(o)-1e-12: c+=1
    return o,(c+1)/(n+1)
def ci(d,seed=SEED,n=20000):
    r=np.random.default_rng(seed); m=[r.choice(d,size=len(d),replace=True).mean() for _ in range(n)]
    return float(np.percentile(m,5)),float(np.percentile(m,95))
def gap(v):
    v=np.sort(v); g=np.diff(v); s=v[-1]-v[0]
    return float(100*g.max()/s) if s>0 else 0.0

F,Pw,S=load('free_ext'),load('hold30'),load('hold66')
Fp,Pp,Sp=load('free_ext','pt_dbm'),load('hold30','pt_dbm'),load('hold66','pt_dbm')
Fr,Sr=load('free_ext','rb'),load('hold66','rb')
Fh=load('free_ext','ho_per_ep'); Fret=load('free_ext','return_mean')
Pret,Pcv=load('hold30','return_mean'),load('hold30','cvar25')
Fcv=load('free_ext','cvar25'); Pho,Prb=load('hold30','ho_per_ep'),load('hold30','rb')

P('='*72); P('FROZEN FINAL NUMBERS  (python freeze_final.py)'); P('240 runs, seeds 20-99, 3 arms | seed %d | %d permutations'%(SEED,NPERM)); P('='*72)
P(); P('[A] THE THREE ARMS -- out-of-sample RLF %')
P('%-24s %4s %8s %8s %8s %8s'%('arm','n','mean','sd','median','worst'))
for nm,v in [('F nothing inert',F),('P power inert',Pw),('S spectrum inert',S)]:
    P('%-24s %4d %8.3f %8.3f %8.3f %8.3f'%(nm,len(v),v.mean(),v.std(ddof=1),np.median(v),v.max()))
P(); P('[B] COLLAPSES (power < 25 dBm)')
for nm,v in [('F',Fp),('P',Pp),('S',Sp)]: P('  %-3s %2d / 80'%(nm,(v<25).sum()))
P(); P('[C] CO-PRIMARY TESTS')
o,p=perm(Pw-S);  P('  CP1  P minus S : %+.4f pp, p = %.5f'%(o,p))
o2,p2=perm(S-F); lo,hi=ci(S-F)
P('  CP2  S minus F : %+.4f pp, p = %.5f, 90%% CI [%+.4f, %+.4f]'%(o2,p2,lo,hi))
P('       equivalence bound +/-%.2f : %s'%(EQ,'MET' if (lo>-EQ and hi<EQ) else 'NOT MET'))
o3,p3=perm(F-Pw); P('  REF  F minus P : %+.4f pp, p = %.5f'%(o3,p3))
P(); P('[D] BRANCH SPREAD, arm F, n=80 (largest gap as %% of spread)')
P('  power     %5.1f%%'%gap(Fp)); P('  spectrum  %5.1f%%'%gap(Fr)); P('  handover  %5.1f%%'%gap(Fh))
P('  narrow-band runs in F : %d / 80 (%.0f%%)'%((Fr<30).sum(),100*(Fr<30).mean()))
P(); P('[E] COST ASYMMETRY within arm F (n=80)')
lo_,hi_=F[Fp<25],F[Fp>=25]
hn,hw=F[(Fp>=25)&(Fr<30)],F[(Fp>=25)&(Fr>=30)]
P('  power    low %2d %6.3f%%  high %2d %6.3f%%  -> %.2fx'%(len(lo_),lo_.mean(),len(hi_),hi_.mean(),lo_.mean()/hi_.mean()))
P('  spectrum narrow %2d %6.3f%%  wide %2d %6.3f%%  -> %.2fx (within high power)'%(len(hn),hn.mean(),len(hw),hw.mean(),hn.mean()/hw.mean()))
P('  absolute: power %+.2f pp | spectrum %+.2f pp'%(lo_.mean()-hi_.mean(),hn.mean()-hw.mean()))
P(); P('[F] THRESHOLD SENSITIVITY (arm F)')
for pc in (24.,25.,26.):
    for sc in (25.,30.,35.):
        l,h=F[Fp<pc],F[Fp>=pc]; a,b=F[(Fp>=pc)&(Fr<sc)],F[(Fp>=pc)&(Fr>=sc)]
        if len(l) and len(h) and len(a) and len(b):
            P('  power<%2.0f spec<%2.0f : power %.2fx | spectrum %.2fx'%(pc,sc,l.mean()/h.mean(),a.mean()/b.mean()))
P(); P('[G] NO-DEGRADATION CHECK (arm P vs arm F)')
P('  return   F %7.3f   P %7.3f'%(Fret.mean(),Pret.mean()))
P('  cvar25   F %7.3f   P %7.3f'%(Fcv.mean(),Pcv.mean()))
P('  ho/ep    F %7.4f   P %7.4f'%(Fh.mean(),Pho.mean()))
P('  RB       F %7.3f   P %7.3f'%(Fr.mean(),Prb.mean()))
P(); P('[H] DERIVED AND OUTLIER FIGURES CITED IN THE TEXT')
from scipy.stats import fisher_exact
_,fp = fisher_exact([[6,14],[2,18]])
P('  Fisher 6/20 vs 2/20 (the underpowered first attempt) : p = %.3f'%fp)
i97 = int(np.argmax(Fh)) + 20
P('  outlier run: seed %d | handovers/ep %.2f | RLF %.2f%% | power %.2f dBm'
  %(i97, Fh.max(), F[np.argmax(Fh)], Fp[np.argmax(Fh)]))
rest = np.sort(Fh)[:-1]
P('  other 79 handover values: min %.2f  max %.2f'%(rest.min(), rest.max()))
g2 = np.diff(rest); P('  handover gap statistic excluding the outlier : %.1f%%'
                      %(100*g2.max()/(rest[-1]-rest[0])))
P('  handover median (arm F) %.3f  | arm P median %.3f'%(np.median(Fh), np.median(Pho)))
P('  absolute pp differences: power %+.2f | spectrum %+.2f'
  %(lo_.mean()-hi_.mean(), hn.mean()-hw.mean()))
P('  (the manuscript rounds these to 6.9 and 0.4)')

P(); P('[I] BRANCH OCCUPANCY, arm F -- counts, no shape statistic')
P('  power   : %2d below 25 dBm | %2d between 25-28 | %2d at 28+'
  %((Fp<25).sum(), ((Fp>=25)&(Fp<28)).sum(), (Fp>=28).sum()))
P('  spectrum: %2d below 20 RB  | %2d between 20-50 | %2d at 50+'
  %((Fr<20).sum(), ((Fr>=20)&(Fr<50)).sum(), (Fr>=50).sum()))
P('  handover: %2d within 0.26-0.79 | %2d above 1.0'%((Fh<=1).sum(), (Fh>1).sum()))
P('  gap statistic on spectrum excluding the 4 intermediate runs:')
_s2=np.sort(Fr[(Fr<20)|(Fr>=50)])
P('    %.1f%% (against 36.7%% with them included)'%(100*np.diff(_s2).max()/(_s2[-1]-_s2[0])))

open(os.path.join(DATA,'FROZEN_FINAL.txt') if DATA.endswith('results') else os.path.join(HERE,'FROZEN_FINAL.txt'),'w').write('\n'.join(out)+'\n')
print('\n-> FROZEN_FINAL.txt written')
