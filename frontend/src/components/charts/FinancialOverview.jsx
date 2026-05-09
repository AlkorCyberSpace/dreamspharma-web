import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { PieChart as PieChartIcon, Loader2 } from "lucide-react";
import { getStoreAnalyticsAPI } from "../../services/allAPI";

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-4 rounded-xl shadow-2xl border border-gray-100 min-w-[150px]">
        <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">{label}</p>
        <div className="space-y-2">
          {payload.map((entry, index) => (
            <div key={index} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }}></div>
                <span className="text-xs font-medium text-gray-600 capitalize">{entry.name}</span>
              </div>
              <span className="text-sm font-bold text-gray-800">₹{parseFloat(entry.value).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

const FinancialOverview = ({ selectedMonth, selectedYear }) => {
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = async (month, year) => {
    try {
      setLoading(true);
      
      // Calculate start and end date for the selected month/year
      const startDate = `${year}-${String(month).padStart(2, '0')}-01`;
      const lastDay = new Date(year, month, 0).getDate();
      const endDate = `${year}-${String(month).padStart(2, '0')}-${lastDay}`;

      const response = await getStoreAnalyticsAPI({ 
        period: "custom",
        date_from: startDate,
        date_to: endDate
      });

      if (response.data.success) {
        let mappedData = response.data.stores.map(store => ({
          name: store.store_name,
          income: parseFloat(store.gross_income),
          expense: parseFloat(store.discounts_given) + 
                   parseFloat(store.wallet_credits_given) + 
                   parseFloat(store.returns_amount),
          revenue: parseFloat(store.revenue)
        }));

        // Fallback Mock Data if API returns empty list
        if (mappedData.length === 0) {
          mappedData = [
            { name: "Bangalore Logistics", income: 45000, expense: 32000, revenue: 13000 },
            { name: "Jaipur Logistics", income: 52000, expense: 35000, revenue: 17000 },
            { name: "Thrissur Store", income: 68000, expense: 42000, revenue: 26000 },
            { name: "Cochi Hub", income: 61000, expense: 38000, revenue: 23000 },
          ];
        }

        setChartData(mappedData);
      }
    } catch (error) {
      console.error("Error fetching financial analytics:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics(selectedMonth, selectedYear);
  }, [selectedMonth, selectedYear]);

  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-[#e2e8f0] h-[55vh] flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <PieChartIcon size={18} className="text-[#127690]" />
          <h3 className="text-gray-700 font-bold tracking-tight text-sm uppercase">Financial Overview</h3>
        </div>

        <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-[#1e64a7ff]"></div>
                <span className="text-[10px] font-bold text-gray-500 uppercase">Income</span>
            </div>
            <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-[#b90b0bff]"></div>
                <span className="text-[10px] font-bold text-gray-500 uppercase">Expense</span>
            </div>
            <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-[#61bce6ff]"></div>
                <span className="text-[10px] font-bold text-gray-500 uppercase">Revenue</span>
            </div>
        </div>
      </div>
      
      <div className="flex-1 w-full relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="animate-spin text-[#127690]" size={32} />
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#94a3b8", fontSize: 10, fontWeight: 600 }}
                dy={10}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#94a3b8", fontSize: 10, fontWeight: 600 }}
                tickFormatter={(value) => `₹${value >= 1000 ? (value / 1000).toFixed(1) + 'k' : value}`}
              />
              <Tooltip 
                  content={<CustomTooltip />} 
                  cursor={{ fill: "#f8fafc" }} 
              />
              <Bar dataKey="income" name="income" fill="#1e64a7ff" radius={[4, 4, 0, 0]} barSize={12} />
              <Bar dataKey="expense" name="expense" fill="#b90b0bff" radius={[4, 4, 0, 0]} barSize={12} />
              <Bar dataKey="revenue" name="revenue" fill="#61bce6ff" radius={[4, 4, 0, 0]} barSize={12} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default FinancialOverview;

