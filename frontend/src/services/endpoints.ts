import { apiRequest, USE_MOCKS } from "./apiClient";
import {
  mockAdvisorReply,
  mockAssessmentResponse,
  mockEnrichment,
  mockForecast,
  mockPlan,
  mockRecommendation,
} from "./mocks";
import {
  validateAdvisorChatResponse,
  validateAssessmentResponse,
  validateEnrichmentResponse,
  validateForecastResult,
  validatePlanResponse,
  validateRecommendation,
} from "./validation";
import type {
  AdvisorChatRequest,
  AdvisorChatResponse,
  AssessmentResponse,
  EnrichmentRequest,
  EnrichmentResponse,
  ForecastResult,
  HouseholdAssessment,
  PlanResponse,
  Recommendation,
  RecommendationMetric,
  BenchmarkData,
} from "@/types";

const mockDelay = <T>(value: T | Promise<T>, ms = 600) =>
  new Promise<T>((r) => setTimeout(() => r(value), ms));

const metricQuery = (metric?: RecommendationMetric) => (metric ? `?metric=${metric}` : "");

// Live responses are validated with Zod, so contract drift fails loudly instead of rendering
// `undefined` fields.

export const postAssessment = (data: HouseholdAssessment): Promise<AssessmentResponse> =>
  USE_MOCKS
    ? mockDelay(mockAssessmentResponse(data), 400)
    : apiRequest<unknown>("/assessment", { method: "POST", body: data }).then(
        validateAssessmentResponse,
      );

/** Forecast + recommendation from one engine run — what the results flow uses. */
export const postPlan = (
  data: HouseholdAssessment,
  metric?: RecommendationMetric,
): Promise<PlanResponse> =>
  USE_MOCKS
    ? mockDelay(mockPlan(data), 900)
    : apiRequest<unknown>(`/plan${metricQuery(metric)}`, { method: "POST", body: data }).then(
        validatePlanResponse,
      );

export const postForecast = (data: HouseholdAssessment): Promise<ForecastResult> =>
  USE_MOCKS
    ? mockDelay(mockForecast(data), 900)
    : apiRequest<unknown>("/forecast", { method: "POST", body: data }).then(validateForecastResult);

export const postRecommendation = (
  data: HouseholdAssessment,
  metric?: RecommendationMetric,
): Promise<Recommendation> =>
  USE_MOCKS
    ? mockDelay(mockRecommendation(data), 700)
    : apiRequest<unknown>(`/recommendation${metricQuery(metric)}`, {
        method: "POST",
        body: data,
      }).then(validateRecommendation);

/** Coordinates, roof proposal and site PV yield (503 when the MCP service is disabled). */
export const postLocationEnrich = (data: EnrichmentRequest): Promise<EnrichmentResponse> =>
  USE_MOCKS
    ? mockDelay(mockEnrichment(), 500)
    : apiRequest<unknown>("/location/enrich", { method: "POST", body: data }).then(
        validateEnrichmentResponse,
      );

export const postAdvisorChat = (data: AdvisorChatRequest): Promise<AdvisorChatResponse> =>
  USE_MOCKS
    ? mockDelay(mockAdvisorReply(data.user_message), 700)
    : apiRequest<unknown>("/advisor/chat", { method: "POST", body: data }).then(
        validateAdvisorChatResponse,
      );

export const getBenchmark = (): Promise<BenchmarkData> =>
  USE_MOCKS
    ? mockDelay(
        {
          household: {
            location: "50667, DE",
            occupants: 3,
            annual_electricity_kwh: 3500,
            heating_type: "gas",
            heating_annual_kwh: 14000,
            vehicle_type: "petrol",
            annual_mileage_km: 12000,
            roof_area_m2: 35,
            roof_orientation: "south",
            roof_tilt_deg: 32,
          },
          recommendation: {
            scenario: "full_upgrade",
            break_even_year: 8,
            monthly_instalment_eur: 209,
            cumulative_savings_eur: 24828,
            description:
              "Solar panels + battery storage + heat pump + EV charger. Highest projected 20-year cumulative net savings under the central price scenario.",
          },
          scenarios_count: 6,
          projection_years: 20,
          model_version: "4.0",
        },
        300,
      )
    : apiRequest<BenchmarkData>("/benchmark", { method: "GET" });
