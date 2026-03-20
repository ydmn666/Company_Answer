import { apiClient } from "./client";

export async function askQuestion(payload) {
  // 问答主请求。
  const response = await apiClient.post("/chat/ask", payload);
  return response.data;
}

export async function fetchSessions() {
  // 左侧历史会话列表。
  const response = await apiClient.get("/chat/sessions");
  return response.data;
}

export async function fetchSession(id) {
  // 某条历史会话详情。
  const response = await apiClient.get(`/chat/sessions/${id}`);
  return response.data;
}
