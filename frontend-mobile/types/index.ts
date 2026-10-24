// Types matching the backend Pydantic schemas (backend/src/models/forecast_schemas.py),
// documented in documentation/app/API_CONTRACT.md. Example input: model_input1.json;
// example output: model_output_v2.json.

// ---------------------------------------------------------------------------
// Request — HouseholdAssessment
// ---------------------------------------------------------------------------

export interface Location {
  postcode: string;
  country: string;
}

export interface HouseholdElectricity {
  annual_kwh: number;
  current_tariff_type: string;
  arbeitspreis_eur_per_kwh: number;
  grundpreis_eur_per_month: number;
  contract_end_date: string | null;
}

export interface HouseholdRoof {
  available: boolean;
  usable_area_m2: number | null;
  orientation: string | null;
  tilt_deg: number | null;
  shading_factor: number | null;
  /** Site PV yield (e.g. from POST /location/enrich); null → engine regional table. */
  specific_yield_kwh_per_kwp?: number | null;
}

export interface Household {
  occupants: number;
  electricity: HouseholdElectricity;
  roof: HouseholdRoof;
}

export interface HeatingBuilding {
  floor_area_m2: number;
  insulation_class: string;
}

export interface Heating {
  fuel_type: string;
  annual_consumption: number | null;
  annual_spend_eur: number | null;
  building: HeatingBuilding;
}

export interface Vehicle {
  vehicle_type: string;
  annual_mileage_km: number | null;
  fuel_consumption_l_per_100km: number | null;
  annual_fuel_spend_eur: number | null;
}

export interface Mobility {
  vehicle_count: number;
  vehicles: Vehicle[];
}

export interface UpgradeCandidates {
  solar_pv: boolean;
  battery: boolean;
  heat_pump: boolean;
  ev_charger: boolean;
  solar_pv_kwp: number | null;
  battery_kwh: number | null;
  heat_pump_kw: number | null;
}

export interface Financing {
  loan_term_years: number;
  loan_rate_pct: number;
  known_subsidy_eur: number | null;
}

export interface ForecastHorizon {
  short_term_months: number;
  long_term_years: number;
}

export interface HouseholdAssessment {
  location: Location;
  household: Household;
  heating: Heating;
  mobility: Mobility;
  upgrade_candidates: UpgradeCandidates;
  financing: Financing;
  forecast_horizon: ForecastHorizon;
}

// ---------------------------------------------------------------------------
// Response — ForecastResult
// ---------------------------------------------------------------------------

export interface MonthlyCostEur {
  electricity: number;
  heating: number;
  mobility: number;
  total: number;
}

/** Scenario costs: `total` includes the loan instalment. */
export interface ScenarioMonthlyCostEur extends MonthlyCostEur {
  financing_installment: number;
}

export interface ShortTermForecastPoint {
  month: string;
  total_eur: number;
}

export interface LongTermForecastPoint {
  year: number;
  annual_total_eur: number;
}

export interface ScenarioShortTermForecastPoint extends ShortTermForecastPoint {
  saving_eur: number;
}

export interface ScenarioLongTermForecastPoint extends LongTermForecastPoint {
  annual_saving_eur: number;
  cumulative_saving_eur?: number | null;
  scenario?: string | null;
}

export interface Baseline {
  monthly_cost_eur: MonthlyCostEur;
  short_term_forecast: ShortTermForecastPoint[];
  long_term_forecast: LongTermForecastPoint[];
}

export interface ScenarioComponents {
  solar_pv: boolean;
  battery: boolean;
  heat_pump: boolean;
  ev_charger: boolean;
}

export interface ScenarioSizing {
  solar_pv_kwp: number | null;
  battery_kwh: number | null;
  heat_pump_kw: number | null;
}

export interface LongTermBand {
  low: ScenarioLongTermForecastPoint[];
  high: ScenarioLongTermForecastPoint[];
}

export interface ScenarioFinancials {
  gross_investment_eur: number;
  subsidy_eur: number;
  financed_principal_eur: number;
  loan_term_months: number;
  horizon_years: number;
  cumulative_net_savings_central_eur: number;
  cumulative_net_savings_low_eur: number;
  cumulative_net_savings_high_eur: number;
  break_even_year: number | null;
}

export interface Scenario {
  id: string;
  components: ScenarioComponents;
  sizing: ScenarioSizing;
  monthly_cost_eur: ScenarioMonthlyCostEur;
  /** Average monthly net saving in year 1, loan instalment included (can be negative). */
  monthly_saving_eur: number;
  /** Average monthly saving once the loan is repaid (today's prices). */
  monthly_saving_post_payoff_eur: number;
  self_consumption_ratio: number;
  payback_month: number | null;
  short_term_forecast: ScenarioShortTermForecastPoint[];
  long_term_forecast: ScenarioLongTermForecastPoint[];
  long_term_band?: LongTermBand | null;
  financials?: ScenarioFinancials | null;
}

export interface ModelInfo {
  name: string;
  version: string;
  engine: string;
}

export interface ForecastResult {
  model?: ModelInfo | null;
  assumptions_used?: Record<string, unknown> | null;
  validation_warnings: string[];
  baseline: Baseline;
  scenarios: Scenario[];
}

// ---------------------------------------------------------------------------
// Response — Recommendation / PlanResponse
// ---------------------------------------------------------------------------

export type RecommendationMetric = "monthly_net" | "cumulative_central";

export interface RankedScenarioItem {
  id: string;
  score_eur: number;
  metric: RecommendationMetric;
}

export interface Recommendation {
  /** null when no scenario is available (e.g. no usable roof). */
  selected_scenario_id: string | null;
  selected_scenario: Scenario | null;
  ranked_scenarios: RankedScenarioItem[];
  metric_used: RecommendationMetric;
  rationale: string;
}

export interface PlanResponse {
  forecast: ForecastResult;
  recommendation: Recommendation;
}

// ---------------------------------------------------------------------------
// Assessment, advisor, enrichment, benchmark
// ---------------------------------------------------------------------------

export interface AssessmentResponse {
  assessment_id: string;
  status: string;
  message: string;
}

export interface AdvisorChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AdvisorChatRequest {
  user_message: string;
  /** Plan the user is looking at; null → the advisor runs the onboarding in chat. */
  plan?: PlanResponse | null;
  assessment_id?: string | null;
  /** Earlier turns, oldest first (max 20). */
  conversation_history?: AdvisorChatMessage[];
}

export interface AdvisorChatResponse {
  advisor_message: string;
  context_used: string[];
  suggestions: string[];
  /** Set when chat onboarding computed a plan (same services as POST /plan). */
  assessment?: HouseholdAssessment | null;
  plan?: PlanResponse | null;
}

export interface EnrichmentRequest {
  postcode?: string | null;
  address?: string | null;
  country?: "DE";
}

export interface EnrichmentRoof {
  usable_area_m2: number | null;
  tilt_deg: number | null;
  azimuth_deg: number | null;
  orientation: string | null;
  max_array_kwp: number | null;
  low_confidence: boolean;
}

export interface EnrichmentResponse {
  lat: number;
  lon: number;
  roof: EnrichmentRoof | null;
  specific_yield_kwh_per_kwp: number | null;
  source: { roof: string; pv_yield: string };
  warnings: string[];
}

export interface BenchmarkHousehold {
  location: string;
  occupants: number;
  annual_electricity_kwh: number;
  heating_type: string;
  heating_annual_kwh: number;
  vehicle_type: string;
  annual_mileage_km: number;
  roof_area_m2: number;
  roof_orientation: string;
  roof_tilt_deg: number;
}

/** GET /benchmark: the average German household run through the same engine as POST /plan. */
export interface BenchmarkRecommendation {
  scenario: string;
  description: string;
  rationale: string;
  metric: RecommendationMetric;
  break_even_year: number | null;
  monthly_instalment_eur: number;
  /** Year-1 monthly net incl. the loan instalment (can be negative). */
  monthly_saving_eur: number;
  monthly_saving_post_payoff_eur: number;
  cumulative_savings_eur: number;
  cumulative_savings_low_eur: number;
  cumulative_savings_high_eur: number;
}

export interface BenchmarkSeriesPoint {
  year: number;
  central: number | null;
  low: number | null;
  high: number | null;
}

export interface BenchmarkData {
  household: BenchmarkHousehold;
  recommendation: BenchmarkRecommendation;
  cumulative_series: BenchmarkSeriesPoint[];
  scenarios_count: number;
  projection_years: number;
  model_version: string;
  /** First forecast month ("YYYY-MM"); totals depend on it. */
  forecast_start: string | null;
}
