import React from "react";

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle: string;
  trend: "up" | "down" | "neutral";
  color: string;
  loading: boolean;
}

const trendIcons: Record<KPICardProps["trend"], React.ReactNode> = {
  up: (
    <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 19.5l15-15m0 0H8.25m11.25 0v11.25" />
    </svg>
  ),
  down: (
    <svg className="h-4 w-4 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 4.5l15 15m0 0V8.25m0 11.25H8.25" />
    </svg>
  ),
  neutral: (
    <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
    </svg>
  ),
};

const borderColorMap: Record<string, string> = {
  blue: "border-l-blue-500",
  indigo: "border-l-indigo-500",
  amber: "border-l-amber-500",
  green: "border-l-green-500",
  purple: "border-l-purple-500",
  teal: "border-l-teal-500",
};

const KPICard: React.FC<KPICardProps> = ({ title, value, subtitle, trend, color, loading }) => {
  const borderClass = borderColorMap[color] || "border-l-blue-500";

  if (loading) {
    return (
      <div className={`bg-white rounded-lg shadow p-5 border-l-4 ${borderClass} animate-pulse`}>
        <div className="h-3 bg-gray-200 rounded w-3/4 mb-3" />
        <div className="h-8 bg-gray-200 rounded w-1/2 mb-2" />
        <div className="h-3 bg-gray-200 rounded w-2/3" />
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow p-5 border-l-4 ${borderClass}`}>
      <p className="text-sm font-medium text-gray-500 truncate">{title}</p>
      <div className="mt-2 flex items-baseline space-x-2">
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <span>{trendIcons[trend]}</span>
      </div>
      <p className="mt-1 text-xs text-gray-400">{subtitle}</p>
    </div>
  );
};

export default KPICard;
