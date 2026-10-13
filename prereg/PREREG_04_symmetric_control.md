# PRE-REGISTRATION — the symmetric control: does fixing the *harmless* branch help too?

Frozen: 21 September 2026, before any spectrum-fixed run existed.
20 training runs, plus pre-specified re-analysis of existing data.

---

## 1. The objection this exists to close

Earlier results establish that fixing the transmit-power branch eliminates the collapse
(0 of 20 against 6 of 20) at no measurable cost, and that the spectrum branch splits just as
sharply while costing far less.

A reviewer can still object: **"you only ever fixed one branch. Perhaps fixing *any* branch
helps - a smaller action space is simply easier to learn."** Nothing in the existing runs
answers this, because the harmless branch has never been fixed.

This is the missing symmetric control, and it is the experiment most able to break the central
claim.

## 2. The question

If the spectrum branch - the one whose modes cost far less - is fixed instead, does the power
lottery persist?

## 3. Design

New environment mode `hold66`, the exact mirror of `hold30`: the spectrum update becomes a
no-op, so allocation stays at `RB_MAX` (66 resource blocks), its reset value, for the whole
episode. Transmit power is learned as usual.

**A note on what "fixing a branch" means here.** `BRANCHES` is hardcoded `[2, 3, 3]` in the
controller, so neither `hold30` nor `hold66` removes a network head: all of a branch's outputs
map to the same actuator state, rendering the branch **inert**. The control quantity is fixed;
the head is not deleted. The manuscript must say "rendered inert", not "removed". Both arms are
treated identically in this respect, so the comparison is sound.

- **S1, spectrum fixed:** 20 seeds, `P2_SPEC_ACT=hold66`, power learned (`inc3`), otherwise
  identical to the published configuration.
- **References, no new training:** `basin_v2` (both learned, 6 of 20 collapse) and `hold30`
  (power fixed, 0 of 20).

## 4. Verification required before the runs count

1. The patch must be **inert when off**: the existing spectrum actuator must reproduce
   bit-identically for every (allocation, action) pair, and a full 1500-episode rerun of seed 0
   without the flag must reproduce `basin_v2/model_s0_metrics.csv` on all 26 outcome columns to
   1e-6.
2. `hold66` must demonstrably pin allocation: every evaluation episode must report mean
   allocation of exactly 66.00.
3. Runs must record `spec_act = hold66`, checked by the runner before a job counts as done.

## 5. Primary outcome and predictions, fixed in advance

**Primary:** the number of S1 runs, out of 20, landing in the low-power mode (mean transmit
power < 25 dBm).

- **H-BRANCH-SPECIFIC** (the paper's claim) predicts **>= 4 of 20** collapse. Fixing the
  harmless branch leaves the power lottery essentially untouched; the reference rate is 6 of 20.
- **H-ANY-SIMPLIFICATION** predicts **<= 2 of 20**. Reducing the action space helps regardless
  of which branch is reduced, and the paper's central claim is wrong.
- **3 of 20** is declared **indeterminate** in advance and will be written up as such.

**Secondary:** out-of-sample `rlf_rate`, paired by seed against `basin_v2` (two-sided sign-flip
permutation test, 200,000 draws, seed 20260921), and compared against `hold30`'s 1.27%.

## 6. Kill condition

**If S1 collapses on <= 2 of 20, the central claim of the paper is undermined** and must be
reported that way: the benefit would then be attributable to action-space reduction in general
rather than to the identity of the branch. In that event the paper is reframed or withdrawn,
not patched.

## 7. Pre-specified re-analysis of existing runs (no new compute)

To avoid selecting analyses after seeing results, the following are fixed now.

1. **Pooled analysis at n = 160.** All eight existing configurations enter the branch-mode
   cross-tabulation. Primary pooled quantities: mean RLF for low-power vs high-power runs, and
   for narrow vs wide spectrum **within the high-power stratum**.
2. **Threshold sensitivity.** The power cut is re-run at 24, 25, 26 dBm and the spectrum cut at
   25, 30, 35 RB. The qualitative conclusion - power mode costly, spectrum mode not - must hold
   at every combination, or the dependence is reported.
3. **Actuator generality.** The per-branch split statistic is reported for `inc3`, `inc7` and
   `direct8` separately. Noted in advance: `direct8` already shows a 17.1% power-split gap, i.e.
   **not bimodal**, so the claim must be stated as conditional on actuator design rather than
   universal.
4. **Reporting in the literature's units.** Branch distributions are additionally reported as
   min-max IPR-90 (Tanaka & Mahmood) so the comparison with that work is direct rather than
   asserted.

No further analyses will be added after results are seen without being labelled post-hoc.

---

# ADDENDUM, 22 September 2026 — a statement in section 3 above is FACTUALLY WRONG

The original text is left unaltered above, as a frozen pre-registration should be. This addendum
records an error in it, found on 22 September 2026 while designing follow-up experiments.

## What section 3 claims

> "`BRANCHES` is hardcoded `[2, 3, 3]` in the controller, so neither `hold30` nor `hold66`
> removes a network head ... Both arms are treated identically in this respect, so the comparison
> is sound."

## What the code actually does

`paper2_env.py` line 195:

```python
self.action_space = spaces.MultiDiscrete([2, PWR_N_ACT, 3])
```

The spectrum dimension is hardcoded to 3. The power dimension is `PWR_N_ACT`, which is **1**
under `hold30`. `paper2_controller.py` line 704 then resizes the network in place:

```python
BRANCHES[1] = int(PE.PWR_N_ACT)
```

with a hard guard requiring the network's branch widths to equal the environment's action space.
So the hardcoded `[2, 3, 3]` is overridden before the network is built.

Verified by instantiating the environment under each mode:

| configuration | action space | power head | spectrum head |
|---|---|---|---|
| F, `inc3` | `[2, 3, 3]` | 3 outputs | 3 outputs |
| **P, `hold30`** | `[2, 1, 3]` | **1 output — the head is reduced** | 3 outputs |
| **S, `hold66`** | `[2, 3, 3]` | 3 outputs | **3 outputs — head intact, effect removed** |

**P removes a network head; S does not.** The two arms are therefore *not* the same operation
applied to different branches, and the sentence "both arms are treated identically in this
respect" is false.

## Consequence for the result obtained under this pre-registration

The P-versus-S contrast confounds two things: which control quantity is frozen, and whether the
corresponding head, its parameters, its TD loss and its gradient into the shared encoder still
exist. The observed P > S is consistent with branch identity mattering, and equally consistent
with head removal helping where S never removed one.

**Unaffected:** the F-versus-P comparison, and the cost stratification, which is computed within
arm F alone.

## What is being done about it

A follow-up pre-registration (`PREREG_05`) adds a **forced-action** arm — the power head kept at
its full three outputs and trained normally, with the environment applying PT_MAX regardless of
the chosen action — and a **head-reduced spectrum** arm. Those two restore architectural symmetry
and allow branch identity to be separated from head removal. The result reported under the
present pre-registration is to be read as provisional on that outcome.

This error was ours, was not raised by any reviewer in this form, and is recorded here rather
than quietly corrected.
