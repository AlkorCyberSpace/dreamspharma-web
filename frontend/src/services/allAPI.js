import axios from "axios";
import { serverUrl } from "./serverUrl";

// const axiosInstance = axios.create({
//   baseURL: serverUrl,
// });
const axiosInstance = axios.create({
  baseURL: serverUrl,
  headers: {
    "ngrok-skip-browser-warning": "true"
  }
});
axiosInstance.interceptors.request.use(
  (config) => {
    const access = localStorage.getItem("access");

    if (access) {
      config.headers.Authorization = `Bearer ${access}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

let isRefreshing = false;
let refreshSubscribers = [];

const subscribeTokenRefresh = (cb) => {
  refreshSubscribers.push(cb);
};

const onRefreshed = (token) => {
  refreshSubscribers.map((cb) => cb(token));
  refreshSubscribers = [];
};

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status;
    const config = error.config;
    const originalRequest = config;

    if (status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(axiosInstance(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refresh = localStorage.getItem("refresh");

      if (!refresh) {
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const res = await axios.post(`${serverUrl}retailer-auth/token/refresh/`, {
          refresh: refresh,
        });

        const { access: newAccess, refresh: newRefresh } = res.data;
        localStorage.setItem("access", newAccess);
        if (newRefresh) {
          localStorage.setItem("refresh", newRefresh);
        }

        onRefreshed(newAccess);
        isRefreshing = false;

        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        return axiosInstance(originalRequest);
      } catch (err) {
        isRefreshing = false;
        refreshSubscribers = [];
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        window.location.href = "/login";
        return Promise.reject(err);
      }
    }

    return Promise.reject(error);
  }
);

export default axiosInstance;

export const refreshTokenAPI = async (refresh) => {
  return axios.post(`${serverUrl}retailer-auth/token/refresh/`, {
    refresh: refresh,
  });
};

export const loginAPI = (data) => {
  return axiosInstance.post("auth/login/", data);
};

// dashboard statistics
export const getDashboardStatsAPI = () => {
  return axiosInstance.get("superadmin/dashboard/statistics/");
};

export const getRetailersAPI = () => {
  return axiosInstance.get("superadmin/retailers/");
};

// SuperAdmin - Get Profile Information
export const getSuperAdminProfileAPI = () => {
  return axiosInstance.get("superadmin/profile/");
};

// SuperAdmin - Update Profile Image
export const updateSuperAdminProfileImageAPI = (data) => {
  return axiosInstance.post("superadmin/profile/image/", data, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

// SuperAdmin - Delete Profile Image
export const deleteSuperAdminProfileImageAPI = () => {
  return axiosInstance.delete("superadmin/profile/image/");
};

// SuperAdmin - Change Password
export const changeSuperAdminPasswordAPI = (data) => {
  return axiosInstance.post("superadmin/change-password/", data);
};

// SuperAdmin - Logout
export const superAdminLogoutAPI = () => {
  return axiosInstance.post("superadmin/logout/");
};

// SuperAdmin - Approve KYC
export const approveRetailerAPI = (userId) => {
  return axiosInstance.post(`superadmin/kyc/approve/${userId}/`);
};

// SuperAdmin - Reject KYC
export const rejectRetailerAPI = (userId, reason) => {
  return axiosInstance.post(`superadmin/kyc/reject/${userId}/`, reason);
};

// ERP - Get Master Data (Products)
export const getProductsAPI = () => {
  return axiosInstance.get("erp/ws_c2_services_get_master_data");
};

// ERP - Update Product Info (SuperAdmin Only)
export const updateProductInfoAPI = (data) => {
  return axiosInstance.post("erp/update_product_info/", data, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

// ==================== CATEGORIES ENDPOINTS ====================

export const getCategoriesAPI = () => {
  return axiosInstance.get("superadmin/add-category/");
};

export const addCategoryAPI = (data) => {
  return axiosInstance.post("superadmin/add-category/", data, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const updateCategoryAPI = (id, data) => {
  return axiosInstance.put(`superadmin/add-category/${id}/`, data, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const deleteCategoryAPI = (id) => {
  return axiosInstance.delete(`superadmin/add-category/${id}/`);
};

// ==================== BRANDS ENDPOINTS (Renamed from Category) ====================

// SuperAdmin - Assign Brand to Product
export const assignBrandToProductAPI = (data) => {
  return axiosInstance.post("superadmin/assign-brand/", data);
};

// ==================== ORDERS ENDPOINTS ====================

// ERP - Create Sales Order
export const createSalesOrderAPI = (data) => {
  return axiosInstance.post("erp/ws_c2_services_create_sale_order", data);
};

// ==================== OFFERS ENDPOINTS ====================

// Get all offers
export const getOffersAPI = () => {
  return axiosInstance.get("offers/");
};

// Add a new offer
export const addOfferAPI = (data) => {
  return axiosInstance.post("offers/", data, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

// Get offer details
export const getOfferDetailAPI = (id) => {
  return axiosInstance.get(`offers/${id}/`);
};

// Update an offer
export const updateOfferAPI = (id, data) => {
  return axiosInstance.put(`offers/${id}/`, data, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

// Delete an offer
export const deleteOfferAPI = (id) => {
  return axiosInstance.delete(`offers/${id}/`);
};

// ==================== ADMIN NOTIFICATIONS ENDPOINTS ====================

// SuperAdmin - List Notifications
export const getAdminNotificationsAPI = () => {
  return axiosInstance.get("superadmin/notifications/");
};

// SuperAdmin - Mark Notification as Read
export const markAdminNotificationReadAPI = (notificationId) => {
  return axiosInstance.post(`superadmin/notifications/${notificationId}/mark-read/`);
};
// SuperAdmin - audit logs
export const getAuditLogsAPI = (params) => {
  return axiosInstance.get("superadmin/audit-logs/", { params });
};

export const  getOrdersApi = (params) => {
  return axiosInstance.get("superadmin/orders/", { params });
}

export const getReportSummaryApi =() =>{
  return axiosInstance.get('superadmin/reports/summary/')
}