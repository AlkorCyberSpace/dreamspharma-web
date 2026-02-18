// Sidebar.jsx
import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  ShoppingCart,
  RefreshCcw,
  Package,
  FileBarChart2,
  Tag,
  FileText,
  Settings,
  Database,
} from "lucide-react";

export default function Sidebar() {
  const menuItems = [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
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
      <div className="flex items-center gap-3 mb-10">
        <div className="w-8 h-8 bg-teal-600 rounded-md flex items-center justify-center text-white font-bold">
          DP
        </div>
        <h1 className="text-xl font-semibold text-teal-700">
          Dreams Pharma
        </h1>
      </div>

      {/* Menu */}
      <ul className="space-y-2">
        {menuItems.map((item, index) => {
          const Icon = item.icon;

          return (
            <li key={index}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 pl-10 py-4  text-sm font-medium transition-all duration-200
                   ${
                     isActive
                       ? "bg-[#F5F7FA] text-[#127690] shadow-sm border-l-5 border-[#127690]"
                       : "text-gray-600 hover:bg-[#F5F7FA] hover:text-[#5f8b96]   hover:shadow-sm"
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
