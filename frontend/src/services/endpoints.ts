import { apiRequest, USE_MOCKS } from "./apiClient";
import {
  mockAdvisorReply,
  mockAssessmentResponse,
  mockBenchmark,
  mockEnrichment,
  mockForecast,
  mockPlan,
  mockRecommendation,
} from "./mocks";
import {
  validateAdvisorChatResponse,
  validateAssessmentResponse,
  validateBenchmarkData,
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

/** Benchmark household for the landing page, computed by the engine (same services as /plan). */
export const getBenchmark = (): Promise<BenchmarkData> =>
  USE_MOCKS
    ? mockDelay(mockBenchmark(), 300)
    : apiRequest<unknown>("/benchmark", { method: "GET" }).then(validateBenchmarkData);
