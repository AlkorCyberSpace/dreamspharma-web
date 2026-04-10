import React, { useEffect, useState } from "react";
import StatCard from "./StatCard";
import DailyOrderVolume from "./charts/DailyOrderVolume";
import RefundTrends from "./charts/RefundTrends";
import OrdersByStatus from "./charts/OrdersByStatus";
import {
    Users,
    AlertCircle,
    ShoppingCart,
    TrendingUp,
    CheckCircle,
    RotateCcw,
} from "lucide-react";
import { getDashboardStatsAPI } from "../services/allAPI";

const Dashboard = () => {
    const [dashboardData, setDashboardData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDashboard = async () => {
            try {
                const res = await getDashboardStatsAPI();
                console.log("Dashboard API:", res.data);

                // ✅ IMPORTANT FIX
                setDashboardData(res.data.statistics);
            } catch (err) {
                console.error("Dashboard API Error:", err);
            } finally {
                setLoading(false);
            }
        };

        fetchDashboard();
    }, []);

    if (loading) {
        return <p className="p-6 text-gray-500">Loading dashboard...</p>;
    }

    return (
        <div className="space-y-3">

            {/* First Row */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <StatCard
                    variant="primary"
                    title="Total Retailers"
                    value={dashboardData?.total_retailers || 0}
                    change={dashboardData?.retailers_change_text || ""}
                    icon={Users}
                />

                <StatCard
                    variant="strong"
                    title="Pending KYC"
                    value={dashboardData?.pending_kyc || 0}
                    change={dashboardData?.pending_kyc_change_text || ""}
                    icon={AlertCircle}
                />

                <StatCard
                    variant="soft"
                    title="Total Orders"
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

            {/* Second Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* <StatCard
                    variant="strong"
                    title="Orders in Dispatch"
                    value={dashboardData?.orders_in_dispatch || 0}
                    change={dashboardData?.dispatch_change_text || ""}
                    icon={TrendingUp}
                /> */}

                {/* <StatCard
                    variant="primary"
                    title="Top Selling Product"
                    value={dashboardData?.top_selling_product || "N/A"}
                    change={`${dashboardData?.top_selling_change_percentage || 0}%`}
                    icon={CheckCircle}
                /> */}

                {/* <StatCard
                    variant="strong"
                    title="Pending Refund"
                    value={dashboardData?.pending_refund || 0}
                    change={dashboardData?.pending_refund_change_text || ""}
                    icon={RotateCcw}
                /> */}
            </div>

            {/* Charts */}
            <div className="p-1">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

                    {/* Main Chart */}
                    <div className="lg:col-span-2">
                        <DailyOrderVolume
                            data={dashboardData?.daily_order_volume || []}
                        />
                    </div>

                    {/* Side Charts */}
                    <div className="flex flex-col gap-4">

                        <RefundTrends
                            data={dashboardData?.refund_trends || []}
                        />

                        <OrdersByStatus
                            data={dashboardData?.orders_by_status || []}
                        />

                    </div>
                </div>
            </div>

        </div>
    );
};

export default Dashboard;