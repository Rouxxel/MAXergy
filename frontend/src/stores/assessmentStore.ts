import { create } from "zustand";
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
  country: "DE",
  financingTermMonths: 84,
  heatingType: "gas",
  heatingSpendType: "gas",
  heatingSpendSeason: "annual",
  hasFeedInTariff: false,
  vehicleOwnership: false,
};

export const useAssessmentStore = create<AssessmentState>((set, get) => ({
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
      !d.country ||
      !d.postalCode ||
      d.monthlyElectricitySpend === undefined ||
      !d.heatingType ||
      d.heatingSpend === undefined ||
      d.vehicleOwnership === undefined ||
      d.roofSize === undefined ||
      !d.financingTermMonths
    )
      return null;
    return d as HouseholdAssessment;
  },
}));