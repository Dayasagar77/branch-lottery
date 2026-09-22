# PRE-REGISTRATION — seed extension to settle branch-specificity, properly powered

Frozen: 21 September 2026, before any seed above 19 was trained for these arms.
240 new runs (seeds 20-99, three arms).

---

## 1. Why the previous attempt did not settle it

The earlier symmetric-control experiment fired its kill condition, on a design with two
defects the authors introduced:

1. **The primary metric was partly tautological.** Collapse count is 0 for the
   power-inert arm *by construction*.
2. **The threshold was below the study's resolving power.** 6/20 against 2/20 is
   Fisher p = 0.235.

This pre-registration fixes both and sizes the experiment from a power analysis rather
than by guess.

## 2. Power analysis (done before writing this, on the existing 20 pairs)

Paired difference, power-inert minus spectrum-inert, RLF rate: mean -0.810 pp,
sd 2.588, dz = 0.313. **Median difference 0.00** - the effect lives entirely in a
handful of seeds, so the distribution is heavy-tailed and a normal-theory calculation
understates the required n.

Bootstrap power (3000 resamples of the observed paired differences, alpha = 0.05
two-sided):

| pairs | Wilcoxon | mean-permutation |
|---|---|---|
| 40 | 45% | 49% |
| 60 | 64% | 71% |
| 80 | 76% | 83% |
| **100** | **86%** | **91%** |
| 120 | 91% | 95% |

**Target: 100 pairs**, i.e. 80 fresh seeds added to the existing 20.

*Caveat recorded in advance:* this curve assumes the 20 observed differences are
representative. They are themselves a 20-pair sample, so the power estimate is
uncertain, and powering to an observed effect biases toward optimism. 100 pairs is
therefore a floor, not a guarantee.

## 3. The structural asymmetry - stated before the data, not after

The power-inert arm **cannot** produce a low-power run. So when it beats the
spectrum-inert arm, part of that advantage is structural rather than learned.

This does not make the comparison circular, because the two hypotheses still make
different predictions:

- **H-BRANCH-SPECIFIC:** the power branch's low mode is the expensive one. Pinning it
  should improve reliability; pinning the spectrum branch should not, because the
  spectrum branch has no expensive mode to remove.
- **H-ANY-SIMPLIFICATION:** pinning any actuator stabilises learning. Both arms should
  improve, comparably.

The discriminating contrast is therefore **spectrum-inert against both-free**, which
involves no structurally protected arm. That is why it is a co-primary below.

## 4. Design

Seeds **20-99** (80 fresh seeds), three arms, otherwise the published configuration:

- **F, both free** - `inc3` power, default spectrum. Folder `free_ext`.
- **P, power inert** - `hold30`, spectrum free. Folder `hold30`.
- **S, spectrum inert** - `hold66`, power free. Folder `hold66`.

Existing seeds 0-19 are already-seen data. **The primary tests run on seeds 20-99
only**, as an independent confirmatory sample.

## 5. Primary outcomes, fixed in advance

**Primary metric is out-of-sample RLF rate.** Collapse count is demoted to descriptive,
for the tautology reason above.

**Co-primary 1 - branch-specificity.** Paired difference P minus S over the 80 fresh
seeds; two-sided sign-flip permutation test, 200,000 draws, seed 20260921.
*H-BRANCH-SPECIFIC predicts P significantly better than S (p < 0.05, negative
difference).*

**Co-primary 2 - does simplification help generically?** Paired difference S minus F
over the 80 fresh seeds, same test.
*H-ANY-SIMPLIFICATION predicts S significantly better than F. H-BRANCH-SPECIFIC
predicts no significant difference.*

Because Co-primary 2 may need to support a null, an **equivalence bound** is fixed now:
if the 90% confidence interval on the S-minus-F difference lies entirely within
+/- 0.75 pp, S and F are declared practically equivalent. 0.75 pp is roughly half the
1.5 pp gap that separates a healthy controller from a mediocre one in these runs.

**Reference - the established comparison.** F minus P, expected to reproduce the
significant improvement already seen. If it does *not* replicate on fresh seeds, the
entire result is in doubt and that is reported first, above everything else.

## 6. Decision rules, fixed in advance

| Co-primary 1 (P vs S) | Co-primary 2 (S vs F) | Conclusion |
|---|---|---|
| P better, p<0.05 | no sig. diff / equivalent | **H-BRANCH-SPECIFIC supported.** Branch identity matters. |
| no sig. diff | S better, p<0.05 | **H-ANY-SIMPLIFICATION.** Claim dies; paper reframed. |
| P better, p<0.05 | S better, p<0.05 | Both effects real; branch identity modulates a generic benefit. |
| no sig. diff | no sig. diff | **UNDERPOWERED DESPITE THE EXTENSION.** Fall back to section 7. |

## 7. Pre-committed fallback

If the outcome is the bottom row, **no further seeds will be run on this question.**
The paper falls back to the measurement-only framing, with the design rule stated as a
*hypothesis the data are consistent with*, not as a demonstrated prescription.

This fallback is committed to now so that a null result cannot be answered with yet
another extension.

## 8. Verification before the runs count

The three arms must record, respectively: (`pwr_act=inc3`, `spec_act=inc3`),
(`pwr_act=hold30`), (`pwr_act=inc3`, `spec_act=hold66`). Each runner checks this before
a job counts as done, and refuses to start unless the environment reports the expected
mode. Both actuator patches were verified inert (worst difference 0.0; 26/26 outcome
columns reproduced on a full rerun).
