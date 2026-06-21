import type {
  AdvisorChatResponse,
  AssessmentResponse,
  ForecastResult,
  HouseholdAssessment,
  Recommendation,
  Scenario,
  ShortTermForecastPoint,
  LongTermForecastPoint,
  MonthlyCostEur,
  Baseline,
} from "@/types";

const createForecastPoints = (months: number, baseCost: number): ShortTermForecastPoint[] =>
  Array.from({ length: months }, (_, i) => ({
    month: `${2026 + Math.floor(i / 12)}-${String(((i % 12) + 1)).padStart(2, '0')}`,
    total_eur: baseCost * (1 + 0.03 * (i / 12)), // 3% annual escalation
  }));

const createLongTermForecastPoints = (years: number, baseCost: number): LongTermForecastPoint[] =>
  Array.from({ length: years }, (_, i) => ({
    year: 2026 + i,
    annual_total_eur: baseCost * 12 * (1 + 0.03 * i), // 3% annual escalation
  }));

const createMonthlyCost = (total: number): MonthlyCostEur => ({
  electricity: total * 0.4,
  heating: total * 0.35,
  mobility: total * 0.25,
  total,
});

const scenarios: Scenario[] = [
  {
    id: "solar_only",
    components: { solar_pv: true, battery: false, heat_pump: false, ev_charger: false },
    sizing: { solar_pv_kwp: 5, battery_kwh: null, heat_pump_kw: null },
    monthly_cost_eur: createMonthlyCost(245),
    financing_installment_eur: 120,
    monthly_saving_eur: 92,
    monthly_saving_post_payoff_eur: 212,
    self_consumption_ratio: 0.3,
    payback_month: 90,
    short_term_forecast: createForecastPoints(12, 245),
    long_term_forecast: createLongTermForecastPoints(20, 245),
  },
  {
    id: "pv_battery",
    components: { solar_pv: true, battery: true, heat_pump: false, ev_charger: false },
    sizing: { solar_pv_kwp: 5, battery_kwh: 7.5, heat_pump_kw: null },
    monthly_cost_eur: createMonthlyCost(199),
    financing_installment_eur: 198,
    monthly_saving_eur: 138,
    monthly_saving_post_payoff_eur: 336,
    self_consumption_ratio: 0.65,
    payback_month: 85,
    short_term_forecast: createForecastPoints(12, 199),
    long_term_forecast: createLongTermForecastPoints(20, 199),
  },
  {
    id: "pv_heatpump",
    components: { solar_pv: true, battery: false, heat_pump: true, ev_charger: false },
    sizing: { solar_pv_kwp: 5, battery_kwh: null, heat_pump_kw: 9 },
    monthly_cost_eur: createMonthlyCost(123),
    financing_installment_eur: 250,
    monthly_saving_eur: 214,
    monthly_saving_post_payoff_eur: 464,
    self_consumption_ratio: 0.45,
    payback_month: 77,
    short_term_forecast: createForecastPoints(12, 123),
    long_term_forecast: createLongTermForecastPoints(20, 123),
  },
  {
    id: "pv_ev",
    components: { solar_pv: true, battery: false, heat_pump: false, ev_charger: true },
    sizing: { solar_pv_kwp: 5, battery_kwh: null, heat_pump_kw: null },
    monthly_cost_eur: createMonthlyCost(161),
    financing_installment_eur: 180,
    monthly_saving_eur: 176,
    monthly_saving_post_payoff_eur: 356,
    self_consumption_ratio: 0.4,
    payback_month: 82,
    short_term_forecast: createForecastPoints(12, 161),
    long_term_forecast: createLongTermForecastPoints(20, 161),
  },
  {
    id: "pv_battery_heatpump",
    components: { solar_pv: true, battery: true, heat_pump: true, ev_charger: false },
    sizing: { solar_pv_kwp: 5, battery_kwh: 7.5, heat_pump_kw: 9 },
    monthly_cost_eur: createMonthlyCost(77),
    financing_installment_eur: 318,
    monthly_saving_eur: 260,
    monthly_saving_post_payoff_eur: 578,
    self_consumption_ratio: 0.75,
    payback_month: 72,
    short_term_forecast: createForecastPoints(12, 77),
    long_term_forecast: createLongTermForecastPoints(20, 77),
  },
  {
    id: "full_upgrade",
    components: { solar_pv: true, battery: true, heat_pump: true, ev_charger: true },
    sizing: { solar_pv_kwp: 5, battery_kwh: 7.5, heat_pump_kw: 9 },
    monthly_cost_eur: createMonthlyCost(41),
    financing_installment_eur: 439,
    monthly_saving_eur: 296,
    monthly_saving_post_payoff_eur: 735,
    self_consumption_ratio: 0.8,
    payback_month: 68,
    short_term_forecast: createForecastPoints(12, 41),
    long_term_forecast: createLongTermForecastPoints(20, 41),
  },
];

export const mockAssessmentResponse = (
  _a: HouseholdAssessment,
): AssessmentResponse => ({ id: "mock_" + Date.now(), status: "created" });

export const mockForecast = (_a: HouseholdAssessment): ForecastResult => {
  const baseline: Baseline = {
    monthly_cost_eur: createMonthlyCost(337),
    short_term_forecast: createForecastPoints(12, 337),
    long_term_forecast: createLongTermForecastPoints(20, 337),
  };

  return {
    baseline,
    scenarios,
  };
};

export const mockRecommendation = (_a: HouseholdAssessment): Recommendation => {
  const selected = scenarios[4]; // pv_battery_heatpump
  return {
    selected_scenario: selected,
    ranked_scenarios: scenarios.sort((a, b) => b.monthly_saving_eur - a.monthly_saving_eur),
    reasoning: "Based on your household profile, the Solar + Battery + Heat Pump combination offers the best balance of monthly savings and payback period. The battery increases self-consumption to 75%, while the heat pump replaces your most expensive heating fuel.",
  };
};

const advisorReplies = [
  "Your recommendation pairs rooftop solar with a battery and a heat pump. Solar covers daytime load, the battery shifts excess to evening, and the heat pump replaces your most expensive fuel — together they cut your bill by an estimated €260/month.",
  "We chose this configuration because your heating spend is the largest single line item. Electrifying it with a heat pump powered by your own solar gives the highest return per euro financed.",
  "Extending your financing term lowers the monthly payment but increases total interest. Most households break even faster on a 6-year term because savings outpace the slightly higher payment.",
];

export const mockAdvisorReply = (msg: string): AdvisorChatResponse => {
  const lower = msg.toLowerCase();
  if (lower.includes("financing") || lower.includes("term"))
    return { reply: advisorReplies[2] };
  if (lower.includes("why") || lower.includes("config"))
    return { reply: advisorReplies[1] };
  return { reply: advisorReplies[0] };
};