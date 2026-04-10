import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { TrendingUp } from "lucide-react";

const data = [
  { name: "Oct", refunds: 40 },
  { name: "Nov", refunds: 45 },
  { name: "Dec", refunds: 65 },
  { name: "Jan", refunds: 50 },
  { name: "Feb", refunds: 55 },
  { name: "Mar", refunds: 75 },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#127690] text-white p-3 rounded-lg shadow-xl border-none">
        <p className="text-sm font-semibold">{`Refunds: ${payload[0].value}`}</p>
        <p className="text-xs opacity-80">{label}</p>
      </div>
    );
  }
  return null;
};

const RefundTrends = () => {
  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-[#e2e8f0] h-53.75 flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp size={18} className="text-gray-500" />
        <h3 className="text-gray-600 font-medium">Refund Trends</h3>
      </div>
      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -30, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#94a3b8", fontSize: 10 }}
              dy={5}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#94a3b8", fontSize: 10 }}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f1f5f9" }} />
            <Bar dataKey="refunds" fill="#0ea5e9" radius={[4, 4, 0, 0]} barSize={25} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default RefundTrends;
