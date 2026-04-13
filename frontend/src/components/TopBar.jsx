import React, { useState, useEffect } from 'react';
import { Bell, LogOut, Menu } from "lucide-react";
import { useNavigate } from 'react-router-dom';
import { superAdminLogoutAPI, getAdminNotificationsAPI, markAdminNotificationReadAPI, getSuperAdminProfileAPI } from '../services/allAPI';
import { mediaUrl } from '../services/serverUrl';
import NotificationModal from './NotificationModal';

export default function Topbar({ onToggleSidebar }) {
  const navigate = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [adminName, setAdminName] = useState('Admin');
  const [adminRole, setAdminRole] = useState('Super Admin');
  const [profileImage, setProfileImage] = useState(null);

  const fetchNotifications = async () => {
    try {
      const response = await getAdminNotificationsAPI();
      if (response && response.data) {
        // Adjust for backend response structure (it returns { data: [...] } based on maindash/views.py)
        const fetchedNotifs = response.data.data || [];
        setNotifications(fetchedNotifs);
        const count = fetchedNotifs.filter(n => !n.is_read).length;
        setUnreadCount(count);
      }
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    }
  };

  const fetchAdminProfile = async () => {
    try {
      const response = await getSuperAdminProfileAPI();
      if (response && response.data) {
        const profile = response.data.profile;
        // Use first_name and last_name if available, otherwise use username
        const name = profile.first_name && profile.last_name 
          ? `${profile.first_name} ${profile.last_name}` 
          : profile.username || 'Admin';
        setAdminName(name);
        setAdminRole(profile.get_role_display || 'Super Admin');
        
        if (profile.profile_image) {
          setProfileImage(`${mediaUrl}${profile.profile_image}`);
        }
      }
    } catch (error) {
      console.error("Failed to fetch admin profile:", error);
    }
  };

  useEffect(() => {
    fetchNotifications();
    fetchAdminProfile();
    // Poll for new notifications every minute
    const interval = setInterval(fetchNotifications, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleMarkAsRead = async (id) => {
    try {
      await markAdminNotificationReadAPI(id);
      // Optimistic update
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error("Failed to mark as read:", error);
    }
  };

  const handleLogout = async () => {
    const confirmed = window.confirm("Are you sure you want to logout?");
    if (!confirmed) return;

    try {
      await superAdminLogoutAPI();
    } catch (error) {
      console.error("Logout API failed:", error);
    } finally {
      localStorage.removeItem("token");
      localStorage.removeItem("superadminInfo");
      navigate("/login");
    }
  };

  return (
    <div className="bg-[#EDEDED] mx-6 py-4 flex justify-between items-center relative">
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
            Welcome back, {adminName.split(' ')[0]}
          </h2>
          <span className="text-xs text-gray-500 hidden sm:block">
            Real-time operational insights and system health
          </span>
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-6">

        {/* Notification Icon Container */}
        <div className="relative">
          <Bell 
            className="text-gray-600 cursor-pointer hover:text-blue-500 transition-colors" 
            size={20} 
            onClick={() => setIsModalOpen(true)}
          />
          {unreadCount > 0 && (
            <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold flex items-center justify-center rounded-full border-2 border-[#EDEDED] shadow-sm">
              {unreadCount}
            </span>
          )}
        </div>

        {/* Profile Section */}
        <div className="flex items-center gap-3">
          <div className="text-sm leading-tight hidden sm:block text-right">
            <p className="font-medium text-gray-700">{adminName}</p>
            <p className="text-xs text-gray-500 font-medium">{adminRole}</p>
          </div>
          <img
            src={profileImage || "https://i.pravatar.cc/40"}
            alt="Profile"
            className="w-9 h-9 rounded-full object-cover shadow-sm border border-gray-200"
          />
        </div>

        {/* Logout Icon */}
        <LogOut
          className="text-gray-600 cursor-pointer hover:text-red-500 transition-colors"
          size={20}
          onClick={handleLogout}
        />

      </div>

      {/* Notification Modal */}
      <NotificationModal 
        isOpen={isModalOpen}
        notifications={notifications}
        onClose={() => setIsModalOpen(false)}
        onMarkAsRead={handleMarkAsRead}
      />
    </div>
  );
}

