# PRE-REGISTRATION — does learning transmit power earn its place at all?

Frozen: 21 September 2026, before any fixed-power run existed. 20 training runs.

---

## 1. Why this comes first

A re-reading of the actuator data reframed the problem. The bands, by arm, over 20 seeds:

| Arm | Floor (<25 dBm) | Interior (25-28) | Ceiling (>=28) | Ceiling reliability |
|---|---|---|---|---|
| `inc3` | 6 runs, 8.90% RLF | 0 | 14 runs | **0.957%** |
| `inc7` | 9 runs, 9.76% | 0 | 11 runs | 1.236% |
| `direct8` | **2 runs**, 7.10% | 10 runs, 3.58% | 8 runs | 1.800% |

Three things follow, none of which was the working picture:

1. **Direct addressing's real effect is cutting catastrophic runs from 6/20 to 2/20** - not
   "producing interior policies". The interior policies are a side effect, and a mediocre one.
2. **It nonetheless loses under the screening rule.** `inc3` yields 14 usable ceiling runs at
   0.957%; `direct8` yields 8 at 1.800%. Fewer good runs and worse reliability.
3. **`inc7` is worse than `inc3`** - 9 floor runs against 6, mean RLF 5.07 against 3.34. More
   actions and faster traversal made things worse, which is backwards.

The ceiling is simply the good policy. The interior is mediocre. The floor is a disaster. So the
question was never "how do we reach the interior"; it is **"why does the controller ever leave
the ceiling?"**

Which exposes a cheap alternative never tested in this project: **do not learn transmit power at
all.** No such baseline existed in the repository - checked.

## 2. The question

Does a controller that manages only handover and spectrum, with transmit power pinned at
PT_MAX, match the reliability of the ceiling runs that the full controller produces?

## 3. Design

New actuator mode `hold30`: one power action, always PT_MAX. Added the same way `inc7` and
`direct8` were - a named mode, inert unless `P2_PWR_ACT=hold30`.

- **Arm A, fixed power:** 20 seeds, `P2_PWR_ACT=hold30`, otherwise identical to the published
  configuration (1500 episodes, alpha = 0.25, feed-forward, anticipation on, PER on, 500
  held-out evaluations, single thread).
- **Arm B, published comparison:** the existing `inc3` runs (`basin_v2`, seeds 0-19). No new
  training.

Seeds 0-19 in both, paired.

## 4. Verification required before the runs count

The published actuator must be proved unchanged: for every (power, action) pair over the
1 dB grid, `inc3` under the patched environment must reproduce the unpatched values with
**worst difference 0.0**. If it does not, the runs are discarded.

## 5. Primary comparison and predictions, fixed in advance

**Primary:** out-of-sample `rlf_rate` of the 20 fixed-power runs, against the **0.957%** mean of
`inc3`'s 14 ceiling runs.

- **P-REDUNDANT:** fixed power matches or beats 0.957%, with a spread far smaller than the full
  controller's. Then learning power earns nothing in this setting, and the bimodality is
  self-inflicted by including a control dimension whose optimum sits at a boundary.
- **P-EARNED:** fixed power is meaningfully worse than 0.957%. Then the power branch does its
  job, the lottery is a real cost, and engineering it away is worth compute.

**Test:** the fixed-power runs are unpaired with respect to the ceiling subset (which seeds land
at the ceiling is itself an outcome), so a two-sample permutation test on the difference of
means, 200,000 draws, fixed seed, two-sided. Also reported: the full 20-run distribution against
all 20 `inc3` runs, paired by seed, which is the honest like-for-like comparison of *strategies*
rather than of hand-picked survivors.

**Chance/floor check, required before interpretation:** the spread of a one-action branch is
necessarily zero on the power dimension, so a smaller spread is not evidence of anything by
itself. Only the *level* of reliability decides this.

## 6. Kill conditions

- If fixed power is worse than 0.957% by more than its own spread, **P-REDUNDANT dies**.
- If fixed power fails to train at all, or the handover/spectrum branches degrade, that is
  reported as-is and not presented as evidence either way.

## 7. What a P-REDUNDANT result would mean

It would not be a new algorithm. It would be a sharp negative claim about action-space design:
*including a controllable dimension whose optimum lies at a boundary can create a convergence
lottery that costs reliability and buys nothing.*

*(A final paragraph of the original, concerning internal supervision arrangements, is omitted
from this public copy. No scientific content was removed.)*
