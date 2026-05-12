import React, { useEffect, useState } from "react";
import StatCard from "./StatCard";
import DailyOrderVolume from "./charts/DailyOrderVolume";
import FinancialOverview from "./charts/FinancialOverview";
import OrdersByStatus from "./charts/OrdersByStatus";

// import InventoryInsights from "./charts/WarehousePerformance";
import InventoryInsights from "./charts/InventoryInsights";

import {
    Users,
    AlertCircle,
    ShoppingCart,
    TrendingUp,
    CheckCircle,
    RotateCcw,
} from "lucide-react";
import { getDashboardStatsAPI, getWarehouseOrdersAPI } from "../services/allAPI";

const Dashboard = () => {
    const [dashboardData, setDashboardData] = useState(null);
    const [warehouseData, setWarehouseData] = useState(null);
    const [loading, setLoading] = useState(true);

    // Timeframe filter states
    const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
    const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

    // Applied states for charts that fetch independently
    const [appliedMonth, setAppliedMonth] = useState(new Date().getMonth() + 1);
    const [appliedYear, setAppliedYear] = useState(new Date().getFullYear());

    const months = [
        { name: "January", value: 1 }, { name: "February", value: 2 },
        { name: "March", value: 3 }, { name: "April", value: 4 },
        { name: "May", value: 5 }, { name: "June", value: 6 },
        { name: "July", value: 7 }, { name: "August", value: 8 },
        { name: "September", value: 9 }, { name: "October", value: 10 },
        { name: "November", value: 11 }, { name: "December", value: 12 }
    ];

    const currentYear = new Date().getFullYear();
    const years = Array.from({ length: 5 }, (_, i) => currentYear - i);

    const fetchAllData = async (month, year) => {
        setLoading(true);
        try {
            const params = { month, year };
            const [statsRes, warehouseRes] = await Promise.all([
                getDashboardStatsAPI(params),
                getWarehouseOrdersAPI({ ...params, period: 'date' }) // Get daily data for the selected month
            ]);

            console.log("Dashboard Stats:", statsRes.data);
            console.log("Warehouse Orders:", warehouseRes.data);

            setDashboardData(statsRes.data.statistics);
            setWarehouseData(warehouseRes.data);
        } catch (err) {
            console.error("Dashboard Fetch Error:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAllData(appliedMonth, appliedYear);
    }, []);

    const handleApply = () => {
        setAppliedMonth(selectedMonth);
        setAppliedYear(selectedYear);
        fetchAllData(selectedMonth, selectedYear);
    };

    if (loading && !dashboardData) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 border-4 border-[#127690] border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-gray-500 font-medium">Loading analytics...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {/* First Row - Stat Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    variant="primary"
                    title="Total Retailers (MTD)"
                    value={dashboardData?.total_retailers || 0}
                    change={dashboardData?.retailers_change_text || ""}
                    icon={Users}
                />

                <StatCard
                    variant="strong"
                    title="Pending KYC (MTD)"
                    value={dashboardData?.pending_kyc || 0}
                    change={dashboardData?.pending_kyc_change_text || ""}
                    icon={AlertCircle}
                />

                <StatCard
                    variant="soft"
                    title="Total Orders (MTD)"
                    value={dashboardData?.total_orders || 0}
                    change={dashboardData?.orders_change_text || ""}
                    icon={ShoppingCart}
                />

                <StatCard
                    variant="primary"
                    title="Top Selling Product"
                    value={dashboardData?.top_selling_product || "N/A"}
                    change={`${dashboardData?.top_selling_change_percentage || 0}%`}
                    icon={CheckCircle}
                />
            </div>
            <div className="flex justify-end">
                <div className="flex items-center bg-white border border-gray-200 rounded-xl p-1 shadow-sm w-fit">
                    <div className="px-3 py-1.5 border-r border-gray-100  sm:block">
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Timeframe</span>
                    </div>

                    <div className="flex items-center gap-1 px-2">
                        <select
                            value={selectedMonth}
                            onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                            className="bg-transparent text-sm font-medium text-gray-700 outline-none cursor-pointer py-1.5 px-2 hover:bg-gray-50 rounded-lg transition-colors"
                        >
                            {months.map(m => (
                                <option key={m.value} value={m.value}>{m.name}</option>
                            ))}
                        </select>

                        <div className="w-px h-4 bg-gray-200 mx-1"></div>

                        <select
                            value={selectedYear}
                            onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                            className="bg-transparent text-sm font-medium text-gray-700 outline-none cursor-pointer py-1.5 px-2 hover:bg-gray-50 rounded-lg transition-colors"
                        >
                            {years.map(y => (
                                <option key={y} value={y}>{y}</option>
                            ))}
                        </select>
                    </div>

                    <button
                        onClick={handleApply}
                        className="bg-[#127690] text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-[#0e5e73] transition-all shadow-sm ml-2 active:scale-95"
                    >
                        Apply
                    </button>
                </div>
            </div>


            {/* Charts */}
            <div className="p-1">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

                    {/* Main Chart */}
                    <div className="lg:col-span-2 flex flex-col gap-4">
                        <FinancialOverview
                            selectedMonth={appliedMonth}
                            selectedYear={appliedYear}
                            data={dashboardData?.financial_overview || []}
                        />
                        <InventoryInsights />
                    </div>

                    {/* Side Charts */}
                    <div className="flex flex-col gap-4">
                        <DailyOrderVolume
                            data={dashboardData?.daily_order_volume || []}
                        />
                        

                        <OrdersByStatus
                            selectedMonth={appliedMonth}
                            selectedYear={appliedYear}
                        />

                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;