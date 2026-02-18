import React from 'react'
import { Bell, LogOut } from "lucide-react";
export default function Topbar() {
  return (
    <div className="bg-[#EDEDED]  mx-6 py-4 flex justify-between items-center">
      <div>
        <h2 className="text-xl text-[#505050] font-semibold">
          Welcome back, John
        </h2>
        <span className="text-xs text-gray-500">
          Real-time operational insights and system health
        </span>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-6">

        {/* Notification Icon */}
        <Bell className="text-gray-600 cursor-pointer" size={20} />

        {/* Profile Section */}
        <div className="flex items-center gap-3">
          
          {/* Profile Image */}
               {/* Name & Role */}
          <div className="text-sm leading-tight">
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
