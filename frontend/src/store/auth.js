import { create } from "zustand";

const storageKey = "knowledge-auth";

function readPersistedState() {
  // 登录态保存在 localStorage，页面刷新后还能恢复。
  try {
    return JSON.parse(localStorage.getItem(storageKey) || "{}");
  } catch {
    return {};
  }
}

export const useAuthStore = create((set) => ({
  token: readPersistedState().token || "",
  user: readPersistedState().user || null,
  setAuth: ({ token, user }) => {
    // 登录成功后统一在这里保存 token + 用户信息。
    localStorage.setItem(storageKey, JSON.stringify({ token, user }));
    set({ token, user });
  },
  logout: () => {
    // 主动退出或 token 失效时都走这里。
    localStorage.removeItem(storageKey);
    set({ token: "", user: null });
  },
}));
