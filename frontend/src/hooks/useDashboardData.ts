import { useQuery } from "@tanstack/react-query";
import {
  fetchOverviewMetrics,
  fetchTimeToTreatment,
  fetchTreatmentPatterns,
  fetchGeographicData,
  fetchPatients,
} from "../services/api";
import { useFilterStore } from "../store/useFilterStore";

export function useOverviewMetrics() {
  const { stage, state } = useFilterStore();
  return useQuery({
    queryKey: ["overview-metrics", stage, state],
    queryFn: () => fetchOverviewMetrics(stage, state),
  });
}

export function useTimeToTreatment() {
  const { stage, state } = useFilterStore();
  return useQuery({
    queryKey: ["time-to-treatment", stage, state],
    queryFn: () => fetchTimeToTreatment(stage, state),
  });
}

export function useTreatmentPatterns() {
  const { stage } = useFilterStore();
  return useQuery({
    queryKey: ["treatment-patterns", stage],
    queryFn: () => fetchTreatmentPatterns(stage),
  });
}

export function useGeographicData() {
  return useQuery({
    queryKey: ["geographic"],
    queryFn: fetchGeographicData,
  });
}

export function usePatients(page: number, pageSize: number) {
  const { stage, state } = useFilterStore();
  return useQuery({
    queryKey: ["patients", page, pageSize, stage, state],
    queryFn: () => fetchPatients(page, pageSize, stage, state),
  });
}
