import type {
  AdvisorChatResponse,
  AssessmentResponse,
  ForecastResult,
  HouseholdAssessment,
  Recommendation,
  Scenario,
} from "@/types";

const scenarios: Scenario[] = [
  {
    id: "solar",
    name: "Solar Only",
    components: ["Rooftop Solar"],
    monthlySavings: 92,
    upfrontCost: 8500,
    financingCost: 120,
    paybackYears: 7.5,
    carbonReductionKg: 1800,
  },
  {
    id: "solar-battery",
    name: "Solar + Battery",
    components: ["Rooftop Solar", "Home Battery"],
    monthlySavings: 138,
    upfrontCost: 14200,
    financingCost: 198,
    paybackYears: 7.1,
    carbonReductionKg: 2400,
  },
  {
    id: "solar-battery-hp",
    name: "Solar + Battery + Heat Pump",
    components: ["Rooftop Solar", "Home Battery", "Heat Pump"],
    monthlySavings: 214,
    upfrontCost: 22800,
    financingCost: 318,
    paybackYears: 6.4,
    carbonReductionKg: 4100,
    recommended: true,
  },
  {
    id: "solar-battery-ev",
    name: "Solar + Battery + EV Charger",
    components: ["Rooftop Solar", "Home Battery", "EV Charger"],
    monthlySavings: 176,
    upfrontCost: 16400,
    financingCost: 228,
    paybackYears: 6.8,
    carbonReductionKg: 3200,
  },
  {
    id: "full",
    name: "Full Upgrade",
    components: ["Solar", "Battery", "Heat Pump", "EV Charger", "Insulation"],
    monthlySavings: 268,
    upfrontCost: 31500,
    financingCost: 439,
    paybackYears: 6.9,
    carbonReductionKg: 5400,
  },
];

export const mockAssessmentResponse = (
  _a: HouseholdAssessment,
): AssessmentResponse => ({ id: "mock_" + Date.now(), ok: true });

export const mockForecast = (a: HouseholdAssessment): ForecastResult => {
  const current =
    a.monthlyElectricitySpend + a.heatingSpend + (a.fuelSpend ?? 0);
  const recommended = scenarios.find((s) => s.recommended) ?? scenarios[2];
  const future = Math.max(0, current - recommended.monthlySavings);
  return {
    monthlySavings: recommended.monthlySavings,
    currentSpend: current,
    futureSpend: future,
    financingCost: recommended.financingCost,
    roi: 14.2,
    paybackTimeline: recommended.paybackYears,
    carbonReduction: recommended.carbonReductionKg,
    scenarios,
  };
};

export const mockRecommendation = (a: HouseholdAssessment): Recommendation => {
  const s = scenarios.find((x) => x.recommended) ?? scenarios[2];
  return {
    scenario: s,
    reasoning: `Based on your roof of ${a.roofSize} m², heating type "${a.heatingType}", and current spend, this bundle maximizes monthly savings within a ${Math.round(a.financingTermMonths / 12)}-year financing term.`,
  };
};

const advisorReplies = [
  "Your recommendation pairs rooftop solar with a battery and a heat pump. Solar covers daytime load, the battery shifts excess to evening, and the heat pump replaces your most expensive fuel — together they cut your bill by an estimated €214/month.",
  "We chose this configuration because your heating spend is the largest single line item. Electrifying it with a heat pump powered by your own solar gives the highest return per euro financed.",
  "Extending your financing term lowers the monthly payment but increases total interest. Most households break even faster on a 7-year term because savings outpace the slightly higher payment.",
];

export const mockAdvisorReply = (msg: string): AdvisorChatResponse => {
  const lower = msg.toLowerCase();
  if (lower.includes("financing") || lower.includes("term"))
    return { reply: advisorReplies[2] };
  if (lower.includes("why") || lower.includes("config"))
    return { reply: advisorReplies[1] };
  return { reply: advisorReplies[0] };
};