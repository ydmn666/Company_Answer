import {
  DatabaseOutlined,
  FileTextOutlined,
  HistoryOutlined,
  LogoutOutlined,
  MessageOutlined,
  PlusOutlined,
  UploadOutlined,
  UserSwitchOutlined,
} from "@ant-design/icons";
import { Button, Empty, Layout, Menu, Space, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { fetchSessions } from "../api/chat";
import { useAuthStore } from "../store/auth";

const { Sider, Header, Content } = Layout;

export function WorkspaceLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const [sessions, setSessions] = useState([]);
  const selectedSessionId = new URLSearchParams(location.search).get("session");

  useEffect(() => {
    fetchSessions()
      .then((data) => setSessions(data || []))
      .catch(() => message.error("会话列表加载失败。"));
  }, [location.pathname, location.search]);

  const navItems = [
    { key: "/chat", icon: <MessageOutlined />, label: "知识问答" },
    ...(user?.role === "admin"
      ? [
          { key: "/documents", icon: <FileTextOutlined />, label: "管理文档" },
          { key: "/documents/upload", icon: <UploadOutlined />, label: "上传文档" },
        ]
      : []),
  ];

  const roleText = user?.role === "admin" ? "管理员" : "员工";

  return (
    <Layout className="workspace-shell">
      <Sider width={264} breakpoint="lg" collapsedWidth="0" className="workspace-sider minimal gpt-style">
        <div className="workspace-brand compact">
          <div className="brand-icon">
            <DatabaseOutlined />
          </div>
          <div>
            <Typography.Text className="eyebrow">企业知识系统</Typography.Text>
            <Typography.Title level={5}>知识中台</Typography.Title>
          </div>
        </div>

        <div className="sidebar-main">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={navItems}
            className="workspace-nav"
            onClick={({ key }) => navigate(key)}
          />

          <div className="sidebar-history">
            <div className="sidebar-history-head">
              <Typography.Text className="eyebrow">最近会话</Typography.Text>
              <Button size="small" icon={<PlusOutlined />} onClick={() => navigate("/chat?new=1")}>
                新对话
              </Button>
            </div>

            <div className="sidebar-history-list">
              {sessions.length ? (
                sessions.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`sidebar-history-item ${selectedSessionId === item.id ? "active" : ""}`.trim()}
                    onClick={() => navigate(`/chat?session=${item.id}`)}
                  >
                    <span className="history-item-icon">
                      <HistoryOutlined />
                    </span>
                    <span className="history-item-copy">
                      <span className="history-item-title">{item.title}</span>
                      <span className="history-item-time">{new Date(item.created_at).toLocaleString()}</span>
                    </span>
                  </button>
                ))
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无历史会话" />
              )}
            </div>
          </div>
        </div>
      </Sider>

      <Layout>
        <Header className="workspace-header compact">
          <div className="header-right">
            <Tag bordered={false} className="subtle-tag header-role-tag">
              <Space size={6}>
                <UserSwitchOutlined />
                {roleText}
              </Space>
            </Tag>
            <Button
              icon={<LogoutOutlined />}
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              退出登录
            </Button>
          </div>
        </Header>

        <Content className="workspace-content">
          <div className="workspace-content-inner">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
