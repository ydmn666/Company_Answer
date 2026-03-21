import { apiClient } from "./client";

export async function uploadDocument(formData) {
  const response = await apiClient.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function fetchDocuments(query) {
  const response = await apiClient.get("/documents", {
    params: query ? { query } : undefined,
  });
  return response.data;
}

export async function fetchDocument(id) {
  const response = await apiClient.get(`/documents/${id}`);
  return response.data;
}

export async function updateDocument(id, payload) {
  const response = await apiClient.patch(`/documents/${id}`, payload);
  return response.data;
}

export async function deleteDocument(id) {
  const response = await apiClient.delete(`/documents/${id}`);
  return response.data;
}
