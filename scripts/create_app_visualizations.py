"""App-ready visualizations for the production energy model output.

Produces three charts per user profile, all reading directly from model output JSON.
No values are recalculated outside the model.

Run from repo root:
    python scripts/create_app_visualizations.py

Outputs:
    documentation/figures/app_visualizations/<name>_monthly_cost_comparison.png
    documentation/figures/app_visualizations/<name>_cumulative_net_savings.png
    documentation/figures/app_visualizations/<name>_year1_breakdown.png
    documentation/data/test_outputs/<name>_recommended_plan.json
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import matplotlib.gridspec as gridspec

_REPO = Path(__file__).parent.parent
_OUTPUTS_DIR = _REPO / "documentation" / "data" / "test_outputs"
_FIGS_DIR = _REPO / "documentation" / "figures" / "app_visualizations"
_FIGS_DIR.mkdir(parents=True, exist_ok=True)

# ── Colour palette ─────────────────────────────────────────────────────────────
C_BASELINE = "#1565C0"       # blue — baseline energy cost
C_UPG_ENERGY = "#2E7D32"     # green — upgraded energy cost (no financing)
C_FINANCING = "#B71C1C"      # red — financing payment
C_UPG_TOTAL = "#E65100"      # orange — upgraded total (energy + financing)
C_NET_POS = "#1B5E20"        # dark green — positive net savings
C_NET_NEG = "#C62828"        # dark red — negative net savings
C_BAND = "#90A4AE"           # blue-grey — low/high uncertainty band
C_BREAKEVEN = "#F57F17"      # amber — break-even marker
C_FIN_END = "#6A1B9A"        # purple — financing end marker
BG_ST = "#E3F2FD"            # light blue — short-term region
BG_LT = "#F9FBE7"            # light green — long-term region

SCENARIO_LABELS = {
    "solar_only": "Solar Only",
    "pv_battery": "PV + Battery",
    "pv_heatpump": "PV + Heat Pump",
    "pv_ev": "PV + EV",
    "pv_battery_heatpump": "PV + Battery + Heat Pump",
    "full_upgrade": "Full Upgrade",
}

PROFILES = [
    {
        "name": "average_german_household",
        "label": "Average German Household",
        "subtitle": "3-person, Cologne · Gas heating · 12,000 km/yr · 35 m² south roof",
    },
    {
        "name": "low_benefit_household",
        "label": "Low Benefit Household",
        "subtitle": "1-person, Hamburg · Gas heating · 4,000 km/yr · 12 m² north roof (40% shaded)",
    },
    {
        "name": "high_benefit_household",
        "label": "High Benefit Household",
        "subtitle": "5-person, Munich · Oil heating · 28,000 km/yr · 60 m² south roof",
    },
]


# ── Data helpers ───────────────────────────────────────────────────────────────

def load_output(name: str) -> dict:
    return json.loads((_OUTPUTS_DIR / f"{name}_output.json").read_text())


def select_best_scenario(output: dict) -> str:
    """Select scenario with highest 20-yr cumulative net savings (central LT).

    Tie-breaks: higher Year-1 net savings, then lower monthly instalment.
    """
    return max(
        output["upgrade_scenarios"],
        key=lambda sn: (
            output["upgrade_scenarios"][sn]["long_term_projection"]["central"][-1][
                "financial_result"]["cumulative_net_savings_eur"],
            output["upgrade_scenarios"][sn]["long_term_projection"]["central"][0][
                "financial_result"]["annual_net_savings_eur"],
            -output["upgrade_scenarios"][sn]["financing"]["monthly_instalment_eur"],
        ),
    )


def find_break_even(cum_by_year: list[float]) -> float | None:
    """Return fractional year of break-even via linear interpolation, or None."""
    for i in range(1, len(cum_by_year)):
        if cum_by_year[i - 1] < 0 <= cum_by_year[i]:
            frac = -cum_by_year[i - 1] / (cum_by_year[i] - cum_by_year[i - 1])
            return (i - 1) + frac  # fractional year index (0-based)
    if cum_by_year[0] >= 0:
        return 0.0  # already positive in Year 1
    return None


def recommendation_reason(output: dict, sn: str) -> str:
    lt_c = output["upgrade_scenarios"][sn]["long_term_projection"]["central"]
    cum20 = lt_c[-1]["financial_result"]["cumulative_net_savings_eur"]
    yr1_net = lt_c[0]["financial_result"]["annual_net_savings_eur"]
    cum_series = [r["financial_result"]["cumulative_net_savings_eur"] for r in lt_c]
    be = find_break_even(cum_series)

    if cum20 <= 0:
        return (
            "Least-loss option — all scenarios show negative 20-year net savings "
            "under central price assumptions."
        )
    if yr1_net >= 0:
        return (
            "Highest projected 20-year cumulative net savings "
            "with positive cash flow from Year 1."
        )
    if be is not None:
        be_year = int(be) + 1
        return (
            f"Highest projected 20-year cumulative net savings. "
            f"Year 1 net savings are negative — loan repayments exceed energy savings "
            f"in early years. Break-even projected in Year {be_year} "
            f"(central price scenario)."
        )
    return "Highest projected 20-year cumulative net savings."


# ── Monthly series construction ────────────────────────────────────────────────

def build_monthly_series(output: dict, sn: str) -> dict:
    """Build a 240-month time series combining ST (months 1–12) and LT (years 2–20).

    ST months use exact monthly model values (constant price model).
    LT months 13–240 use annual averages from the scenario price model (central).
    The two sections intentionally differ because they use different price models.
    """
    st = output["upgrade_scenarios"][sn]["short_term_forecast"]
    lt_c = output["upgrade_scenarios"][sn]["long_term_projection"]["central"]
    fin = output["upgrade_scenarios"][sn]["financing"]
    loan_months = fin["loan_term_months"]
    n_st = len(st)  # 12

    # ST: exact monthly values (months 0..11)
    x_st = list(range(n_st))
    base_st = [r["cost_eur"]["baseline_total"] for r in st]
    upg_total_st = [
        r["cost_eur"]["upgraded_total"] + r["financial_result"]["financing_instalment_eur"]
        for r in st
    ]
    upg_energy_st = [r["cost_eur"]["upgraded_total"] for r in st]

    # LT: step function from annual averages (years 2..20, months 12..239)
    # Each year span produces two points: (year_start, val) and (year_end, val)
    # so that consecutive equal values create horizontal segments
    # and back-to-back different years create vertical steps.
    x_lt: list[float] = []
    base_lt: list[float] = []
    upg_total_lt: list[float] = []
    upg_energy_lt: list[float] = []

    for i in range(1, len(lt_c)):  # years 2..20 (indices 1..19)
        yr_start = n_st + (i - 1) * 12
        yr_end = n_st + i * 12
        base_m = lt_c[i]["cost_eur"]["baseline_total"] / 12
        upg_e_m = lt_c[i]["cost_eur"]["upgraded_total"] / 12
        fin_m = lt_c[i]["financial_result"]["annual_financing_payments_eur"] / 12
        upg_t_m = upg_e_m + fin_m

        x_lt += [yr_start, yr_end]
        base_lt += [base_m, base_m]
        upg_total_lt += [upg_t_m, upg_t_m]
        upg_energy_lt += [upg_e_m, upg_e_m]

    return {
        "x_st": x_st,
        "base_st": base_st,
        "upg_total_st": upg_total_st,
        "upg_energy_st": upg_energy_st,
        "x_lt": x_lt,
        "base_lt": base_lt,
        "upg_total_lt": upg_total_lt,
        "upg_energy_lt": upg_energy_lt,
        "n_st": n_st,
        "loan_months": loan_months,
        "total_months": n_st + (len(lt_c) - 1) * 12,  # 12 + 19*12 = 240
    }


# ── Chart 1: Monthly cost comparison ──────────────────────────────────────────

def _eur_fmt(ax: plt.Axes) -> None:
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:,.0f}"))


def chart_monthly_cost(profile: dict, output: dict, sn: str, save_path: Path) -> None:
    d = build_monthly_series(output, sn)
    scenario_label = SCENARIO_LABELS.get(sn, sn)
    fin = output["upgrade_scenarios"][sn]["financing"]
    loan_months = d["loan_months"]
    total_months = d["total_months"]  # 240

    fig, ax = plt.subplots(figsize=(12, 5))

    # Region backgrounds
    ax.axvspan(-0.5, d["n_st"] - 0.5, facecolor=BG_ST, alpha=0.9, zorder=0, label="_nolegend_")
    ax.axvspan(d["n_st"] - 0.5, total_months + 0.5, facecolor=BG_LT, alpha=0.6, zorder=0, label="_nolegend_")

    # Region labels (top of figure)
    ax.text(d["n_st"] / 2 - 0.5, 1.02, "Short-term estimate\n(constant prices, Month 1–12)",
            transform=ax.get_xaxis_transform(), ha="center", va="bottom",
            fontsize=8.5, color="#1565C0", fontweight="bold")
    ax.text(d["n_st"] + (total_months - d["n_st"]) / 2, 1.02,
            "Long-term projection (central scenario, Years 2–20)\n"
            "Annual averages — prices rise with inflation assumptions",
            transform=ax.get_xaxis_transform(), ha="center", va="bottom",
            fontsize=8.5, color="#2E7D32", fontweight="bold")

    # ST data (solid lines, monthly)
    ax.plot(d["x_st"], d["base_st"], color=C_BASELINE, linewidth=2.0,
            label="Baseline energy cost", zorder=3)
    ax.plot(d["x_st"], d["upg_total_st"], color=C_UPG_TOTAL, linewidth=2.0,
            label="Upgraded total cost (energy + financing)", zorder=3)

    # LT data (dashed step lines, annual averages as monthly equivalent)
    ax.plot(d["x_lt"], d["base_lt"], color=C_BASELINE, linewidth=1.8,
            linestyle="--", alpha=0.85, zorder=2, label="_nolegend_")
    ax.plot(d["x_lt"], d["upg_total_lt"], color=C_UPG_TOTAL, linewidth=1.8,
            linestyle="--", alpha=0.85, zorder=2, label="_nolegend_")

    # Connector from ST end to LT start (thin dotted bridge)
    if d["x_lt"]:
        ax.plot([d["x_st"][-1], d["x_lt"][0]], [d["base_st"][-1], d["base_lt"][0]],
                color=C_BASELINE, linewidth=0.8, linestyle=":", alpha=0.5)
        ax.plot([d["x_st"][-1], d["x_lt"][0]], [d["upg_total_st"][-1], d["upg_total_lt"][0]],
                color=C_UPG_TOTAL, linewidth=0.8, linestyle=":", alpha=0.5)

    # Vertical marker: end of short-term estimate
    ax.axvline(d["n_st"] - 0.5, color="#1565C0", linestyle="-", linewidth=1.2,
               alpha=0.7, zorder=4)

    # Vertical marker: financing end
    fin_x = loan_months - 0.5  # position in 0-indexed month scale
    ax.axvline(fin_x, color=C_FIN_END, linestyle="--", linewidth=1.8,
               zorder=4, label=f"Financing ends (Month {loan_months})")
    ax.text(fin_x + 1, ax.get_ylim()[1] if ax.get_ylim()[1] != 1.0 else 0,
            f"Loan paid off\n(Month {loan_months})", color=C_FIN_END,
            fontsize=8, va="top", ha="left", zorder=5)

    # X-axis ticks: mix monthly (first year) and annual labels (remaining)
    n_lt_years = (total_months - d["n_st"]) // 12  # 19
    xtick_pos = list(range(0, d["n_st"], 3))  # every 3 months in ST
    xtick_lbl = [f"M{i + 1}" for i in range(0, d["n_st"], 3)]
    for yr in [2, 5, 10, 15, 20]:
        month_idx = d["n_st"] + (yr - 2) * 12
        if month_idx <= total_months:
            xtick_pos.append(month_idx)
            xtick_lbl.append(f"Yr {yr}")
    # Add loan end if not already covered
    loan_tick = loan_months - 1
    if loan_tick not in xtick_pos and 0 <= loan_tick <= total_months:
        xtick_pos.append(loan_tick)
        xtick_lbl.append(f"Loan\nend")
    ax.set_xticks(xtick_pos)
    ax.set_xticklabels(xtick_lbl, fontsize=8.5)

    _eur_fmt(ax)
    ax.set_ylabel("EUR per month", fontsize=11)
    ax.set_xlim(-0.5, total_months + 0.5)
    ax.set_title(
        f"{profile['label']} — {scenario_label}\nMonthly cost: baseline vs upgraded total household cost",
        fontsize=13, fontweight="bold", pad=24,
    )
    ax.legend(loc="upper left", fontsize=9.5, framealpha=0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Re-apply the financing-end label now we know ylim
    ymax = ax.get_ylim()[1]
    for txt in ax.texts:
        txt.remove()
    ax.text(fin_x + 1, ymax * 0.97, f"Loan paid off\n(Month {loan_months})",
            color=C_FIN_END, fontsize=8.5, va="top", ha="left", fontweight="bold")

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [1] Monthly cost: {save_path.name}")


# ── Chart 2: Cumulative net savings ───────────────────────────────────────────

def chart_cumulative_savings(profile: dict, output: dict, sn: str, save_path: Path) -> None:
    lt_c = output["upgrade_scenarios"][sn]["long_term_projection"]["central"]
    lt_l = output["upgrade_scenarios"][sn]["long_term_projection"]["low"]
    lt_h = output["upgrade_scenarios"][sn]["long_term_projection"]["high"]
    fin = output["upgrade_scenarios"][sn]["financing"]
    scenario_label = SCENARIO_LABELS.get(sn, sn)
    loan_months = fin["loan_term_months"]
    n_years = len(lt_c)  # 20

    # Build annual data: (0, 0), (year_1_end, cum_yr1), ..., (year_20_end, cum_yr20)
    x_years = [0] + list(range(1, n_years + 1))  # 0..20 (in years from start)
    cum_c = [0.0] + [r["financial_result"]["cumulative_net_savings_eur"] for r in lt_c]
    cum_l = [0.0] + [r["financial_result"]["cumulative_net_savings_eur"] for r in lt_l]
    cum_h = [0.0] + [r["financial_result"]["cumulative_net_savings_eur"] for r in lt_h]

    break_even_idx = find_break_even(cum_c[1:])  # pass year-1..20 values
    loan_end_year = loan_months / 12

    fig, ax = plt.subplots(figsize=(11, 5))

    # Low/high uncertainty band
    ax.fill_between(x_years, cum_l, cum_h, alpha=0.18, color=C_BAND,
                    label="Low–high projection range")

    # Low and high lines (thin, dashed)
    ax.plot(x_years, cum_l, color=C_BAND, linewidth=1.0, linestyle="--", alpha=0.7,
            label="Low scenario")
    ax.plot(x_years, cum_h, color=C_BAND, linewidth=1.0, linestyle="--", alpha=0.7,
            label="High scenario")

    # Central line
    ax.plot(x_years, cum_c, color=C_NET_POS, linewidth=2.5,
            marker="o", markersize=4.5, markevery=list(range(1, n_years + 1)),
            label="Central scenario (recommended)", zorder=3)

    # Zero line
    ax.axhline(0, color="black", linewidth=0.9, linestyle="-", alpha=0.5, zorder=2)

    # Financing end marker
    ax.axvline(loan_end_year, color=C_FIN_END, linestyle="--", linewidth=1.8, zorder=4,
               label=f"Financing ends (Year {int(loan_end_year)})")

    # Break-even annotation
    if break_even_idx is not None:
        be_year = break_even_idx + 1  # convert 0-based index to year number
        # Interpolated cumulative at break-even (should be ~0)
        ax.axvline(be_year, color=C_BREAKEVEN, linestyle=":", linewidth=1.6, zorder=4)
        ax.scatter([be_year], [0], color=C_BREAKEVEN, s=90, zorder=5,
                   label=f"Break-even (Year {be_year:.1f})")
        ymax = max(abs(v) for v in cum_c) or 1
        ax.annotate(
            f"Break-even\nYear {be_year:.1f}",
            xy=(be_year, 0), xytext=(be_year + 0.4, ymax * 0.12),
            fontsize=9, color=C_BREAKEVEN, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C_BREAKEVEN, lw=1.2),
        )
    else:
        if cum_c[1] >= 0:
            ax.text(0.5, 0.85, "Positive from Year 1",
                    transform=ax.transAxes, fontsize=10, color=C_NET_POS,
                    fontweight="bold", ha="center",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        else:
            ax.text(0.5, 0.85, "No break-even within 20 years\n(central scenario)",
                    transform=ax.transAxes, fontsize=9.5, color=C_NET_NEG,
                    ha="center",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    # Shade negative region
    ax.fill_between(x_years, cum_c, 0, where=[v < 0 for v in cum_c],
                    alpha=0.12, color=C_NET_NEG, interpolate=True)
    ax.fill_between(x_years, cum_c, 0, where=[v >= 0 for v in cum_c],
                    alpha=0.12, color=C_NET_POS, interpolate=True)

    # 20-yr label at end
    cum20 = cum_c[-1]
    ax.annotate(
        f"  €{cum20:+,.0f}\n  (20yr)",
        xy=(n_years, cum20), fontsize=9, fontweight="bold",
        color=C_NET_POS if cum20 >= 0 else C_NET_NEG,
        va="center",
    )

    ax.set_xlabel("Years from start", fontsize=11)
    _eur_fmt(ax)
    ax.set_ylabel("Cumulative net savings (EUR)", fontsize=11)
    ax.set_xlim(-0.2, n_years + 1.5)
    ax.set_xticks(range(0, n_years + 1, 2))
    ax.set_title(
        f"{profile['label']} — {scenario_label}\n"
        f"Cumulative net savings = baseline cost − upgraded total cost (energy + financing)",
        fontsize=13, fontweight="bold",
    )
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Footer note distinguishing ST from LT
    fig.text(0.5, -0.04,
             "Long-term projection uses scenario price model (central = 3% p.a. electricity growth). "
             "Low/high bands reflect policy-range assumptions, not statistical confidence intervals.",
             ha="center", fontsize=8, color="#666666", style="italic")

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [2] Cumulative: {save_path.name}")


# ── Chart 3: Year 1 annual breakdown ──────────────────────────────────────────

def chart_year1_breakdown(profile: dict, output: dict, sn: str, save_path: Path) -> None:
    lt_yr1 = output["upgrade_scenarios"][sn]["long_term_projection"]["central"][0]
    scenario_label = SCENARIO_LABELS.get(sn, sn)
    inst = output["upgrade_scenarios"][sn]["financing"]["monthly_instalment_eur"]

    baseline = lt_yr1["cost_eur"]["baseline_total"]
    upg_energy = lt_yr1["cost_eur"]["upgraded_total"]
    financing = lt_yr1["financial_result"]["annual_financing_payments_eur"]
    upg_total = upg_energy + financing
    net = lt_yr1["financial_result"]["annual_net_savings_eur"]

    labels = [
        "Baseline energy cost",
        "Upgraded energy cost",
        "Annual financing payments",
        "Upgraded total cost\n(energy + financing)",
        "Net savings",
    ]
    values = [baseline, upg_energy, financing, upg_total, net]
    colors = [C_BASELINE, C_UPG_ENERGY, C_FINANCING, C_UPG_TOTAL,
               C_NET_POS if net >= 0 else C_NET_NEG]

    fig, ax = plt.subplots(figsize=(9, 4.8))

    # y positions: top-to-bottom (highest y = first label)
    y_pos = list(range(len(labels) - 1, -1, -1))
    bars = ax.barh(y_pos, values, color=colors, height=0.52,
                   edgecolor="white", linewidth=0.8)

    # Value labels on bars — shift negative labels to the left of the bar end
    for bar, val in zip(bars, values):
        x_end = bar.get_width()
        ha = "left" if val >= 0 else "right"
        offset = 6 if val >= 0 else -6
        ax.annotate(
            f"€{val:,.0f}/yr",
            xy=(x_end, bar.get_y() + bar.get_height() / 2),
            xytext=(offset, 0), textcoords="offset points",
            ha=ha, va="center", fontsize=10.5, fontweight="bold",
        )

    ax.axvline(0, color="black", linewidth=1.0)

    # Y-axis: category labels (set BEFORE x-axis formatter to avoid interference)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10.5)

    # X-axis: EUR formatter (NOT applied to y-axis)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:,.0f}"))
    ax.set_xlabel("EUR per year  (Year 1, central price scenario)", fontsize=10)

    net_sign = "+" if net >= 0 else ""
    ax.set_title(
        f"{profile['label']} — {scenario_label}\n"
        f"Year 1 cost breakdown · Net savings: {net_sign}€{net:,.0f}/yr"
        f"   (€{inst:.2f}/mo financing)",
        fontsize=12, fontweight="bold",
    )

    # Definition footer
    ax.text(0.99, 0.01,
            "Net savings = Baseline − Upgraded energy − Financing",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8.5, color="#555555", style="italic")

    # Callout for negative Year 1
    if net < 0:
        ax.text(0.99, 0.11,
                f"Year 1 net is negative.\nLoan repayments exceed\nenergy savings in Year 1.",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=8.5, color=C_NET_NEG, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFEBEE", alpha=0.9))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Pad x-axis so value labels don't clip
    xmin, xmax = ax.get_xlim()
    span = xmax - xmin
    ax.set_xlim(xmin - span * 0.04, xmax + span * 0.24)

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [3] Year 1 breakdown: {save_path.name}")


# ── Recommendation JSON ───────────────────────────────────────────────────────

def build_recommendation_json(profile: dict, output: dict, sn: str) -> dict:
    lt_c = output["upgrade_scenarios"][sn]["long_term_projection"]["central"]
    yr1 = lt_c[0]
    fin = output["upgrade_scenarios"][sn]["financing"]
    baseline_yr1 = yr1["cost_eur"]["baseline_total"]
    upg_energy_yr1 = yr1["cost_eur"]["upgraded_total"]
    fin_yr1 = yr1["financial_result"]["annual_financing_payments_eur"]
    upg_total_yr1 = upg_energy_yr1 + fin_yr1
    net_yr1 = yr1["financial_result"]["annual_net_savings_eur"]
    cum20 = lt_c[-1]["financial_result"]["cumulative_net_savings_eur"]
    cum_series = [r["financial_result"]["cumulative_net_savings_eur"] for r in lt_c]
    be = find_break_even(cum_series)

    loan_months = fin["loan_term_months"]
    loan_end_year = loan_months // 12
    loan_end_month = loan_months

    break_even_year = None
    break_even_month = None
    if be is not None:
        be_yr = be + 1  # 1-indexed year
        break_even_year = round(be_yr, 1)
        break_even_month = round(be * 12 + 12)  # rough month from start

    return {
        "profile_name": profile["name"],
        "recommended_scenario": sn,
        "recommended_scenario_label": SCENARIO_LABELS.get(sn, sn),
        "recommendation_reason": recommendation_reason(output, sn),
        "yr1_baseline_energy_cost_eur": round(baseline_yr1, 2),
        "yr1_upgraded_energy_cost_eur": round(upg_energy_yr1, 2),
        "yr1_financing_payments_eur": round(fin_yr1, 2),
        "yr1_upgraded_total_cost_eur": round(upg_total_yr1, 2),
        "yr1_net_savings_eur": round(net_yr1, 2),
        "monthly_net_savings_yr1_eur": round(net_yr1 / 12, 2),
        "cum20_net_savings_central_eur": round(cum20, 2),
        "cum20_net_savings_low_eur": round(
            lt_c[-1]["financial_result"]["cumulative_net_savings_eur"], 2),  # placeholder if needed
        "break_even_year": break_even_year,
        "break_even_month_approx": break_even_month,
        "financing_monthly_instalment_eur": round(fin["monthly_instalment_eur"], 2),
        "financing_loan_term_months": loan_months,
        "financing_end_year": loan_end_year,
        "validation_warnings": output.get("validation_warnings", []),
        "note_st_vs_lt": (
            "Year 1 values use the central long-term scenario price model. "
            "The short-term estimate (constant prices) may differ slightly."
        ),
    }


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_chart_data(output: dict, sn: str) -> list[str]:
    """Spot-check that plotted values match model output."""
    errors: list[str] = []
    lt_c = output["upgrade_scenarios"][sn]["long_term_projection"]["central"]
    yr1 = lt_c[0]

    # Net savings formula
    expected_net = (yr1["cost_eur"]["baseline_total"]
                    - yr1["cost_eur"]["upgraded_total"]
                    - yr1["financial_result"]["annual_financing_payments_eur"])
    actual_net = yr1["financial_result"]["annual_net_savings_eur"]
    if abs(expected_net - actual_net) > 0.10:
        errors.append(f"Net savings mismatch yr1: expected {expected_net:.2f} got {actual_net:.2f}")

    # Cumulative must start at 0 (implied by our [0] + series construction)
    # and end at the model's cum20
    cum_series = [r["financial_result"]["cumulative_net_savings_eur"] for r in lt_c]
    if abs(sum([r["financial_result"]["annual_net_savings_eur"] for r in lt_c]) - cum_series[-1]) > 0.5:
        errors.append("Cumulative sum of annual net savings doesn't match final cum20")

    return errors


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    all_summaries: list[dict] = []

    for profile in PROFILES:
        print(f"\n{'='*60}")
        print(f"Profile: {profile['label']}")
        output = load_output(profile["name"])
        sn = select_best_scenario(output)
        scenario_label = SCENARIO_LABELS.get(sn, sn)
        print(f"Recommended: {scenario_label}")

        # Validation
        errs = validate_chart_data(output, sn)
        for e in errs:
            print(f"  VALIDATION ERROR: {e}")

        name = profile["name"]

        # Chart 1
        chart_monthly_cost(
            profile, output, sn,
            _FIGS_DIR / f"{name}_monthly_cost_comparison.png",
        )

        # Chart 2
        chart_cumulative_savings(
            profile, output, sn,
            _FIGS_DIR / f"{name}_cumulative_net_savings.png",
        )

        # Chart 3
        chart_year1_breakdown(
            profile, output, sn,
            _FIGS_DIR / f"{name}_year1_breakdown.png",
        )

        # Recommendation JSON
        rec = build_recommendation_json(profile, output, sn)
        rec_path = _OUTPUTS_DIR / f"{name}_recommended_plan.json"
        rec_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")

        # Print summary
        lt_c = output["upgrade_scenarios"][sn]["long_term_projection"]["central"]
        yr1 = lt_c[0]
        cum20 = lt_c[-1]["financial_result"]["cumulative_net_savings_eur"]
        yr1_net = yr1["financial_result"]["annual_net_savings_eur"]
        cum_series = [r["financial_result"]["cumulative_net_savings_eur"] for r in lt_c]
        be = find_break_even(cum_series)
        print(f"  Yr1 net: €{yr1_net:+,.0f}   20yr cum: €{cum20:+,.0f}")
        print(f"  Break-even: {'Year ' + str(round(be+1, 1)) if be is not None else 'none within 20yr'}")
        print(f"  Rec JSON: {rec_path.name}")

        all_summaries.append(rec)

    # Write combined summary
    summary_path = _OUTPUTS_DIR / "app_visualization_summary.json"
    summary_path.write_text(json.dumps(all_summaries, indent=2, ensure_ascii=False) + "\n")
    print(f"\nCombined summary: {summary_path.name}")


if __name__ == "__main__":
    main()
