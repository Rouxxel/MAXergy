// Types matching backend Pydantic schemas from model_input1.json and model_output_1.json

export interface Location {
  postcode: string;
  country: string;
}

export interface HouseholdOccupants {
  count: number;
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
}

export interface Household {
  occupants: HouseholdOccupants;
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
  known_subsidy_eur: number;
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

export interface MonthlyCostEur {
  electricity: number;
  gas_oil: number;
  fuel: number;
  total: number;
}

export interface ForecastPoint {
  month: number;
  year: number;
  cost_eur: number;
}

export interface Baseline {
  monthly_cost_eur: MonthlyCostEur;
  short_term_forecast: ForecastPoint[];
  long_term_forecast: ForecastPoint[];
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

export interface Scenario {
  id: string;
  components: ScenarioComponents;
  sizing: ScenarioSizing;
  monthly_cost_eur: MonthlyCostEur;
  financing_installment_eur: number;
  monthly_saving_eur: number;
  monthly_saving_post_payoff_eur: number;
  self_consumption_ratio: number;
  payback_month: number | null;
  short_term_forecast: ForecastPoint[];
  long_term_forecast: ForecastPoint[];
}

export interface ForecastResult {
  baseline: Baseline;
  scenarios: Scenario[];
}

export interface Recommendation {
  selected_scenario: Scenario;
  ranked_scenarios: Scenario[];
  reasoning: string;
}

export interface AdvisorChatRequest {
  user_message: string;
  forecast_result: ForecastResult | null;
  assessment_id: string | null;
}

export interface AdvisorChatResponse {
  advisor_message: string;
  context_used: string[];
  suggestions: string[];
}

export interface AssessmentResponse {
  id: string;
  status: string;
}