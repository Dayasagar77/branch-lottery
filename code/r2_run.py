#!/usr/bin/env python3
"""PREREG_05 primary 2x2: the FA and SR arms. Pausable and resumable.

  python r2_run.py --arm fa --workers 8         # forced-action power arm
  python r2_run.py --arm sr --workers 8         # spectrum-head-reduced arm
  python r2_run.py --arm fa --status            # progress only, runs nothing
  python r2_run.py --arm fa --max_minutes 60    # do an hour, then stop cleanly

Stop at any moment with Ctrl+C, or by creating the file R2_STOP_<ARM> in this folder.
Finished runs are on disk; unfinished ones leave no metrics file and are simply redone.

The actuator mode is set INSIDE this file, not in your shell, so it cannot be forgotten
or set wrong. paper2_controller.py is NOT modified by this package.

This script deliberately prints NO outcome numbers. Looking at results while the run is
in progress would invalidate the pre-registered test.
"""
import argparse, os, subprocess, sys, time, csv, datetime, threading, re
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

# ---------------------------------------------------------------------------------------
# Arm definitions. Everything that differs between the two arms lives here and nowhere else.
#   env      : the mode variables, set before any import of paper2_env
#   expect   : what the environment must report at pre-flight  (PREREG_05 6.5, first half)
#   nvec     : the action space each arm must produce          (PREREG_05 6.5, second half)
#   extra    : command-line flags added to COMMON
#   cols     : metrics columns every finished run must carry
# ---------------------------------------------------------------------------------------
ARMS = {
    'fa': dict(
        folder='force30',
        env={'P2_PWR_ACT': 'force30', 'P2_SPEC_ACT': 'inc3'},
        expect=('force30', 3, 'inc3', 3),
        nvec=[2, 3, 3],
        extra=[],                                  # force30 is not in the --pwr_act choices
        cols={'pwr_act': 'force30', 'spec_act': 'inc3', 'pwr_n_act': 3},
    ),
    'sr': dict(
        folder='hold66r',
        env={'P2_PWR_ACT': 'inc3', 'P2_SPEC_ACT': 'hold66r'},
        expect=('inc3', 3, 'hold66r', 1),
        nvec=[2, 3, 1],
        extra=['--pwr_act', 'inc3'],               # inc3 IS in the choices, so keep guard G1a
        cols={'pwr_act': 'inc3', 'spec_act': 'hold66r', 'pwr_n_act': 3},
    ),
    # width-scaling probe: same FD-QR configuration as arm B0 (fdqr_q0.98) but with the power
    # branch widened from 3 to 11 actions, so the spectrum branch's conditioning context grows
    # from 6 possible prefixes to 22. Paired on seeds with the existing width-3 runs.
    'h11': dict(
        folder='fdqr_h11',
        env={'P2_PWR_ACT': 'hybrid11', 'P2_SPEC_ACT': 'inc3'},
        expect=('hybrid11', 11, 'inc3', 3),
        nvec=[2, 11, 3],
        extra=['--pwr_act', 'hybrid11', '--fdqr', '--fdqr_q', '0.98'],
        cols={'pwr_act': 'hybrid11', 'spec_act': 'inc3', 'pwr_n_act': 11},
        require_fdqr=True,
    ),
    # PREREG_06 width-scaling: the middle width. Spectrum's conditioning context goes to 14.
    'i7': dict(
        folder='fdqr_i7',
        env={'P2_PWR_ACT': 'inc7', 'P2_SPEC_ACT': 'inc3'},
        expect=('inc7', 7, 'inc3', 3),
        nvec=[2, 7, 3],
        extra=['--pwr_act', 'inc7', '--fdqr', '--fdqr_q', '0.98'],
        cols={'pwr_act': 'inc7', 'spec_act': 'inc3', 'pwr_n_act': 7},
        require_fdqr=True,
    ),
    # PREREG_07: EXACT joint selection — the ceiling. Identical to arm B0 (fdqr_q0.98) in every
    # respect except that selection enumerates all 18 joint actions and scores each with the last
    # branch's cost head at a complete prefix. Paired with B0 on seeds 0-19.
    'exact': dict(
        folder='fdqr_exact',
        env={'P2_PWR_ACT': 'inc3', 'P2_SPEC_ACT': 'inc3', 'P2_FDQR': '1', 'P2_FDQR_EXACT': '1'},
        expect=('inc3', 3, 'inc3', 3),
        nvec=[2, 3, 3],
        extra=['--pwr_act', 'inc3', '--fdqr', '--fdqr_q', '0.98'],
        cols={'pwr_act': 'inc3', 'spec_act': 'inc3', 'pwr_n_act': 3},
        require_fdqr=True,
    ),
    # PREREG_SCAF01: all-run ban-vs-price replication on fresh seeds 40-139. Invocations are
    # byte-identical to the original C2 (fdqr_soft) and B0 (fdqr_q0.98) runs, which were
    # launched by command line alone with NO P2_* variable set. scrub=True removes any P2_*
    # variable from this process (and so from every child) before anything starts.
    'rep_c2': dict(
        folder='scaf_rep_c2',
        env={},
        scrub=True,
        expect=('inc3', 3, 'inc3', 3),
        nvec=[2, 3, 3],
        extra=['--fdqr', '--fdqr_q', '0.98', '--fdqr_soft', '1.0'],
        cols={'pwr_act': 'inc3', 'spec_act': 'inc3', 'pwr_n_act': 3, 'fdqr_q': '0.98',
              'fd_soft': '1.0', 'fd_rand': '0.0', 'fd_pen': '0.0', 'pin_release': 0},
        require_fdqr=True,
    ),
    'rep_b0': dict(
        folder='scaf_rep_b0',
        env={},
        scrub=True,
        expect=('inc3', 3, 'inc3', 3),
        nvec=[2, 3, 3],
        extra=['--fdqr', '--fdqr_q', '0.98'],
        cols={'pwr_act': 'inc3', 'spec_act': 'inc3', 'pwr_n_act': 3, 'fdqr_q': '0.98',
              'fd_soft': '0.0', 'fd_rand': '0.0', 'fd_pen': '0.0', 'pin_release': 0},
        require_fdqr=True,
    ),
}

COMMON = ['--train', '--episodes', '1500', '--eval_n', '500',
          '--eval_n_train', '200', '--threads', '1', '--ff']

ARM = None          # filled in by main() before anything else happens
CFG = None
STOP = PROG = LOCKF = None
_LOCK = threading.RLock()
_PROCS = set()


def outstem(seed):
    d = os.path.join(HERE, 'models', CFG['folder'])
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'model_s%d' % seed)


def done(seed):
    """A run counts as done only if its metrics row exists and records THIS arm's config.

    Any surprise at all - missing file, truncated write, wrong mode - is treated as
    'not done', so the run is simply redone. This must never raise: a crash here on
    resume would strand the whole arm.
    """
    m = outstem(seed) + '_metrics.csv'
    if not os.path.exists(m):
        return False
    try:
        import pandas as pd
        df = pd.read_csv(m)
        if len(df) == 0:
            return False
        r = df.iloc[0]
        if int(r['seed']) != seed or int(r['episodes']) != 1500:
            return False
        want_fdqr = bool(CFG.get('require_fdqr', False))
        got_fdqr = bool(int(r['fdqr'])) if 'fdqr' in r.index and pd.notna(r['fdqr']) else False
        if got_fdqr != want_fdqr:
            return False
        if CFG.get('scrub'):
            # no metrics column records P2_FDQR_EXACT, so verify the child's environment from
            # the log header written before launch: it must show no P2_* variable at all
            try:
                with open(outstem(seed) + '.log') as lf:
                    head = [next(lf, '') for _ in range(4)]
            except Exception:
                return False
            if not any(h.strip() == 'P2_* in child environment: none' for h in head):
                return False
        for col, want in CFG['cols'].items():
            if col not in r.index:
                return False
            got = r[col]
            if isinstance(want, int):
                if int(got) != want:
                    return False
            elif str(got) != want:
                return False
        return True
    except Exception:
        return False


def log(seed, secs, status):
    # must be serialised: with several runs going at once, two appends can interleave
    with _LOCK:
        is_new = not os.path.exists(PROG)
        with open(PROG, 'a', newline='') as fh:
            w = csv.writer(fh)
            if is_new:
                w.writerow(['utc', 'seed', 'arm', 'seconds', 'status'])
            w.writerow([datetime.datetime.utcnow().isoformat(timespec='seconds'),
                        seed, ARM, '%.1f' % secs, status])


def run_one(seed):
    stem = outstem(seed)
    cmd = [PY, os.path.join(HERE, 'paper2_controller.py')] + COMMON + \
          ['--seed', str(seed), '--out', stem] + CFG['extra']
    t0 = time.time()
    proc = None
    try:
        with open(stem + '.log', 'w') as fh:
            fh.write(' '.join(cmd) + '\n')
            fh.write(' '.join('%s=%s' % (k, v) for k, v in sorted(CFG['env'].items())) + '\n')
            fh.write('P2_* in child environment: %s\n\n'
                     % (sorted('%s=%s' % (k, v) for k, v in os.environ.items() if k.startswith('P2_')) or 'none'))
            fh.flush()
            proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                    cwd=HERE, env=os.environ.copy())
            with _LOCK:
                _PROCS.add(proc)
            rc = proc.wait()
    finally:
        with _LOCK:
            _PROCS.discard(proc)
    dt = time.time() - t0
    ok = (rc == 0) and done(seed)
    log(seed, dt, 'ok' if ok else 'FAIL rc=%s' % rc)
    return ok, dt


def kill_children():
    with _LOCK:
        procs = list(_PROCS)
    for pr in procs:
        try:
            pr.terminate()
        except Exception:
            pass
    for pr in procs:
        try:
            pr.wait(timeout=10)
        except Exception:
            try:
                pr.kill()
            except Exception:
                pass


def pid_alive(pid):
    try:
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        return False
    except Exception:
        return None


def find_orphans(seed_lo, seed_hi):
    """Training processes of THIS arm left over from a runner that died. The old runners
    matched on a stale 'sc3_' string and so never found anything; this matches on the arm's
    own output folder, which is what actually appears in the command line."""
    try:
        out = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=25).stdout
        import json
        data = json.loads(out) if out.strip() else []
        if isinstance(data, dict):
            data = [data]
        needle = re.compile(r'[\\/]%s[\\/]model_s(\d+)' % re.escape(CFG['folder']))
        found = []
        for d in data:
            cl = d.get('CommandLine') or ''
            if 'paper2_controller.py' not in cl:
                continue
            m = needle.search(cl)
            if not m:
                continue
            sd = int(m.group(1))
            if seed_lo <= sd <= seed_hi and int(d['ProcessId']) != os.getpid():
                found.append((int(d['ProcessId']), sd))
        return found
    except Exception:
        return []


def clear_orphans(seed_lo, seed_hi):
    orph = find_orphans(seed_lo, seed_hi)
    if not orph:
        return True
    print('\nFound %d run(s) of this arm left over from an interrupted runner:' % len(orph))
    for pid, sd in orph:
        print('   process %d - seed %d' % (pid, sd))
    print('These would write the same files as this run. Stopping them first.')
    for pid, sd in orph:
        try:
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, timeout=20)
        except Exception:
            pass
    time.sleep(2)
    still = find_orphans(seed_lo, seed_hi)
    if still:
        print('Could not stop: %s - close them yourself before running.'
              % ', '.join(str(x[0]) for x in still))
        return False
    print('Stopped. Those seeds left no results and will simply be redone.\n')
    return True


def take_lock():
    if os.path.exists(LOCKF):
        try:
            pid = int(open(LOCKF).read().split()[0])
        except Exception:
            pid = None
        alive = pid_alive(pid) if pid else None
        if alive:
            print('Another r2_run.py --arm %s is already running (process %d).' % (ARM, pid))
            print('Only one copy per arm may run, or they would fight over the same seeds.')
            return False
        print('(clearing a stale lock from process %s - it is no longer running)' % pid)
    try:
        with open(LOCKF, 'w') as fh:
            fh.write('%d %s' % (os.getpid(), datetime.datetime.now().isoformat(timespec='seconds')))
    except Exception:
        pass
    return True


def drop_lock():
    try:
        os.remove(LOCKF)
    except Exception:
        pass


def free_gb():
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        m = MS(); m.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullAvailPhys / (1024 ** 3)
    except Exception:
        return None


def preflight():
    """PREREG_05 section 6, check 5, both halves: the environment must report the mode this
    arm asked for, AND the action space it builds must be the one the arm is defined by."""
    probe = (
        "import paper2_env as E, pandas as pd, os, json;"
        "p=pd.read_csv('dair_geometry_pool.csv');"
        "e=E.MultiRSUBlockageEnv(p, seed=0, split='test', ho_latency=2);"
        "print(json.dumps([E._PWR_ACT, int(E.PWR_N_ACT), E._SPEC_ACT, int(E.SPEC_N_ACT),"
        "[int(x) for x in e.action_space.nvec]]))"
    )
    r = subprocess.run([PY, '-c', probe], capture_output=True, text=True,
                       cwd=HERE, env=os.environ.copy())
    line = (r.stdout or '').strip().splitlines()[-1] if (r.stdout or '').strip() else ''
    try:
        import json
        got = json.loads(line)
    except Exception:
        print('PRE-FLIGHT FAILED: could not read the environment probe.')
        print('stdout: %r' % (r.stdout or '')[-500:])
        print('stderr: %r' % (r.stderr or '')[-500:])
        return False
    want_mode, want_nvec = list(CFG['expect']), CFG['nvec']
    if got[:4] != want_mode:
        print('PRE-FLIGHT FAILED: environment reports mode %s, expected %s.' % (got[:4], want_mode))
        return False
    if got[4] != want_nvec:
        print('PRE-FLIGHT FAILED: action space %s, expected %s.' % (got[4], want_nvec))
        return False
    print('PRE-FLIGHT OK: mode %s | action space %s' % (got[:4], got[4]))
    return True


def main():
    global ARM, CFG, STOP, PROG, LOCKF
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', required=True, choices=sorted(ARMS))
    ap.add_argument('--seed_lo', type=int, default=20)
    ap.add_argument('--seed_hi', type=int, default=99)
    ap.add_argument('--workers', type=int, default=1,
                    help='how many runs at the same time. Each run still uses exactly one '
                         'core, so this does not change any result.')
    ap.add_argument('--max_minutes', type=float, default=None)
    ap.add_argument('--max_runs', type=int, default=None)
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()

    ARM = a.arm
    CFG = ARMS[ARM]
    STOP = os.path.join(HERE, 'R2_STOP_%s' % ARM.upper())
    PROG = os.path.join(HERE, 'r2_%s_progress.csv' % ARM)
    LOCKF = os.path.join(HERE, 'R2_RUNNING_%s.lock' % ARM)

    # set the mode HERE, before the probe and before any child is started, so neither this
    # process nor any child can pick up a stale value from the shell
    if CFG.get('scrub'):
        for k in [k for k in os.environ if k.startswith('P2_') and k not in CFG['env']]:
            del os.environ[k]
    for k, v in CFG['env'].items():
        os.environ[k] = v

    seeds = list(range(a.seed_lo, a.seed_hi + 1))
    total = len(seeds)
    n_done = sum(done(s) for s in seeds)

    secs = []
    if os.path.exists(PROG):
        with open(PROG) as fh:
            for row in csv.DictReader(fh):
                if row['status'] == 'ok':
                    secs.append(float(row['seconds']))
    avg = (sum(secs) / len(secs)) if secs else 707.0
    left = (total - n_done) * avg / 3600.0 / max(a.workers, 1)
    print('arm %s (%s)  seeds %d-%d' % (ARM.upper(), CFG['folder'], a.seed_lo, a.seed_hi))
    print('runs complete : %d / %d' % (n_done, total))
    print('mean run time : %.1f min   estimated time left: %.1f h  (%d at a time)'
          % (avg / 60, left, a.workers))
    if a.status:
        return
    if os.path.exists(STOP):
        print('%s present - delete it to run.' % os.path.basename(STOP))
        return
    if not preflight():
        return
    if not take_lock():
        return
    if not clear_orphans(a.seed_lo, a.seed_hi):
        drop_lock()
        return

    if a.workers > 1:
        g = free_gb()
        if g is not None:
            print('free memory: %.1f GB | each run needs about 0.55 GB' % g)
            if g < 0.7 * a.workers:
                print('WARNING: that is tight for %d at a time. Close some apps, or use fewer.'
                      % a.workers)
        if a.workers > 10:
            print('WARNING: more than 10 at a time on this machine is likely to thrash.')

    t_start = time.time()
    st = {'n': 0, 'fails': 0, 'stop': False}

    def do(s):
        with _LOCK:
            if st['stop']:
                return
            if os.path.exists(STOP):
                st['stop'] = True
                print('\n%s seen - stopping cleanly. Rerun to resume.' % os.path.basename(STOP))
                return
            if a.max_minutes and (time.time() - t_start) / 60 >= a.max_minutes:
                if not st['stop']:
                    print('\ntime budget reached - finishing what is running, then stopping.')
                st['stop'] = True
                return
            if a.max_runs and st['n'] >= a.max_runs:
                if not st['stop']:
                    print('\nrun budget reached - finishing what is running, then stopping.')
                st['stop'] = True
                return
        if done(s):
            return
        with _LOCK:
            print('  seed %d started' % s, flush=True)
        ok, dt = run_one(s)
        with _LOCK:
            print('  seed %d %s  %.1f min' % (s, 'ok' if ok else 'FAILED', dt / 60), flush=True)
            if ok:
                st['fails'] = 0
                st['n'] += 1
                print('  %d/%d done | %.2f h this session'
                      % (sum(done(x) for x in seeds), total, (time.time() - t_start) / 3600),
                      flush=True)
            else:
                st['fails'] += 1
                print('    (recorded as FAIL in %s; it will be retried next time)'
                      % os.path.basename(PROG))
                if st['fails'] >= 3:
                    print('\n3 runs failed in a row - something is wrong. Stopping so you do not')
                    print('burn hours on it. Check the .log beside the last model and tell Claude.')
                    st['stop'] = True

    try:
        if a.workers <= 1:
            for s in seeds:
                do(s)
        else:
            with ThreadPoolExecutor(max_workers=a.workers) as ex:
                list(ex.map(do, seeds))
    except KeyboardInterrupt:
        st['stop'] = True
        print('\n\ninterrupted - stopping the runs that were in progress ...')
        kill_children()
        print('stopped. Unfinished runs left no results and will simply be redone.')
    finally:
        kill_children()
        drop_lock()

    print('\nstopped with %d / %d runs complete. Rerun the same command to continue.'
          % (sum(done(s) for s in seeds), total))


if __name__ == '__main__':
    main()
