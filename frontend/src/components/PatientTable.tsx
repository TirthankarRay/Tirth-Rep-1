import React, { useState, useMemo } from "react";
import { PatientDetail } from "../types/index";

interface PatientTableProps {
  patients: PatientDetail[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

type SortField =
  | "external_id"
  | "age"
  | "gender"
  | "state"
  | "stage"
  | "treatment"
  | "insurance_type"
  | "days_to_treatment";

type SortDirection = "asc" | "desc";

const calculateAge = (dateOfBirth: string | null): number | null => {
  if (!dateOfBirth) return null;
  const birth = new Date(dateOfBirth);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age;
};

const getStage = (patient: PatientDetail): string => {
  if (patient.diagnoses.length > 0 && patient.diagnoses[0].stage) {
    return patient.diagnoses[0].stage;
  }
  return "--";
};

const getTreatment = (patient: PatientDetail): string => {
  const firstLine = patient.treatment_episodes.find((ep) => ep.line_of_therapy === 1);
  if (firstLine?.regimen_category) return firstLine.regimen_category;
  if (firstLine?.regimen_name) return firstLine.regimen_name;
  if (patient.treatment_episodes.length > 0) {
    const ep = patient.treatment_episodes[0];
    return ep.regimen_category || ep.regimen_name || "--";
  }
  return "--";
};

const getDaysToTreatment = (patient: PatientDetail): number | null => {
  if (patient.diagnoses.length === 0) return null;
  const diagDate = patient.diagnoses[0].diagnosis_date;
  if (!diagDate) return null;

  const firstLine = patient.treatment_episodes.find((ep) => ep.line_of_therapy === 1);
  const treatmentStart = firstLine?.treatment_start_date || patient.treatment_episodes[0]?.treatment_start_date;
  if (!treatmentStart) return null;

  const diag = new Date(diagDate);
  const treat = new Date(treatmentStart);
  const diff = Math.round((treat.getTime() - diag.getTime()) / (1000 * 60 * 60 * 24));
  return diff >= 0 ? diff : null;
};

const PatientTable: React.FC<PatientTableProps> = ({
  patients,
  total,
  page,
  pageSize,
  onPageChange,
}) => {
  const [sortField, setSortField] = useState<SortField>("external_id");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const enrichedPatients = useMemo(
    () =>
      patients.map((p) => ({
        raw: p,
        external_id: p.external_id || p.patient_id,
        age: calculateAge(p.date_of_birth),
        gender: p.gender || "--",
        state: p.state || "--",
        stage: getStage(p),
        treatment: getTreatment(p),
        insurance_type: p.insurance_type || "--",
        days_to_treatment: getDaysToTreatment(p),
      })),
    [patients]
  );

  const sortedPatients = useMemo(() => {
    return [...enrichedPatients].sort((a, b) => {
      const dir = sortDirection === "asc" ? 1 : -1;
      const valA = a[sortField];
      const valB = b[sortField];

      if (valA == null && valB == null) return 0;
      if (valA == null) return 1;
      if (valB == null) return -1;

      if (typeof valA === "number" && typeof valB === "number") {
        return (valA - valB) * dir;
      }

      return String(valA).localeCompare(String(valB)) * dir;
    });
  }, [enrichedPatients, sortField, sortDirection]);

  const totalPages = Math.ceil(total / pageSize);

  const sortIcon = (field: SortField) => {
    if (sortField !== field) {
      return (
        <svg className="inline h-3 w-3 ml-1 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 15L12 18.75 15.75 15m-7.5-6L12 5.25 15.75 9" />
        </svg>
      );
    }
    return sortDirection === "asc" ? (
      <svg className="inline h-3 w-3 ml-1 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
      </svg>
    ) : (
      <svg className="inline h-3 w-3 ml-1 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
      </svg>
    );
  };

  const columns: { label: string; field: SortField }[] = [
    { label: "Patient ID", field: "external_id" },
    { label: "Age", field: "age" },
    { label: "Gender", field: "gender" },
    { label: "State", field: "state" },
    { label: "Stage", field: "stage" },
    { label: "Treatment", field: "treatment" },
    { label: "Insurance", field: "insurance_type" },
    { label: "Days to Treatment", field: "days_to_treatment" },
  ];

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        Patient Details
      </h3>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.field}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700"
                  onClick={() => handleSort(col.field)}
                >
                  {col.label}
                  {sortIcon(col.field)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedPatients.map((p) => (
              <tr key={p.raw.patient_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-blue-600">
                  {p.external_id}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {p.age != null ? p.age : "--"}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {p.gender}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {p.state}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  <span
                    className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      p.stage === "ES-SCLC"
                        ? "bg-red-100 text-red-800"
                        : p.stage === "LS-SCLC"
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {p.stage}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {p.treatment}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {p.insurance_type}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {p.days_to_treatment != null ? p.days_to_treatment : "--"}
                </td>
              </tr>
            ))}
            {sortedPatients.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-400">
                  No patients found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex items-center justify-between border-t pt-4">
        <p className="text-sm text-gray-500">
          Showing {(page - 1) * pageSize + 1}--{Math.min(page * pageSize, total)} of{" "}
          {total.toLocaleString()} patients
        </p>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="px-3 py-1.5 text-sm font-medium rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Prev
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="px-3 py-1.5 text-sm font-medium rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

export default PatientTable;
