#!/usr/bin/env python3
"""PREREG_05 adjudication — the 2x2 factorial separating branch identity from head removal.

Frozen spec (PREREG_05 sections 4 and 5), reproduced here verbatim in code:

  co-primary 1, BRANCH main effect : (FA - S) + (P - SR)
  co-primary 2, ARCHITECTURE effect: (P - FA) + (SR - S)
  secondary, interaction           : (FA - S) - (P - SR)   [reported, NOT tested]

  test      : two-sided sign-flip permutation, 200,000 draws, RNG seed 20260922
  effects   : mean, median, 20,000-draw bootstrap 95% interval, sign counts
  primary   : out-of-sample RLF rate on the 500 held-out episodes

ALPHA. The pre-registration fixed the test but did not fix an alpha. This script therefore
declares, before any number was computed: the project's standing 0.05 adjudicates the decision
table, and the result at 0.025 (Bonferroni for two co-primaries) is reported alongside as a
robustness statement. Exact p-values are printed so any other threshold can be applied.

Read-only. Trains nothing.
"""
import numpy as np, pandas as pd, glob, re, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, '..', '..', 'Paper2', 'code'))
# works from the released repository (../results) or from the original tree (Paper2/code/models)
_REPO = os.path.abspath(os.path.join(HERE, '..', 'results'))
MODELS = _REPO if os.path.isdir(os.path.join(_REPO, 'free_ext')) else os.path.join(CODE, 'models')
ARMS = {'F': 'free_ext', 'P': 'hold30', 'S': 'hold66', 'FA': 'force30', 'SR': 'hold66r'}
SEEDS = list(range(20, 100))

def load(folder):
    out = {}
    for f in glob.glob(os.path.join(MODELS, folder, 'model_s*_metrics.csv')):
        s = int(re.search(r'model_s(\d+)_', f).group(1))
        if s in SEEDS:
            out[s] = float(pd.read_csv(f).iloc[0]['rlf_rate'])
    return np.array([out[s] for s in SEEDS])

R = {k: load(v) for k, v in ARMS.items()}
for k, v in R.items():
    assert len(v) == 80, '%s has %d runs' % (k, len(v))

def signflip(d, B=200_000, seed=20260922):
    rng = np.random.default_rng(seed)
    obs = d.mean()
    flips = rng.choice(np.array([-1.0, 1.0]), size=(B, d.size))
    null = (flips * d).mean(axis=1)
    p = (1 + int(np.sum(np.abs(null) >= abs(obs)))) / (1 + B)
    return obs, p

def boot(d, B=20_000, seed=20260922):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, d.size, size=(B, d.size))
    m = d[idx].mean(axis=1)
    return np.percentile(m, 2.5), np.percentile(m, 97.5)

def report(name, d, tested=True):
    lo, hi = boot(d)
    neg, zer, pos = int((d < 0).sum()), int((d == 0).sum()), int((d > 0).sum())
    line = ('%-28s mean %+7.4f  median %+7.4f  95%% CI [%+7.4f, %+7.4f]  signs -/0/+ %d/%d/%d'
            % (name, d.mean(), np.median(d), lo, hi, neg, zer, pos))
    if tested:
        obs, p = signflip(d)
        line += '  p = %.6f' % p
        print(line)
        return p
    print(line)
    return None

print('=' * 104)
print('PREREG_05 ADJUDICATION — 2x2 factorial, seeds 20-99, n = 80 per arm, 400 runs')
print('=' * 104)
print('\nARM MEANS (held-out RLF rate, %):')
for k in ('F', 'P', 'S', 'FA', 'SR'):
    print('   %-3s %-10s mean %6.3f   median %6.3f   max %6.3f'
          % (k, ARMS[k], R[k].mean(), np.median(R[k]), R[k].max()))

print('\nTHE 2x2 (mean held-out RLF %):')
print('   %-26s %-14s %-14s' % ('', 'head kept (3)', 'head reduced (1)'))
print('   %-26s %-14.3f %-14.3f' % ('power pinned at 30 dBm', R['FA'].mean(), R['P'].mean()))
print('   %-26s %-14.3f %-14.3f' % ('spectrum pinned at 66 RB', R['S'].mean(), R['SR'].mean()))
print('   %-26s %-14.3f' % ('reference F, nothing pinned', R['F'].mean()))

d_branch = (R['FA'] - R['S']) + (R['P'] - R['SR'])
d_arch   = (R['P'] - R['FA']) + (R['SR'] - R['S'])
d_inter  = (R['FA'] - R['S']) - (R['P'] - R['SR'])

print('\nCO-PRIMARIES (two-sided sign-flip, 200,000 draws, seed 20260922):')
p_branch = report('branch  (FA-S)+(P-SR)', d_branch)
p_arch   = report('arch    (P-FA)+(SR-S)', d_arch)
print('\nSECONDARY (reported, NOT tested — underpowered by declaration):')
report('interaction (FA-S)-(P-SR)', d_inter, tested=False)

print('\nCOMPONENT CONTRASTS (context only, not the co-primaries):')
for nm, d in (('FA - S', R['FA'] - R['S']), ('P - SR', R['P'] - R['SR']),
              ('P - FA', R['P'] - R['FA']), ('SR - S', R['SR'] - R['S']),
              ('F - P ', R['F'] - R['P'])):
    report(nm, d, tested=False)

def verdict(pb, pa, alpha):
    b, a = pb < alpha, pa < alpha
    if b and not a:  return 'H-IDENTITY SUPPORTED — the branch-identity claim survives the confound.'
    if a and not b:  return '*** KILL CONDITION FIRED *** — claim refuted; the benefit is head removal.'
    if b and a:      return 'BOTH mechanisms operate — claim narrows, both effect sizes reported.'
    return 'NEITHER significant — underpowered or no effect; branch-identity drops to a hypothesis.'

print('\n' + '=' * 104)
for alpha in (0.05, 0.025):
    print('at alpha = %-6s branch p = %.6f (%s) | architecture p = %.6f (%s)'
          % (alpha, p_branch, 'sig' if p_branch < alpha else 'ns',
             p_arch, 'sig' if p_arch < alpha else 'ns'))
    print('   -> %s' % verdict(p_branch, p_arch, alpha))
print('=' * 104)
print('\nDirection note: H-IDENTITY predicted the branch effect to be significantly NEGATIVE;')
print('H-HEAD predicted the architecture effect to be significantly NEGATIVE. A significant')
print('POSITIVE effect is not support for either hypothesis and must be reported as such.')
