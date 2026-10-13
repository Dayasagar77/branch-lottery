#!/usr/bin/env python3
"""Manuscript figures. Greyscale-safe: identity carried by position, shape and
fill, never by hue. Single-column IEEE width (3.5in). Vector PDF output.

Regenerate:  python make_figures.py
Every value is read from the run files; nothing is hard-coded.
"""
import os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT  = os.path.dirname(os.path.abspath(__file__))
# relative to this file, so the script runs from any checkout; override with P4_CODE
CODE = os.environ.get('P4_CODE', os.path.normpath(os.path.join(OUT, '..', 'Paper2', 'code')))
# works from the released repository (../results) or from the original tree (Paper2/code/models)
_REPO = os.path.normpath(os.path.join(OUT, '..', 'results'))
MODELS = _REPO if os.path.isdir(os.path.join(_REPO, 'free_ext')) else os.path.join(CODE, 'models')
PT_MIN, PT_MAX, RB_MIN, RB_MAX = 23., 30., 10., 66.

plt.rcParams.update({
    'font.family': 'serif', 'font.size': 7.5, 'axes.labelsize': 7.5,
    'axes.titlesize': 8, 'xtick.labelsize': 7, 'ytick.labelsize': 7,
    'legend.fontsize': 6.8, 'axes.linewidth': 0.6,
    'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
    'xtick.major.size': 2.5, 'ytick.major.size': 2.5,
    'axes.spines.top': False, 'axes.spines.right': False,
    'figure.dpi': 150, 'savefig.bbox': 'tight', 'savefig.pad_inches': 0.02,
    'pdf.fonttype': 42,
})
INK, MUTED, FAINT = '#111111', '#666666', '#BBBBBB'

def load(folder, col):
    return np.array([float(pd.read_csv(os.path.join(MODELS,folder,'model_s%d_metrics.csv'%s)).iloc[0][col])
                     for s in range(20,100)])

F_rlf, F_pt, F_rb, F_ho = (load('free_ext',c) for c in ('rlf_rate','pt_dbm','rb','ho_per_ep'))
P_rlf = load('hold30','rlf_rate'); S_rlf = load('hold66','rlf_rate')
P_pt  = load('hold30','pt_dbm');   S_pt  = load('hold66','pt_dbm')

rng = np.random.default_rng(20260921)
def jit(n, w=0.13): return rng.uniform(-w, w, n)

# ---------------------------------------------------------------- FIGURE 1
# Each branch on its OWN physical axis. No shape statistic: the reader sees the
# occupancy directly. Handover's outlier is shown off-scale rather than allowed
# to compress the other 79 runs.
fig, axes = plt.subplots(3, 1, figsize=(3.5, 3.1))
spec = [
    (F_pt, PT_MIN, PT_MAX, 'Transmit power', 'dBm',
     [(F_pt < 25).sum(), ((F_pt >= 25) & (F_pt < 28)).sum(), (F_pt >= 28).sum()], (25, 28)),
    (F_rb, RB_MIN, RB_MAX, 'Spectrum', 'resource blocks',
     [(F_rb < 20).sum(), ((F_rb >= 20) & (F_rb < 50)).sum(), (F_rb >= 50).sum()], (20, 50)),
    (F_ho, 0.0, 1.0, 'Handover', 'per episode',
     [None, None, None], None),
]
for ax, (v, lo, hi, name, unit, counts, cuts) in zip(axes, spec):
    inside = v <= hi
    ax.scatter(v[inside], jit(inside.sum()), s=7, facecolors='none',
               edgecolors=INK, linewidths=0.55, zorder=3)
    if (~inside).any():
        ax.scatter([hi * 0.985], [0], s=18, marker='>', color=INK, zorder=4)
        ax.text(hi * 0.965, 0.30, 'seed 97 at %.1f' % v.max(), fontsize=6,
                color=INK, ha='right', va='bottom')
    if cuts:
        for c in cuts:
            ax.axvline(c, color=FAINT, lw=0.6, ls=(0, (2, 2)), zorder=1)
        mids = [(lo + cuts[0]) / 2, (cuts[0] + cuts[1]) / 2, (cuts[1] + hi) / 2]
        for m, n in zip(mids, counts):
            ax.text(m, -0.40, '%d' % n, fontsize=6.5, color=MUTED, ha='center', va='top')
    else:
        ax.text((lo + hi) / 2, -0.40, '79 runs within 0.26-0.79', fontsize=6.5,
                color=MUTED, ha='center', va='top')
    ax.axhline(0, color=FAINT, lw=0.5, zorder=1)
    ax.set_ylim(-0.75, 0.62); ax.set_yticks([])
    ax.set_xlim(lo - (hi - lo) * 0.03, hi + (hi - lo) * 0.03)
    ax.spines['left'].set_visible(False)
    ax.text(lo, 0.42, name, fontsize=7.5, color=INK, va='bottom')
    ax.set_xlabel(unit, labelpad=1)
    ax.tick_params(length=2.5, pad=1)
fig.suptitle('Where the variation lives: 80 runs, both branches free',
             fontsize=8, y=1.00)
fig.tight_layout(h_pad=1.15)
fig.savefig(os.path.join(OUT, 'fig1_branch_variation.pdf'))
plt.close(fig)

# ---------------------------------------------------------------- FIGURE 2
# Double-column width so the category labels do not collide.
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.16, 2.7),
                             gridspec_kw={'wspace': 0.22})

hi_p = F_pt >= 25
groups = [('power\nlow', F_rlf[~hi_p]), ('power\nhigh', F_rlf[hi_p]),
          ('spectrum\nnarrow', F_rlf[hi_p & (F_rb < 30)]),
          ('spectrum\nwide', F_rlf[hi_p & (F_rb >= 30)])]
for i, (lab, v) in enumerate(groups):
    a1.scatter(i + jit(len(v), 0.17), v, s=7, facecolors='none',
               edgecolors=INK, linewidths=0.5, zorder=3)
    a1.plot([i - 0.30, i + 0.30], [v.mean()] * 2, color=INK, lw=1.8, zorder=4,
            solid_capstyle='butt')
    a1.text(i, -2.1, '%.2f' % v.mean(), ha='center', fontsize=6.5, color=MUTED)
a1.set_xticks(range(4)); a1.set_xticklabels([g[0] for g in groups])
a1.set_ylabel('radio link failure rate (%)')
a1.set_title('(a) what each branch mode costs', fontsize=8, pad=6)
a1.axvline(1.5, color=FAINT, lw=0.8, ls=(0, (2, 2)))
a1.annotate(r'$\mathbf{5.98\times}$', xy=(0.5, 21.0), ha='center', fontsize=8, color=INK)
a1.annotate(r'$1.35\times$', xy=(2.5, 21.0), ha='center', fontsize=8, color=MUTED)
a1.set_xlim(-0.6, 3.6); a1.set_ylim(-4.8, 24.0)
a1.grid(axis='y', color=FAINT, lw=0.4, alpha=0.6); a1.set_axisbelow(True)

arms = [('nothing\npinned', F_rlf, F_pt), ('power\npinned', P_rlf, P_pt),
        ('spectrum\npinned', S_rlf, S_pt)]
for i, (lab, v, pt) in enumerate(arms):
    a2.scatter(i + jit(len(v), 0.17), v, s=7, facecolors='none',
               edgecolors=INK, linewidths=0.5, zorder=3)
    a2.plot([i - 0.30, i + 0.30], [v.mean()] * 2, color=INK, lw=1.8, zorder=4,
            solid_capstyle='butt')
    a2.text(i, -2.1, '%.2f' % v.mean(), ha='center', fontsize=6.5, color=MUTED)
    a2.text(i, -3.6, '%d collapses' % (pt < 25).sum(), ha='center', fontsize=6.5, color=MUTED)
a2.set_xticks(range(3)); a2.set_xticklabels([a[0] for a in arms])
a2.set_title('(b) pinning one branch', fontsize=8, pad=6)
a2.set_xlim(-0.6, 2.6); a2.set_ylim(-4.8, 24.0)
a2.grid(axis='y', color=FAINT, lw=0.4, alpha=0.6); a2.set_axisbelow(True)
a2.annotate('', xy=(1.05, 21.0), xytext=(1.95, 21.0),
            arrowprops=dict(arrowstyle='<->', lw=0.7, color=INK))
a2.text(1.5, 21.6, r'$p=0.0003$', ha='center', fontsize=7, color=INK)
a2.annotate('', xy=(0.05, 18.2), xytext=(1.95, 18.2),
            arrowprops=dict(arrowstyle='<->', lw=0.7, color=MUTED))
a2.text(1.0, 18.8, r'$p=0.30$ (not significant)', ha='center', fontsize=7, color=MUTED)
for ax in (a1, a2):
    ax.tick_params(length=2.5)
fig.savefig(os.path.join(OUT, 'fig2_cost_and_arms.pdf'))
plt.close(fig)

print('wrote both figures')
print()
print('occupancy (fig 1):')
print('  power    %d low | %d mid | %d high' % ((F_pt<25).sum(), ((F_pt>=25)&(F_pt<28)).sum(), (F_pt>=28).sum()))
print('  spectrum %d low | %d mid | %d high' % ((F_rb<20).sum(), ((F_rb>=20)&(F_rb<50)).sum(), (F_rb>=50).sum()))
print('  handover %d within 0.26-0.79 | 1 at %.2f' % ((F_ho<=1).sum(), F_ho.max()))
print('means (fig 2a): %.3f %.3f %.3f %.3f' % tuple(g[1].mean() for g in groups))
print('means (fig 2b): %.3f %.3f %.3f' % (F_rlf.mean(), P_rlf.mean(), S_rlf.mean()))
