import React from "react";
import {
  DollarSign,
  TrendingUp,
  Download,
} from "lucide-react";
import {
  LineChart,
  Line,
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

export default function Reports() {
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
    { name: "Antidiabetic", value: 75000 },
  ];

  const StatCard = ({ title, value, growth, icon }) => (
    <div className="bg-gradient-to-r from-teal-600 to-teal-500 text-white p-5 rounded-xl shadow-md relative">
      <div className="absolute top-4 right-4 bg-white/20 p-2 rounded-full">
        {icon}
      </div>
      <h3 className="text-sm opacity-90">{title}</h3>
      <h2 className="text-2xl font-bold mt-1">{value}</h2>
      <p className="text-xs mt-1 text-green-200">{growth}</p>
    </div>
  );

  const ReportCard = ({ title, desc }) => (
    <div className="flex justify-between items-center bg-white p-5 rounded-xl shadow-sm border">
      <div>
        <h4 className="font-semibold text-gray-700">{title}</h4>
        <p className="text-sm text-gray-400">{desc}</p>
      </div>
      <button className="flex items-center gap-2 bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg text-sm">
        <Download size={16} />
        Excel
      </button>
    </div>
  );

  return (
    <div className="p-8 bg-gray-100 min-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            Reports & Analytics
          </h1>
          <p className="text-sm text-gray-500">
            Comprehensive business insights and data exports
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">Time Selection:</span>
          <input
            type="date"
            className="border rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="date"
            className="border rounded-lg px-3 py-2 text-sm"
          />
          <button className="bg-teal-600 hover:bg-teal-700 text-white px-5 py-2 rounded-lg text-sm">
            Apply
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
        <StatCard
          title="Total Revenue (MTD)"
          value="₹ 1,85,000"
          growth="+12% from last month"
          icon={<DollarSign size={18} />}
        />
        <StatCard
          title="Orders (MTD)"
          value="147"
          growth="+8% from last month"
          icon={<TrendingUp size={18} />}
        />
        <StatCard
          title="Avg Order Value"
          value="₹12,585"
          growth="+5% from last month"
          icon={<DollarSign size={18} />}
        />
        <StatCard
          title="Active Retailers"
          value="1,247"
          growth="+15% from last month"
          icon={<TrendingUp size={18} />}
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
        {/* Revenue Chart */}
        <div className="bg-white p-6 rounded-xl shadow-sm border">
          <h3 className="font-semibold text-gray-700 mb-4">
            Preview - Homepage Banner
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={revenueData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#0f766e"
                fill="#0f766e"
                fillOpacity={0.2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Refund Chart */}
        <div className="bg-white p-6 rounded-xl shadow-sm border">
          <h3 className="font-semibold text-gray-700 mb-4">
            Refund Trends
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={refundData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#0f766e" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Custom Reports */}
      <div>
        <h2 className="text-lg font-semibold text-gray-700 mb-4">
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