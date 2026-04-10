import React, { useEffect, useState, useRef } from 'react';
import { Upload, Camera, Check, X, Trash2, AlertTriangle, Info, Eye, EyeOff } from 'lucide-react';
import { getSuperAdminProfileAPI, updateSuperAdminProfileImageAPI, deleteSuperAdminProfileImageAPI, changeSuperAdminPasswordAPI } from '../services/allAPI';
import { mediaUrl } from '../services/serverUrl';

const Profile = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [profileImage, setProfileImage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState({ show: false, message: "", type: "success" });
  const [confirmModal, setConfirmModal] = useState({ show: false, title: "", message: "", onConfirm: null });
  const fileInputRef = useRef(null);

  const showToast = (message, type = "success") => {
    setToast({ show: true, message, type });
    setTimeout(() => setToast({ show: false, message: "", type: "success" }), 3000);
  };

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await getSuperAdminProfileAPI();
        if (response.status === 200) {
          const profile = response.data.profile;
          setUsername(profile.username || '');
          setEmail(profile.email || '');
          if (profile.profile_image) {
            setProfileImage(profile.profile_image);
          }
          console.log(profile);
        }
      } catch (error) {
        console.error("Failed to fetch profile:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile()
  }, [])

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploading(true);
      try {
        const formData = new FormData();
        formData.append("profile_image", file);
        const response = await updateSuperAdminProfileImageAPI(formData);
        if (response.status === 200) {
          const newImagePath = response.data.data.profile_image;
          setProfileImage(newImagePath);
          showToast("Profile image updated successfully!", "success");
        }
      } catch (error) {
        console.error("Failed to upload image:", error);
        showToast("Failed to upload profile image.", "error");
      } finally {
        setUploading(false);
      }
    }
  };

  const handleImageDelete = async () => {
    setConfirmModal({
      show: true,
      title: "Remove Profile Image?",
      message: "Are you sure you want to remove your profile image? This action cannot be undone.",
      onConfirm: async () => {
        try {
          const response = await deleteSuperAdminProfileImageAPI();
          if (response.status === 200) {
            setProfileImage(null);
            showToast("Profile image removed successfully!", "success");
          }
        } catch (error) {
          console.error("Failed to delete image:", error);
          showToast("Failed to remove profile image.", "error");
        }
        setConfirmModal({ show: false, title: "", message: "", onConfirm: null });
      }
    });
  };

  const handlePasswordUpdate = async () => {
    if (!currentPassword || !newPassword) {
      showToast("Please fill in both password fields.", "error");
      return;
    }

    try {
      const response = await changeSuperAdminPasswordAPI({
        old_password: currentPassword,
        new_password: newPassword
      });

      if (response.status === 200) {
        showToast("Password changed successfully!", "success");
        setCurrentPassword('');
        setNewPassword('');
      }
    } catch (error) {
      console.error("Failed to change password:", error);

      let errorMessage = "Failed to change password.";

      if (error.response?.data) {
        const data = error.response.data;

        // Check for nested details first (more specific)
        if (data.details) {
          if (data.details.non_field_errors) {
            errorMessage = data.details.non_field_errors[0];
          } else {
            // Get the first error from any field (e.g., "new_password")
            const fieldErrors = Object.values(data.details);
            if (fieldErrors.length > 0 && Array.isArray(fieldErrors[0])) {
              errorMessage = fieldErrors[0][0];
            }
          }
        } else if (data.error) {
          errorMessage = data.error;
        }
      }

      showToast(errorMessage, "error");
    }
  };

  const handleCancel = () => {
    setCurrentPassword('');
    setNewPassword('');
    showToast("Changes discarded.", "info");
  };

  return (
    <div className="h-full overflow-y-auto ml-2 mt-3 bg-white ">
      <div className="mb-10">
        <h1 className="text-xl font-semibold text-[#505050] tracking-tight">
          Profile Settings & Account Management
        </h1>
        <p className="text-xs text-[#505050] opacity-70">
          Manage your personal details and account preferences securely.
        </p>
      </div>

      <div className="max-w-6xl">
        {/*  Upload Section */}
        <div className="flex flex-col md:flex-row items-center gap-10 mb-10">
          <div className="relative">
            <div className={`w-44 h-44 rounded-full overflow-hidden border-4 border-white shadow-lg ring-1 ring-gray-100 bg-[#E7F1F4] flex items-center justify-center relative group cursor-pointer`} onClick={() => fileInputRef.current.click()}>
              {(loading || uploading) ? (
                <div className="w-8 h-8 border-4 border-[#125B6C] border-t-transparent rounded-full animate-spin" />
              ) : profileImage ? (
                <img
                  src={profileImage.startsWith('http') ? profileImage : `${mediaUrl}${profileImage}?t=${new Date().getTime()}`}
                  alt="Profile"
                  className="w-full h-full object-cover group-hover:opacity-80 transition-opacity"
                />
              ) : (
                <div className="text-[#125B6C] font-bold text-5xl uppercase">
                  {username?.charAt(0) || 'A'}
                </div>
              )}
            </div>
            {profileImage ? (
              <button
                onClick={handleImageDelete}
                className="absolute bottom-0 right-0 p-2 bg-red-500 rounded-full text-white shadow-md hover:bg-red-600 transition-colors border-2 border-white"
              >
                <Trash2 size={16} />
              </button>
            ) : (
              <button
                onClick={() => fileInputRef.current.click()}
                className="absolute bottom-0 right-0 p-2 bg-red-500 rounded-full text-white shadow-md hover:bg-red-600 transition-colors border-2 border-white"
              >
                <Camera size={16} />
              </button>
            )}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleImageUpload}
              className="hidden"
              accept="image/*"
            />
          </div>

          <div className="flex-1 w-full">
            <div
              onClick={() => fileInputRef.current.click()}
              className="border-3 border-dashed border-gray-200 rounded-2xl p-8 flex flex-col items-center justify-center  cursor-pointer group"
            >
              <div className="mb-3 p-3 bg-white rounded-xl shadow-sm group-hover:scale-110 transition-transform">
                <Upload size={24} className={uploading ? "animate-bounce text-teal-600" : "text-gray-400"} />
              </div>
              <p className="text-sm text-gray-500 font-medium text-center">
                {uploading ? "Uploading..." : <>{"Drag & drop medias, or "}<span className="text-teal-600 font-bold">Browse</span></>}
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
              className="w-full px-5 py-2 border border-gray-100 rounded-xl bg-gray-50/30 focus:bg-white focus:ring-1 focus:border-teal-100 outline-none transition-all text-[#505050]"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-semibold text-[#505050] ml-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-5 py-2 border border-gray-100 rounded-xl bg-gray-50/30 focus:bg-white focus:ring-1 focus:border-teal-100 outline-none transition-all text-[#505050]"
            />
          </div>
        </div>

        {/* Change Password Section */}
        <div className="mb-1">
          <h2 className="text-lg font-semibold text-[#505050] mb-4 tracking-tight">Change Password</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-[#505050] ml-1">Current Password</label>
              <div className="relative">
                <input
                  type={showCurrentPassword ? "text" : "password"}
                  placeholder="Enter the current password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full px-5 py-2 border border-gray-100 rounded-xl bg-gray-50/30 focus:bg-white focus:ring-1 focus:border-teal-100 outline-none transition-all text-[#505050] placeholder:text-gray-300 pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-[#125B6C] transition-colors"
                >
                  {showCurrentPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold text-[#505050] ml-1">New Password</label>
              <div className="relative">
                <input
                  type={showNewPassword ? "text" : "password"}
                  placeholder="Enter the new password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-5 py-2 border border-gray-100 rounded-xl bg-gray-50/30 focus:bg-white focus:ring-1 focus:border-teal-100 outline-none transition-all text-[#505050] placeholder:text-gray-300 pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-[#125B6C] transition-colors"
                >
                  {showNewPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row justify-end gap-4 pt-4 border-t border-gray-50 mt-1">
          <button
            onClick={handleCancel}
            className="px-6 py-3 border border-[#125B6C] text-[#125B6C] font-bold rounded-lg hover:bg-gray-50 transition-all uppercase tracking-wider text-sm min-w-[180px]"
          >
            CANCEL
          </button>
          <button
            onClick={handlePasswordUpdate}
            className="px-6 py-3 bg-[#125B6C] text-white font-bold rounded-lg hover:bg-[#0e4856] transition-all uppercase tracking-wider text-sm min-w-[180px] shadow-lg shadow-teal-900/10"
          >
            Save
          </button>
        </div>
      </div>

      {toast.show && (
        <div className={`fixed top-6 right-6 z-[200] px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 transition-all duration-300 animate-in fade-in slide-in-from-top-4 ${toast.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
          {toast.type === 'success' ? <Check size={20} className="text-green-600" /> : <X size={20} className="text-red-600" />}
          <span className="text-sm font-semibold">{toast.message}</span>
          <button onClick={() => setToast({ show: false, message: "", type: "success" })} className="p-1 hover:bg-white/50 rounded-lg transition-colors"><X size={16} /></button>
        </div>
      )}

      {/* Custom Confirmation Modal */}
      {confirmModal.show && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in" onClick={() => setConfirmModal({ ...confirmModal, show: false })}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden text-center p-8 relative animate-in zoom-in-95 duration-200" onClick={(e) => e.stopPropagation()}>
            <div className="w-20 h-20 bg-red-50 text-red-500 rounded-full flex items-center justify-center mx-auto mb-6">
              <AlertTriangle size={40} />
            </div>
            <h3 className="text-2xl font-bold text-[#505050] mb-3">{confirmModal.title}</h3>
            <p className="text-sm text-gray-500 mb-8 leading-relaxed">{confirmModal.message}</p>
            <div className="flex gap-4 justify-center">
              <button
                onClick={() => setConfirmModal({ ...confirmModal, show: false })}
                className="px-4 py-2 text-sm font-bold text-[#505050] bg-gray-100 rounded-xl hover:bg-gray-200 transition-all flex-1 uppercase tracking-wider"
              >
                Cancel
              </button>
              <button
                onClick={confirmModal.onConfirm}
                className="px-4 py-2 text-sm font-bold text-white bg-red-500 rounded-xl hover:bg-red-600 transition-all flex-1 shadow-lg shadow-red-500/20 uppercase tracking-wider"
              >
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile;
