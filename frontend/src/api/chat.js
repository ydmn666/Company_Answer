import { apiClient } from "./client";
import { useAuthStore } from "../store/auth";

export async function askQuestionStream(payload, handlers = {}, options = {}) {
  const token = useAuthStore.getState().token;
  const response = await fetch(`${apiClient.defaults.baseURL}/chat/ask-stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal: options.signal,
  });

  if (!response.ok) {
    let detail = "提问失败，请稍后重试。";
    try {
      const body = await response.json();
      detail = body?.detail || detail;
    } catch {
      // noop
    }
    throw new Error(detail);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("未收到流式响应。");
  }

  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  const emitEvent = (block) => {
    const lines = block.split("\n");
    let eventName = "message";
    const dataLines = [];

    lines.forEach((line) => {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    });

    if (!dataLines.length) return;

    const payloadText = dataLines.join("\n");
    let eventPayload = {};
    try {
      eventPayload = JSON.parse(payloadText);
    } catch {
      eventPayload = { raw: payloadText };
    }

    if (eventName === "session") handlers.onSession?.(eventPayload);
    if (eventName === "citations") handlers.onCitations?.(eventPayload.citations || []);
    if (eventName === "token") handlers.onToken?.(eventPayload.content || "");
    if (eventName === "done") handlers.onDone?.(eventPayload);
    if (eventName === "error") handlers.onError?.(eventPayload);
  };

  while (true) {
    if (options.signal?.aborted) {
      throw new DOMException("Aborted", "AbortError");
    }

    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    blocks.forEach(emitEvent);
  }

  if (buffer.trim()) {
    emitEvent(buffer);
  }
}

export async function fetchSessions(options = {}) {
  const response = await apiClient.get("/chat/sessions", {
    signal: options.signal,
  });
  return response.data;
}

export async function fetchSession(id, options = {}) {
  const response = await apiClient.get(`/chat/sessions/${id}`, {
    signal: options.signal,
  });
  return response.data;
}

export async function updateSession(id, payload) {
  const response = await apiClient.patch(`/chat/sessions/${id}`, payload);
  return response.data;
}

export async function deleteSession(id) {
  const response = await apiClient.delete(`/chat/sessions/${id}`);
  return response.data;
}
