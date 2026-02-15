import { create } from "zustand";
import type { Filters } from "../types/index";

interface FilterStore extends Filters {
  setStage: (stage: string | null) => void;
  setState: (state: string | null) => void;
  setLineOfTherapy: (line: number | null) => void;
  setInsuranceType: (type: string | null) => void;
  resetAll: () => void;
}

const initialState: Filters = {
  stage: null,
  state: null,
  lineOfTherapy: null,
  insuranceType: null,
};

export const useFilterStore = create<FilterStore>((set) => ({
  ...initialState,
  setStage: (stage) => set({ stage }),
  setState: (state) => set({ state }),
  setLineOfTherapy: (lineOfTherapy) => set({ lineOfTherapy }),
  setInsuranceType: (insuranceType) => set({ insuranceType }),
  resetAll: () => set(initialState),
}));
