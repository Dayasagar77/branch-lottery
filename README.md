# Branch-level decomposition of run-to-run variation in a Sub-THz RRM controller

Code, pre-registrations and per-run results for the pinning experiments of:

> **Bimodal Power Convergence Turns Deep Reinforcement Learning for 140 GHz Vehicular
> Networks into a Reliability Lottery**
> G. Dayasagar and Deepa Nivethika S., School of Computer Science and Engineering,
> Vellore Institute of Technology, Chennai.

The paper's other experiments are archived as listed in its Data and Code Availability
section, mainly at https://github.com/Dayasagar77/bimodal.

A branched quantile-regression DQN jointly manages handover, transmit power and sub-band
allocation for a single vehicular UE served by four roadside gNBs at 140 GHz, on DAIR-V2X
intersection trajectories with 3D ray-cast blockage.

Across random seeds the controller converges bimodally on two of its three action branches.
The paper asks which branch is responsible for the *operationally expensive* variation, and
what fixing it costs.

## Headline results

| | |
|---|---|
| Transmit-power branch, low mode | multiplies radio link failure rate by **5.98x** |
| Spectrum branch, low mode | multiplies it by **1.35x** |
| Pinning the power branch | 0 of 80 collapses, mean RLF 1.28% against 3.27% |
| Pinning the spectrum branch | not significantly better than pinning nothing (p = 0.30) |
| Branch or network head? (2x2 factorial) | branch effect -2.94 pp (p = 0.00001); head-removal effect +0.22 pp (p = 0.73) |
| Price of fixing power | **+30%** radiated power against all free runs, **+2%** against those that already converged well |
| Seed selection instead | best-of-5 matches it; best-of-10 beats it, at 10x the training cost |

Every experiment except the exploratory A1 sweep was pre-registered before execution. Negative results - a failed shape
statistic, a failed reward-reweighting sweep, a failed curriculum, an underpowered pilot, and a
failed equivalence test - are reported as such.

## What is here

```
code/        the environment, the controller, the runners, the analysis and figure scripts
prereg/      the five frozen pre-registrations, as written before the runs (PREREG_04 carries a dated addendum)
results/     per-run outputs for all 540 runs, plus the frozen numeric references
```

### The 540 runs

| Set | Folder | Seeds | n | Role |
|---|---|---|---|---|
| A1 power learned | `basin_v2` | 0-19 | 20 | exploratory |
| A2 power fixed | `hold30` | 0-19 | 20 | remedy test, paired with A1 |
| A3 pin-and-release | `pin750` | 0-19 | 20 | curriculum test |
| Spectrum-pinned pilot | `hold66` | 0-19 | 20 | underpowered, reported as such |
| Reward sweep | `wpwr_w0.02/0.05/0.45` | 0-19 | 60 | three weights |
| **F** nothing pinned | `free_ext` | 20-99 | 80 | co-primary, and the stratification sample |
| **P** power pinned, head reduced | `hold30` | 20-99 | 80 | co-primary |
| **S** spectrum pinned | `hold66` | 20-99 | 80 | co-primary |
| **FA** power pinned, head kept | `force30` | 20-99 | 80 | 2x2 factorial |
| **SR** spectrum pinned, head reduced | `hold66r` | 20-99 | 80 | 2x2 factorial |

*Pinned* means the actuator applies a fixed value whatever the branch selects; *head reduced*
means the branch's network head is also cut to one output, removing it from learning. P reduces
the power head while S keeps the spectrum head, so P against S alone crosses branch identity with
head removal. FA and SR complete the 2x2 that separates them. A1 and F are the same
configuration on disjoint seed ranges.

Seeds 0-19 and 20-99 are disjoint. Note that the 80 runs of F serve as **both** the
confirmatory stratification sample and one arm of the co-primary test - they are not an
additional 80 runs.

### Per-run files

For each run: `model_sN_metrics.csv` (one row of summary outcomes), `model_sN_returns.csv`
(1500 training episodes, with per-episode transmit power, allocation and handovers),
`model_sN_eval.csv` (500 held-out evaluation episodes) and `model_sN_eval_train.csv`
(200 in-sample episodes, used for the seed-selection baseline).

### What is deliberately not here

- **The DAIR-V2X dataset.** It is available from its providers under their own licence and is
  not redistributed. `code/extract_dair_geometry.py` derives the scene geometry the environment
  consumes.
- **Trained checkpoints** (84 MB of `.pt` files). Every reported number is derived from the CSVs
  above, which are included in full.

## Reproducing the numbers

`results/FROZEN_FINAL.txt`, `results/FROZEN_REVISION.txt` and `results/R2_RESULT_20260922.txt`
contain every number that appears in the paper, regenerated from the per-run files by
`code/freeze_final.py`, `code/revision_analysis.py` and `code/r2_analysis.py`; `code/make_figures.py`
redraws both figures. None requires retraining. See `REPRODUCE.md`.

## Licence

MIT, see `LICENSE`. The DAIR-V2X data is not covered by it.
