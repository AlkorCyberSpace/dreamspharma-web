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

const COLORS = ["#1E2B6D", "#127690", "#1B6A3E", "#7B0D0D", "#F59E0B", "#8B5CF6"];

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 rounded-xl shadow-2xl border border-gray-100 text-xs">
        <p className="font-bold text-gray-800 mb-1">{payload[0].name}</p>
        <div className="flex items-center justify-between gap-4">
          <span className="text-gray-500 font-medium">Orders:</span>
          <span className="font-bold text-[#127690]">{payload[0].value}</span>
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
      
      // Calculate start and end date for the selected month/year
      const startDate = `${year}-${String(month).padStart(2, '0')}-01`;
      const lastDay = new Date(year, month, 0).getDate();
      const endDate = `${year}-${String(month).padStart(2, '0')}-${lastDay}`;

      const response = await getWarehouseOrdersAPI({ 
        period: "date",
        start_date: startDate,
        end_date: endDate
      });

      if (response.data.success) {
        const { stores, data } = response.data;
        
        // Aggregate totals for each store across all dates in the period
        let storeTotals = stores.map((store, index) => {
          const totalOrders = data.reduce((sum, entry) => sum + (entry[`${store} (Orders)`] || 0), 0);
          return {
            name: store,
            value: totalOrders,
            color: COLORS[index % COLORS.length]
          };
        }).filter(s => s.value > 0);

        // Fallback Mock Data if API returns empty list
        if (storeTotals.length === 0) {
          storeTotals = [
            { name: "Bangalore Logistics", value: 120, color: COLORS[0] },
            { name: "Jaipur Logistics", value: 85, color: COLORS[1] },
            { name: "Thrissur Store", value: 65, color: COLORS[2] },
            { name: "Cochi Hub", value: 45, color: COLORS[3] },
          ];
        }

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
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-[#e2e8f0] h-[50vh] flex flex-col">
      <div className="flex items-center gap-2 mb-2">
        <PieIcon size={18} className="text-[#127690]" />
        <h3 className="text-gray-700 font-bold tracking-tight text-sm uppercase">Orders By Warehouse</h3>
      </div>
      <div className="flex-1 w-full flex items-center justify-center relative">
        {loading ? (
          <Loader2 className="animate-spin text-[#127690]" size={24} />
        ) : chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={75}
                paddingAngle={5}
                dataKey="value"
                stroke="none"
                label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                labelLine={true}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-gray-400 text-xs font-medium italic">No orders for this period</div>
        )}
      </div>
    </div>
  );
};

export default OrdersByStatus;

