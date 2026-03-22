import { apiClient } from "./client";

export async function uploadDocument(formData, options = {}) {
  const response = await apiClient.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    signal: options.signal,
  });
  return response.data;
}

export async function fetchDocuments(query, options = {}) {
  const response = await apiClient.get("/documents", {
    params: query ? { query } : undefined,
    signal: options.signal,
  });
  return response.data;
}

export async function fetchDocument(id, options = {}) {
  const response = await apiClient.get(`/documents/${id}`, {
    signal: options.signal,
  });
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
