import React, { useState } from 'react';
import { Upload, Camera, Check, X } from 'lucide-react';

const Profile = () => {
  const [username, setUsername] = useState('John Carter');
  const [email, setEmail] = useState('Johncarter@gmail.com');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');

  return (
    <div className="h-full overflow-y-auto px-4 py-5 bg-white  border-l-2 border-gray-100 rounded-tl-3xl">
      {/* Header */}
      <div className="mb-10">
        <h1 className="text-xl font-semibold text-[#505050] tracking-tight">
          Profile Settings & Account Management
        </h1>
        <p className="text-xs text-[#505050] opacity-70 mt-1">
          Manage your personal details and account preferences securely.
        </p>
      </div>

      <div className="max-w-6xl">
        {/* Avatar and Upload Section */}
        <div className="flex flex-col md:flex-row items-center gap-10 mb-10">
          <div className="relative">
            <div className="w-44 h-44 rounded-full overflow-hidden border-4 border-white shadow-lg ring-1 ring-gray-100">
              <img
                src="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=200&h=200&auto=format&fit=crop"
                alt="Profile"
                className="w-full h-full object-cover"
              />
            </div>
            <button className="absolute bottom-0 right-0 p-2 bg-red-500 rounded-full text-white shadow-md hover:bg-red-600 transition-colors border-2 border-white">
              <Camera size={16} />
            </button>
          </div>

          <div className="flex-1 w-full">
            <div className="border-3 border-dashed border-gray-200 rounded-2xl p-8 flex flex-col items-center justify-center  cursor-pointer group">
              <div className="mb-3 p-3 bg-white rounded-xl shadow-sm group-hover:scale-110 transition-transform">
                <Upload size={24} className="text-gray-400" />
              </div>
              <p className="text-sm text-gray-500 font-medium text-center">
                Drag & drop medias, or <span className="text-teal-600 font-bold">Browse</span>
              </p>
              <p className="text-[11px] text-gray-400 mt-1 uppercase tracking-wider">
                Supported formats: PNG, JPG Maximum file size: 5MB
              </p>
            </div>
          </div>
        </div>

        {/* Personal Details Form */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-5">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-[#505050] ml-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-5 py-3 border border-gray-100 rounded-xl bg-gray-50/30 focus:bg-white focus:ring-2 focus:ring-teal-100 focus:border-teal-500 outline-none transition-all text-[#505050]"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-semibold text-[#505050] ml-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-5 py-3 border border-gray-100 rounded-xl bg-gray-50/30 focus:bg-white focus:ring-2 focus:ring-teal-100 focus:border-teal-500 outline-none transition-all text-[#505050]"
            />
          </div>
        </div>

        {/* Change Password Section */}
        <div className="mb-1">
          <h2 className="text-lg font-semibold text-[#505050] mb-4 tracking-tight">Change Password</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-[#505050] ml-1">Current Password</label>
              <input
                type="password"
                placeholder="Enter the current password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-5 py-3 border border-gray-100 rounded-xl bg-gray-50/30 focus:bg-white focus:ring-2 focus:ring-teal-100 focus:border-teal-500 outline-none transition-all text-[#505050] placeholder:text-gray-300"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold text-[#505050] ml-1">New Password</label>
              <input
                type="password"
                placeholder="Enter the new password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-5 py-3 border border-gray-100 rounded-xl bg-gray-50/30 focus:bg-white focus:ring-2 focus:ring-teal-100 focus:border-teal-500 outline-none transition-all text-[#505050] placeholder:text-gray-300"
              />
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row justify-end gap-4 pt-4 border-t border-gray-50 mt-8">
          <button className="px-10 py-3 border border-[#125B6C] text-[#125B6C] font-bold rounded-lg hover:bg-gray-50 transition-all uppercase tracking-wider text-sm min-w-[180px]">
            CANCEL
          </button>
          <button className="px-10 py-3 bg-[#125B6C] text-white font-bold rounded-lg hover:bg-[#0e4856] transition-all uppercase tracking-wider text-sm min-w-[180px] shadow-lg shadow-teal-900/10">
            Save
          </button>
        </div>
      </div>
    </div>
  );
};

export default Profile;
