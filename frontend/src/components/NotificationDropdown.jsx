import React from "react";
import { X, Check } from "lucide-react";

const NotificationDropdown = ({ notifications, onMarkAsRead, onClose }) => {
  return (
    <div className="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-xl z-50 overflow-hidden">
      <div className="p-3 border-b border-gray-100 flex justify-between items-center bg-gray-50">
        <h3 className="text-sm font-semibold text-gray-700">Notifications</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <X size={16} />
        </button>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {notifications && notifications.length > 0 ? (
          notifications.map((notif) => (
            <div
              key={notif.id}
              className={`p-3 border-b border-gray-50 hover:bg-gray-50 transition-colors cursor-pointer flex gap-3 ${
                !notif.is_read ? "bg-blue-50/50" : ""
              }`}
              onClick={() => !notif.is_read && onMarkAsRead(notif.id)}
            >
              <div className="flex-1">
                <p className={`text-sm ${!notif.is_read ? "font-semibold" : "text-gray-600"}`}>
                  {notif.message || notif.title}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {new Date(notif.created_at).toLocaleString()}
                </p>
              </div>
              {!notif.is_read && (
                <div className="w-2 h-2 bg-blue-500 rounded-full self-center"></div>
              )}
            </div>
          ))
        ) : (
          <div className="p-6 text-center text-gray-400 text-sm">
            No notifications available
          </div>
        )}
      </div>

      <div className="p-2 border-t border-gray-100 bg-gray-50 text-center">
        <button className="text-xs text-blue-600 font-medium hover:underline">
          View all notifications
        </button>
      </div>
    </div>
  );
};

export default NotificationDropdown;
