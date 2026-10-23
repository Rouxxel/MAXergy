import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { EnrichmentResponse, HouseholdAssessment } from "@/types";
import { zustandStorage } from "@/lib/storage";

export type AssessmentDraft = Partial<HouseholdAssessment>;

/**
 * Engine defaults, identical to the backend's GET /assumptions (tariff, financing) so the web
 * form, the mobile app and the MCP onboarding propose the same values.
 */
export const ENGINE_DEFAULTS = {
  arbeitspreis_eur_per_kwh: 0.32,
  grundpreis_eur_per_month: 12.5,
  loan_term_years: 15,
  loan_rate_pct: 4.5,
} as const;

export const DEFAULT_ROOF = {
  available: true,
  usable_area_m2: 40,
  orientation: "south",
  tilt_deg: 30,
  shading_factor: 0.1,
  specific_yield_kwh_per_kwp: null,
};

export const DEFAULT_ELECTRICITY = {
  annual_kwh: 3000,
  current_tariff_type: "fixed",
  arbeitspreis_eur_per_kwh: ENGINE_DEFAULTS.arbeitspreis_eur_per_kwh,
  grundpreis_eur_per_month: ENGINE_DEFAULTS.grundpreis_eur_per_month,
  contract_end_date: null,
};

interface AssessmentState {
  draft: AssessmentDraft;
  step: number;
  submitting: boolean;
  submittedId?: string;
  /** Last POST /location/enrich result and the postcode it was looked up for. */
  enrichment?: EnrichmentResponse;
  enrichedPostcode?: string;
  setField: <K extends keyof HouseholdAssessment>(key: K, value: HouseholdAssessment[K]) => void;
  setStep: (step: number) => void;
  setSubmitting: (v: boolean) => void;
  setSubmittedId: (id: string) => void;
  /** Pre-fill the roof (area, tilt, orientation, site PV yield) from a location lookup. */
  applyEnrichment: (postcode: string, result: EnrichmentResponse) => void;
  reset: () => void;
  getCompleted: () => HouseholdAssessment | null;
}

const initial: AssessmentDraft = {
  location: {
    postcode: "",
    country: "DE",
  },
  household: {
    occupants: 2,
    electricity: DEFAULT_ELECTRICITY,
    roof: DEFAULT_ROOF,
  },
  heating: {
    fuel_type: "gas",
    annual_consumption: 20000,
    annual_spend_eur: 2000,
    building: {
      floor_area_m2: 120,
      insulation_class: "medium",
    },
  },
  mobility: {
    vehicle_count: 0,
    vehicles: [],
  },
  // All upgrades are considered by default (same as the MCP onboarding); the engine drops
  // scenarios that need a component the user switches off.
  upgrade_candidates: {
    solar_pv: true,
    battery: true,
    heat_pump: true,
    ev_charger: true,
    solar_pv_kwp: null,
    battery_kwh: null,
    heat_pump_kw: null,
  },
  financing: {
    loan_term_years: ENGINE_DEFAULTS.loan_term_years,
    loan_rate_pct: ENGINE_DEFAULTS.loan_rate_pct,
    known_subsidy_eur: 0,
  },
  forecast_horizon: {
    short_term_months: 12,
    long_term_years: 20,
  },
};

export const useAssessmentStore = create<AssessmentState>()(
  persist(
    (set, get) => ({
      draft: initial,
      step: 0,
      submitting: false,
      setField: (key, value) => set((s) => ({ draft: { ...s.draft, [key]: value } })),
      setStep: (step) => set({ step }),
      setSubmitting: (submitting) => set({ submitting }),
      setSubmittedId: (submittedId) => set({ submittedId }),
      applyEnrichment: (postcode, result) =>
        set((s) => {
          const household = s.draft.household ?? initial.household!;
          const roof = household.roof;
          const scanned = result.roof;
          return {
            enrichment: result,
            enrichedPostcode: postcode,
            draft: {
              ...s.draft,
              household: {
                ...household,
                roof: {
                  ...roof,
                  usable_area_m2: scanned?.usable_area_m2 ?? roof.usable_area_m2,
                  tilt_deg: scanned?.tilt_deg ?? roof.tilt_deg,
                  orientation: scanned?.orientation ?? roof.orientation,
                  specific_yield_kwh_per_kwp: result.specific_yield_kwh_per_kwp,
                },
              },
            },
          };
        }),
      reset: () =>
        set({
          draft: initial,
          step: 0,
          submitting: false,
          submittedId: undefined,
          enrichment: undefined,
          enrichedPostcode: undefined,
        }),
      getCompleted: () => {
        const d = get().draft;
        if (
          !d.location?.postcode ||
          !d.location?.country ||
          !d.household?.occupants ||
          !d.household?.electricity?.annual_kwh ||
          !d.heating?.fuel_type ||
          !d.heating?.building?.floor_area_m2 ||
          d.mobility?.vehicle_count === undefined ||
          !d.upgrade_candidates ||
          !d.financing?.loan_term_years ||
          !d.forecast_horizon?.short_term_months
        )
          return null;
        return d as HouseholdAssessment;
      },
    }),
    {
      name: "maxergy-assessment-storage",
      storage: zustandStorage,
      // v2: engine defaults, supported fuels/vehicle types only. Older drafts restart.
      version: 2,
      migrate: () => ({ draft: initial, step: 0 }),
      partialize: (state) => ({
        draft: state.draft,
        step: state.step,
        enrichment: state.enrichment,
        enrichedPostcode: state.enrichedPostcode,
      }),
    },
  ),
);
