// DashboardLayout.jsx
import React from "react";
import { Outlet } from "react-router-dom";
import Topbar from "../components/TopBar";
import Sidebar from "../components/sidebar";

export default function DashboardLayout() {
  return (
    <div className="flex h-screen bg-[#EDEDED]">
      <Sidebar />

      <div className="flex-1 flex flex-col">
        <Topbar />

        <div className="px-6 py-1 overflow-y-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
