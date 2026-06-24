import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ForecastResult, Recommendation, Scenario } from "@/types";
import { zustandStorage } from "@/lib/storage";

interface ResultsState {
  forecast?: ForecastResult;
  recommendation?: Recommendation;
  selectedScenarioId?: string;
  setForecast: (f: ForecastResult) => void;
  setRecommendation: (r: Recommendation) => void;
  selectScenario: (id: string) => void;
  getSelected: () => Scenario | undefined;
  reset: () => void;
}

type PersistedResultsState = Pick<ResultsState, "forecast" | "recommendation" | "selectedScenarioId">;

export const useResultsStore = create<ResultsState>()(
  persist(
    (set, get) => ({
      setForecast: (forecast) => set({ forecast }),
      setRecommendation: (recommendation) =>
        set({ recommendation, selectedScenarioId: recommendation.selected_scenario.id }),
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
      partialize: (state): PersistedResultsState => ({
        forecast: state.forecast,
        recommendation: state.recommendation,
        selectedScenarioId: state.selectedScenarioId,
      }),
    },
  ),
);