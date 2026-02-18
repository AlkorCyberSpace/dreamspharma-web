import React from "react";
import StatCard from "./StatCard";
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
        <div className="space-y-3">

            {/* First Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
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
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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

        </div>
    );
};

export default Dashboard;
