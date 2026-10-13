#!/usr/bin/env python3
"""PREREG_05 section 6, checks 3 and 4 -- proved at the ENVIRONMENT level.

Check 3 (force30): the power branch keeps three outputs, and transmit power is pinned
at exactly 30.00 dBm no matter which of the three actions is chosen.
Check 4 (hold66r): the spectrum branch is reduced to a single output and allocation is
pinned at exactly 66.00 RB.

These are proved here for EVERY policy, not for one trained policy, by driving the
environment directly. That is strictly stronger than showing it for one run, and it
costs seconds instead of hours.

The clause in check 3 about the action histogram is read as follows, and this reading is
recorded BEFORE the check is run: under force30 the three power actions are behaviourally
identical, so a converged greedy policy is EXPECTED to concentrate on one of them. What the
clause exists to prove is that the head was not silently collapsed. The decisive evidence is
therefore (a) branch width 3 in the action space, (b) all three actions addressable and
accepted by the environment, and (c) all three appearing under a policy that explores.
Concentration of a greedy policy is not a defect and is not treated as a failure.

Prints PASS or FAIL per clause and exits non-zero on any failure.
Produces no outcome number belonging to the factorial.
"""
import os, sys, itertools, json

MODE_P = sys.argv[1] if len(sys.argv) > 1 else 'inc3'
MODE_S = sys.argv[2] if len(sys.argv) > 2 else 'inc3'
NEP    = int(sys.argv[3]) if len(sys.argv) > 3 else 40

os.environ['P2_PWR_ACT']  = MODE_P
os.environ['P2_SPEC_ACT'] = MODE_S

import numpy as np, pandas as pd
import paper2_env as PE

EVAL_SEED_BASE = 900_000_000
fails = []

def chk(label, ok, detail=''):
    print(('PASS  ' if ok else 'FAIL  ') + label + (('   ' + detail) if detail else ''))
    if not ok:
        fails.append(label)

print('=' * 78)
print('PREREG_05 section 6 -- environment-level proof')
print('P2_PWR_ACT=%s   P2_SPEC_ACT=%s   episodes=%d' % (MODE_P, MODE_S, NEP))
print('=' * 78)

# ---- clause 1: the module agrees with what was asked for -------------------------------
chk('module reports the requested power mode',
    PE._PWR_ACT == MODE_P, 'reports %r' % PE._PWR_ACT)
chk('module reports the requested spectrum mode',
    PE._SPEC_ACT == MODE_S, 'reports %r' % PE._SPEC_ACT)

# ---- clause 2: branch widths ------------------------------------------------------------
exp_p = {'force30': 3, 'range28': 3, 'hold30': 1, 'hold28': 1, 'hold29': 1, 'inc3': 3}[MODE_P]
exp_s = 1 if MODE_S == 'hold66r' else 3
chk('power branch width', PE.PWR_N_ACT == exp_p, 'PWR_N_ACT=%d expected %d' % (PE.PWR_N_ACT, exp_p))
chk('spectrum branch width', PE.SPEC_N_ACT == exp_s, 'SPEC_N_ACT=%d expected %d' % (PE.SPEC_N_ACT, exp_s))

pool = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dair_geometry_pool.csv'))
env = PE.MultiRSUBlockageEnv(pool, seed=0, split='test', ho_latency=2)
nvec = [int(x) for x in env.action_space.nvec]
chk('action space', nvec == [2, exp_p, exp_s], 'nvec=%s expected %s' % (nvec, [2, exp_p, exp_s]))

# ---- clause 3: the actuator is policy-independent ---------------------------------------
grid = [float(x) for x in np.arange(PE.PT_MIN, PE.PT_MAX + 0.001, 1.0)]
vals = sorted({round(PE._apply_pwr(pt, a), 6) for pt in grid for a in range(PE.PWR_N_ACT)})
if MODE_P == 'force30':
    chk('force30 pins power for EVERY (power, action) pair',
        vals == [30.0], 'reachable set from the 1 dB grid = %s' % vals)
elif MODE_P == 'range28':
    chk('range28 forbids everything below 28 dBm',
        min(vals) >= 28.0 and max(vals) == float(PE.PT_MAX), 'reachable set = %s' % vals)
elif MODE_P == 'inc3':
    chk('inc3 remains free (control)',
        len(vals) > 1, 'reachable set = %s' % vals)

# ---- clause 4: rollouts under a policy that explores everything --------------------------
rng = np.random.default_rng(12345)
pt_bad, rb_bad = [], []
hist_p = [0] * PE.PWR_N_ACT
hist_s = [0] * PE.SPEC_N_ACT
for i in range(NEP):
    obs, info = env.reset(seed=EVAL_SEED_BASE + i)
    pts, rbs = [], []
    done = trunc = False
    while not (done or trunc):
        a = [int(rng.integers(2)), int(rng.integers(PE.PWR_N_ACT)), int(rng.integers(PE.SPEC_N_ACT))]
        hist_p[a[1]] += 1
        hist_s[a[2]] += 1
        obs, r, done, trunc, i2 = env.step(a)
        pts.append(i2['pt']); rbs.append(i2['rb'])
    mpt = round(float(np.mean(pts)), 4)
    mrb = round(float(np.mean(rbs)), 4)
    if MODE_P == 'force30' and mpt != 30.0:
        pt_bad.append((i, mpt))
    if MODE_S in ('hold66', 'hold66r') and mrb != float(PE.RB_MAX):
        rb_bad.append((i, mrb))

if MODE_P == 'force30':
    chk('every episode reports mean transmit power of exactly 30.00',
        not pt_bad, '%d/%d episodes off; worst %s' % (len(pt_bad), NEP, pt_bad[:3] or 'none'))
    chk('all three power actions selected and accepted',
        all(h > 0 for h in hist_p), 'histogram %s' % hist_p)
if MODE_S in ('hold66', 'hold66r'):
    chk('every episode reports mean allocation of exactly %.2f RB' % PE.RB_MAX,
        not rb_bad, '%d/%d episodes off; worst %s' % (len(rb_bad), NEP, rb_bad[:3] or 'none'))
if MODE_S == 'hold66r':
    chk('spectrum branch offers exactly one action',
        len(hist_s) == 1 and hist_s[0] > 0, 'histogram %s' % hist_s)

print('-' * 78)
print('power-action histogram   : %s' % hist_p)
print('spectrum-action histogram: %s' % hist_s)
print('-' * 78)
if fails:
    print('RESULT: %d clause(s) FAILED -> %s' % (len(fails), fails))
    sys.exit(1)
print('RESULT: all clauses passed for P2_PWR_ACT=%s P2_SPEC_ACT=%s' % (MODE_P, MODE_S))
