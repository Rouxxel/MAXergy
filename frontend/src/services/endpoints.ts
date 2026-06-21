import { apiRequest, USE_MOCKS } from "./apiClient";
import {
  mockAdvisorReply,
  mockAssessmentResponse,
  mockForecast,
  mockRecommendation,
} from "./mocks";
import type {
  AdvisorChatRequest,
  AdvisorChatResponse,
  AssessmentResponse,
  ForecastResult,
  HouseholdAssessment,
  Recommendation,
  BenchmarkData,
} from "@/types";

const mockDelay = <T,>(value: T, ms = 600) =>
  new Promise<T>((r) => setTimeout(() => r(value), ms));

export const postAssessment = (
  data: HouseholdAssessment,
): Promise<AssessmentResponse> =>
  USE_MOCKS
    ? mockDelay(mockAssessmentResponse(data), 400)
    : apiRequest<AssessmentResponse>("/assessment", { method: "POST", body: data });

export const postForecast = (
  data: HouseholdAssessment,
): Promise<ForecastResult> =>
  USE_MOCKS
    ? mockDelay(mockForecast(data), 900)
    : apiRequest<ForecastResult>("/forecast", { method: "POST", body: data });

export const postRecommendation = (
  data: HouseholdAssessment,
): Promise<Recommendation> =>
  USE_MOCKS
    ? mockDelay(mockRecommendation(data), 700)
    : apiRequest<Recommendation>("/recommendation", { method: "POST", body: data });

export const postAdvisorChat = (
  data: AdvisorChatRequest,
): Promise<AdvisorChatResponse> =>
  USE_MOCKS
    ? mockDelay(mockAdvisorReply(data.user_message), 700)
    : apiRequest<AdvisorChatResponse>("/advisor/chat", { method: "POST", body: data });

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