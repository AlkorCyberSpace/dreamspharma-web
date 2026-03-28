
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
  X,
} from "lucide-react";

export default function Sidebar({ isOpen, onClose }) {
  const menuItems = [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard, end: true },
    { name: "Retailers & KYC", path: "/retailers", icon: Users },
    { name: "Orders", path: "/orders", icon: ShoppingCart },
    { name: "Refunds", path: "/refunds", icon: RefreshCcw },
    { name: "Products", path: "/products", icon: Package },
    { name: "Categories", path: "/categories", icon: Database },
    { name: "Reports", path: "/reports", icon: FileBarChart2 },
    { name: "Offers & Banners", path: "/offers", icon: Tag },
    { name: "Audit Logs", path: "/audit", icon: FileText },
    { name: "Profile Settings", path: "/Profile", icon: Settings },
  ];

  return (
    <>
      {/* Overlay – only on sm/md when sidebar is open */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`
          fixed top-0 left-0 h-full w-64 bg-[#EDEDED] z-40
          shadow-[4px_0_15px_rgba(0,0,0,0.08)] py-6
          transition-transform duration-300 ease-in-out
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
          lg:relative lg:translate-x-0 lg:block lg:flex-shrink-0
        `}
      >
        {/* Logo Section */}
        <div className="flex items-center justify-between gap-3 mb-10 px-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-teal-600 rounded-md flex items-center justify-center text-white font-bold text-xs">
              DP
            </div>
            <h1 className="text-xl font-semibold text-teal-700">
              Dreams Pharma
            </h1>
          </div>
          {/* Close button – only visible on sm/md */}
          <button
            onClick={onClose}
            className="lg:hidden p-1 rounded text-gray-500 hover:bg-gray-200 transition-colors"
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
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
                  onClick={() => {
                    // Auto-close sidebar on navigation for sm/md screens
                    if (window.innerWidth < 1024) onClose?.();
                  }}
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
      </aside>
    </>
  );
}
