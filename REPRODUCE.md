# Reproducing the results

Two levels: re-deriving every reported number from the stored run files (minutes, no GPU, no
dataset needed), and retraining the runs from scratch (about 14-17 hours of CPU per 80-run arm
serially, roughly 2 hours wall clock at 8-10 parallel workers).

---

## 1. Re-derive every number in the paper (no retraining)

`revision_analysis.py` needs only the Python 3 standard library.
`freeze_final.py` additionally needs `numpy`, `pandas` and `scipy` (`pip install -r
requirements.txt`).

```bash
cd code
python revision_analysis.py > ../results/FROZEN_REVISION_check.txt
diff ../results/FROZEN_REVISION.txt ../results/FROZEN_REVISION_check.txt

python freeze_final.py        # rewrites ../results/FROZEN_FINAL.txt in place
git diff --stat ../results/FROZEN_FINAL.txt

python r2_analysis.py > ../results/R2_RESULT_check.txt     # the 2x2 factorial
diff ../results/R2_RESULT_20260922.txt ../results/R2_RESULT_check.txt

python make_figures.py        # redraws fig1 and fig2 into this folder (needs matplotlib)
```

The diff should be empty and `git diff` should report no change. Both scripts detect whether
they are being run from this repository (`../results`) or from the original working tree
(`models/`), so no paths need editing.

Verified on 22 September 2026: both regenerate their frozen outputs byte-identically.
Re-verified on 23 September 2026 after the factorial arms were added: `revision_analysis.py`
is still byte-identical, `r2_analysis.py` reproduces `R2_RESULT_20260922.txt` exactly, and
`make_figures.py` redraws both figures from `../results` with the values printed in the paper. `revision_analysis.py` covers the analyses added in revision: the
experimental inventory, band occupancy, co-primary effect sizes with bootstrap confidence
intervals, the multi-objective view, the best-of-N seed-selection baseline, the handover tail
screen, the spectrum-use replication check, and the training-dynamics analysis.

## 2. Retrain from scratch

### Prerequisites

- Python 3, PyTorch (CPU is sufficient; all reported runs are single-threaded CPU)
- The DAIR-V2X dataset, obtained from its providers
- `python code/extract_dair_geometry.py` to derive the scene geometry

### The runs

Each runner refuses to start unless the environment reports the actuator mode it expects, and
each job is only counted as done once the recorded configuration matches.

```bash
cd code
python free_run.py   --seeds 20-99     # F, nothing pinned
python hold30_run.py --seeds 0-99      # A2 (0-19) and P (20-99), power pinned, head reduced
python hold66_run.py --seeds 0-99      # pilot (0-19) and S (20-99), spectrum pinned
python pin_run.py    --seeds 0-19      # A3, pin-and-release curriculum
python r2_check34.py                   # proves force30 / hold66r act as specified, before any run
python r2_run.py --arm fa              # FA (20-99), power pinned, head kept
python r2_run.py --arm sr              # SR (20-99), spectrum pinned, head reduced
```

`r2_run.py` also defines arms belonging to other studies on the same controller; only `fa` and
`sr` are used by this paper.

### Verifying the actuator patches are inert

Before any patched run counts, the pre-existing actuator must reproduce bit-identically:

```bash
python armB_check.py
```

This reruns seed 0 under `inc3` with the current code and compares 26 outcome columns against
the stored `basin_v2/model_s0_metrics.csv` at 1e-6, ignoring wall-clock and latency columns.
This check is required by every pre-registration in `prereg/`.

## 3. Determinism

Shadow fading is pre-drawn once per episode, so `reset(seed=k)` fixes both the scene and the
entire fading realisation; configurations are therefore compared on byte-identical scenarios.
Scene assignment uses a fixed split seed independent of the training seed: 30 scenes for
training, 15 held out. Every reported number comes from the held-out scenes.

Permutation tests use 200,000 draws with RNG seed 20260921; the revision analyses use seed
20260922. Both are fixed in the scripts.
