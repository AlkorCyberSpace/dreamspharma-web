import axios from "axios";
import { serverUrl } from "./serverUrl";

const axiosInstance = axios.create({
  baseURL: serverUrl,
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
    const {
      config,
      response: { status },
    } = error;
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
        const res = await axios.post(`${serverUrl}auth/token/refresh/`, {
          refresh: refresh,
        });

        const newAccess = res.data.access;
        localStorage.setItem("access", newAccess);

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
  return axios.post(`${serverUrl}auth/token/refresh/`, {
    refresh: refresh,
  });
};

export const loginAPI = (data) => {
  return axiosInstance.post("auth/login/", data);
};

export const getRetailersAPI = () => {
  return axiosInstance.get("superadmin/retailers/");
};

// SuperAdmin - Approve KYC
export const approveRetailerAPI = (userId) => {
  return axiosInstance.post(`superadmin/kyc/approve/${userId}/`);
};

// SuperAdmin - Reject KYC
export const rejectRetailerAPI = (userId, reason) => {
  return axiosInstance.post(`superadmin/kyc/reject/${userId}/`, reason);
};