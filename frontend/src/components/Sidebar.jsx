
import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ShoppingCart,
  RefreshCcw,
  Package,
  Database,
  FileBarChart2,
  Tag,
  FileText,
  Settings,
  Users,
} from "lucide-react";

export default function Sidebar() {
  const menuItems = [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard, end: true },
    { name: "Retailers & KYC", path: "/retailers", icon: Users },
    { name: "Orders", path: "/orders", icon: ShoppingCart },
    { name: "Refunds", path: "/refunds", icon: RefreshCcw },
    { name: "Products", path: "/products", icon: Package },
    { name: "ERP Sync Monitor", path: "/erp", icon: Database },
    { name: "Reports", path: "/reports", icon: FileBarChart2 },
    { name: "Offers & Banners", path: "/offers", icon: Tag },
    { name: "Audit Logs", path: "/audit", icon: FileText },
    { name: "Settings", path: "/settings", icon: Settings },
  ];

  return (
    <div className="w-64 bg-[#EDEDED] shadow-[4px_0_15px_rgba(0,0,0,0.08)] min-h-screen py-6">

      {/* Logo Section */}
      <div className="flex items-center gap-3 mb-10 px-6">
        <div className="w-8 h-8 bg-teal-600 rounded-md flex items-center justify-center text-white font-bold">
          DP
        </div>
        <h1 className="text-xl font-semibold text-teal-700">
          Dreams Pharma
        </h1>
      </div>

      {/* Menu */}
      <ul className="space-y-1">
        {menuItems.map((item, index) => {
          const Icon = item.icon;

          return (
            <li key={index}>
              <NavLink
                to={item.path}
                end={item.end}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-10 py-3 text-sm font-medium transition-all duration-200
                   ${isActive
                    ? "bg-white text-[#127690] border-l-4 border-[#127690]"
                    : "text-gray-600 hover:bg-white hover:text-[#5f8b96]"
                  }`
                }
              >
                <Icon size={18} />
                {item.name}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </div>
  );
}