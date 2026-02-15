import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { TimeToTreatmentResponse } from "../types/index";

interface TimeToTreatmentChartProps {
  data: TimeToTreatmentResponse;
}

const bucketIsWithinTarget = (bucket: string): boolean => {
  const match = bucket.match(/^(\d+)/);
  if (!match) return false;
  const startDay = parseInt(match[1], 10);
  return startDay < 21;
};

const TimeToTreatmentChart: React.FC<TimeToTreatmentChartProps> = ({ data }) => {
  const chartData = data.distribution.map((item) => ({
    ...item,
    withinTarget: bucketIsWithinTarget(item.bucket),
  }));

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        Time to Treatment Analysis
      </h3>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="bucket"
            tick={{ fontSize: 12, fill: "#6B7280" }}
            axisLine={{ stroke: "#D1D5DB" }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "#6B7280" }}
            axisLine={{ stroke: "#D1D5DB" }}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === "count") return [value, "Patients"];
              return [value, name];
            }}
            contentStyle={{
              backgroundColor: "#fff",
              border: "1px solid #E5E7EB",
              borderRadius: "6px",
              fontSize: "13px",
            }}
          />
          <ReferenceLine
            x={null}
            y={null}
            label={{
              value: "21-day target",
              position: "top",
              fill: "#EF4444",
              fontSize: 12,
            }}
            stroke="#EF4444"
            strokeDasharray="5 5"
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.withinTarget ? "#22C55E" : entry.bucket.startsWith("28") || entry.bucket.includes("30") || entry.bucket.includes(">") ? "#EF4444" : "#F97316"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-3 gap-4 border-t pt-4">
        <div className="text-center">
          <p className="text-sm text-gray-500">Median</p>
          <p className="text-xl font-bold text-gray-800">
            {data.median_days != null ? `${data.median_days} days` : "--"}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-500">Mean</p>
          <p className="text-xl font-bold text-gray-800">
            {data.mean_days != null ? `${data.mean_days.toFixed(1)} days` : "--"}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-500">{"Within Target (\u226421d)"}</p>
          <p className="text-xl font-bold text-green-600">
            {data.within_target_rate.toFixed(1)}%
          </p>
        </div>
      </div>
    </div>
  );
};

export default TimeToTreatmentChart;
