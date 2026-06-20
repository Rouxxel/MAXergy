export type HeatingType =
  | "electric"
  | "gas"
  | "oil"
  | "district"
  | "coal"
  | "wood_pellets"
  | "other";

export type VehicleType = "ev" | "gas" | "hydrogen";

export type SpendSeason = "annual" | "spring" | "summer" | "autumn" | "winter";

/** Financing term expressed in months (1 month – 360 months / 30 years). */
export type FinancingTerm = number;

export interface HouseholdAssessment {
  country: string;
  postalCode: string;
  monthlyElectricitySpend: number;
  hasFeedInTariff: boolean;
  heatingType: HeatingType;
  heatingSpend: number;
  /** Heating type the spend applies to (often matches `heatingType`). */
  heatingSpendType: HeatingType;
  /** Season the heating spend reflects, or "annual" for a yearly average. */
  heatingSpendSeason: SpendSeason;
  vehicleOwnership: boolean;
  vehicleCount?: number;
  vehicleType?: VehicleType;
  vehicleMonthlyKm?: number;
  fuelSpend?: number;
  roofSize: number;
  /** Financing term in months. */
  financingTermMonths: FinancingTerm;
}

export interface Scenario {
  id: string;
  name: string;
  components: string[];
  monthlySavings: number;
  upfrontCost: number;
  financingCost: number;
  paybackYears: number;
  carbonReductionKg: number;
  recommended?: boolean;
}

export interface ForecastResult {
  monthlySavings: number;
  currentSpend: number;
  futureSpend: number;
  financingCost: number;
  roi: number;
  paybackTimeline: number;
  carbonReduction: number;
  scenarios: Scenario[];
}

export interface Recommendation {
  scenario: Scenario;
  reasoning: string;
}

export interface AdvisorMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
}

export interface AdvisorChatRequest {
  message: string;
  history: AdvisorMessage[];
  assessmentId?: string;
}

export interface AdvisorChatResponse {
  reply: string;
}

export interface AssessmentResponse {
  id: string;
  ok: true;
}