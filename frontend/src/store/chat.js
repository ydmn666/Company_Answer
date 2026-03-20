import { create } from "zustand";

export const useChatStore = create((set) => ({
  // 问答页核心前端状态。
  activeSessionId: null,
  messages: [],
  setActiveSessionId: (activeSessionId) => set({ activeSessionId }),
  setMessages: (messages) => set({ messages }),
  appendMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  resetMessages: () => set({ messages: [] }),
}));
