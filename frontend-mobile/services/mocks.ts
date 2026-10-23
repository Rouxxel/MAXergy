/**
 * Mock responses for EXPO_PUBLIC_USE_MOCKS=true.
 *
 * The plan mock is a real backend response: POST /plan for documentation/data/model_input1.json,
 * recorded from the production engine (fixtures/plan_model_input1.json, same file as the web app
 * and backend/mcp/tests/fixtures/). Mock mode therefore shows the same honest numbers as live
 * mode for that example household — including negative savings while the loan runs — whatever
 * the user entered. Re-record the fixture when the API contract changes.
 */
import type {
  AdvisorChatResponse,
  AssessmentResponse,
  EnrichmentResponse,
  ForecastResult,
  HouseholdAssessment,
  PlanResponse,
  Recommendation,
} from "@/types";
import planFixture from "./fixtures/plan_model_input1.json";
import { validatePlanResponse } from "./validation";

let plan: PlanResponse | undefined;

export const mockPlan = (_a: HouseholdAssessment): PlanResponse =>
  (plan ??= validatePlanResponse(planFixture));

export const mockForecast = (a: HouseholdAssessment): ForecastResult => mockPlan(a).forecast;

export const mockRecommendation = (a: HouseholdAssessment): Recommendation =>
  mockPlan(a).recommendation;

export const mockAssessmentResponse = (_a: HouseholdAssessment): AssessmentResponse => ({
  assessment_id: "mock_" + Date.now(),
  status: "created",
  message: "Assessment stored (mock mode)",
});

export const mockEnrichment = (): EnrichmentResponse => ({
  lat: 52.53,
  lon: 13.38,
  roof: {
    usable_area_m2: 40,
    tilt_deg: 30,
    azimuth_deg: 180,
    orientation: "south",
    max_array_kwp: 6.7,
    low_confidence: false,
  },
  specific_yield_kwh_per_kwp: 980,
  source: { roof: "google_solar", pv_yield: "pvgis" },
  warnings: ["Mock mode: example values, not looked up."],
});

const advisorReplies = {
  financing:
    "A longer loan term lowers the monthly instalment but adds interest. Your plan shows the monthly figure while the loan runs and the saving once it is repaid — compare both before choosing a term.",
  why: "The recommended bundle is the one with the highest long-term net savings in your forecast. Check the rationale on the results screen: it lists the instalment, the saving after payoff and the break-even year.",
  default:
    "Your recommendation combines the upgrades with the best long-term outcome for your household. If the monthly figure is negative, that is the loan instalment outweighing early savings — the saving after payoff and the cumulative total show the longer view.",
};

export const mockAdvisorReply = (msg: string): AdvisorChatResponse => {
  const lower = msg.toLowerCase();
  const reply =
    lower.includes("financing") || lower.includes("term") || lower.includes("loan")
      ? advisorReplies.financing
      : lower.includes("why") || lower.includes("config")
        ? advisorReplies.why
        : advisorReplies.default;
  return {
    advisor_message: reply,
    context_used: ["mock"],
    suggestions: ["What happens after the loan is repaid?", "Why this bundle?"],
  };
};
