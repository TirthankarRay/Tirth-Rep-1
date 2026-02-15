import React from "react";
import { GeographicResponse } from "../types/index";

interface GeographicHeatMapProps {
  data: GeographicResponse;
}

const GeographicHeatMap: React.FC<GeographicHeatMapProps> = ({ data }) => {
  const sorted = [...data.states]
    .sort((a, b) => b.patient_count - a.patient_count)
    .slice(0, 15);

  const maxCount = sorted.length > 0 ? sorted[0].patient_count : 1;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        Geographic Distribution (Top 15 States)
      </h3>

      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-2 pr-4 w-16">
                Rank
              </th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-2 pr-4 w-20">
                State
              </th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-2 pr-4 w-24">
                Patients
              </th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-2">
                Distribution
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sorted.map((stateMetric, index) => {
              const widthPercent = (stateMetric.patient_count / maxCount) * 100;
              return (
                <tr key={stateMetric.state} className="hover:bg-gray-50">
                  <td className="py-2 pr-4 text-sm text-gray-500">
                    {index + 1}
                  </td>
                  <td className="py-2 pr-4 text-sm font-medium text-gray-800">
                    {stateMetric.state}
                  </td>
                  <td className="py-2 pr-4 text-sm text-gray-600">
                    {stateMetric.patient_count.toLocaleString()}
                  </td>
                  <td className="py-2">
                    <div className="flex items-center">
                      <div className="w-full bg-gray-100 rounded-full h-3">
                        <div
                          className="bg-blue-500 h-3 rounded-full transition-all duration-300"
                          style={{ width: `${widthPercent}%` }}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {sorted.length === 0 && (
          <p className="text-center text-gray-400 py-8 text-sm">
            No geographic data available
          </p>
        )}
      </div>
    </div>
  );
};

export default GeographicHeatMap;
