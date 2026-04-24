import React, { useEffect, useState } from "react";
import { DollarSign, TrendingUp, Download } from "lucide-react";
import {
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Area,
  AreaChart,
  BarChart,
  Bar,
} from "recharts";
import { getReportSummaryApi } from "../services/allAPI";

export default function Reports() {
  const [summary, setSummary] = useState({})
  const revenueData = [
    { month: "Aug", revenue: 0 },
    { month: "Sep", revenue: 95000 },
    { month: "Oct", revenue: 190000 },
    { month: "Nov", revenue: 250000 },
    { month: "Dec", revenue: 300000 },
  ];

  const refundData = [
    { name: "Analgesics", value: 30000 },
    { name: "Antibiotics", value: 65000 },
    { name: "Cardiovascular", value: 20000 },
    { name: "Antihistamines", value: 75000 },
  ];

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReportSummary = async () => {
      try {
        const response = await getReportSummaryApi();
        console.log("Full response:", response);
        console.log("Data:", response.data);
        // Extract the nested 'data' object from the response
        setSummary(response.data?.data || {});

      } catch (err) {
        console.error("Error fetching summary:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchReportSummary();
  }, []);
  /* ---------- Stat Card ---------- */

  const StatCard = ({ title, value, growth, icon, index = 0 }) => {
    const isLight = index % 2 === 0;
    
    // Determine if growth is positive or negative
    const growthStr = String(growth);
    const isNegative = growthStr.includes("-");
    const arrow = isNegative ? "↓" : "↑";
    const colorClass = isNegative ? "text-red-600" : "text-[#008258]";
    const cleanGrowth = growthStr.replace("+", "").replace("+ ", "").replace("-", "");

    return (
      <div
        className={`relative p-5 rounded-xl shadow-sm border border-gray-100
        ${isLight
            ? "bg-gradient-to-r from-[#f4f8f9] via-[#c1d9dd] to-[#67a7b3]"
            : "bg-gradient-to-r from-[#64a5b1] to-[#529ba7]"
          }
        text-gray-800 overflow-hidden`}
      >
        <div className="absolute right-4 top-5 bg-[#177286] w-10 h-10 rounded-full flex items-center justify-center text-white shadow-sm">
          {icon}
        </div>

        <h2 className="text-2xl font-medium">{value}</h2>
        <p className="mt-1 text-[17px] text-gray-700">{title}</p>
        <p className={`mt-1 text-sm font-medium ${colorClass}`}>
          {arrow} {cleanGrowth}
        </p>
      </div>
    );
  };

  /* ---------- Report Card ---------- */

  const ReportCard = ({ title, desc }) => (
    <div className="flex justify-between items-center bg-white p-5 rounded-xl shadow border border-gray-100">
      <div>
        <h4 className="font-semibold text-gray-700">{title}</h4>
        <p className="text-sm text-gray-400">{desc}</p>
      </div>

      <button className="flex items-center gap-2 bg-[#2e7d88] hover:bg-[#24656d] text-white px-4 py-2 rounded-lg text-sm">
        <Download size={16} />
        Excel
      </button>
    </div>
  );

  return (
    <div className=" min-h-screen ml-2 mt-3">

      {/* ---------- HEADER ---------- */}

      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-xl font-semibold text-[#505050] tracking-tight">
            Reports & Analytics
          </h1>

          <p className="text-sm text-[#8E8E8E] ">
            Comprehensive business insights and data exports
          </p>
        </div>

        <div className="flex flex-col items-start gap-1">
          <span className="text-sm text-gray-600">Time Selection:</span>
          <div className="flex gap-2">
            <input
              type="date"
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />

            <input
              type="date"
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />

            <button className="bg-[#2e7d88] hover:bg-[#24656d] text-white px-5 py-2 rounded-lg text-sm">
              Apply
            </button>
          </div>
        </div>
      </div>

      {/* ---------- STATS ---------- */}

      {loading ? (
        <p>Loading...</p>
      ) : summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            index={0}
            title="Total Revenue (MTD)"
            value={`₹ ${summary?.total_revenue ? summary.total_revenue.toFixed(2) : 0}`}
            growth={`${summary?.revenue_change_percentage >= 0 ? '+' : ''}${summary?.revenue_change_percentage || "0"}%`}
            icon={<DollarSign size={20} />}
          />

          <StatCard
            index={1}
            title="Orders (MTD)"
            value={summary?.total_orders || 0}
            growth={`${summary?.orders_change_percentage >= 0 ? '+' : ''}${summary?.orders_change_percentage || "0"}%`}
            icon={<TrendingUp size={20} />}
          />

          <StatCard
            index={2}
            title="Avg Order Value"
            value={`₹ ${summary?.avg_order_value ? summary.avg_order_value.toFixed(2) : 0}`}
            growth={`${summary?.avg_order_change_percentage >= 0 ? '+' : ''}${summary?.avg_order_change_percentage || "0"}%`}
            icon={<DollarSign size={20} />}
          />

          <StatCard
            index={3}
            title="Active Retailers"
            value={summary?.active_retailers || 0}
            growth={`+0%`} // Active retailers doesn't have a change percentage yet
            icon={<TrendingUp size={20} />}
          />
        </div>

      )}

      {/* ---------- CHARTS ---------- */}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-8">

        {/* Revenue Chart */}
        <div className="bg-white p-6 rounded-xl shadow border border-gray-100">
          <h3 className="font-semibold text-gray-700 mb-4">
            Preview - Homepage Banner
          </h3>

          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={revenueData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />

              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#2e7d88"
                fill="#2e7d88"
                fillOpacity={0.2}
                strokeWidth={3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Refund Chart */}
        <div className="bg-white p-6 rounded-xl shadow border border-gray-100">
          <h3 className="font-semibold text-gray-700 mb-4">
            Refund Trends
          </h3>

          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={refundData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />

              <Bar
                dataKey="value"
                fill="#2e7d88"
                radius={[6, 6, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ---------- CUSTOM REPORTS ---------- */}

      <div>
        <h2 className="text-lg font-semibold text-gray-700 mb-5">
          Generate Custom Reports
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <ReportCard
            title="Order Report"
            desc="Detailed order list with all transactions"
          />

          <ReportCard
            title="Revenue Report"
            desc="Financial summary and revenue breakdown"
          />

          <ReportCard
            title="Refund Report"
            desc="All refund transactions and approvals"
          />

          <ReportCard
            title="Retailer Activity Report"
            desc="Retailer-wise ordering patterns"
          />

          <ReportCard
            title="Product Performance Report"
            desc="Best/worst selling products"
          />

          <ReportCard
            title="KYC Status Report"
            desc="KYC approval/rejection statistics"
          />
        </div>
      </div>

    </div>
  );
}