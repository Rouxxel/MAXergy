import { z } from "zod";
import type { HouseholdAssessment, ForecastResult, Recommendation, AdvisorChatRequest, AdvisorChatResponse, AssessmentResponse } from "@/types";

// Location schema
const LocationSchema = z.object({
  postcode: z.string().min(1),
  country: z.string().min(1),
});

// Step-specific schemas for progressive validation
export const StepCountrySchema = z.object({
  location: z.object({
    country: z.string().min(1),
  }),
});

export const StepPostcodeSchema = z.object({
  location: z.object({
    postcode: z.string().min(1),
  }),
});

export const StepOccupantsSchema = z.object({
  household: z.object({
    occupants: z.number().min(1).max(20),
  }),
});

export const StepElectricitySchema = z.object({
  household: z.object({
    electricity: z.object({
      annual_kwh: z.number().min(0),
      current_tariff_type: z.string(),
      arbeitspreis_eur_per_kwh: z.number().min(0),
      grundpreis_eur_per_month: z.number().min(0),
      contract_end_date: z.string().nullable(),
    }),
  }),
});

export const StepRoofSchema = z.object({
  household: z.object({
    roof: z.object({
      available: z.boolean(),
      usable_area_m2: z.number().nullable(),
      orientation: z.string().nullable(),
      tilt_deg: z.number().nullable(),
      shading_factor: z.number().nullable(),
    }),
  }),
});

export const StepHeatingSchema = z.object({
  heating: z.object({
    fuel_type: z.string(),
    annual_consumption: z.number().nullable(),
    annual_spend_eur: z.number().nullable(),
    building: z.object({
      floor_area_m2: z.number().min(0),
      insulation_class: z.string(),
    }),
  }),
});

export const StepMobilitySchema = z.object({
  mobility: z.object({
    vehicle_count: z.number().min(0).max(5),
    vehicles: z.array(z.object({
      vehicle_type: z.string(),
      annual_mileage_km: z.number().nullable(),
      fuel_consumption_l_per_100km: z.number().nullable(),
      annual_fuel_spend_eur: z.number().nullable(),
    })),
  }),
});

export const StepUpgradesSchema = z.object({
  upgrade_candidates: z.object({
    solar_pv: z.boolean(),
    battery: z.boolean(),
    heat_pump: z.boolean(),
    ev_charger: z.boolean(),
    solar_pv_kwp: z.number().nullable(),
    battery_kwh: z.number().nullable(),
    heat_pump_kw: z.number().nullable(),
  }),
});

export const StepFinancingSchema = z.object({
  financing: z.object({
    loan_term_years: z.number().min(1).max(30),
    loan_rate_pct: z.number().min(0).max(100),
    known_subsidy_eur: z.number().min(0),
  }),
});

export const StepHorizonSchema = z.object({
  forecast_horizon: z.object({
    short_term_months: z.number().min(1).max(60),
    long_term_years: z.number().min(1).max(30),
  }),
});

// Household schemas
const HouseholdElectricitySchema = z.object({
  annual_kwh: z.number().min(0),
  current_tariff_type: z.string(),
  arbeitspreis_eur_per_kwh: z.number().min(0),
  grundpreis_eur_per_month: z.number().min(0),
  contract_end_date: z.string().nullable(),
});

const HouseholdRoofSchema = z.object({
  available: z.boolean(),
  usable_area_m2: z.number().nullable(),
  orientation: z.string().nullable(),
  tilt_deg: z.number().nullable(),
  shading_factor: z.number().nullable(),
});

const HouseholdSchema = z.object({
  occupants: z.number().min(1).max(20),
  electricity: HouseholdElectricitySchema,
  roof: HouseholdRoofSchema,
});

// Heating schema
const HeatingBuildingSchema = z.object({
  floor_area_m2: z.number().min(0),
  insulation_class: z.string(),
});

const HeatingSchema = z.object({
  fuel_type: z.string(),
  annual_consumption: z.number().nullable(),
  annual_spend_eur: z.number().nullable(),
  building: HeatingBuildingSchema,
});

// Mobility schema
const VehicleSchema = z.object({
  vehicle_type: z.string(),
  annual_mileage_km: z.number().nullable(),
  fuel_consumption_l_per_100km: z.number().nullable(),
  annual_fuel_spend_eur: z.number().nullable(),
});

const MobilitySchema = z.object({
  vehicle_count: z.number().min(0).max(5),
  vehicles: z.array(VehicleSchema),
});

// Upgrade candidates schema
const UpgradeCandidatesSchema = z.object({
  solar_pv: z.boolean(),
  battery: z.boolean(),
  heat_pump: z.boolean(),
  ev_charger: z.boolean(),
  solar_pv_kwp: z.number().nullable(),
  battery_kwh: z.number().nullable(),
  heat_pump_kw: z.number().nullable(),
});

// Financing schema
const FinancingSchema = z.object({
  loan_term_years: z.number().min(1).max(30),
  loan_rate_pct: z.number().min(0).max(100),
  known_subsidy_eur: z.number().min(0),
});

// Forecast horizon schema
const ForecastHorizonSchema = z.object({
  short_term_months: z.number().min(1).max(60),
  long_term_years: z.number().min(1).max(30),
});

// Main assessment schema
export const HouseholdAssessmentSchema = z.object({
  location: LocationSchema,
  household: HouseholdSchema,
  heating: HeatingSchema,
  mobility: MobilitySchema,
  upgrade_candidates: UpgradeCandidatesSchema,
  financing: FinancingSchema,
  forecast_horizon: ForecastHorizonSchema,
}) satisfies z.ZodType<HouseholdAssessment>;

// Forecast result schemas
const MonthlyCostEurSchema = z.object({
  electricity: z.number(),
  heating: z.number(),
  mobility: z.number(),
  total: z.number(),
});

const ShortTermForecastPointSchema = z.object({
  month: z.string(),
  total_eur: z.number(),
});

const LongTermForecastPointSchema = z.object({
  year: z.number(),
  annual_total_eur: z.number(),
});

const BaselineSchema = z.object({
  monthly_cost_eur: MonthlyCostEurSchema,
  short_term_forecast: z.array(ShortTermForecastPointSchema),
  long_term_forecast: z.array(LongTermForecastPointSchema),
});

const ScenarioComponentsSchema = z.object({
  solar_pv: z.boolean(),
  battery: z.boolean(),
  heat_pump: z.boolean(),
  ev_charger: z.boolean(),
});

const ScenarioSizingSchema = z.object({
  solar_pv_kwp: z.number().nullable(),
  battery_kwh: z.number().nullable(),
  heat_pump_kw: z.number().nullable(),
});

const ScenarioSchema = z.object({
  id: z.string(),
  components: ScenarioComponentsSchema,
  sizing: ScenarioSizingSchema,
  monthly_cost_eur: MonthlyCostEurSchema,
  financing_installment_eur: z.number(),
  monthly_saving_eur: z.number(),
  monthly_saving_post_payoff_eur: z.number(),
  self_consumption_ratio: z.number(),
  payback_month: z.number().nullable(),
  short_term_forecast: z.array(ShortTermForecastPointSchema),
  long_term_forecast: z.array(LongTermForecastPointSchema),
});

export const ForecastResultSchema = z.object({
  baseline: BaselineSchema,
  scenarios: z.array(ScenarioSchema),
}) satisfies z.ZodType<ForecastResult>;

// Recommendation schema
export const RecommendationSchema = z.object({
  selected_scenario: ScenarioSchema,
  ranked_scenarios: z.array(ScenarioSchema),
  reasoning: z.string(),
}) satisfies z.ZodType<Recommendation>;

// Advisor chat schemas
const AdvisorMessageSchema = z.object({
  id: z.string(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  createdAt: z.number(),
});

export const AdvisorChatRequestSchema = z.object({
  user_message: z.string().min(1),
  forecast_result: z.null(),
  assessment_id: z.string().nullable(),
}) satisfies z.ZodType<AdvisorChatRequest>;

export const AdvisorChatResponseSchema = z.object({
  advisor_message: z.string(),
  context_used: z.array(z.string()),
  suggestions: z.array(z.string()),
}) satisfies z.ZodType<AdvisorChatResponse>;

// Assessment response schema
export const AssessmentResponseSchema = z.object({
  id: z.string(),
  status: z.string(),
}) satisfies z.ZodType<AssessmentResponse>;

// Validation functions
export function validateHouseholdAssessment(data: unknown): HouseholdAssessment {
  return HouseholdAssessmentSchema.parse(data);
}

export function validateForecastResult(data: unknown): ForecastResult {
  return ForecastResultSchema.parse(data);
}

export function validateRecommendation(data: unknown): Recommendation {
  return RecommendationSchema.parse(data);
}

export function validateAdvisorChatRequest(data: unknown): AdvisorChatRequest {
  return AdvisorChatRequestSchema.parse(data);
}

export function validateAdvisorChatResponse(data: unknown): AdvisorChatResponse {
  return AdvisorChatResponseSchema.parse(data);
}

export function validateAssessmentResponse(data: unknown): AssessmentResponse {
  return AssessmentResponseSchema.parse(data);
}
