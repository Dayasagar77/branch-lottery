"""Revision analyses for the TMLCN review response.

Run from the repository:  cd code && python revision_analysis.py > ../results/FROZEN_REVISION_check.txt
Every number in the revised manuscript that is new comes from this script.
Run from Paper2/code:  python revision_analysis.py > FROZEN_REVISION.txt
No retraining: all inputs are stored per-run files under models/.
"""
import glob,csv,re,random,statistics as st
import os
# works from the repository (../results) or from the original tree (models/)
R = '../results/' if os.path.isdir('../results/free_ext') else 'models/'
SEED=20260922
def load(d,lo,hi):
    o={}
    for f in sorted(glob.glob(R+d+'/model_s*_metrics.csv')):
        s=int(re.search(r'model_s(\d+)_',f).group(1))
        if lo<=s<=hi:
            r=next(csv.DictReader(open(f)))
            o[s]={'rlf':float(r['rlf_rate']),'inrlf':float(r['insample_rlf_rate']),
                  'pt':float(r['pt_dbm']),'rb':float(r['rb']),'ho':float(r['ho_per_ep']),
                  'ret':float(r['return_mean']),'cvar':float(r['cvar25'])}
    return o
def q(v,p):
    v=sorted(v); k=(len(v)-1)*p; i=int(k); return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(k-i)
def boot(d,n=20000):
    random.seed(SEED); m=[sum(random.choice(d) for _ in d)/len(d) for _ in range(n)]
    m.sort(); return m[int(.025*n)],m[int(.975*n)]

F,P,S=load('free_ext',20,99),load('hold30',20,99),load('hold66',20,99)
A1,A2=load('basin_v2',0,19),load('hold30',0,19)
seeds=sorted(set(F)&set(P)&set(S))

print('[A] EXPERIMENTAL INVENTORY')
for nm,d,lo,hi in [('A1 power learned','basin_v2',0,19),('A2 power fixed','hold30',0,19),
                   ('A3 pin-and-release','pin750',0,19),('spectrum-inert pilot','hold66',0,19),
                   ('w_pwr 0.02','wpwr_w0.02',0,19),('w_pwr 0.05','wpwr_w0.05',0,19),
                   ('w_pwr 0.45','wpwr_w0.45',0,19),('F nothing inert','free_ext',20,99),
                   ('P power inert','hold30',20,99),('S spectrum inert','hold66',20,99)]:
    n=len(glob.glob(R+d+'/model_s*_metrics.csv'))
    k=len([f for f in glob.glob(R+d+'/model_s*_metrics.csv')
           if lo<=int(re.search(r'model_s(\d+)_',f).group(1))<=hi])
    print('  %-22s dir=%-12s seeds %3d-%-3d  n=%3d'%(nm,d,lo,hi,k))
print('  NOTE: free_ext seeds 20-99 serve as BOTH the confirmatory A1 stratification')
print('        and the F arm of the co-primary test. Not independent samples.')

print('\n[B] BAND OCCUPANCY, arm F (n=%d)'%len(F))
lo_=[s for s in F if F[s]['pt']<25]; hi_=[s for s in F if F[s]['pt']>=28]
print('  power  : %d below 25 dBm | %d in [25,28) | %d at or above 28 dBm'%(
      len(lo_),len([s for s in F if 25<=F[s]['pt']<28]),len(hi_)))
print('  spectrum: %d below 20 RB | %d in [20,50] | %d above 50 RB'%(
      len([s for s in F if F[s]['rb']<20]),len([s for s in F if 20<=F[s]['rb']<=50]),
      len([s for s in F if F[s]['rb']>50])))
print('  spectrum at the <30 RB narrow-band definition: %d narrow'%len([s for s in F if F[s]['rb']<30]))

print('\n[C] CO-PRIMARY EFFECT SIZES (paired, n=%d)'%len(seeds))
print('  contrast   mean      median    95%% CI                 +/-/0        trimmed(8)')
for nm,a,b in [('P - S',P,S),('S - F',S,F),('F - P',F,P)]:
    d=[a[s]['rlf']-b[s]['rlf'] for s in seeds]; l,h=boot(d)
    print('  %-10s %-9.3f %-9.3f [%+7.3f, %+7.3f]   %-12s %.3f'%(nm,st.mean(d),st.median(d),l,h,
          '%d/%d/%d'%(sum(1 for x in d if x>0),sum(1 for x in d if x<0),sum(1 for x in d if x==0)),
          st.mean(sorted(d)[4:-4])))

print('\n[D] MULTI-OBJECTIVE VIEW (paired seeds)')
print('  arm                RLF    p90    p95    worst  mW      RB     HO/ep  CVaR')
for nm,A in [('F nothing inert',F),('P power inert',P),('S spectrum inert',S)]:
    v=[A[s]['rlf'] for s in seeds]
    print('  %-18s %-6.3f %-6.3f %-6.3f %-6.3f %-7.1f %-6.2f %-6.3f %.2f'%(nm,st.mean(v),q(v,.9),q(v,.95),max(v),
          st.mean(10**(A[s]['pt']/10) for s in seeds),st.mean(A[s]['rb'] for s in seeds),
          st.mean(A[s]['ho'] for s in seeds),st.mean(A[s]['cvar'] for s in seeds)))

print('\n[E] SEED-SELECTION BASELINE (best-of-N on F by in-sample RLF, held-out scored)')
xs=[F[s]['inrlf'] for s in F]; ys=[F[s]['rlf'] for s in F]
mx,my=st.mean(xs),st.mean(ys)
r=sum((a-mx)*(b-my) for a,b in zip(xs,ys))/((sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**0.5)
print('  correlation(in-sample RLF, held-out RLF) = %.3f'%r)
Pm=st.mean(P[s]['rlf'] for s in P); Pw=max(P[s]['rlf'] for s in P)
print('  N    mean   median p90    p95    max    P(>P worst)')
random.seed(SEED); ks=list(F)
for N in [1,2,3,5,10,20]:
    pk=[F[min(random.sample(ks,N),key=lambda s:F[s]['inrlf'])]['rlf'] for _ in range(4000)]
    print('  %-4d %-6.3f %-6.3f %-6.3f %-6.3f %-6.3f %.1f%%'%(N,st.mean(pk),st.median(pk),q(pk,.9),q(pk,.95),max(pk),
          100*sum(1 for p in pk if p>Pw)/len(pk)))
print('  P (power inert, single run): mean %.3f  worst %.3f'%(Pm,Pw))

print('\n[F] HANDOVER TAIL SCREEN (> 5 handovers/episode)')
for nm,A in [('F',F),('P',P),('S',S)]:
    bad=[(s,A[s]['ho'],A[s]['rlf']) for s in A if A[s]['ho']>5]
    ok=[A[s]['ho'] for s in A if A[s]['ho']<=5]
    print('  %-3s %d/80 pathological %-28s | others %.3f-%.3f'%(nm,len(bad),
          ', '.join('s%d(%.1f HO, %.1f%%)'%b for b in bad) or '-',min(ok),max(ok)))
clean=[s for s in seeds if max(F[s]['ho'],P[s]['ho'],S[s]['ho'])<=5]
print('  robustness, excluding the %d seeds with any pathology:'%(len(seeds)-len(clean)))
for nm,A in [('F',F),('P',P),('S',S)]:
    print('    %-3s all %.3f   clean %.3f'%(nm,st.mean(A[s]['rlf'] for s in seeds),st.mean(A[s]['rlf'] for s in clean)))

print('\n[G] SPECTRUM-USE CLAIM: does the n=20 result replicate at n=80?')
hp20=[s for s in A1 if A1[s]['pt']>=28]; hp80=[s for s in F if F[s]['pt']>=28]
print('  n=20 : A2 %.2f RB vs A1 high-power subset %.2f RB   -> fixed power uses LESS'%(
      st.mean(A2[s]['rb'] for s in A2), st.mean(A1[s]['rb'] for s in hp20)))
print('  n=80 : P  %.2f RB vs F  high-power subset %.2f RB   -> fixed power uses MORE'%(
      st.mean(P[s]['rb'] for s in P), st.mean(F[s]['rb'] for s in hp80)))
print('  The n=20 direction DOES NOT REPLICATE.')

print('\n[H] TRAINING DYNAMICS (arm F, per-episode pt_mean)')
tr={}
for s in F:
    tr[s]=[float(x['pt_mean']) for x in csv.DictReader(open(R+'free_ext/model_s%d_returns.csv'%s))]
print('  episode  median low   median high  gap(dB)')
for e in [0,100,200,300,500,750,1000,1499]:
    a=st.median(tr[s][e] for s in lo_); b=st.median(tr[s][e] for s in hi_)
    print('  %-8d %-12.2f %-12.2f %+.2f'%(e,a,b,b-a))
def auc(p,n):
    t=0; c=0
    for a in p:
        for b in n:
            c+=1; t+= 1 if a<b else (0.5 if a==b else 0)
    return max(t/c,1-t/c)
cols=['pt_mean','return','rb_mean','ho','steps']
dat={s:{c:[float(x[c]) for x in csv.DictReader(open(R+'free_ext/model_s%d_returns.csv'%s))] for c in cols} for s in F}
print('  AUC for predicting the low mode from the first K episodes (in-sample, optimistic)')
print('  K     '+''.join('%-9s'%c for c in cols))
for K in [100,200,300,500,750,1000]:
    print('  %-6d'%K+''.join('%-9.3f'%auc([sum(dat[s][c][:K])/K for s in lo_],[sum(dat[s][c][:K])/K for s in hi_]) for c in cols))
