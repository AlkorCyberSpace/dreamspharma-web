import React, { useEffect, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { PieChart as PieIcon, Loader2 } from "lucide-react";
import { getWarehouseOrdersAPI } from "../../services/allAPI";

const COLORS = [
  "#1E2B6D",
  "#127690",
  "#1B6A3E",
  "#7B0D0D",
  "#F59E0B",
  "#8B5CF6",
];

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 rounded-xl shadow-2xl border border-gray-100 text-xs">
        <p className="font-bold text-gray-800 mb-1">
          {payload[0].name}
        </p>

        <div className="flex items-center justify-between gap-4">
          <span className="text-gray-500 font-medium">
            Orders:
          </span>

          <span className="font-bold text-[#127690]">
            {payload[0].value}
          </span>
        </div>
      </div>
    );
  }

  return null;
};

const OrdersByStatus = ({ selectedMonth, selectedYear }) => {
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchWarehouseData = async (month, year) => {
    try {
      setLoading(true);

      const startDate = `${year}-${String(month).padStart(2, "0")}-01`;

      const lastDay = new Date(year, month, 0).getDate();

      const endDate = `${year}-${String(month).padStart(
        2,
        "0"
      )}-${lastDay}`;

      const response = await getWarehouseOrdersAPI({
        period: "date",
        start_date: startDate,
        end_date: endDate,
      });

      if (response.data.success) {
        const { stores, data } = response.data;

        const storeTotals = stores
          .map((store, index) => {
            const totalOrders = data.reduce(
              (sum, entry) =>
                sum + (entry[`${store} (Orders)`] || 0),
              0
            );

            return {
              name: store,
              value: totalOrders,
              color: COLORS[index % COLORS.length],
            };
          })
          .filter((s) => s.value > 0);

        setChartData(storeTotals);
      }
    } catch (error) {
      console.error("Error fetching warehouse orders:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWarehouseData(selectedMonth, selectedYear);
  }, [selectedMonth, selectedYear]);

  return (
    <div className="bg-white p-6 rounded-3xl shadow-sm border border-[#e2e8f0] h-[50vh] flex flex-col">

      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-[#127690]/10 flex items-center justify-center">
          <PieIcon size={18} className="text-[#127690]" />
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-800">
            Orders By Warehouse
          </h3>

          <p className="text-xs text-gray-400">
            Warehouse order distribution
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 relative">

        {loading ? (
          <div className="w-full h-full flex items-center justify-center">
            <Loader2
              className="animate-spin text-[#127690]"
              size={28}
            />
          </div>
        ) : chartData.length > 0 ? (

          <ResponsiveContainer width="100%" height="100%">
            <PieChart>

              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={65}
                outerRadius={90}
                paddingAngle={4}
                dataKey="value"
                stroke="none"
                label={({ percent }) =>
                  `${(percent * 100).toFixed(0)}%`
                }
                labelLine={false}
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.color}
                  />
                ))}
              </Pie>

              <Tooltip content={<CustomTooltip />} />

            </PieChart>
          </ResponsiveContainer>

        ) : (

          <div className="relative w-full h-full flex items-center justify-center">

            {/* Placeholder Donut */}
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={[{ value: 1 }]}
                  dataKey="value"
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={90}
                  fill="#eef2f7"
                  stroke="none"
                />
              </PieChart>
            </ResponsiveContainer>

            {/* Empty State */}
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">

              <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mb-4">
                <PieIcon
                  size={24}
                  className="text-gray-400"
                />
              </div>

              <h3 className="text-sm font-semibold text-gray-700">
                No Orders Found
              </h3>

              <p className="text-xs text-gray-400 mt-1 max-w-[220px] leading-relaxed">
                No warehouse order activity found for the selected timeframe.
              </p>

            </div>

          </div>
        )}
      </div>
    </div>
  );
};

export default OrdersByStatus;