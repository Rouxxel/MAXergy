/**
 * The three savings numbers MAXergy shows everywhere (web, mobile, MCP presentation guidance),
 * with one wording:
 *   1. monthly net saving in year 1, loan instalment included — "During financing" when negative;
 *   2. monthly saving after the loan is repaid;
 *   3. cumulative net saving over the horizon (central prices, low–high range).
 */
import type { Scenario } from "@/types";

const fmt = (n: number) => Math.round(Math.abs(n)).toLocaleString("en-US");

/** €1,234 (no sign). */
export const euro = (n: number | null | undefined) => (n == null ? "–" : `€${fmt(n)}`);

/** +€1,234 / −€1,234. */
export const signedEuro = (n: number | null | undefined) =>
  n == null ? "–" : `${n < 0 ? "−" : "+"}€${fmt(n)}`;

export interface SavingsSummary {
  savesFromStart: boolean;
  primaryLabel: string;
  primaryValue: string;
  primaryNote: string;
  afterPayoff: string;
  longTerm: string | null;
  longTermRange: string | null;
  /** One sentence with all three numbers (advisor, sharing). */
  sentence: string;
}

export function summarizeSavings(s: Scenario): SavingsSummary {
  const m = s.monthly_saving_eur;
  const after = s.monthly_saving_post_payoff_eur;
  const f = s.financials;
  const years = f?.horizon_years;
  const loanYears = f ? Math.round(f.loan_term_months / 12) : null;
  const savesFromStart = m >= 0;
  const tail = f ? `; ${years}-year net ${signedEuro(f.cumulative_net_savings_central_eur)}` : "";
  return {
    savesFromStart,
    primaryLabel: savesFromStart ? "You could save" : "During financing",
    primaryValue: savesFromStart ? euro(m) : signedEuro(m),
    primaryNote: savesFromStart
      ? "per month from the start, loan instalment included"
      : "per month compared with today, loan instalment included",
    afterPayoff: `After payoff: ${signedEuro(after)}/month`,
    longTerm: f ? `${years}-year net: ${signedEuro(f.cumulative_net_savings_central_eur)}` : null,
    longTermRange: f
      ? `${signedEuro(f.cumulative_net_savings_low_eur)} to ${signedEuro(f.cumulative_net_savings_high_eur)} with low/high energy prices`
      : null,
    sentence: savesFromStart
      ? `Saves ${euro(m)}/month from the start (loan included), ${euro(after)}/month after payoff${tail}.`
      : `Costs ${euro(m)}/month more during ${loanYears ? `the ${loanYears}-year loan` : "the loan"}, then saves ${euro(after)}/month${tail}.`,
  };
}

/** Plain-language list of the assumptions behind a forecast, for the "Assumptions" disclosure. */
export function describeAssumptions(
  assumptions: Record<string, unknown> | null | undefined,
): string[] {
  if (!assumptions) return [];
  const a = assumptions as {
    pv_yield_source?: string;
    pv_specific_yield_kwh_per_kwp?: number;
    heat_pump_scop?: number;
    battery_usable_kwh?: number;
    investment_costs?: { loan_term_years?: number; annual_rate_pct?: number };
  };
  const out: string[] = [];
  if (a.pv_specific_yield_kwh_per_kwp)
    out.push(
      `Solar yield ${Math.round(a.pv_specific_yield_kwh_per_kwp)} kWh per kWp per year (${
        a.pv_yield_source === "pvgis_site" ? "PVGIS for your site" : "regional average"
      })`,
    );
  if (a.battery_usable_kwh) out.push(`Battery ${a.battery_usable_kwh} kWh usable`);
  if (a.heat_pump_scop) out.push(`Heat pump seasonal efficiency (SCOP) ${a.heat_pump_scop}`);
  const loan = a.investment_costs;
  if (loan?.loan_term_years)
    out.push(`Loan ${loan.loan_term_years} years at ${loan.annual_rate_pct ?? "?"} %`);
  out.push(
    "Prices: your current tariff for year 1; long-term totals use central price growth, with low/high scenarios as the range",
  );
  return out;
}
