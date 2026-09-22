#!/usr/bin/env python3
"""Arm B integrity check.

basin_v2 (the published inc3 runs used as Arm B) was written by an OLDER version
of paper2_controller.py: its metrics file has 33 columns, today's has 57. The
controller has gained features since. If any of them changed baseline behaviour,
then comparing fixed-power runs (today's code) against basin_v2 (old code) would
be confounded -- a difference could come from the code, not from freezing power.

This reruns seed 0 under inc3 with TODAY'S code and checks it reproduces
basin_v2 seed 0. Outcome columns must match to within floating-point noise.

  python armB_check.py          # run it (about 10 minutes)
  python armB_check.py --only_compare   # just compare an existing run
"""
import os, sys, subprocess, argparse
import pandas as pd, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REF  = os.path.join(HERE, 'models', 'basin_v2', 'model_s0_metrics.csv')
OUTD = os.path.join(HERE, 'models', '_armBcheck')
STEM = os.path.join(OUTD, 'model_s0')

# Columns that are allowed to differ: wall-clock timing and latency are
# machine- and load-dependent, not properties of the learned policy.
IGNORE = {'train_s', 'lat_mean_ms', 'lat_p50_ms', 'lat_p95_ms', 'lat_p99_ms',
          'lat_max_ms', 'lat_n'}
TOL = 1e-6


def compare():
    if not os.path.exists(STEM + '_metrics.csv'):
        print('no check run found at', STEM + '_metrics.csv')
        return False
    ref = pd.read_csv(REF).iloc[0]
    new = pd.read_csv(STEM + '_metrics.csv').iloc[0]
    bad, checked = [], 0
    for c in ref.index:
        if c in IGNORE or c not in new.index:
            continue
        a, b = ref[c], new[c]
        try:
            fa, fb = float(a), float(b)
        except (TypeError, ValueError):
            checked += 1
            if str(a) != str(b):
                bad.append((c, a, b))
            continue
        checked += 1
        if not (abs(fa - fb) <= TOL * max(1.0, abs(fa))):
            bad.append((c, fa, fb))
    print('compared %d columns (ignored %d timing/latency)' % (checked, len(IGNORE)))
    if bad:
        print('\nMISMATCH -- today\'s code does NOT reproduce basin_v2:\n')
        print('%-22s %-20s %-20s' % ('COLUMN', 'basin_v2 (old code)', 'today'))
        for c, a, b in bad:
            print('%-22s %-20s %-20s' % (c, str(a)[:20], str(b)[:20]))
        print('\nArm B cannot be taken from basin_v2. It must be retrained under')
        print('today\'s code (20 inc3 runs) before any fixed-power comparison is made.')
        return False
    print('\nVERIFIED: today\'s code reproduces basin_v2 seed 0 exactly on every')
    print('outcome column. basin_v2 is a valid Arm B.')
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only_compare', action='store_true')
    a = ap.parse_args()
    if not a.only_compare:
        if os.environ.get('P2_PWR_ACT') != 'inc3':
            print('Set P2_PWR_ACT=inc3 first (got %r).' % os.environ.get('P2_PWR_ACT'))
            return 2
        os.makedirs(OUTD, exist_ok=True)
        cmd = [sys.executable, os.path.join(HERE, 'paper2_controller.py'),
               '--train', '--episodes', '1500', '--eval_n', '500',
               '--eval_n_train', '200', '--threads', '1', '--ff',
               '--pwr_act', 'inc3', '--seed', '0', '--out', STEM]
        print('rerunning seed 0 under inc3 with today\'s code (about 10 minutes)...')
        with open(STEM + '.log', 'w') as fh:
            fh.write(' '.join(cmd) + '\n\n'); fh.flush()
            rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=HERE).returncode
        if rc != 0:
            print('the run failed, rc=%s -- see %s' % (rc, STEM + '.log'))
            return 1
    return 0 if compare() else 1


if __name__ == '__main__':
    sys.exit(main())
