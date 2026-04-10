import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Calendar } from "lucide-react";

const data = [
  { name: "Feb 1", orders: 10 },
  { name: "Feb 2", orders: 35 },
  { name: "Feb 3", orders: 60 },
  { name: "Feb 4", orders: 58 },
  { name: "Feb 5", orders: 85 },
  { name: "Feb 6", orders: 110 },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#127690] text-white p-3 rounded-lg shadow-xl border-none">
        <p className="text-sm font-semibold">{`Orders: ${payload[0].value}`}</p>
        <p className="text-xs opacity-80">{label}</p>
      </div>
    );
  }
  return null;
};

const DailyOrderVolume = ({ data }) => {
  const chartData = data && data.length > 0 ? data : [];

  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-[#e2e8f0]">
      <div className="flex items-center gap-2 mb-6">
        <Calendar size={18} className="text-gray-500" />
        <h3 className="text-gray-600 font-medium">Daily Order Volume</h3>
      </div>

      {/* ✅ FIXED HEIGHT */}
      <div className="w-full h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorOrders" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#127690" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#127690" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />

            <XAxis
              dataKey="date"  
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              dy={10}
            />

            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#94a3b8", fontSize: 12 }}
            />

            <Tooltip content={<CustomTooltip />} />

            <Area
              type="monotone"
              dataKey="orders"
              stroke="#127690"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorOrders)"
              activeDot={{ r: 6 }}
              dot={{ r: 4 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default DailyOrderVolume;
