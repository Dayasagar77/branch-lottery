# PRE-REGISTRATION — is the low-power collapse a trap, or a preference?

Frozen: 21 September 2026, before any pin-release training run existed. 20 training runs.

---

## 1. What is open

The fixed-power result established that removing the learned power dimension eliminates the
collapse (0 of 20 against 6 of 20), and that reweighting the power term cannot achieve this
across a 22-fold range. It did **not** establish why the full controller ever leaves the
ceiling. Two hypotheses remain live:

- **H-TRAP** - the collapse is an early attractor. The per-step power saving is immediate and
  certain; the reliability cost is rare and delayed. The policy is pulled to low power before
  the rare-event cost registers, and once there the high-power region is rarely revisited, so
  its value is never learned.
- **H-PREFERENCE** - the low-power basin is genuinely preferred by the objective as experienced
  in training, and the agent would return to it from anywhere.

The controller bootstraps CVaR-greedily (alpha = 0.25), and CVaR ranks the ceiling **above** the
floor (77.76 against 72.63), while mean return ranks them the other way (80.27 against 89.38).
The agent's own criterion therefore does not endorse the floor - which weighs against
H-PREFERENCE but does not settle it, because what matters is the objective as experienced during
training, not at convergence.

## 2. The question

If the power branch is held at maximum for the first half of training and then released, where
does the policy go?

## 3. Design

New flag `--pin_release N`: for the first N training episodes the power branch's action is
forced to its no-change action. The environment resets transmit power to PT_MAX at the start of
every episode, so holding keeps power at maximum throughout the pinned phase. **The forced
action is the one recorded in the replay transition**, so the agent is never taught that a
decrease did nothing.

- **Arm P:** 20 seeds (0-19), `--pin_release 750`, otherwise identical to the published
  configuration.
- **Comparisons, no new training:** `basin_v2` (unpinned, same 20 seeds) and `hold30` (power
  removed entirely, same 20 seeds).

**Why 750 and not later.** Exploration decays as `eps = max(0.05, 1 - ep/1050)`. At episode 750
it is still about 0.29, so roughly three exploratory power actions in ten remain available after
release. The agent therefore retains a real opportunity to find the low-power basin. Releasing
near the end of training would make "stays at the ceiling" trivially true and the test
worthless. This threshold is fixed here, before any run.

## 4. Verification required before the runs count

1. The patch must be **inert when the flag is off**: seed 0 under `inc3` with `--pin_release`
   absent must reproduce `basin_v2/model_s0_metrics.csv` on all 26 outcome columns to 1e-6. If
   it fails, every pin-release run is discarded.
2. The pin must demonstrably engage and release. **Satisfied:** a 10-episode probe with
   `--pin_release 4` recorded per-episode mean power of exactly 30.000 dBm for episodes 1-4 and
   free movement (29.768, 29.909, 29.879, ...) from episode 5.
3. The hold action must be derived, not assumed: computed as the action satisfying
   `_apply_pwr(PT_MAX, k) == PT_MAX`, with the run aborting if no such action exists or the
   branch width does not match the network. **Confirmed:** `inc3` -> action 1 of 3.

## 5. Primary outcome and predictions, fixed in advance

**Primary:** the number of Arm P runs, out of 20, that finish in the low-power basin (mean
transmit power below 25 dBm).

- **H-TRAP predicts:** collapses fall sharply from the unpinned 6 of 20, toward `hold30`'s
  0 of 20. The pin is doing causal work: the basin is reachable only early.
- **H-PREFERENCE predicts:** collapses return to roughly 6 of 20. Released policies drift back
  down, because low power is where the objective actually points.

**Secondary:** out-of-sample `rlf_rate`, compared against `basin_v2` paired by seed (two-sided
sign-flip permutation test, 200,000 draws, seed 20260921), and against the fixed-power runs'
1.27%.

**Decisive threshold, fixed now:** H-TRAP is supported if Arm P collapses on **2 or fewer** of
20 seeds. H-PREFERENCE is supported if it collapses on **5 or more**. Between 3 and 4 is
declared **indeterminate** - a partial effect that would need more seeds, and will not be
written up as a clean result either way.

**The six seeds that matter most** are 1, 2, 5, 7, 16 and 19 - the ones that collapsed unpinned.
Their individual outcomes are reported, but the primary is the count over all 20, to avoid
selecting on the outcome.

## 6. Kill conditions

- If pinning degrades the runs that were already healthy - the 14 previously-ceiling seeds
  materially worse on `rlf_rate` - the mechanism is reported as harmful regardless of what it
  does to the collapses.
- If Arm P's reliability is worse than `hold30`'s 1.27%, the released power branch is not buying
  anything, and the honest conclusion is that removing the dimension remains the better
  engineering answer.
- If runs fail to train, that is reported as-is and not interpreted.

## 7. What each outcome would mean

**H-TRAP supported:** the diagnosis is an early-attractor problem, and pinning-then-releasing
becomes a candidate mechanism. It would still face a prior-art gate (warm-starting and curricula
are long established), so any claim would rest on the diagnosis and on the 22-fold sweep showing
reweighting cannot substitute, not on the novelty of pinning as such.

**H-PREFERENCE supported:** the reward specification is the problem after all, and the
constrained formulation becomes the right direction.

Either way the result is informative. That is the reason to run it before committing to a
direction.
