import React from "react";
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

const Dashboard = () => {
    return (
        <div className="space-y-6">

            {/* First Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard
                    variant="primary"
                    title="Total Retailers"
                    value="1,247"
                    change="+12% from last week"
                    icon={Users}
                />

                <StatCard
                    variant="strong"
                    title="Pending KYC"
                    value="23"
                    change="-5% from last week"
                    icon={AlertCircle}
                />

                <StatCard
                    variant="soft"
                    title="Total Orders"
                    value="55"
                    change="+8% from last week"
                    icon={ShoppingCart}
                />
            </div>

            {/* Second Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard
                    variant="strong"
                    title="Orders in Dispatch"
                    value="30"
                    change="+3% from last week"
                    icon={TrendingUp}
                />

                <StatCard
                    variant="primary"
                    title="Top Selling Product"
                    value="Dolo-650"
                    change="+12% from last week"
                    icon={CheckCircle}
                />

                <StatCard
                    variant="strong"
                    title="Pending Refund"
                    value="7"
                    change="-2% from last week"
                    icon={RotateCcw}
                />
            </div>

            {/* Charts Row - Styled with Blue Border like in the image */}
            <div className="p-4 ">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Main Chart Slot (2/3 width) */}
                    <div className="lg:col-span-2">
                        <DailyOrderVolume />
                    </div>

                    {/* Side Charts Slots (1/3 width) stacked vertically */}
                    <div className="flex flex-col gap-4">
                        <RefundTrends />
                        <OrdersByStatus />
                    </div>
                </div>
            </div>

        </div>
    );
};

export default Dashboard;
