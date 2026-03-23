import { apiClient } from "./client";

function downloadBlob(blob, filename) {
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = filename || "document.bin";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
}

export async function uploadDocument(formData, options = {}) {
  const response = await apiClient.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    signal: options.signal,
  });
  return response.data;
}

export async function fetchDocuments(query, options = {}) {
  const response = await apiClient.get("/documents", {
    params: {
      ...(query ? { query } : {}),
      ...(options.fileType ? { file_type: options.fileType } : {}),
    },
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

export async function fetchChunkDetail(chunkId, options = {}) {
  const response = await apiClient.get(`/documents/chunks/${chunkId}`, {
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

export async function batchDeleteDocuments(ids) {
  const response = await apiClient.post("/documents/batch-delete", { ids });
  return response.data;
}

export async function downloadDocumentSource(id, filename) {
  const response = await apiClient.get(`/documents/${id}/download`, {
    responseType: "blob",
  });
  downloadBlob(response.data, filename);
}
