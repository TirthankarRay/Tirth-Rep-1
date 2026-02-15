import React from "react";
import KPICard from "./KPICard";
import { OverviewMetrics } from "../types/index";

interface KPICardRowProps {
  metrics: OverviewMetrics | null;
  loading: boolean;
}

const KPICardRow: React.FC<KPICardRowProps> = ({ metrics, loading }) => {
  const cards = [
    {
      title: "Total Patients",
      value: metrics?.total_patients?.toLocaleString() ?? "--",
      subtitle: "All-time registered patients",
      trend: "neutral" as const,
      color: "blue",
    },
    {
      title: "New Diagnoses (YTD)",
      value: metrics?.new_diagnoses_ytd?.toLocaleString() ?? "--",
      subtitle: "Year-to-date new cases",
      trend: "up" as const,
      color: "indigo",
    },
    {
      title: "Time to Treatment",
      value: metrics?.median_time_to_treatment_days != null ? `${metrics.median_time_to_treatment_days}d` : "--",
      subtitle: "Median days to first treatment",
      trend: metrics?.median_time_to_treatment_days != null && metrics.median_time_to_treatment_days <= 21 ? "down" as const : "up" as const,
      color: "amber",
    },
    {
      title: "Biomarker Testing Rate",
      value: metrics?.biomarker_testing_rate != null ? `${(metrics.biomarker_testing_rate * 100).toFixed(1)}%` : "--",
      subtitle: "Patients with biomarker tests",
      trend: "up" as const,
      color: "green",
    },
    {
      title: "IO Uptake Rate",
      value: metrics?.immunotherapy_uptake_rate != null ? `${(metrics.immunotherapy_uptake_rate * 100).toFixed(1)}%` : "--",
      subtitle: "Immunotherapy adoption",
      trend: "up" as const,
      color: "purple",
    },
    {
      title: "Trial Enrollment",
      value: metrics?.clinical_trial_enrollment_rate != null ? `${(metrics.clinical_trial_enrollment_rate * 100).toFixed(1)}%` : "--",
      subtitle: "Clinical trial participation",
      trend: "neutral" as const,
      color: "teal",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
      {cards.map((card) => (
        <KPICard
          key={card.title}
          title={card.title}
          value={card.value}
          subtitle={card.subtitle}
          trend={card.trend}
          color={card.color}
          loading={loading}
        />
      ))}
    </div>
  );
};

export default KPICardRow;
