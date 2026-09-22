#!/usr/bin/env python3
"""Freeze EVERY number that will appear in the paper, recomputed from source run files.

Nothing in the manuscript may be typed from memory. This writes FROZEN_NUMBERS.txt;
each claim in the draft must be traceable to a line here.
"""
import os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RNG_SEED, N_PERM = 20260921, 200_000
FLOOR, CEIL = 25.0, 28.0
out = []
def P(s=''): out.append(s); print(s)


def load(folder, n=20):
    rows = []
    for s in range(n):
        p = os.path.join(HERE, 'models', folder, 'model_s%d_metrics.csv' % s)
        if not os.path.exists(p):
            return None
        r = pd.read_csv(p).iloc[0]
        rows.append(dict(seed=s, rlf=float(r['rlf_rate']), pt=float(r['pt_dbm']),
                         rb=float(r['rb']), ret=float(r['return_mean']),
                         cvar=float(r['cvar25']), ho=float(r['ho_per_ep']),
                         steps=float(r['steps'])))
    return pd.DataFrame(rows)


def perm_two(x, y, n=N_PERM, seed=RNG_SEED):
    obs = x.mean() - y.mean(); pool = np.concatenate([x, y]); nx = len(x)
    rng = np.random.default_rng(seed); c = 0
    for _ in range(n):
        rng.shuffle(pool)
        if abs(pool[:nx].mean() - pool[nx:].mean()) >= abs(obs) - 1e-12: c += 1
    return obs, (c + 1) / (n + 1)


def perm_paired(d, n=N_PERM, seed=RNG_SEED):
    obs = d.mean(); rng = np.random.default_rng(seed); c = 0
    for _ in range(n):
        if abs((d * rng.choice([-1.0, 1.0], size=len(d))).mean()) >= abs(obs) - 1e-12: c += 1
    return obs, (c + 1) / (n + 1)


def gap(v):
    v = np.sort(v); g = np.diff(v); i = int(np.argmax(g))
    span = v[-1] - v[0]
    return float(g[i]), float(g[i] / span * 100) if span > 0 else 0.0, i + 1


B, H, Pn = load('basin_v2'), load('hold30'), load('pin750')
P('=' * 78); P('FROZEN NUMBERS  (regenerate with: python freeze_numbers.py)')
P('seed %d | %d permutations | floor <%.0f dBm | ceiling >=%.0f dBm' % (RNG_SEED, N_PERM, FLOOR, CEIL))
P('=' * 78)

P(); P('[T1] THE THREE ARMS -- out-of-sample RLF %, 500 held-out episodes per run')
P('%-24s %3s %8s %8s %8s %8s %8s' % ('arm', 'n', 'mean', 'sd', 'min', 'median', 'max'))
for nm, D in [('A1 inc3 (power free)', B), ('A2 hold30 (power fixed)', H), ('A3 pin750 (pin+release)', Pn)]:
    v = D['rlf'].values
    P('%-24s %3d %8.4f %8.4f %8.4f %8.4f %8.4f'
      % (nm, len(v), v.mean(), v.std(ddof=1), v.min(), np.median(v), v.max()))
c = B[B['pt'] >= CEIL]
P('%-24s %3d %8.4f %8.4f %8.4f %8.4f %8.4f'
  % ('A1 ceiling subset', len(c), c['rlf'].mean(), c['rlf'].std(ddof=1),
     c['rlf'].min(), np.median(c['rlf']), c['rlf'].max()))

P(); P('[T2] COLLAPSES (mean transmit power < %.0f dBm)' % FLOOR)
for nm, D in [('inc3 power free', B), ('hold30 power fixed', H), ('pin750 pin+release', Pn)]:
    P('  %-22s %2d / 20' % (nm, int((D['pt'] < FLOOR).sum())))

P(); P('[T3] TESTS')
o, p = perm_two(H['rlf'].values, c['rlf'].values)
P('  hold30 vs inc3-ceiling, unpaired : %+.4f pp, p = %.5f' % (o, p))
o, p = perm_paired(H['rlf'].values - B['rlf'].values)
P('  hold30 vs inc3-all, paired       : %+.4f pp, p = %.5f' % (o, p))
o, p = perm_paired(Pn['rlf'].values - B['rlf'].values)
P('  pin750 vs inc3-all, paired       : %+.4f pp, p = %.5f' % (o, p))
P('  hold30 mean minus pin750 mean    : %+.4f pp' % (H['rlf'].mean() - Pn['rlf'].mean()))

P(); P('[T4] REWARD-WEIGHT SWEEP (same 20 seeds, same config)')
P('  %-10s %-8s %8s %8s %10s' % ('folder', 'W_PWR', 'collapsed', 'ceiling', 'mean RLF%'))
for f, w in [('wpwr_w0.02', '0.02'), ('wpwr_w0.05', '0.05'), ('basin_v2', '0.15'), ('wpwr_w0.45', '0.45')]:
    D = load(f)
    if D is None: P('  %-10s MISSING' % f); continue
    P('  %-10s %-8s %8d %8d %10.3f'
      % (f, w, int((D['pt'] < FLOOR).sum()), int((D['pt'] >= CEIL).sum()), D['rlf'].mean()))
P('  %-10s %-8s %8d %8d %10.3f' % ('hold30', 'n/a', 0, 20, H['rlf'].mean()))

P(); P('[T5] BRANCH SPLIT, inc3 (basin_v2), 20 runs')
for lbl, k in [('power  (dBm)', 'pt'), ('spectrum (RB)', 'rb'), ('handover (/ep)', 'ho')]:
    v = B[k].values; g, pc, nlow = gap(v)
    P('  %-15s gap %8.3f = %5.1f%% of spread | %s'
      % (lbl, g, pc, ('TWO CLUSTERS, %d low / %d high' % (nlow, 20 - nlow)) if pc > 50 else 'one group'))
    P('  %-15s sorted: %s' % ('', ' '.join('%.2f' % x for x in np.sort(v))))
P('  low-power seeds   : %s' % sorted(B[B['pt'] < FLOOR]['seed'].tolist()))
P('  low-spectrum seeds: %s' % sorted(B[B['rb'] < 30]['seed'].tolist()))
P('  narrow-band count by arm: inc3 %d, hold30 %d, pin750 %d'
  % ((B['rb'] < 30).sum(), (H['rb'] < 30).sum(), (Pn['rb'] < 30).sum()))

P(); P('[T6] 2x2 -- all 60 runs, stratified by both branch modes')
A = pd.concat([B, H, Pn])
P('  %-8s %-8s %5s %11s %9s' % ('power', 'spectrum', 'runs', 'mean RLF%', 'worst'))
for lp in (True, False):
    for ls in (True, False):
        g2 = A[((A['pt'] < FLOOR) == lp) & ((A['rb'] < 30) == ls)]
        P('  %-8s %-8s %5d %11.2f %9.2f'
          % ('quiet' if lp else 'loud', 'narrow' if ls else 'wide', len(g2),
             g2['rlf'].mean() if len(g2) else float('nan'),
             g2['rlf'].max() if len(g2) else float('nan')))
q, l = A[A['pt'] < FLOOR]['rlf'], A[A['pt'] >= FLOOR]['rlf']
nw, wd = A[A['rb'] < 30]['rlf'], A[A['rb'] >= 30]['rlf']
P('  power   : quiet %d runs %.4f%% vs loud %d runs %.4f%%  -> ratio %.2fx'
  % (len(q), q.mean(), len(l), l.mean(), q.mean() / l.mean()))
P('  spectrum: narrow %d runs %.4f%% vs wide %d runs %.4f%% -> ratio %.2fx'
  % (len(nw), nw.mean(), len(wd), wd.mean(), nw.mean() / wd.mean()))

P(); P('[T7] REWARD DECOMPOSITION per episode (inc3 floor vs ceiling)')
W_REL, RLF_PEN, W_PWR, W_SPEC, W_HO = 1.0, 20.0, 0.15, 0.05, 0.05
PT_MIN, PT_MAX, RB_MIN, RB_MAX = 23., 30., 10, 66
def dec(folder, seeds):
    acc = []
    for s in seeds:
        e = pd.read_csv(os.path.join(HERE, 'models', folder, 'model_s%d_eval.csv' % s))
        st, pt, rb = e['steps'].values, e['mean_pt'].values, e['mean_rb'].values
        ho, rl, ret = e['n_ho'].values, e['rlf'].values.astype(float), e['ret'].values
        acc.append(dict(ret=ret.mean(), link=(W_REL*(st-rl)).mean(),
                        rlf=(-RLF_PEN*rl).mean(),
                        pwr=(-W_PWR*((pt-PT_MIN)/(PT_MAX-PT_MIN))*st).mean(),
                        spec=(-W_SPEC*((rb-RB_MIN)/(RB_MAX-RB_MIN))*st).mean(),
                        hoc=(-W_HO*ho).mean()))
    return pd.DataFrame(acc).mean()
fl = dec('basin_v2', B[B['pt'] < FLOOR]['seed'].tolist())
ce = dec('basin_v2', B[B['pt'] >= CEIL]['seed'].tolist())
P('  %-10s %9s %9s %9s %9s %9s %9s' % ('', 'return', 'link+', 'RLF-', 'power-', 'spec-', 'ho-'))
for nm, d in [('floor', fl), ('ceiling', ce)]:
    P('  %-10s %9.2f %9.2f %9.2f %9.2f %9.2f %9.2f'
      % (nm, d['ret'], d['link'], d['rlf'], d['pwr'], d['spec'], d['hoc']))
P('  %-10s %9.2f %9.2f %9.2f %9.2f %9.2f %9.2f'
  % ('difference', fl['ret']-ce['ret'], fl['link']-ce['link'], fl['rlf']-ce['rlf'],
     fl['pwr']-ce['pwr'], fl['spec']-ce['spec'], fl['hoc']-ce['hoc']))

P(); P('[T8] MEAN RETURN vs CVaR25 -- the two rank the basins oppositely')
f2, c2 = B[B['pt'] < FLOOR], B[B['pt'] >= CEIL]
P('  floor   : return %8.3f  cvar25 %8.3f  (n=%d)' % (f2['ret'].mean(), f2['cvar'].mean(), len(f2)))
P('  ceiling : return %8.3f  cvar25 %8.3f  (n=%d)' % (c2['ret'].mean(), c2['cvar'].mean(), len(c2)))
P('  floor minus ceiling: return %+.3f | cvar25 %+.3f' %
  (f2['ret'].mean()-c2['ret'].mean(), f2['cvar'].mean()-c2['cvar'].mean()))
P('  hold30  : return %8.3f  cvar25 %8.3f' % (H['ret'].mean(), H['cvar'].mean()))

P(); P('[T9] PER-SEED, all three arms')
P('  %4s | %8s %8s | %8s %8s | %8s %8s' % ('seed','inc3 dBm','inc3 RLF','fix dBm','fix RLF','pin dBm','pin RLF'))
for s in range(20):
    P('  %4d | %8.2f %8.2f | %8.2f %8.2f | %8.2f %8.2f'
      % (s, B.loc[s,'pt'], B.loc[s,'rlf'], H.loc[s,'pt'], H.loc[s,'rlf'], Pn.loc[s,'pt'], Pn.loc[s,'rlf']))

P(); P('[T10] SECONDARY MEANS (for the no-degradation claim)')
for nm, D in [('inc3 all', B), ('inc3 ceiling', c), ('hold30', H), ('pin750', Pn)]:
    P('  %-14s return %8.3f | cvar25 %8.3f | ho/ep %6.4f | RB %7.3f'
      % (nm, D['ret'].mean(), D['cvar'].mean(), D['ho'].mean(), D['rb'].mean()))

P(); P('[T11] SUBGROUP CLAIMS USED IN THE TEXT')
prev_hi = B[B['pt'] >= CEIL]['seed'].tolist()
prev_lo = B[B['pt'] < FLOOR]['seed'].tolist()
dh = H.set_index('seed').loc[prev_hi, 'rlf'].values - B.set_index('seed').loc[prev_hi, 'rlf'].values
P('  A2 minus A1 on the %d previously-high-power seeds : %+.4f pp (mean)' % (len(prev_hi), dh.mean()))
P('  A1 mean RLF on the %d collapsed seeds             : %.4f %%' % (len(prev_lo), B.set_index('seed').loc[prev_lo,'rlf'].mean()))
P('  A2 mean RLF on those same seeds                   : %.4f %%' % H.set_index('seed').loc[prev_lo,'rlf'].mean())
dp = Pn.set_index('seed').loc[prev_hi, 'rlf'].values - B.set_index('seed').loc[prev_hi, 'rlf'].values
P('  A3 minus A1 on the previously-high-power seeds    : %+.4f pp (mean)' % dp.mean())
P('  A3: of those %d, worse on %d, better on %d, equal on %d'
  % (len(prev_hi), int((dp > 0).sum()), int((dp < 0).sum()), int((dp == 0).sum())))
P('  A3 rescued to high power, of the %d collapsed     : %d'
  % (len(prev_lo), int((Pn.set_index('seed').loc[prev_lo,'pt'] >= CEIL).sum())))
P('  reward decomposition: link+RLF cost paid by low mode = %.4f' % (2.67 + 1.59))

open(os.path.join(HERE, 'FROZEN_NUMBERS.txt'), 'w').write('\n'.join(out) + '\n')
print('\n-> written to FROZEN_NUMBERS.txt')
