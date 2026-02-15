import { useState } from "react";
import KPICardRow from "../components/KPICardRow";
import TimeToTreatmentChart from "../components/TimeToTreatmentChart";
import TreatmentPatternsChart from "../components/TreatmentPatternsChart";
import GeographicHeatMap from "../components/GeographicHeatMap";
import PatientTable from "../components/PatientTable";
import FilterPanel from "../components/FilterPanel";
import {
  useOverviewMetrics,
  useTimeToTreatment,
  useTreatmentPatterns,
  useGeographicData,
  usePatients,
} from "../hooks/useDashboardData";
import { useFilterStore } from "../store/useFilterStore";

export default function Dashboard() {
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const filters = useFilterStore();

  const { data: metrics, isLoading: metricsLoading } = useOverviewMetrics();
  const { data: tttData } = useTimeToTreatment();
  const { data: txPatterns } = useTreatmentPatterns();
  const { data: geoData } = useGeographicData();
  const { data: patientData } = usePatients(page, pageSize);

  return (
    <div className="space-y-6">
      <FilterPanel
        filters={filters}
        onFilterChange={(key, value) => {
          if (key === "stage") filters.setStage(value);
          else if (key === "state") filters.setState(value);
          else if (key === "insuranceType") filters.setInsuranceType(value);
        }}
      />

      <KPICardRow metrics={metrics ?? null} loading={metricsLoading} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {tttData && <TimeToTreatmentChart data={tttData} />}
        {txPatterns && <TreatmentPatternsChart data={txPatterns} />}
      </div>

      {geoData && <GeographicHeatMap data={geoData} />}

      {patientData && (
        <PatientTable
          patients={patientData.items}
          total={patientData.total}
          page={patientData.page}
          pageSize={patientData.page_size}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
