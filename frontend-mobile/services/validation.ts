import { z } from "zod";
import type {
  HouseholdAssessment,
  ForecastResult,
  Recommendation,
  PlanResponse,
  AdvisorChatRequest,
  AdvisorChatResponse,
  AssessmentResponse,
  EnrichmentResponse,
  BenchmarkData,
} from "@/types";

// Location schema
const LocationSchema = z.object({
  postcode: z.string().min(1),
  country: z.string().min(1),
});

// Step-specific schemas for progressive validation
export const StepCountrySchema = z.object({
  location: z.object({
    country: z.literal("DE", { error: "MAXergy currently supports households in Germany only" }),
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
    roof: z
      .object({
        available: z.boolean(),
        usable_area_m2: z.number().nullable(),
        orientation: z.string().nullable(),
        tilt_deg: z.number().min(0).max(90).nullable(),
        shading_factor: z.number().min(0).max(1).nullable(),
      })
      .refine((r) => !r.available || (r.usable_area_m2 ?? 0) > 0, {
        message: "Enter the usable roof area (or switch off solar if the roof can't take panels)",
        path: ["usable_area_m2"],
      }),
  }),
});

export const StepHeatingSchema = z.object({
  heating: z.object({
    fuel_type: z.enum(["gas", "oil"], { error: "MAXergy can currently model gas or oil heating only" }),
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
      vehicle_type: z.enum(["petrol", "diesel", "hybrid", "phev", "electric"]),
      annual_mileage_km: z
        .number({ error: "Enter the yearly mileage for each vehicle" })
        .positive({ error: "Enter the yearly mileage for each vehicle" }),
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
  specific_yield_kwh_per_kwp: z.number().positive().max(2000).nullish(),
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
  known_subsidy_eur: z.number().min(0).nullable(),
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

// Forecast result schemas (backend ForecastResult; unknown keys are stripped)
const MonthlyCostEurSchema = z.object({
  electricity: z.number(),
  heating: z.number(),
  mobility: z.number(),
  total: z.number(),
});

const ScenarioMonthlyCostEurSchema = MonthlyCostEurSchema.extend({
  financing_installment: z.number(),
});

const ShortTermForecastPointSchema = z.object({
  month: z.string(),
  total_eur: z.number(),
});

const LongTermForecastPointSchema = z.object({
  year: z.number(),
  annual_total_eur: z.number(),
});

const ScenarioShortTermForecastPointSchema = ShortTermForecastPointSchema.extend({
  saving_eur: z.number(),
});

const ScenarioLongTermForecastPointSchema = LongTermForecastPointSchema.extend({
  annual_saving_eur: z.number(),
  cumulative_saving_eur: z.number().nullish(),
  scenario: z.string().nullish(),
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

const ScenarioFinancialsSchema = z.object({
  gross_investment_eur: z.number(),
  subsidy_eur: z.number(),
  financed_principal_eur: z.number(),
  loan_term_months: z.number(),
  horizon_years: z.number(),
  cumulative_net_savings_central_eur: z.number(),
  cumulative_net_savings_low_eur: z.number(),
  cumulative_net_savings_high_eur: z.number(),
  break_even_year: z.number().nullable(),
});

const ScenarioSchema = z.object({
  id: z.string(),
  components: ScenarioComponentsSchema,
  sizing: ScenarioSizingSchema,
  monthly_cost_eur: ScenarioMonthlyCostEurSchema,
  monthly_saving_eur: z.number(),
  monthly_saving_post_payoff_eur: z.number(),
  self_consumption_ratio: z.number(),
  payback_month: z.number().nullable(),
  short_term_forecast: z.array(ScenarioShortTermForecastPointSchema),
  long_term_forecast: z.array(ScenarioLongTermForecastPointSchema),
  long_term_band: z
    .object({
      low: z.array(ScenarioLongTermForecastPointSchema),
      high: z.array(ScenarioLongTermForecastPointSchema),
    })
    .nullish(),
  financials: ScenarioFinancialsSchema.nullish(),
});

export const ForecastResultSchema = z.object({
  model: z.object({ name: z.string(), version: z.string(), engine: z.string() }).nullish(),
  assumptions_used: z.record(z.string(), z.unknown()).nullish(),
  validation_warnings: z.array(z.string()).default([]),
  baseline: BaselineSchema,
  scenarios: z.array(ScenarioSchema),
}) satisfies z.ZodType<ForecastResult, unknown>;

// Recommendation / plan schemas
const RecommendationMetricSchema = z.enum(["monthly_net", "cumulative_central"]);

export const RecommendationSchema = z.object({
  selected_scenario_id: z.string().nullable(),
  selected_scenario: ScenarioSchema.nullable(),
  ranked_scenarios: z.array(
    z.object({ id: z.string(), score_eur: z.number(), metric: RecommendationMetricSchema }),
  ),
  metric_used: RecommendationMetricSchema,
  rationale: z.string(),
}) satisfies z.ZodType<Recommendation, unknown>;

export const PlanResponseSchema = z.object({
  forecast: ForecastResultSchema,
  recommendation: RecommendationSchema,
}) satisfies z.ZodType<PlanResponse, unknown>;

// Advisor chat schemas
const AdvisorChatMessageSchema = z.object({
  role: z.enum(["user", "assistant"]),
  content: z.string().max(4000),
});

export const AdvisorChatRequestSchema = z.object({
  user_message: z.string().min(1).max(1000),
  plan: PlanResponseSchema.nullish(),
  assessment_id: z.string().nullish(),
  conversation_history: z.array(AdvisorChatMessageSchema).max(20).optional(),
}) satisfies z.ZodType<AdvisorChatRequest, unknown>;

export const AdvisorChatResponseSchema = z.object({
  advisor_message: z.string(),
  context_used: z.array(z.string()).default([]),
  suggestions: z.array(z.string()).default([]),
  assessment: HouseholdAssessmentSchema.nullish(),
  plan: PlanResponseSchema.nullish(),
}) satisfies z.ZodType<AdvisorChatResponse, unknown>;

// Assessment response schema
export const AssessmentResponseSchema = z.object({
  assessment_id: z.string(),
  status: z.string(),
  message: z.string(),
}) satisfies z.ZodType<AssessmentResponse, unknown>;

// Location enrichment schema
export const EnrichmentResponseSchema = z.object({
  lat: z.number(),
  lon: z.number(),
  roof: z
    .object({
      usable_area_m2: z.number().nullable(),
      tilt_deg: z.number().nullable(),
      azimuth_deg: z.number().nullable(),
      orientation: z.string().nullable(),
      max_array_kwp: z.number().nullable(),
      low_confidence: z.boolean(),
    })
    .nullable(),
  specific_yield_kwh_per_kwp: z.number().nullable(),
  source: z.object({ roof: z.string(), pv_yield: z.string() }),
  warnings: z.array(z.string()).default([]),
}) satisfies z.ZodType<EnrichmentResponse, unknown>;

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

export function validatePlanResponse(data: unknown): PlanResponse {
  return PlanResponseSchema.parse(data);
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

export function validateEnrichmentResponse(data: unknown): EnrichmentResponse {
  return EnrichmentResponseSchema.parse(data);
}

// Benchmark schema (GET /benchmark)
export const BenchmarkDataSchema = z.object({
  household: z.object({
    location: z.string(),
    occupants: z.number(),
    annual_electricity_kwh: z.number(),
    heating_type: z.string(),
    heating_annual_kwh: z.number(),
    vehicle_type: z.string(),
    annual_mileage_km: z.number(),
    roof_area_m2: z.number(),
    roof_orientation: z.string(),
    roof_tilt_deg: z.number(),
  }),
  recommendation: z.object({
    scenario: z.string(),
    description: z.string(),
    rationale: z.string(),
    metric: z.enum(["monthly_net", "cumulative_central"]),
    break_even_year: z.number().nullable(),
    monthly_instalment_eur: z.number(),
    monthly_saving_eur: z.number(),
    monthly_saving_post_payoff_eur: z.number(),
    cumulative_savings_eur: z.number(),
    cumulative_savings_low_eur: z.number(),
    cumulative_savings_high_eur: z.number(),
  }),
  cumulative_series: z.array(
    z.object({
      year: z.number(),
      central: z.number().nullable(),
      low: z.number().nullable(),
      high: z.number().nullable(),
    }),
  ),
  scenarios_count: z.number(),
  projection_years: z.number(),
  model_version: z.string(),
  forecast_start: z.string().nullable(),
}) satisfies z.ZodType<BenchmarkData, unknown>;

export function validateBenchmarkData(data: unknown): BenchmarkData {
  return BenchmarkDataSchema.parse(data);
}
