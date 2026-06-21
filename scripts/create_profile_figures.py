"""Create comparison figures and summary for the three test profiles.

Run from repo root:
    python scripts/create_profile_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ── Paths ─────────────────────────────────────────────────────────────────────

_REPO = Path(__file__).parent.parent
_PROFILES_DIR = _REPO / "documentation" / "data" / "test_profiles"
_OUTPUTS_DIR = _REPO / "documentation" / "data" / "test_outputs"
_FIGURES_DIR = _REPO / "documentation" / "figures" / "test_profiles"
_FIGURES_DIR.mkdir(parents=True, exist_ok=True)

PROFILES = [
    {
        "name": "average_german_household",
        "label": "Average German Household",
        "description": (
            "3-person semi-detached house in Cologne. "
            "Typical electricity use (3,500 kWh), gas heating (14,000 kWh), "
            "12,000 km/yr petrol, 35 m² south-facing roof. "
            "Standard 15-yr loan at 4.5 %."
        ),
    },
    {
        "name": "low_benefit_household",
        "label": "Low Benefit Household",
        "description": (
            "Single-person flat in Hamburg. "
            "Low electricity use (1,500 kWh), minimal gas heating (4,500 kWh), "
            "4,000 km/yr, small 12 m² north-facing shaded roof (40 % shading). "
            "Shorter 10-yr loan at 6.5 %."
        ),
    },
    {
        "name": "high_benefit_household",
        "label": "High Benefit Household",
        "description": (
            "5-person detached house in Munich. "
            "High electricity use (7,200 kWh), oil heating (3,200 litres), "
            "28,000 km/yr petrol SUV, 60 m² south-facing roof (5 % shading). "
            "20-yr green mortgage at 3.5 %."
        ),
    },
]


# ── Best-plan selection ────────────────────────────────────────────────────────

def select_best_plan(output: dict) -> dict:
    """Choose the upgrade scenario with highest 20-yr cumulative net savings (central LT).

    Tie-breakers:
      1. Higher Year-1 net savings
      2. Lower monthly financing instalment
      3. Positive cash flow during loan term (more years positive)
    """
    candidates = []
    for sn, sc in output["upgrade_scenarios"].items():
        lt = sc["long_term_projection"]["central"]
        cum20 = lt[-1]["financial_result"]["cumulative_net_savings_eur"]
        yr1_net = lt[0]["financial_result"]["annual_net_savings_eur"]
        inst = sc["financing"]["monthly_instalment_eur"]
        loan_months = sc["financing"]["loan_term_months"]
        loan_years = loan_months // 12

        # Count years with positive cumulative savings during loan period
        positive_during_loan = sum(
            1 for yr in lt[:loan_years]
            if yr["financial_result"]["cumulative_net_savings_eur"] > 0
        )

        candidates.append({
            "scenario": sn,
            "cum20": cum20,
            "yr1_net": yr1_net,
            "instalment": inst,
            "positive_during_loan": positive_during_loan,
        })

    # Primary: highest cumulative savings; tie-breaks: yr1_net desc, instalment asc, positive_during_loan desc
    best = max(
        candidates,
        key=lambda c: (c["cum20"], c["yr1_net"], -c["instalment"], c["positive_during_loan"]),
    )
    return best


# ── Year-1 metrics extractor ───────────────────────────────────────────────────

def year1_metrics(output: dict, scenario: str) -> dict:
    sc = output["upgrade_scenarios"][scenario]
    lt = sc["long_term_projection"]["central"]
    yr1 = lt[0]

    baseline_yr1 = yr1["cost_eur"]["baseline_total"]
    upgraded_yr1 = yr1["cost_eur"]["upgraded_total"]
    reduction_yr1 = yr1["cost_eur"]["energy_cost_reduction"]
    fin_yr1 = yr1["financial_result"]["annual_financing_payments_eur"]
    net_yr1 = yr1["financial_result"]["annual_net_savings_eur"]
    cum20 = lt[-1]["financial_result"]["cumulative_net_savings_eur"]
    inst = sc["financing"]["monthly_instalment_eur"]

    return {
        "baseline_yr1_eur": round(baseline_yr1, 2),
        "upgraded_yr1_eur": round(upgraded_yr1, 2),
        "reduction_yr1_eur": round(reduction_yr1, 2),
        "financing_yr1_eur": round(fin_yr1, 2),
        "net_yr1_eur": round(net_yr1, 2),
        "monthly_net_savings_yr1_eur": round(net_yr1 / 12, 2),
        "cum20_eur": round(cum20, 2),
        "monthly_instalment_eur": round(inst, 2),
    }


# ── Figure creation ───────────────────────────────────────────────────────────

_SCENARIO_DISPLAY = {
    "solar_only": "Solar Only",
    "pv_battery": "PV + Battery",
    "pv_heatpump": "PV + Heat Pump",
    "pv_ev": "PV + EV",
    "pv_battery_heatpump": "PV + Battery + Heat Pump",
    "full_upgrade": "Full Upgrade",
}


def create_figure(profile: dict, output: dict, best: dict, metrics: dict, fig_path: Path) -> None:
    scenario_label = _SCENARIO_DISPLAY.get(best["scenario"], best["scenario"])
    title = f"{profile['label']}\nBest plan: {scenario_label}"

    labels = ["Baseline\nenergy cost", "Upgraded\nenergy cost", "Net savings\n(after financing)"]
    values = [metrics["baseline_yr1_eur"], metrics["upgraded_yr1_eur"], metrics["net_yr1_eur"]]
    colors = ["#4472C4", "#70AD47", "#FF0000" if metrics["net_yr1_eur"] < 0 else "#FF7F0E"]

    fig, ax = plt.subplots(figsize=(8, 5))

    bars = ax.bar(labels, values, color=colors, width=0.5, edgecolor="white", linewidth=1.2)

    # Zero line
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.6)

    # Value labels on bars
    for bar, val in zip(bars, values):
        y = bar.get_height()
        ha = "center"
        va = "bottom" if val >= 0 else "top"
        offset = 15 if val >= 0 else -15
        ax.annotate(
            f"€{val:,.0f}",
            xy=(bar.get_x() + bar.get_width() / 2, y),
            xytext=(0, offset),
            textcoords="offset points",
            ha=ha, va=va,
            fontsize=11, fontweight="bold",
        )

    ax.set_title(title, fontsize=13, fontweight="bold", pad=14)
    ax.set_ylabel("EUR per year", fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:,.0f}"))
    ax.tick_params(axis="x", labelsize=11)
    ax.tick_params(axis="y", labelsize=10)

    # Subtitle with 20yr context
    subtitle = (
        f"Year 1 values · Central price scenario · "
        f"20-yr cumulative net savings: €{metrics['cum20_eur']:,.0f}"
    )
    ax.set_xlabel(subtitle, fontsize=9, labelpad=10, color="#555555")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Pad y-axis so labels don't clip
    ymin, ymax = ax.get_ylim()
    pad = (ymax - ymin) * 0.18
    ax.set_ylim(ymin - pad, ymax + pad)

    fig.tight_layout()
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Figure saved: {fig_path.relative_to(_REPO)}")


# ── Summary builders ──────────────────────────────────────────────────────────

def build_summary_entry(profile: dict, output: dict) -> dict:
    best = select_best_plan(output)
    metrics = year1_metrics(output, best["scenario"])
    fig_path = _FIGURES_DIR / f"{profile['name']}_comparison.png"
    in_path = _PROFILES_DIR / f"{profile['name']}.json"
    out_path = _OUTPUTS_DIR / f"{profile['name']}_output.json"

    return {
        "profile_name": profile["name"],
        "profile_description": profile["description"],
        "input_json_path": str(in_path.relative_to(_REPO)),
        "output_json_path": str(out_path.relative_to(_REPO)),
        "best_scenario": best["scenario"],
        "best_scenario_selection_basis": "highest 20-yr cumulative net savings (central LT scenario)",
        "baseline_yr1_energy_cost_eur": metrics["baseline_yr1_eur"],
        "upgraded_yr1_energy_cost_eur": metrics["upgraded_yr1_eur"],
        "yr1_energy_cost_reduction_eur": metrics["reduction_yr1_eur"],
        "yr1_financing_payments_eur": metrics["financing_yr1_eur"],
        "yr1_net_savings_eur": metrics["net_yr1_eur"],
        "monthly_net_savings_yr1_eur": metrics["monthly_net_savings_yr1_eur"],
        "cum20_net_savings_eur": metrics["cum20_eur"],
        "monthly_instalment_eur": metrics["monthly_instalment_eur"],
        "figure_path": str(fig_path.relative_to(_REPO)),
        "validation_warnings": output.get("validation_warnings", []),
    }


def build_markdown(summaries: list[dict]) -> str:
    lines = [
        "# Model Test Summary — Three Household Profiles",
        "",
        "All values from the production pipeline (`scripts/energy_model/`), "
        "central long-term price scenario, Year 1 annual figures.",
        "",
        "## Results",
        "",
        "| Profile | Best plan | Baseline cost | Upgraded cost | Yr1 net savings | 20yr cumulative |",
        "|---|---|---|---|---|---|",
    ]
    for s in summaries:
        scenario_label = _SCENARIO_DISPLAY.get(s["best_scenario"], s["best_scenario"])
        lines.append(
            f"| {s['profile_name'].replace('_', ' ').title()} "
            f"| {scenario_label} "
            f"| €{s['baseline_yr1_energy_cost_eur']:,.0f} "
            f"| €{s['upgraded_yr1_energy_cost_eur']:,.0f} "
            f"| €{s['yr1_net_savings_eur']:,.0f} "
            f"| €{s['cum20_net_savings_eur']:,.0f} |"
        )

    lines += [
        "",
        "## Profile notes",
        "",
    ]
    for s in summaries:
        lines += [
            f"### {s['profile_name'].replace('_', ' ').title()}",
            "",
            s["profile_description"],
            "",
            f"- **Best plan:** {_SCENARIO_DISPLAY.get(s['best_scenario'], s['best_scenario'])}",
            f"- **Monthly instalment:** €{s['monthly_instalment_eur']:.2f}",
            f"- **Year 1 energy reduction:** €{s['yr1_energy_cost_reduction_eur']:,.0f}",
            f"- **Year 1 financing payments:** €{s['yr1_financing_payments_eur']:,.0f}",
            f"- **Year 1 net savings:** €{s['yr1_net_savings_eur']:,.0f}",
            f"- **Avg monthly net savings (Yr1):** €{s['monthly_net_savings_yr1_eur']:.2f}",
            f"- **Validation warnings:** {s['validation_warnings'] or 'none beyond kWp/battery size estimates'}",
            "",
        ]

    lines += [
        "## Modelling notes",
        "",
        "- ST forecast uses `ConstantShortTermPriceModel` (prices frozen at user tariff).",
        "- LT projection uses `ScenarioPriceModel` (low / central / high annual trend). "
          "Central used for best-plan selection.",
        "- Solar kWp estimated from usable roof area (0.2 kWp/m²) when not explicitly provided.",
        "- Battery defaults to 10.0 kWh when not specified.",
        "- Year 1 values are from `long_term_projection.central[0]`.",
        "- 20-yr values are from `long_term_projection.central[-1].financial_result.cumulative_net_savings_eur`.",
    ]

    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    summaries = []

    for profile in PROFILES:
        out_path = _OUTPUTS_DIR / f"{profile['name']}_output.json"
        output = json.loads(out_path.read_text())

        best = select_best_plan(output)
        metrics = year1_metrics(output, best["scenario"])

        print(f"\n[{profile['label']}]")
        print(f"  Best plan: {best['scenario']}  (cum20={best['cum20']:+,.0f})")
        print(f"  Baseline yr1: €{metrics['baseline_yr1_eur']:,.0f}")
        print(f"  Upgraded yr1: €{metrics['upgraded_yr1_eur']:,.0f}")
        print(f"  Net yr1:      €{metrics['net_yr1_eur']:+,.0f}  ({metrics['monthly_net_savings_yr1_eur']:+.2f}/mo)")

        fig_path = _FIGURES_DIR / f"{profile['name']}_comparison.png"
        create_figure(profile, output, best, metrics, fig_path)

        summaries.append(build_summary_entry(profile, output))

    # Write summary JSON
    summary_json_path = _OUTPUTS_DIR / "model_test_summary.json"
    summary_json_path.write_text(json.dumps(summaries, indent=2, ensure_ascii=False) + "\n")
    print(f"\nSummary JSON: {summary_json_path.relative_to(_REPO)}")

    # Write summary Markdown
    summary_md_path = _OUTPUTS_DIR / "model_test_summary.md"
    summary_md_path.write_text(build_markdown(summaries))
    print(f"Summary MD:   {summary_md_path.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
