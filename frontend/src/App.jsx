import { App as AntdApp } from "antd";
import { AppRouter } from "./router";

export default function App() {
  return (
    <AntdApp>
      <AppRouter />
    </AntdApp>
  );
}
