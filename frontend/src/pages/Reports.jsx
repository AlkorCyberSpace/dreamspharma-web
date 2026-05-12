import React, { useEffect, useState } from "react";
import { DollarSign, TrendingUp, Download } from "lucide-react";
import axiosInstance, { getReportSummaryApi } from "../services/allAPI";

export default function Reports() {

  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(true);

  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth();

  const [selectedMonth, setSelectedMonth] = useState(currentMonth);
  const [selectedYear, setSelectedYear] = useState(currentYear);

  // NEW STORE FILTER
  const [selectedStore, setSelectedStore] = useState("all");

  // DEMO STORE LIST
  // Later fetch dynamically from backend
  const stores = [
    { id: "all", name: "All Warehouses" },
    { id: 1, name: "Edapally Toll" },
    { id: 2, name: "Edapally Lulu" },
    { id: 3, name: "Chelakkara" },
    { id: 4, name: "Calicut Hub" },
  ];

  const months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);

  /* ---------------- FETCH SUMMARY ---------------- */

  const fetchReportSummary = async (startDate = null, endDate = null) => {
    setLoading(true);

    try {

      const response = await getReportSummaryApi(
        startDate,
        endDate
      );

      setSummary(response.data?.data || {});

    } catch (err) {

      console.error("Error fetching summary:", err);

    } finally {

      setLoading(false);
    }
  };

  useEffect(() => {

    const start = new Date(
      selectedYear,
      selectedMonth,
      1
    ).toISOString().split("T")[0];

    const end = new Date(
      selectedYear,
      selectedMonth + 1,
      0
    ).toISOString().split("T")[0];

    fetchReportSummary(start, end);

  }, [selectedMonth, selectedYear, selectedStore]);

  /* ---------------- DOWNLOAD EXCEL ---------------- */

  const handleDownloadExcel = async (title) => {

    const start = new Date(
      selectedYear,
      selectedMonth,
      1
    ).toISOString().split("T")[0];

    const end = new Date(
      selectedYear,
      selectedMonth + 1,
      0
    ).toISOString().split("T")[0];

    // API ROUTES
    const typeMap = {

      "Order Report": "store-wise/orders",

      "Revenue Report": "store-wise/revenue",

      "Credit Report": "store-wise/credits",

      "Retailer Activity Report":
        "store-wise/retailer-activity",

      "Store Performance Report":
        "store-wise/summary",
    };

    const path = typeMap[title];

    if (!path) return;

    try {

      const params = {
        period: "custom",
        start_date: start,
        end_date: end,
        export: "excel",
      };

      // STORE FILTER
      if (selectedStore !== "all") {
        params.store_id = selectedStore;
      }

      const response = await axiosInstance.get(
        `superadmin/reports/${path}/`,
        {
          params,
          responseType: "blob",
        }
      );

      // FILE DOWNLOAD
      const url = window.URL.createObjectURL(
        new Blob([response.data])
      );

      const link = document.createElement("a");

      link.href = url;

      link.setAttribute(
        "download",
        `${title.replace(/ /g, "_").toLowerCase()}.xlsx`
      );

      document.body.appendChild(link);

      link.click();

      link.remove();

      window.URL.revokeObjectURL(url);

    } catch (err) {

      console.error("Error downloading report:", err);

      if (err.response) {
        console.log(
          "Backend Error:",
          err.response.data
        );
      }
    }
  };

  /* ---------------- STAT CARD ---------------- */

  const StatCard = ({
    title,
    value,
    growth,
    icon,
    index = 0,
  }) => {

    const isLight = index % 2 === 0;

    const growthStr = String(growth);

    const isNegative = growthStr.includes("-");

    const arrow = isNegative ? "↓" : "↑";

    const colorClass = isNegative
      ? "text-red-600"
      : "text-[#008258]";

    const cleanGrowth = growthStr
      .replace("+", "")
      .replace("-", "");

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

        <h2 className="text-2xl font-medium">
          {value}
        </h2>

        <p className="mt-1 text-[17px] text-gray-700">
          {title}
        </p>

        <p className={`mt-1 text-sm font-medium ${colorClass}`}>
          {arrow} {cleanGrowth}
        </p>

      </div>
    );
  };

  /* ---------------- REPORT CARD ---------------- */

  const ReportCard = ({
    title,
    desc,
    onDownload,
  }) => (

    <div className="flex justify-between items-center bg-white p-5 rounded-xl shadow border border-gray-100 transition-all hover:shadow-md hover:border-[#2e7d88]/20">

      <div>
        <h4 className="font-semibold text-gray-700">
          {title}
        </h4>

        <p className="text-sm text-gray-400">
          {desc}
        </p>
      </div>

      <button
        onClick={() => onDownload(title)}
        className="flex items-center gap-2 bg-[#2e7d88] hover:bg-[#24656d] text-white px-4 py-2 rounded-lg text-sm transition-all shadow-sm active:scale-95"
      >
        <Download size={16} />
        Excel
      </button>

    </div>
  );

  return (

    <div className="min-h-screen px-3 sm:px-4 lg:px-2 mt-3">

      {/* HEADER */}

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-5">

        {/* LEFT */}
        <div>

          <h1 className="text-2xl sm:text-3xl font-semibold text-[#505050] tracking-tight leading-tight">
            Reports & Analytics
          </h1>

          <p className="text-sm sm:text-base text-[#8E8E8E] leading-relaxed max-w-xl">
            Comprehensive business insights and data exports
          </p>

        </div>

        {/* FILTERS */}

        <div className="w-full lg:w-auto flex items-center gap-1 sm:gap-2 bg-white px-2 sm:px-3 py-2 rounded-2xl shadow-sm border border-gray-100 overflow-x-auto scrollbar-hide">

          {/* MONTH */}
          <select
            value={selectedMonth}
            onChange={(e) =>
              setSelectedMonth(parseInt(e.target.value))
            }
            className="bg-transparent text-gray-700 text-xs sm:text-sm font-medium py-1.5 sm:py-2 px-2 sm:px-3 outline-none cursor-pointer hover:text-[#2e7d88] rounded-lg min-w-[85px] sm:min-w-[110px]"      >
            {months.map((month, index) => (
              <option
                className="bg-white text-gray-700 border border-green-900"
                key={month}
                value={index}
              >
                {month}
              </option>
            ))}
          </select>

          {/* DIVIDER */}

          <div className="w-px h-4 bg-gray-200 hidden sm:block"></div>

          {/* YEAR */}
          <select
            value={selectedYear}
            onChange={(e) =>
              setSelectedYear(parseInt(e.target.value))
            }
            className="bg-transparent text-gray-700 text-xs sm:text-sm font-medium py-1.5 sm:py-2 px-2 sm:px-3 outline-none cursor-pointer hover:text-[#2e7d88] rounded-lg min-w-[75px] sm:min-w-[90px]"      >
            {years.map((year) => (
              <option
                key={year}
                value={year}
              >
                {year}
              </option>
            ))}
          </select>

          {/* DIVIDER */}

          <div className="w-px h-4 bg-gray-200 hidden sm:block"></div>

          {/* STORE */}
          <select
            value={selectedStore}
            onChange={(e) =>
              setSelectedStore(e.target.value)
            }
            className="bg-transparent text-gray-700 text-xs sm:text-sm font-medium py-1.5 sm:py-2 px-2 sm:px-3 outline-none cursor-pointer hover:text-[#2e7d88] rounded-lg min-w-[120px] sm:min-w-[160px]"      >
            {stores.map((store) => (
              <option
                key={store.id}
                value={store.id}
              >
                {store.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* STATS */}

      {loading ? (

        <p>Loading...</p>

      ) : (

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">

          <StatCard
            index={0}
            title="Total Revenue (MTD)"
            value={`₹ ${summary?.total_revenue
              ? summary.total_revenue.toFixed(2)
              : 0
              }`}
            growth={`${summary?.revenue_change_percentage >= 0 ? "+" : ""
              }${summary?.revenue_change_percentage || "0"}%`}
            icon={<DollarSign size={20} />}
          />

          <StatCard
            index={1}
            title="Orders (MTD)"
            value={summary?.total_orders || 0}
            growth={`${summary?.orders_change_percentage >= 0 ? "+" : ""
              }${summary?.orders_change_percentage || "0"}%`}
            icon={<TrendingUp size={20} />}
          />

          <StatCard
            index={2}
            title="Avg Order Value"
            value={`₹ ${summary?.avg_order_value
              ? summary.avg_order_value.toFixed(2)
              : 0
              }`}
            growth={`${summary?.avg_order_change_percentage >= 0 ? "+" : ""
              }${summary?.avg_order_change_percentage || "0"}%`}
            icon={<DollarSign size={20} />}
          />

          <StatCard
            index={3}
            title="Active Retailers"
            value={summary?.active_retailers || 0}
            growth="+0%"
            icon={<TrendingUp size={20} />}
          />

        </div>
      )}

      {/* REPORTS */}

      <div className="mb-10">

        <div className="flex items-center justify-between mb-6">

          <h2 className="text-xl font-bold text-gray-800">
            Generate Custom Reports
          </h2>

        </div>

        {/* REPORT GRID */}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">

          <ReportCard
            title="Order Report"
            desc="Detailed order list with all transactions"
            onDownload={handleDownloadExcel}
          />

          <ReportCard
            title="Revenue Report"
            desc="Financial summary and revenue breakdown"
            onDownload={handleDownloadExcel}
          />

          <ReportCard
            title="Credit Report"
            desc="All credit transactions and approvals"
            onDownload={handleDownloadExcel}
          />

          <ReportCard
            title="Retailer Activity Report"
            desc="Retailer-wise ordering patterns"
            onDownload={handleDownloadExcel}
          />

          <ReportCard
            title="Store Performance Report"
            desc="Order summary across all stores"
            onDownload={handleDownloadExcel}
          />

        </div>
      </div>
    </div>
  );
}