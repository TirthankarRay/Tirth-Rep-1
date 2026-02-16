import React, { useMemo } from "react";
import type {
  OverviewMetrics,
  TimeToTreatmentResponse,
  TreatmentPatternsResponse,
  GeographicResponse,
} from "../types/index";

interface InsightsSectionProps {
  metrics: OverviewMetrics | null;
  tttData: TimeToTreatmentResponse | null;
  txPatterns: TreatmentPatternsResponse | null;
  geoData: GeographicResponse | null;
}

interface Insight {
  category: "positive" | "caution" | "action" | "info";
  title: string;
  detail: string;
}

const CATEGORY_STYLES: Record<
  Insight["category"],
  { bg: string; border: string; icon: string; iconColor: string; label: string }
> = {
  positive: {
    bg: "bg-green-50",
    border: "border-green-200",
    icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    iconColor: "text-green-600",
    label: "Strength",
  },
  caution: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    icon: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z",
    iconColor: "text-amber-600",
    label: "Needs Attention",
  },
  action: {
    bg: "bg-red-50",
    border: "border-red-200",
    icon: "M12 9v3.75m0-10.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z",
    iconColor: "text-red-600",
    label: "Action Required",
  },
  info: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    icon: "M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z",
    iconColor: "text-blue-600",
    label: "Observation",
  },
};

function deriveInsights(
  metrics: OverviewMetrics | null,
  tttData: TimeToTreatmentResponse | null,
  txPatterns: TreatmentPatternsResponse | null,
  geoData: GeographicResponse | null
): Insight[] {
  const insights: Insight[] = [];

  // --- Treatment Timeliness ---
  if (tttData) {
    if (tttData.within_target_rate >= 75) {
      insights.push({
        category: "positive",
        title: "Strong treatment timeliness",
        detail: `${tttData.within_target_rate.toFixed(0)}% of patients begin treatment within the ${tttData.target_days}-day target window. This exceeds the 75% benchmark and indicates efficient care coordination.`,
      });
    } else if (tttData.within_target_rate >= 60) {
      insights.push({
        category: "caution",
        title: "Treatment timeliness approaching target",
        detail: `${tttData.within_target_rate.toFixed(0)}% of patients start treatment within ${tttData.target_days} days. While a majority meet the target, ${(100 - tttData.within_target_rate).toFixed(0)}% experience delays that may impact outcomes. Investigate referral bottlenecks and scheduling capacity.`,
      });
    } else {
      insights.push({
        category: "action",
        title: "Significant treatment delays detected",
        detail: `Only ${tttData.within_target_rate.toFixed(0)}% of patients begin treatment within ${tttData.target_days} days. A median of ${tttData.median_days} days to first treatment suggests systemic delays in the care pathway that require immediate review.`,
      });
    }

    const latePatients = tttData.distribution.find((d) => d.bucket === "31+");
    if (latePatients && latePatients.percentage >= 10) {
      insights.push({
        category: "caution",
        title: `${latePatients.percentage.toFixed(0)}% of patients wait 31+ days for treatment`,
        detail: `${latePatients.count} patients experienced treatment initiation beyond 31 days. For SCLC — an aggressive malignancy — prolonged delays can lead to disease progression and reduced therapeutic efficacy. Consider fast-track pathways for high-risk cases.`,
      });
    }
  }

  // --- Immunotherapy Adoption ---
  if (metrics) {
    if (metrics.immunotherapy_uptake_rate >= 60) {
      insights.push({
        category: "positive",
        title: "High immunotherapy adoption",
        detail: `IO uptake at ${metrics.immunotherapy_uptake_rate.toFixed(1)}% reflects strong alignment with NCCN guidelines recommending chemo-immunotherapy combinations as first-line standard of care for ES-SCLC.`,
      });
    } else if (metrics.immunotherapy_uptake_rate >= 40) {
      insights.push({
        category: "caution",
        title: "Immunotherapy uptake below expectations",
        detail: `At ${metrics.immunotherapy_uptake_rate.toFixed(1)}%, IO uptake falls short of the guideline-concordant benchmark. Barriers may include insurance coverage gaps, lack of PD-L1 testing follow-through, or provider awareness. Targeted education may improve adoption.`,
      });
    } else {
      insights.push({
        category: "action",
        title: "Low immunotherapy utilization",
        detail: `Only ${metrics.immunotherapy_uptake_rate.toFixed(1)}% of patients are receiving immunotherapy. Given the established survival benefit of atezolizumab and durvalumab in ES-SCLC, this represents a significant care gap requiring intervention.`,
      });
    }
  }

  // --- Biomarker Testing ---
  if (metrics) {
    if (metrics.biomarker_testing_rate >= 80) {
      insights.push({
        category: "positive",
        title: "Robust biomarker testing coverage",
        detail: `${metrics.biomarker_testing_rate.toFixed(1)}% of patients receive biomarker testing, supporting personalized treatment decisions and clinical trial eligibility screening.`,
      });
    } else if (metrics.biomarker_testing_rate >= 65) {
      insights.push({
        category: "info",
        title: "Biomarker testing rate has room for improvement",
        detail: `At ${metrics.biomarker_testing_rate.toFixed(1)}%, approximately ${(100 - metrics.biomarker_testing_rate).toFixed(0)}% of patients lack biomarker data. Reflex testing protocols at diagnosis could close this gap and improve trial enrollment.`,
      });
    } else {
      insights.push({
        category: "action",
        title: "Low biomarker testing rate",
        detail: `Only ${metrics.biomarker_testing_rate.toFixed(1)}% of patients are biomarker-tested. This limits treatment personalization and clinical trial eligibility. Consider implementing standing order sets for PD-L1, TMB, and Ki-67 at diagnosis.`,
      });
    }
  }

  // --- Clinical Trial Enrollment ---
  if (metrics) {
    if (metrics.clinical_trial_enrollment_rate >= 15) {
      insights.push({
        category: "positive",
        title: "Strong clinical trial participation",
        detail: `Trial enrollment at ${metrics.clinical_trial_enrollment_rate.toFixed(1)}% exceeds the national average (~8%). This suggests effective screening and patient engagement strategies.`,
      });
    } else if (metrics.clinical_trial_enrollment_rate >= 8) {
      insights.push({
        category: "info",
        title: "Clinical trial enrollment near national average",
        detail: `At ${metrics.clinical_trial_enrollment_rate.toFixed(1)}%, trial enrollment is near the ~8% national benchmark. Expanding partnerships with academic centers and leveraging biomarker data for eligibility matching could boost participation.`,
      });
    } else {
      insights.push({
        category: "caution",
        title: "Clinical trial enrollment below national average",
        detail: `Trial enrollment at ${metrics.clinical_trial_enrollment_rate.toFixed(1)}% falls below the ~8% national average. Potential barriers include geographic access, awareness, and eligibility screening workflows.`,
      });
    }
  }

  // --- Treatment Patterns ---
  if (txPatterns) {
    const ioRegimens = txPatterns.first_line.filter((r) =>
      r.regimen_category.includes("Atezolizumab") ||
      r.regimen_category.includes("Durvalumab")
    );
    const ioPct = ioRegimens.reduce((sum, r) => sum + r.percentage, 0);
    const chemoOnlyRegimen = txPatterns.first_line.find(
      (r) => r.regimen_category === "Platinum + Etoposide"
    );

    if (chemoOnlyRegimen && chemoOnlyRegimen.percentage > 25) {
      insights.push({
        category: "caution",
        title: `${chemoOnlyRegimen.percentage.toFixed(0)}% on chemo-only first-line`,
        detail: `${chemoOnlyRegimen.count} patients receive platinum/etoposide without immunotherapy. While appropriate for select cases (e.g., autoimmune conditions, poor performance status), this rate warrants review against guideline recommendations for IO-eligible patients.`,
      });
    }

    if (ioPct > 0) {
      insights.push({
        category: "info",
        title: "Chemo-IO dominates first-line regimens",
        detail: `${ioPct.toFixed(0)}% of first-line treatments include checkpoint inhibitors (atezolizumab or durvalumab). This pattern reflects current evidence from IMpower133 and CASPIAN trials establishing chemo-IO as standard of care.`,
      });
    }

    if (txPatterns.second_line.length > 0) {
      const topSecondLine = txPatterns.second_line[0];
      insights.push({
        category: "info",
        title: `${topSecondLine.regimen_category} leads second-line therapy`,
        detail: `${topSecondLine.regimen_category} accounts for ${topSecondLine.percentage.toFixed(0)}% of second-line treatments (${topSecondLine.count} patients). Lurbinectedin adoption at ${txPatterns.second_line.find((r) => r.regimen_category === "Lurbinectedin")?.percentage.toFixed(0) ?? "N/A"}% reflects growing use of this newer agent approved in 2020.`,
      });
    }
  }

  // --- Geographic Variations ---
  if (geoData && geoData.states.length > 0) {
    const statesWithTTT = geoData.states.filter(
      (s) => s.median_time_to_treatment != null
    );
    if (statesWithTTT.length > 1) {
      const sorted = [...statesWithTTT].sort(
        (a, b) => a.median_time_to_treatment! - b.median_time_to_treatment!
      );
      const fastest = sorted[0];
      const slowest = sorted[sorted.length - 1];
      const gap = slowest.median_time_to_treatment! - fastest.median_time_to_treatment!;

      if (gap > 5) {
        insights.push({
          category: "caution",
          title: "Geographic disparity in treatment timeliness",
          detail: `Median time to treatment ranges from ${fastest.median_time_to_treatment!.toFixed(1)} days (${fastest.state}) to ${slowest.median_time_to_treatment!.toFixed(1)} days (${slowest.state}) — a ${gap.toFixed(1)}-day gap. States with longer delays may benefit from telemedicine, regional cancer center partnerships, or navigation programs.`,
        });
      }
    }

    const lowBioStates = geoData.states.filter(
      (s) => s.biomarker_testing_rate != null && s.biomarker_testing_rate < 70
    );
    if (lowBioStates.length >= 5) {
      insights.push({
        category: "info",
        title: `${lowBioStates.length} states below 70% biomarker testing`,
        detail: `States including ${lowBioStates
          .slice(0, 4)
          .map((s) => s.state)
          .join(", ")} have biomarker testing rates under 70%. Targeted quality improvement initiatives in these regions could improve both testing rates and downstream treatment decisions.`,
      });
    }
  }

  return insights;
}

const InsightsSection: React.FC<InsightsSectionProps> = ({
  metrics,
  tttData,
  txPatterns,
  geoData,
}) => {
  const insights = useMemo(
    () => deriveInsights(metrics, tttData, txPatterns, geoData),
    [metrics, tttData, txPatterns, geoData]
  );

  if (insights.length === 0) return null;

  const grouped = {
    action: insights.filter((i) => i.category === "action"),
    caution: insights.filter((i) => i.category === "caution"),
    positive: insights.filter((i) => i.category === "positive"),
    info: insights.filter((i) => i.category === "info"),
  };

  const ordered = [
    ...grouped.action,
    ...grouped.caution,
    ...grouped.positive,
    ...grouped.info,
  ];

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">
            Insights & Interpretation
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Auto-generated clinical quality signals derived from current dashboard data
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
            Action
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />
            Caution
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
            Strength
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />
            Info
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {ordered.map((insight, idx) => {
          const style = CATEGORY_STYLES[insight.category];
          return (
            <div
              key={idx}
              className={`${style.bg} ${style.border} border rounded-lg p-4 flex gap-3`}
            >
              <div className="flex-shrink-0 mt-0.5">
                <svg
                  className={`h-5 w-5 ${style.iconColor}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d={style.icon}
                  />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${style.bg} ${style.iconColor} border ${style.border}`}
                  >
                    {style.label}
                  </span>
                  <h4 className="text-sm font-semibold text-gray-800">
                    {insight.title}
                  </h4>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {insight.detail}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-5 pt-4 border-t border-gray-100">
        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span>
            {ordered.length} insight{ordered.length !== 1 && "s"} generated
          </span>
          <span>|</span>
          <span>
            {grouped.action.length} action{grouped.action.length !== 1 && "s"} required
          </span>
          <span>|</span>
          <span>
            {grouped.positive.length} strength{grouped.positive.length !== 1 && "s"} identified
          </span>
        </div>
      </div>
    </div>
  );
};

export default InsightsSection;
