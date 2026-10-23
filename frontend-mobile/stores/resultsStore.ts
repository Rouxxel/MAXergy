import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ForecastResult, PlanResponse, Recommendation, Scenario } from "@/types";
import { zustandStorage } from "@/lib/storage";

interface ResultsState {
  forecast?: ForecastResult;
  recommendation?: Recommendation;
  selectedScenarioId?: string;
  setPlan: (plan: PlanResponse) => void;
  setForecast: (f: ForecastResult) => void;
  setRecommendation: (r: Recommendation) => void;
  selectScenario: (id: string) => void;
  getSelected: () => Scenario | undefined;
  reset: () => void;
}

export const useResultsStore = create<ResultsState>()(
  persist(
    (set, get) => ({
      setPlan: ({ forecast, recommendation }) =>
        set({
          forecast,
          recommendation,
          selectedScenarioId: recommendation.selected_scenario_id ?? undefined,
        }),
      setForecast: (forecast) => set({ forecast }),
      setRecommendation: (recommendation) =>
        set({
          recommendation,
          selectedScenarioId: recommendation.selected_scenario_id ?? undefined,
        }),
      selectScenario: (selectedScenarioId) => set({ selectedScenarioId }),
      getSelected: () => {
        const { forecast, selectedScenarioId } = get();
        return forecast?.scenarios.find((s) => s.id === selectedScenarioId);
      },
      reset: () =>
        set({
          forecast: undefined,
          recommendation: undefined,
          selectedScenarioId: undefined,
        }),
    }),
    {
      name: "maxergy-results-storage",
      storage: zustandStorage,
      // v2 = API contract with nested financing, financials and structured ranking.
      // Results stored by older versions have a different shape and are discarded.
      version: 2,
      migrate: () => ({}),
      partialize: (state) => ({
        forecast: state.forecast,
        recommendation: state.recommendation,
        selectedScenarioId: state.selectedScenarioId,
      }),
    },
  ),
);
