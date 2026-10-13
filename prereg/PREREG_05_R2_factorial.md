# PRE-REGISTRATION 05 — separating branch identity from head removal, and five further arms

Frozen: 22 September 2026, before any run of any arm described here.
Written in response to reviewer point 3 and to our own finding that configurations P and S are
not architecturally symmetric (see the addendum to PREREG_04).

---

## 1. The defect this exists to repair

`hold30` sets `PWR_N_ACT = 1`, and `paper2_controller.py` resizes the network in place
(`BRANCHES[1] = PE.PWR_N_ACT`). `hold66` leaves the spectrum dimension at its hardcoded 3.
Therefore:

| arm | action space | power head | spectrum head |
|---|---|---|---|
| F | `[2,3,3]` | 3 | 3 |
| P | `[2,1,3]` | **1 (reduced)** | 3 |
| S | `[2,3,3]` | 3 | **3 (intact, effect removed)** |

P removes a head; S does not. The P-versus-S contrast therefore confounds *which branch is
frozen* with *whether a head was deleted*, and cannot on its own support the paper's
branch-identity claim.

## 2. The repair: a 2x2 factorial

Two new arms complete a factorial in which branch identity and head removal are crossed.

| | head kept (3 outputs) | head reduced (1 output) |
|---|---|---|
| **power pinned at 30 dBm** | **FA** (new) | **P** (exists) |
| **spectrum pinned at 66 RB** | **S** (exists) | **SR** (new) |

Reference: **F**, nothing pinned.

- **FA, forced action.** `P2_PWR_ACT=force30`. The power head keeps three outputs and trains
  normally; `_apply_pwr` returns PT_MAX for every action. The action the agent chose is the one
  stored in the replay transition. Architecturally identical to F and S.
- **SR, spectrum head reduced.** `P2_SPEC_ACT=hold66r`. Allocation pinned at RB_MAX **and** the
  spectrum branch reduced to a single action, so the head is reduced exactly as P's is.

Seeds **20-99**, 80 per arm, paired with the existing F, P and S runs on the same seeds and the
same held-out scenes.

## 3. Hypotheses, fixed in advance

- **H-IDENTITY** (the paper's current claim): what matters is which branch is frozen. Predicts a
  **main effect of branch** — power-pinned better than spectrum-pinned at both head levels:
  FA better than S, and P better than SR.
- **H-HEAD**: what matters is removing a head. Predicts a **main effect of architecture** —
  head-reduced better than head-kept at both branch levels: P better than FA, and SR better
  than S.
- **H-BOTH**: both main effects are present.

These are not exclusive, which is the point of crossing them.

## 4. Primary outcomes and tests

**Primary metric:** out-of-sample RLF rate on the 500 held-out episodes, as throughout.

**Co-primary 1 — branch main effect.** The paired quantity
`(FA - S) + (P - SR)` over the 80 seeds, two-sided sign-flip permutation test,
200,000 draws, RNG seed 20260922. H-IDENTITY predicts it is significantly negative.

**Co-primary 2 — architecture main effect.** The paired quantity
`(P - FA) + (SR - S)`, same test. H-HEAD predicts it is significantly negative.

**Secondary — interaction.** `(FA - S) - (P - SR)`, reported with a bootstrap interval, not
tested for significance; we are not powered for an interaction and say so now.

**Effect sizes.** Every contrast is reported with mean, median, a 20,000-draw bootstrap 95%
interval, and the sign counts, as in R1.

## 5. Decision rules, fixed in advance

| Branch effect | Architecture effect | Conclusion |
|---|---|---|
| significant | not significant | **H-IDENTITY supported.** The paper's claim survives the confound. |
| not significant | significant | **KILL CONDITION.** The branch-identity claim is refuted; the benefit is head removal. The paper is reframed around that, not patched. |
| both significant | | Both mechanisms operate. The claim narrows to "branch identity matters, and so does removing a head", with both effect sizes reported. |
| neither significant | | Underpowered or no effect. No further seeds will be run on this question; the paper falls back to the F-vs-P result alone and drops the branch-identity claim to a hypothesis. |

The bottom two rows are committed to now so that an unwelcome result cannot be answered with
another extension.

## 6. Verification required before any run counts

Each new mode must be proved **inert when off**, to the standard already used for `hold30`,
`hold66` and `pin_release`:

1. For every (power, action) pair on the 1 dB grid, `inc3` under the patched environment must
   reproduce the unpatched values with worst difference 0.0.
2. A full 1500-episode rerun of seed 0 under `inc3`/`inc3` with the new flags absent must
   reproduce `basin_v2/model_s0_metrics.csv` on all 26 outcome columns to 1e-6.
3. `force30` must be shown to leave the branch width at 3 and to pin power: every evaluation
   episode reports mean transmit power of exactly 30.00, and the recorded action histogram must
   show all three power actions still being selected.
4. `hold66r` must be shown to reduce the spectrum branch to width 1 and to pin allocation at
   exactly 66.00.
5. Each runner refuses to start unless the environment reports the expected mode and the
   controller's branch widths match the environment's action space.

If any check fails, the runs are discarded rather than interpreted.

## 7. Secondary arms, pre-registered here so they cannot be chosen after the fact

These are exploratory and are labelled as such in any write-up. No decision rule is attached;
they are reported whatever they show.

- **FLAT, flat 18-action QR-DQN.** One head over the 2x3x3 = 18 joint actions, same encoder,
  parameter count matched as closely as a single head allows, same reward, seeds, episodes and
  evaluation scenes. Asks whether bimodal power convergence survives without action branching.
  Highest implementation risk of the package; the branch-width guard does not protect it, so it
  gets its own equivalence check against F on a fixed policy before training.
- **RANGE28.** `P2_PWR_ACT=range28`: the power head keeps three outputs but power is clipped to
  [28, 30] dBm. Asks whether forbidding the unsafe region suffices without freezing the branch.
- **HOLD28, HOLD29.** As P but pinned at 28 and 29 dBm. Asks whether the benefit is "maximum
  power" or merely "enough power". 40 seeds each.
- **DENSE.** A per-step penalty on out-of-sync streaks in addition to the terminal RLF penalty,
  testing the deceptive-gradient mechanism proposed in Section V-C. 40 seeds.

## 8. Generalisation: leave-one-intersection-out

The dataset is the **V2X-Seq-TFD example subset**, which contains four intersections
(`yizhuang#20-1`, 38 scenes; `#4-1`, 25; `#19-1`, 18; `#12-1`, 4). The existing split is at
**scene** level, and every held-out scene belongs to an intersection also present in training.
No unseen-intersection result exists.

Three folds, each training on the scenes of three intersections and evaluating on the fourth
(the 4-scene intersection is used only as a test fold, never as the sole held-out set for a
claim). 40 seeds per fold, configuration F.

**Question, fixed in advance:** does the power branch still converge bimodally when the
evaluation geometry was never trained on?

**Pre-committed reporting:** the occupancy counts per fold are reported whatever they show. If
the bimodality disappears on unseen intersections, that is reported as a limit on the
phenomenon's generality, not as a failed experiment.

## 9. Compute

Measured from the existing runs' recorded `train_s`: about 630-780 s per run, roughly two hours
per 80-seed arm at the 8-10 parallel workers used previously. The package above is approximately
13 hours of wall clock in total.
