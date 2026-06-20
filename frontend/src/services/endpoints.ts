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
    ? mockDelay(mockAdvisorReply(data.message), 700)
    : apiRequest<AdvisorChatResponse>("/advisor/chat", { method: "POST", body: data });