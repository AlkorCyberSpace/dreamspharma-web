// DashboardLayout.jsx
import React, { useState } from "react";
import { Outlet } from "react-router-dom";
import Topbar from "../components/TopBar";
import Sidebar from "../components/Sidebar";

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#EDEDED] overflow-hidden">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Topbar onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />

        <div className="flex-1 px-6 py-3 overflow-y-auto flex flex-col bg-white">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
