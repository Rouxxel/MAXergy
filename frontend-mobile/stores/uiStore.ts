import { create } from "zustand";

interface UiState {
  globalError?: string;
  setError: (msg?: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  setError: (globalError) => set({ globalError }),
}));