import { apiClient } from "./client";

export async function uploadDocument(formData) {
  // 上传文档页的提交入口。
  const response = await apiClient.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function fetchDocuments() {
  // 管理文档页列表数据。
  const response = await apiClient.get("/documents");
  return response.data;
}

export async function fetchDocument(id) {
  // 文档详情抽屉 / 引用详情数据。
  const response = await apiClient.get(`/documents/${id}`);
  return response.data;
}
