"""
Visualize baseline vs scenario forecasts from model_output_1.json.
Produces a single 2-panel PNG: short-term (12 months) on the left,
long-term (20 years) on the right.

Usage:
    python scripts/visualize_forecast.py
    # reads  documentation/data/model_output_1.json
    # writes documentation/images/forecast_comparison.png
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
OUTPUT_JSON = REPO_ROOT / "documentation" / "data" / "model_output_1.json"
IMAGE_OUT = REPO_ROOT / "documentation" / "images" / "forecast_comparison.png"

# ── Style constants ────────────────────────────────────────────────────────────
BASELINE_COLOR = "#333333"
SCENARIO_COLORS = [
    "#E07B39",  # solar_only       — amber
    "#4C9BE8",  # pv_battery       — blue
    "#5DBB63",  # pv_heatpump      — green
    "#A855C8",  # pv_ev            — purple
    "#E84C5A",  # pv_battery_heatpump — red
    "#1AA8A0",  # full_upgrade     — teal
]

SCENARIO_LABELS = {
    "solar_only":            "Solar only",
    "pv_battery":            "PV + Battery",
    "pv_heatpump":           "PV + Heat pump",
    "pv_ev":                 "PV + EV",
    "pv_battery_heatpump":   "PV + Battery + Heat pump",
    "full_upgrade":          "Full upgrade",
}


def _eur_formatter(x, _):
    return f"€{x:,.0f}"


def main() -> None:
    with OUTPUT_JSON.open() as f:
        data = json.load(f)

    baseline = data["baseline"]
    scenarios = data["scenarios"]

    # ── Short-term data ───────────────────────────────────────────────────────
    st_labels = [e["month"] for e in baseline["short_term_forecast"]]
    st_x = range(len(st_labels))
    baseline_st = [e["total_eur"] for e in baseline["short_term_forecast"]]

    # ── Long-term data ────────────────────────────────────────────────────────
    lt_years = [e["year"] for e in baseline["long_term_forecast"]]
    baseline_lt = [e["annual_total_eur"] for e in baseline["long_term_forecast"]]

    # ── Figure layout ─────────────────────────────────────────────────────────
    fig, (ax_st, ax_lt) = plt.subplots(
        1, 2,
        figsize=(16, 6),
        gridspec_kw={"wspace": 0.12},
    )
    fig.patch.set_facecolor("#F7F8FA")
    for ax in (ax_st, ax_lt):
        ax.set_facecolor("#FFFFFF")
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#CCCCCC")
        ax.tick_params(colors="#555555", labelsize=8.5)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_eur_formatter))

    # ── Left panel: short-term ────────────────────────────────────────────────
    ax_st.plot(
        st_x, baseline_st,
        color=BASELINE_COLOR, linewidth=2.2, linestyle="--",
        label="Baseline", zorder=5,
    )
    for scen, color in zip(scenarios, SCENARIO_COLORS):
        st_vals = [e["total_eur"] for e in scen["short_term_forecast"]]
        ax_st.plot(
            st_x, st_vals,
            color=color, linewidth=1.6, alpha=0.88,
            label=SCENARIO_LABELS.get(scen["id"], scen["id"]),
        )

    ax_st.set_title("Short-term forecast — monthly cost (12 months)", fontsize=11, fontweight="bold", pad=10, color="#222222")
    ax_st.set_ylabel("Monthly cost (€)", fontsize=9, color="#444444")
    ax_st.set_xticks(list(st_x))
    ax_st.set_xticklabels(st_labels, rotation=45, ha="right", fontsize=7.5)
    ax_st.grid(axis="y", color="#EEEEEE", linewidth=0.8)
    ax_st.legend(fontsize=8, framealpha=0.9, edgecolor="#CCCCCC", loc="upper left")

    # ── Right panel: long-term ────────────────────────────────────────────────
    ax_lt.plot(
        lt_years, baseline_lt,
        color=BASELINE_COLOR, linewidth=2.2, linestyle="--",
        label="Baseline", zorder=5,
    )
    for scen, color in zip(scenarios, SCENARIO_COLORS):
        lt_vals = [e["annual_total_eur"] for e in scen["long_term_forecast"]]
        ax_lt.plot(
            lt_years, lt_vals,
            color=color, linewidth=1.6, alpha=0.88,
            label=SCENARIO_LABELS.get(scen["id"], scen["id"]),
        )

    # Mark loan payoff year with a vertical band
    loan_end_year = lt_years[0] + 15  # 15-year loan term from model constants
    ax_lt.axvspan(
        loan_end_year - 0.4, loan_end_year + 0.4,
        color="#AAAAAA", alpha=0.18, label=f"Loan paid off ({loan_end_year})",
    )

    ax_lt.set_title("Long-term forecast — annual cost (20 years)", fontsize=11, fontweight="bold", pad=10, color="#222222")
    ax_lt.set_ylabel("Annual cost (€)", fontsize=9, color="#444444")
    ax_lt.set_xlabel("Year", fontsize=9, color="#444444")
    ax_lt.set_xticks(lt_years[::2])  # every other year to avoid crowding
    ax_lt.tick_params(axis="x", labelsize=8)
    ax_lt.grid(axis="y", color="#EEEEEE", linewidth=0.8)
    ax_lt.legend(fontsize=8, framealpha=0.9, edgecolor="#CCCCCC", loc="upper left")

    # ── Footer note ───────────────────────────────────────────────────────────
    fig.text(
        0.5, -0.02,
        "All costs in EUR · Naive (lookup-table) model · placeholder constants — see documentation/models/naive_model.md",
        ha="center", fontsize=7.5, color="#888888",
    )

    IMAGE_OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMAGE_OUT, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"Saved {IMAGE_OUT}")


if __name__ == "__main__":
    main()
