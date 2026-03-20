import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, theme } from "antd";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/global.css";

const appTheme = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: "#486a96",
    colorInfo: "#486a96",
    colorSuccess: "#4d7a6b",
    colorWarning: "#9a7a52",
    colorError: "#a46a6a",
    colorBgBase: "#eef3f7",
    colorBgContainer: "#ffffff",
    colorBorder: "#d3dce5",
    colorTextBase: "#1f2937",
    colorTextSecondary: "#5f6d7c",
    borderRadius: 18,
    fontFamily: "'Noto Sans SC', 'Segoe UI', sans-serif",
    fontSize: 16,
    boxShadowSecondary: "0 16px 36px rgba(31, 41, 55, 0.08)",
  },
  components: {
    Layout: {
      bodyBg: "#eef3f7",
      siderBg: "#f4f7fa",
      headerBg: "#eef3f7",
    },
    Button: { borderRadius: 12, controlHeight: 44, fontWeight: 500 },
    Input: { borderRadius: 12, controlHeight: 46 },
    Card: { borderRadiusLG: 22 },
  },
};

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ConfigProvider theme={appTheme}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>,
);
