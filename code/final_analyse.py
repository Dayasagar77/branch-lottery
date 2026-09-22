#!/usr/bin/env python3
"""FINAL pre-registered analysis.
PREREG_SeedExtension_BranchSpecificity_PROPERLY_POWERED_FROZEN_20260921.md

F = free_ext (both free) | P = hold30 (power inert) | S = hold66 (spectrum inert)
Seeds 20-99, 80 fresh pairs. Primary metric: out-of-sample RLF rate.

CO-PRIMARY 1  P vs S  : H-BRANCH-SPECIFIC predicts P significantly better.
CO-PRIMARY 2  S vs F  : H-ANY-SIMPLIFICATION predicts S significantly better;
                        H-BRANCH-SPECIFIC predicts no difference.
Equivalence bound fixed in advance: 90% CI within +/-0.75 pp => practically equivalent.
"""
import os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SEED, NPERM, EQ = 20260921, 200_000, 0.75

def load(folder, col='rlf_rate'):
    return np.array([float(pd.read_csv(os.path.join(HERE,'models',folder,'model_s%d_metrics.csv'%s)).iloc[0][col])
                     for s in range(20,100)])

def perm(d, seed=SEED, n=NPERM):
    obs = d.mean(); rng = np.random.default_rng(seed); c = 0
    for _ in range(n):
        if abs((d*rng.choice([-1.0,1.0],size=len(d))).mean()) >= abs(obs)-1e-12: c += 1
    return obs, (c+1)/(n+1)

def boot_ci(d, seed=SEED, n=20000, lo=5, hi=95):
    rng = np.random.default_rng(seed)
    m = [rng.choice(d, size=len(d), replace=True).mean() for _ in range(n)]
    return float(np.percentile(m, lo)), float(np.percentile(m, hi))

F, P, S = load('free_ext'), load('hold30'), load('hold66')
Fp, Pp, Sp = load('free_ext','pt_dbm'), load('hold30','pt_dbm'), load('hold66','pt_dbm')

print('='*70); print('FINAL PRE-REGISTERED ANALYSIS -- 80 fresh seeds, 240 runs'); print('='*70)
print('%-26s %6s %7s %7s %7s'%('','mean','sd','median','worst'))
for nm,v in [('F  nothing inert',F),('P  power inert',P),('S  spectrum inert',S)]:
    print('%-26s %6.3f %7.3f %7.3f %7.3f'%(nm,v.mean(),v.std(ddof=1),np.median(v),v.max()))
print()
print('  collapses (power < 25 dBm):  F %2d/80   P %2d/80   S %2d/80'
      % ((Fp<25).sum(), (Pp<25).sum(), (Sp<25).sum()))

print(); print('='*70); print('CO-PRIMARY 1 -- branch specificity:  P vs S'); print('='*70)
o1,p1 = perm(P-S)
print('  paired difference (P minus S) : %+.4f pp' % o1)
print('  permutation p                 : %.5f' % p1)
c1 = (p1 < 0.05) and (o1 < 0)
print('  --> %s' % ('P significantly BETTER than S' if c1 else
                    ('P significantly WORSE' if (p1<0.05 and o1>0) else 'no significant difference')))

print(); print('='*70); print('CO-PRIMARY 2 -- does simplification help generically:  S vs F'); print('='*70)
o2,p2 = perm(S-F)
lo,hi = boot_ci(S-F)
print('  paired difference (S minus F) : %+.4f pp' % o2)
print('  permutation p                 : %.5f' % p2)
print('  90%% CI                        : [%+.4f, %+.4f]' % (lo,hi))
sig2 = (p2 < 0.05) and (o2 < 0)
equiv = (lo > -EQ) and (hi < EQ)
print('  equivalence bound +/-%.2f pp   : %s' % (EQ, 'WITHIN -> practically equivalent' if equiv else 'NOT within'))
print('  --> %s' % ('S significantly BETTER than F' if sig2 else 'S not significantly better than F'))

print(); print('='*70); print('REFERENCE -- F vs P (must replicate)'); print('='*70)
o3,p3 = perm(F-P)
print('  paired difference (F minus P) : %+.4f pp, p = %.5f' % (o3,p3))
print('  --> %s' % ('REPLICATES' if (p3<0.05 and o3>0) else 'DOES NOT REPLICATE -- report first'))

print(); print('='*70); print('PRE-REGISTERED DECISION'); print('='*70)
if c1 and not sig2:
    v = 'H-BRANCH-SPECIFIC SUPPORTED -- branch identity matters'
elif (not c1) and sig2:
    v = 'H-ANY-SIMPLIFICATION -- the claim dies, paper reframed'
elif c1 and sig2:
    v = 'BOTH REAL -- branch identity modulates a generic benefit (weaker claim)'
else:
    v = 'UNDERPOWERED DESPITE THE EXTENSION -- fall back to measurement-only'
print('  ' + v)
