import axios from "axios";
import { useAuthStore } from "../store/auth";

// 所有前端请求统一从这里出去。
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api",
  timeout: 15000,
});

apiClient.interceptors.request.use((config) => {
  // 把登录态里的 token 自动附加到每次请求。
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // token 失效时统一退出，避免前端状态脏掉。
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  },
);
