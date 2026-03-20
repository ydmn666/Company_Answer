import { apiClient } from "./client";

export async function login(payload) {
  // 登录页提交账号密码后走这里。
  const response = await apiClient.post("/auth/login", payload);
  return response.data;
}

export async function fetchMe() {
  // 可用于刷新后恢复当前用户信息。
  const response = await apiClient.get("/auth/me");
  return response.data;
}
