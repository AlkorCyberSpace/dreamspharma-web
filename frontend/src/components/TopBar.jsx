import React from 'react';
import { Bell, LogOut, Menu } from "lucide-react";

export default function Topbar({ onToggleSidebar }) {
  return (
    <div className="bg-[#EDEDED] mx-6 py-4 flex justify-between items-center">
      <div className="flex items-center gap-3">
        {/* Hamburger – only on sm/md */}
        <button
          onClick={onToggleSidebar}
          className="lg:hidden p-1 rounded text-gray-600 hover:bg-gray-200 transition-colors"
          aria-label="Toggle sidebar"
        >
          <Menu size={22} />
        </button>

        <div>
          <h2 className="text-sm sm:text-sm md:text-xl lg:text-2xl text-[#505050] font-semibold">
            Welcome back, John
          </h2>
          <span className="text-xs text-gray-500 hidden sm:block">
            Real-time operational insights and system health
          </span>
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-6">

        {/* Notification Icon */}
        <Bell className="text-gray-600 cursor-pointer" size={20} />

        {/* Profile Section */}
        <div className="flex items-center gap-3">
          {/* Name & Role */}
          <div className="text-sm leading-tight hidden sm:block">
            <p className="font-medium text-gray-700">John Carter</p>
            <p className="text-xs text-gray-500">Super Admin</p>
          </div>
          <img
            src="https://i.pravatar.cc/40"
            alt="Profile"
            className="w-9 h-9 rounded-full object-cover"
          />
        </div>

        {/* Logout Icon */}
        <LogOut className="text-gray-600 cursor-pointer" size={20} />

      </div>
    </div>
  );
}

