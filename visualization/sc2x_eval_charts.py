"""SC2x tutor-evaluation charts from Claude-judged transcripts.

Reads transcripts/<type>/<type>_claude/transcript_*.json (the SC2x simulation:
3 exercises + 3 practices x 18 personas, graded by judge_08/rubric_08) and
writes PNG charts to visualization/outputs/sc2x/.

Charts:
  1. Mean total score by persona type (with spread).
  2. Rubric-section attainment (% of max) by persona type.
  3. Exercise vs practice attainment by persona type.
  4. Total-score distribution by persona type (boxplot).
  5. Heatmap: persona type x rubric section (% of max).
  6. Mean attainment by problem (exercise/practice 01..03).

Run:
    python -m visualization.sc2x_eval_charts
"""
from __future__ import annotations

import glob
import json
from collections import defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_TR = _REPO / "transcripts"
_OUT = _REPO / "visualization" / "outputs" / "sc2x"

# Persona types in a fixed display order, with stable colors.
_TYPES = ["cooperative", "chaotic", "clueless"]
_TYPE_COLOR = {"cooperative": "#2ca25f", "chaotic": "#ff893a", "clueless": "#3a7bd5"}
_SECTIONS = [
    ("1_pedagogy", "Pedagogy"),
    ("2_dialogue_quality", "Dialogue"),
    ("3_communication_quality", "Communication"),
]


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def load_records() -> list[dict]:
    recs: list[dict] = []
    for f in glob.glob(str(_TR / "*" / "*_claude" / "transcript_*.json")):
        d = json.load(open(f, encoding="utf-8"))
        g = d.get("grade") or {}
        if not g:
            continue
        ptype = d["student_persona"].split("_")[0]
        rec = {
            "ptype": ptype,
            "kind": d.get("kind", "?"),
            "number": d.get("exercise_number", "?"),
            "total": g.get("total_score", 0),
            "max": g.get("max_score", 0) or 1,
        }
        for sid, _ in _SECTIONS:
            base = (g.get("sections", {}).get(sid, {}) or {}).get("base", {})
            rec[sid] = base.get("score", 0)
            rec[sid + "_max"] = base.get("max", 0) or 1
        recs.append(rec)
    return recs


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def chart_total_by_type(plt, recs):
    fig, ax = plt.subplots(figsize=(7, 5))
    means, stds = [], []
    for t in _TYPES:
        vals = [r["total"] for r in recs if r["ptype"] == t]
        m = _mean(vals)
        means.append(m)
        stds.append((_mean([(v - m) ** 2 for v in vals])) ** 0.5)
    bars = ax.bar(_TYPES, means, yerr=stds, capsize=6,
                  color=[_TYPE_COLOR[t] for t in _TYPES])
    ax.set_ylim(0, 40)
    ax.set_ylabel("Mean total score (/40)")
    ax.set_title("Tutor score by student persona type (Claude judge, 36 convos each)")
    for b, m in zip(bars, means):
        ax.text(b.get_x() + b.get_width() / 2, m + 0.6, f"{m:.1f}", ha="center", fontweight="bold")
    fig.tight_layout()
    fig.savefig(_OUT / "01_total_by_persona_type.png", dpi=150)
    plt.close(fig)


def chart_sections_by_type(plt, recs):
    import numpy as np
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(_SECTIONS))
    width = 0.26
    for i, t in enumerate(_TYPES):
        rows = [r for r in recs if r["ptype"] == t]
        pct = [100 * _mean([r[sid] for r in rows]) / _mean([r[sid + "_max"] for r in rows])
               for sid, _ in _SECTIONS]
        ax.bar(x + (i - 1) * width, pct, width, label=t, color=_TYPE_COLOR[t])
    ax.set_xticks(x)
    ax.set_xticklabels([f"{lbl}\n(/{recs[0][sid + '_max']})" for sid, lbl in _SECTIONS])
    ax.set_ylim(0, 100)
    ax.set_ylabel("Attainment (% of section max)")
    ax.set_title("Where the tutor loses points: rubric section by persona type")
    ax.legend(title="Persona", loc="lower left")
    ax.axhline(100, color="#999", lw=0.7, ls="--")
    fig.tight_layout()
    fig.savefig(_OUT / "02_sections_by_persona_type.png", dpi=150)
    plt.close(fig)


def chart_kind_by_type(plt, recs):
    import numpy as np
    fig, ax = plt.subplots(figsize=(8, 5))
    kinds = ["exercise", "practice"]
    x = np.arange(len(_TYPES))
    width = 0.36
    for i, k in enumerate(kinds):
        pct = []
        for t in _TYPES:
            rows = [r for r in recs if r["ptype"] == t and r["kind"] == k]
            pct.append(100 * _mean([r["total"] for r in rows]) / _mean([r["max"] for r in rows]))
        ax.bar(x + (i - 0.5) * width, pct, width, label=k,
               color="#6a51a3" if k == "exercise" else "#e6a000")
    ax.set_xticks(x)
    ax.set_xticklabels(_TYPES)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Mean total attainment (% of 40)")
    ax.set_title("Exercises vs practice problems, by persona type")
    ax.legend(title="Content kind", loc="lower left")
    fig.tight_layout()
    fig.savefig(_OUT / "03_exercise_vs_practice.png", dpi=150)
    plt.close(fig)


def chart_distribution(plt, recs):
    fig, ax = plt.subplots(figsize=(7, 5))
    data = [[r["total"] for r in recs if r["ptype"] == t] for t in _TYPES]
    bp = ax.boxplot(data, tick_labels=_TYPES, patch_artist=True, showmeans=True)
    for patch, t in zip(bp["boxes"], _TYPES):
        patch.set_facecolor(_TYPE_COLOR[t]); patch.set_alpha(0.6)
    ax.set_ylim(0, 40)
    ax.set_ylabel("Total score (/40)")
    ax.set_title("Score distribution by persona type")
    fig.tight_layout()
    fig.savefig(_OUT / "04_score_distribution.png", dpi=150)
    plt.close(fig)


def chart_heatmap(plt, recs):
    import numpy as np
    grid = np.zeros((len(_TYPES), len(_SECTIONS)))
    for i, t in enumerate(_TYPES):
        rows = [r for r in recs if r["ptype"] == t]
        for j, (sid, _) in enumerate(_SECTIONS):
            grid[i, j] = 100 * _mean([r[sid] for r in rows]) / _mean([r[sid + "_max"] for r in rows])
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    im = ax.imshow(grid, cmap="RdYlGn", vmin=60, vmax=100, aspect="auto")
    ax.set_xticks(range(len(_SECTIONS))); ax.set_xticklabels([l for _, l in _SECTIONS])
    ax.set_yticks(range(len(_TYPES))); ax.set_yticklabels(_TYPES)
    for i in range(len(_TYPES)):
        for j in range(len(_SECTIONS)):
            ax.text(j, i, f"{grid[i, j]:.0f}%", ha="center", va="center", fontweight="bold")
    ax.set_title("Attainment heatmap: persona type x rubric section (% of max)")
    fig.colorbar(im, ax=ax, label="% of max")
    fig.tight_layout()
    fig.savefig(_OUT / "05_heatmap_type_x_section.png", dpi=150)
    plt.close(fig)


def chart_by_problem(plt, recs):
    fig, ax = plt.subplots(figsize=(9, 5))
    labels, pcts, colors = [], [], []
    for kind, color in (("exercise", "#6a51a3"), ("practice", "#e6a000")):
        for n in ("01", "02", "03"):
            rows = [r for r in recs if r["kind"] == kind and r["number"] == n]
            if not rows:
                continue
            labels.append(f"{kind[:4]} {int(n)}")
            pcts.append(100 * _mean([r["total"] for r in rows]) / _mean([r["max"] for r in rows]))
            colors.append(color)
    bars = ax.bar(labels, pcts, color=colors)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Mean attainment (% of 40, across 18 personas)")
    ax.set_title("Tutor score by problem (Week 1-3 exercises and practice)")
    for b, p in zip(bars, pcts):
        ax.text(b.get_x() + b.get_width() / 2, p + 1, f"{p:.0f}%", ha="center")
    fig.tight_layout()
    fig.savefig(_OUT / "06_by_problem.png", dpi=150)
    plt.close(fig)


def main() -> int:
    recs = load_records()
    if not recs:
        print("No graded transcripts found under transcripts/*/*_claude/.")
        return 1
    _OUT.mkdir(parents=True, exist_ok=True)
    plt = _mpl()
    chart_total_by_type(plt, recs)
    chart_sections_by_type(plt, recs)
    chart_kind_by_type(plt, recs)
    chart_distribution(plt, recs)
    chart_heatmap(plt, recs)
    chart_by_problem(plt, recs)
    print(f"Wrote 6 charts from {len(recs)} graded transcripts to {_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
