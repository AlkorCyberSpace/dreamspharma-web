import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { PieChart as PieIcon } from "lucide-react";

const data = [
  { name: "Confirmed", value: 30, color: "#1E2B6D" },
  { name: "Dispatched", value: 15, color: "#127690" },
  { name: "Delivered", value: 20, color: "#1B6A3E" },
  { name: "Pending", value: 35, color: "#7B0D0D" },
];

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-2 rounded shadow-lg border border-gray-100 text-xs">
        <p className="font-semibold text-gray-700">{`${payload[0].name}: ${payload[0].value}%`}</p>
      </div>
    );
  }
  return null;
};

const OrdersByStatus = () => {
  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-[#e2e8f0] h-53.75 flex flex-col">
      <div className="flex items-center gap-2 mb-2">
        <PieIcon size={18} className="text-gray-500" />
        <h3 className="text-gray-600 font-medium">Orders By Status</h3>
      </div>
      <div className="flex-1 w-full flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={45}
              outerRadius={65}
              paddingAngle={5}
              dataKey="value"
              stroke="none"
              label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
              labelLine={false}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default OrdersByStatus;
