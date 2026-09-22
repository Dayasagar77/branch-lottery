#!/usr/bin/env python3
"""Sub-claim 3 replication runner. Pausable and resumable.

Runs matched pairs (baseline, constrained) on fresh seeds, one job at a time.
Safe to stop at ANY moment: finished jobs are on disk, unfinished ones simply redo.

  python hold66_run.py                     # run until all pairs done
  python hold66_run.py --max_minutes 90    # do 90 minutes, then stop cleanly
  python hold66_run.py --max_pairs 5       # do 5 more pairs, then stop
  python hold66_run.py --status            # show progress, run nothing

To stop a running job gracefully: create a file called SPEC_STOP in this folder,
or just press Ctrl+C. Either way, rerun the same command to resume.

This script deliberately prints NO outcome numbers. Looking at results while the
run is in progress would invalidate the pre-registered test.
"""
import argparse, os, subprocess, sys, time, csv, datetime, threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
STOP = os.path.join(HERE, 'SPEC_STOP')
PROG = os.path.join(HERE, 'spec_progress.csv')
LOCKF = os.path.join(HERE, 'SPEC_RUNNING.lock')
ARMS = [('hold66', [])]

COMMON = ['--train', '--episodes', '1500', '--eval_n', '500',
          '--eval_n_train', '200', '--threads', '1', '--ff',
          '--pwr_act', 'inc3']


def outstem(arm, seed):
    d = os.path.join(HERE, 'models', '' + arm)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'model_s%d' % seed)


def done(arm, seed):
    """A job counts as done only if its metrics row exists and records the right config.

    Any surprise at all - missing file, truncated write, unexpected columns - is
    treated as 'not done', so the job is simply redone. This must never raise:
    a crash here on resume would strand the whole run.
    """
    m = outstem(arm, seed) + '_metrics.csv'
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
        if 'fdqr' in r.index and int(r['fdqr']) == 1:
            return False
        if 'pwr_act' not in r.index or str(r['pwr_act']) != 'inc3':
            return False
        if 'spec_act' not in r.index or str(r['spec_act']) != 'hold66':
            return False
        return True
    except Exception:
        return False


_LOCK = threading.RLock()


def log(seed, arm, secs, status):
    # must be serialised: with several runs going at once, two appends can
    # interleave and corrupt a row
    with _LOCK:
        is_new = not os.path.exists(PROG)
        with open(PROG, 'a', newline='') as fh:
            w = csv.writer(fh)
            if is_new:
                w.writerow(['utc', 'seed', 'arm', 'seconds', 'status'])
            w.writerow([datetime.datetime.utcnow().isoformat(timespec='seconds'),
                        seed, arm, '%.1f' % secs, status])


_PROCS = set()


def run_one(arm, seed, extra):
    stem = outstem(arm, seed)
    cmd = [PY, os.path.join(HERE, 'paper2_controller.py')] + COMMON + \
          ['--seed', str(seed), '--out', stem] + extra
    t0 = time.time()
    proc = None
    try:
        with open(stem + '.log', 'w') as fh:
            fh.write(' '.join(cmd) + '\n\n')
            fh.flush()
            proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=HERE)
            with _LOCK:
                _PROCS.add(proc)
            rc = proc.wait()
    finally:
        with _LOCK:
            _PROCS.discard(proc)
    dt = time.time() - t0
    ok = (rc == 0) and done(arm, seed)
    log(seed, arm, dt, 'ok' if ok else 'FAIL rc=%s' % rc)
    return ok, dt


def kill_children():
    """Stop every training process we started. A half-finished run leaves no
    metrics file, so it is simply redone next time - nothing is corrupted."""
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


def summarise(seeds):
    jobs = sum(done(a, s) for s in seeds for a, _ in ARMS)
    return jobs, jobs


def pid_alive(pid):
    try:
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        return False
    except Exception:
        return None          # cannot tell


def find_orphans(seed_lo, seed_hi):
    """Training processes from a runner that died. If one of these is still
    writing a seed we are about to start, both would write the same files."""
    try:
        out = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=25).stdout
        import json, re
        data = json.loads(out) if out.strip() else []
        if isinstance(data, dict):
            data = [data]
        found = []
        for d in data:
            cl = d.get('CommandLine') or ''
            if 'paper2_controller.py' not in cl or 'sc3_' not in cl:
                continue
            m = re.search(r'--seed\s+(\d+)', cl)
            if not m:
                continue
            sd = int(m.group(1))
            if seed_lo <= sd <= seed_hi and int(d['ProcessId']) != os.getpid():
                found.append((int(d['ProcessId']), sd, 'fdqr' if '--fdqr' in cl else 'base'))
        return found
    except Exception:
        return []


def clear_orphans(seed_lo, seed_hi):
    orph = find_orphans(seed_lo, seed_hi)
    if not orph:
        return True
    print('\nFound %d training run(s) left over from a runner that was interrupted:' % len(orph))
    for pid, sd, arm in orph:
        print('   process %d - seed %d %s' % (pid, sd, arm))
    print('These would write the same files as this run. Stopping them first.')
    for pid, sd, arm in orph:
        try:
            subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                           capture_output=True, timeout=20)
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
    """Refuse to start if another copy is already running these seeds."""
    if os.path.exists(LOCKF):
        try:
            pid = int(open(LOCKF).read().split()[0])
        except Exception:
            pid = None
        alive = pid_alive(pid) if pid else None
        if alive:
            print('Another hold66_run.py is already running (process %d).' % pid)
            print('Only one copy may run at a time, or they would fight over the same seeds.')
            print('Stop that one first, or wait for it to finish.')
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
    """Best-effort free memory, Windows. Returns None if it cannot be read."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed_lo', type=int, default=0)
    ap.add_argument('--seed_hi', type=int, default=19)
    ap.add_argument('--workers', type=int, default=1,
                    help='how many runs to do at the same time. Each run still uses '
                         'exactly one core, so this does not change any result.')
    ap.add_argument('--max_minutes', type=float, default=None)
    ap.add_argument('--max_pairs', type=int, default=None)
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()
    seeds = list(range(a.seed_lo, a.seed_hi + 1))
    total_pairs = len(seeds)

    pairs, jobs_done = summarise(seeds)
    secs = []
    if os.path.exists(PROG):
        with open(PROG) as fh:
            for row in csv.DictReader(fh):
                if row['status'] == 'ok':
                    secs.append(float(row['seconds']))
    avg = (sum(secs) / len(secs)) if secs else 707.0
    left = (len(ARMS) * total_pairs - jobs_done) * avg / 3600.0 / max(a.workers, 1)
    print('pairs complete: %d / %d   (jobs %d / %d)' % (pairs, total_pairs, jobs_done, len(ARMS) * total_pairs))
    print('mean job time : %.1f min   estimated time left: %.1f h  (%d at a time)'
          % (avg / 60, left, a.workers))
    if a.status:
        return
    if os.path.exists(STOP):
        print('SPEC_STOP present - delete it to run.')
        return
    import subprocess as _sp
    chk = _sp.run([PY, '-c',
                   "import paper2_env as E; print(E._PWR_ACT, E.PWR_N_ACT, E._SPEC_ACT)"],
                  capture_output=True, text=True, cwd=HERE).stdout.strip()
    if chk != 'inc3 3 hold66':
        print('PRE-FLIGHT FAILED: environment reports %r, expected \'inc3 3 hold66\'.' % chk)
        print('Set P2_PWR_ACT=inc3 and P2_SPEC_ACT=hold66 before running.')
        return
    print('PRE-FLIGHT OK: %s' % chk)
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
        if a.workers > 6:
            print('WARNING: more than 6 at a time on this machine is likely to thrash.')

    t_start = time.time()
    st = {'pairs': 0, 'fails': 0, 'stop': False}
    joblist = [(arm, s, extra) for s in seeds for arm, extra in ARMS]

    def do(job):
        arm, s, extra = job
        with _LOCK:
            if st['stop']:
                return
            if os.path.exists(STOP):
                st['stop'] = True
                print('\nSPEC_STOP seen - stopping cleanly. Rerun to resume.')
                return
            if a.max_minutes and (time.time() - t_start) / 60 >= a.max_minutes:
                if not st['stop']:
                    print('\ntime budget reached - finishing what is running, then stopping.')
                st['stop'] = True
                return
            if a.max_pairs and st['pairs'] >= a.max_pairs:
                if not st['stop']:
                    print('\npair budget reached - finishing what is running, then stopping.')
                st['stop'] = True
                return
        if done(arm, s):
            return
        with _LOCK:
            print('  seed %d %-4s started' % (s, arm), flush=True)
        ok, dt = run_one(arm, s, extra)
        with _LOCK:
            print('  seed %d %-4s %s  %.1f min' % (s, arm, 'ok' if ok else 'FAILED', dt / 60), flush=True)
            if ok:
                st['fails'] = 0
            else:
                st['fails'] += 1
                print('    (recorded as FAIL in spec_progress.csv; it will be retried next time)')
                if st['fails'] >= 3:
                    print('\n3 runs failed in a row - something is wrong. Stopping so you do not')
                    print('burn hours on it. Check the .log beside the last model and tell Claude.')
                    st['stop'] = True
            if ok:
                st['pairs'] += 1
                p, j = summarise(seeds)
                print('  seed %d complete | %d/%d done | %.2f h this session'
                      % (s, p, total_pairs, (time.time() - t_start) / 3600), flush=True)

    try:
        if a.workers <= 1:
            for job in joblist:
                do(job)
        else:
            with ThreadPoolExecutor(max_workers=a.workers) as ex:
                list(ex.map(do, joblist))
    except KeyboardInterrupt:
        st['stop'] = True
        print('\n\ninterrupted - stopping the runs that were in progress ...')
        kill_children()
        print('stopped. Unfinished runs left no results and will simply be redone.')
    finally:
        kill_children()
        drop_lock()

    p, j = summarise(seeds)
    print('\nstopped with %d / %d pairs complete. Rerun the same command to continue.'
          % (p, total_pairs))


if __name__ == '__main__':
    main()
