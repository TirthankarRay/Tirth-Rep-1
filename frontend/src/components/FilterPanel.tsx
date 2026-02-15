import React from "react";
import { Filters } from "../types/index";

interface FilterPanelProps {
  filters: Filters;
  onFilterChange: (key: string, value: string | null) => void;
}

const US_STATES = [
  "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
  "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
  "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
  "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
  "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
];

const FilterPanel: React.FC<FilterPanelProps> = ({ filters, onFilterChange }) => {
  const handleChange = (field: keyof Filters, value: string | null) => {
    onFilterChange(field, value);
  };

  const handleReset = () => {
    onFilterChange("stage", null);
    onFilterChange("state", null);
    onFilterChange("insuranceType", null);
  };

  const hasActiveFilters =
    filters.stage != null || filters.state != null || filters.insuranceType != null;

  return (
    <div className="bg-white shadow-sm border rounded-lg px-4 py-3">
      <div className="flex flex-wrap items-center gap-4">
        <span className="text-sm font-medium text-gray-600">Filters:</span>

        <div className="flex items-center space-x-2">
          <label htmlFor="filter-stage" className="text-sm text-gray-500">
            Stage
          </label>
          <select
            id="filter-stage"
            value={filters.stage || ""}
            onChange={(e) =>
              handleChange("stage", e.target.value || null)
            }
            className="block rounded-md border-gray-300 shadow-sm text-sm focus:border-blue-500 focus:ring-blue-500 py-1.5 pl-3 pr-8"
          >
            <option value="">All</option>
            <option value="LS-SCLC">LS-SCLC</option>
            <option value="ES-SCLC">ES-SCLC</option>
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <label htmlFor="filter-state" className="text-sm text-gray-500">
            State
          </label>
          <select
            id="filter-state"
            value={filters.state || ""}
            onChange={(e) =>
              handleChange("state", e.target.value || null)
            }
            className="block rounded-md border-gray-300 shadow-sm text-sm focus:border-blue-500 focus:ring-blue-500 py-1.5 pl-3 pr-8"
          >
            <option value="">All</option>
            {US_STATES.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <label htmlFor="filter-insurance" className="text-sm text-gray-500">
            Insurance
          </label>
          <select
            id="filter-insurance"
            value={filters.insuranceType || ""}
            onChange={(e) =>
              handleChange("insuranceType", e.target.value || null)
            }
            className="block rounded-md border-gray-300 shadow-sm text-sm focus:border-blue-500 focus:ring-blue-500 py-1.5 pl-3 pr-8"
          >
            <option value="">All</option>
            <option value="Medicare">Medicare</option>
            <option value="Commercial">Commercial</option>
            <option value="Medicaid">Medicaid</option>
            <option value="Uninsured">Uninsured</option>
          </select>
        </div>

        {hasActiveFilters && (
          <button
            onClick={handleReset}
            className="ml-auto inline-flex items-center px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors"
          >
            <svg
              className="h-3.5 w-3.5 mr-1"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Reset All
          </button>
        )}
      </div>
    </div>
  );
};

export default FilterPanel;
