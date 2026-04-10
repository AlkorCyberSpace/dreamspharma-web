import React, { useState } from "react";
import { X, Truck, Percent, Gift, ShoppingBag, Clock, ChevronLeft, Tag } from "lucide-react";

/**
 * Mapping notification types or keywords to icons
 */
const getNotificationIcon = (message = "", type = "") => {
  const content = (message + " " + type).toLowerCase();
  if (content.includes("service") || content.includes("truck") || content.includes("delivery")) 
    return <Truck size={20} className="text-[#127690]" />;
  if (content.includes("off") || content.includes("discount") || content.includes("%")) 
    return <Percent size={20} className="text-[#127690]" />;
  if (content.includes("gift") || content.includes("voucher")) 
    return <Gift size={20} className="text-[#127690]" />;
  if (content.includes("order") || content.includes("product")) 
    return <ShoppingBag size={20} className="text-[#127690]" />;
  return <Clock size={20} className="text-[#127690]" />;
};

const formatDate = (dateString) => {
  if (!dateString) return "Just now";
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return "Recently";
  }
};

const NotificationModal = ({ isOpen, notifications, onClose, onMarkAsRead }) => {
  const [selectedNotif, setSelectedNotif] = useState(null);

  if (!isOpen) return null;

  const handleNotifClick = (notif) => {
    if (!notif.is_read) {
      onMarkAsRead(notif.id);
    }
    setSelectedNotif(notif);
  };

  const handleClose = () => {
    setSelectedNotif(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-end p-3 bg-black/40 backdrop-blur-[2px]">
      <div className="bg-white w-full max-w-md rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[100vh] animate-in slide-in-from-right duration-300">
        
        {/* Header */}
        <div className="p-2.5 border-b border-gray-50 flex items-center relative">
          {selectedNotif && (
            <button 
              onClick={() => setSelectedNotif(null)} 
              className="absolute left-4 p-1 rounded-full hover:bg-gray-100 text-gray-400 transition-colors"
            >
              <ChevronLeft size={22} />
            </button>
          )}
          <h3 className={`flex-1 text-center text-lg font-bold text-gray-700 tracking-tight ${selectedNotif ? "pl-6" : ""}`}>
            {selectedNotif ? "Notification Detail" : "Notifications"}
          </h3>
          <button 
            onClick={handleClose} 
            className="absolute right-5 p-1 rounded-full hover:bg-gray-100 text-gray-400 transition-colors"
          >
            <X size={22} />
          </button>
        </div>

        {/* Content Area */}
        {selectedNotif ? (
          /* Detailed View */
          <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-white animate-in slide-in-from-right duration-200">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-[#eef5f7] flex items-center justify-center shrink-0">
                {getNotificationIcon(selectedNotif.message, selectedNotif.notification_type)}
              </div>
              <div className="flex-1">
                <span className="text-[10px] font-black text-[#127690] uppercase tracking-widest bg-[#eef5f7] px-2 py-1 rounded-md mb-2 inline-block">
                  {selectedNotif.notification_type || "SYSTEM"}
                </span>
                <h4 className="text-xl font-bold text-gray-800 leading-tight">
                  {selectedNotif.title || "System Update"}
                </h4>
              </div>
            </div>

            <div className="space-y-4">
              <div className="p-5 rounded-2xl bg-[#f8fafc] border border-gray-100">
                <p className="text-gray-600 leading-relaxed whitespace-pre-wrap text-sm">
                  {selectedNotif.message || "No message content available."}
                </p>
              </div>

              <div className="flex flex-col gap-3 pt-4 border-t border-gray-50">
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <Clock size={14} />
                  <span>Received: {formatDate(selectedNotif.created_at)}</span>
                </div>
                {selectedNotif.related_id && (
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <Tag size={14} />
                    <span>Reference ID: {selectedNotif.related_id}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          /* Scrollable List View */
          <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-[#f8fafc]">
            {notifications && notifications.length > 0 ? (
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  className={`group relative bg-white p-3 rounded-2xl shadow-sm border border-gray-100 flex gap-4 items-start transition-all hover:shadow-md hover:translate-y-[-1px] cursor-pointer ${
                    !notif.is_read ? "ring-1 ring-blue-50" : ""
                  }`}
                  onClick={() => handleNotifClick(notif)}
                >
                  {/* Left Icon (Circular) */}
                  <div className="w-12 h-12 rounded-full bg-[#eef5f7] flex items-center justify-center shrink-0 group-hover:bg-[#e0eff2] transition-colors">
                    {getNotificationIcon(notif.message, notif.notification_type)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0 pr-4">
                    <div className="flex justify-between items-start mb-1">
                      <h4 className="text-[11px] font-black text-gray-800 uppercase tracking-[0.1em]">
                        {notif.title || "SYSTEM UPDATE"}
                      </h4>
                      {!notif.is_read && (
                        <span className="w-2.5 h-2.5 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]"></span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 leading-tight line-clamp-2">
                      {notif.message || "No message details provided."}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-12 text-center text-gray-400 flex flex-col items-center">
                <Clock size={48} className="mb-3 opacity-10" />
                <p className="text-sm font-medium italic">No new notifications.</p>
              </div>
            )}
          </div>
        )}
        
        {/* Footer */}
        {!selectedNotif && (
          <div className="p-4 bg-white border-t border-gray-50 text-center">
            <p className="text-[10px] text-gray-400 font-medium uppercase tracking-widest">
              End of list
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default NotificationModal;
