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
import { CalendarDays } from "lucide-react";

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div className="bg-[#127690] text-white px-3 py-2 rounded-xl shadow-xl">
        <p className="text-sm font-semibold">{payload[0].value} Orders</p>
        <p className="text-xs opacity-80">{label}</p>
      </div>
    );
  }
  return null;
};

const DailyOrderVolume = ({ data = [] }) => {

  const chartData = data.map((item) => ({
    date: item.display_date,
    orders: item.orders,
  }));

  return (
    <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-5">

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-[#127690]/10 flex items-center justify-center">
            <CalendarDays size={18} className="text-[#127690]" />
          </div>

          <div>
            <h2 className="text-[15px] font-semibold text-gray-800">
              Daily Order Volume
            </h2>

            <p className="text-xs text-gray-400">
              Orders placed daily
            </p>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="h-[260px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{
              top: 10,
              right: 5,
              left: 0,
              bottom: 0,
            }}
          >
            {/* Gradient */}
            <defs>
              <linearGradient id="ordersGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#127690" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#127690" stopOpacity={0} />
              </linearGradient>
            </defs>

            {/* Grid */}
            <CartesianGrid
              vertical={false}
              stroke="#f1f5f9"
              strokeDasharray="3 3"
            />

            {/* X Axis */}
            <XAxis
              dataKey="date"
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
              minTickGap={30}
            />

            {/* Y Axis */}
            <YAxis
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={35}
              allowDecimals={false}
            />

            {/* Tooltip */}
            <Tooltip
              cursor={{
                stroke: "#127690",
                strokeDasharray: "4 4",
              }}
              content={<CustomTooltip />}
            />

            {/* Area */}
            <Area
              type="monotone"
              dataKey="orders"
              stroke="#127690"
              strokeWidth={3}
              fill="url(#ordersGradient)"
              dot={false}
              activeDot={{
                r: 5,
                strokeWidth: 0,
                fill: "#127690",
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default DailyOrderVolume;