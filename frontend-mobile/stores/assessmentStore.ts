import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { HouseholdAssessment } from "@/types";

export type AssessmentDraft = Partial<HouseholdAssessment>;

interface AssessmentState {
  draft: AssessmentDraft;
  step: number;
  submitting: boolean;
  submittedId?: string;
  setField: <K extends keyof HouseholdAssessment>(
    key: K,
    value: HouseholdAssessment[K],
  ) => void;
  setStep: (step: number) => void;
  setSubmitting: (v: boolean) => void;
  setSubmittedId: (id: string) => void;
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
    electricity: {
      annual_kwh: 3000,
      current_tariff_type: "standard",
      arbeitspreis_eur_per_kwh: 0.35,
      grundpreis_eur_per_month: 10,
      contract_end_date: null,
    },
    roof: {
      available: true,
      usable_area_m2: 50,
      orientation: "south",
      tilt_deg: 30,
      shading_factor: 0.1,
    },
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
  upgrade_candidates: {
    solar_pv: true,
    battery: false,
    heat_pump: false,
    ev_charger: false,
    solar_pv_kwp: null,
    battery_kwh: null,
    heat_pump_kw: null,
  },
  financing: {
    loan_term_years: 7,
    loan_rate_pct: 5.5,
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
      setField: (key, value) =>
        set((s) => ({ draft: { ...s.draft, [key]: value } })),
      setStep: (step) => set({ step }),
      setSubmitting: (submitting) => set({ submitting }),
      setSubmittedId: (submittedId) => set({ submittedId }),
      reset: () => set({ draft: initial, step: 0, submitting: false, submittedId: undefined }),
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
      partialize: (state) => ({ draft: state.draft, step: state.step }),
    },
  ),
);