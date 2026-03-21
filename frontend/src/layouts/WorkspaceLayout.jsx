import {
  DatabaseOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  HistoryOutlined,
  LogoutOutlined,
  MessageOutlined,
  MoreOutlined,
  PlusOutlined,
  PushpinOutlined,
  UploadOutlined,
  UserSwitchOutlined,
} from "@ant-design/icons";
import { Button, Dropdown, Empty, Input, Layout, Menu, Modal, Space, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { deleteSession, fetchSessions, updateSession } from "../api/chat";
import { useAuthStore } from "../store/auth";
import { useChatStore } from "../store/chat";

const { Sider, Header, Content } = Layout;

export function WorkspaceLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const resetMessages = useChatStore((state) => state.resetMessages);
  const setActiveSessionId = useChatStore((state) => state.setActiveSessionId);
  const [sessions, setSessions] = useState([]);
  const selectedSessionId = new URLSearchParams(location.search).get("session");

  const loadSessions = async () => {
    try {
      const data = await fetchSessions();
      setSessions(data || []);
    } catch {
      message.error("会话列表加载失败。");
    }
  };

  useEffect(() => {
    loadSessions();
  }, [location.pathname, location.search]);

  const navItems = [
    { key: "/chat", icon: <MessageOutlined />, label: "知识问答" },
    ...(user?.role === "admin"
      ? [
          { key: "/documents", icon: <FileTextOutlined />, label: "文档管理" },
          { key: "/documents/upload", icon: <UploadOutlined />, label: "上传文档" },
        ]
      : []),
  ];

  const roleText = user?.role === "admin" ? "管理员" : "员工";

  const handleRenameSession = (session) => {
    let nextTitle = session.title;
    Modal.confirm({
      title: "修改会话名称",
      content: (
        <Input
          autoFocus
          defaultValue={session.title}
          onChange={(event) => {
            nextTitle = event.target.value;
          }}
        />
      ),
      onOk: async () => {
        await updateSession(session.id, { title: nextTitle });
        message.success("会话名称已更新。");
        await loadSessions();
      },
    });
  };

  const handleTogglePin = async (session) => {
    try {
      await updateSession(session.id, { pinned: !session.pinned });
      message.success(session.pinned ? "已取消置顶。" : "已置顶会话。");
      await loadSessions();
    } catch {
      message.error("更新会话状态失败。");
    }
  };

  const handleDeleteSession = (session) => {
    Modal.confirm({
      title: "删除会话",
      content: "删除后该会话中的问答记录将一并移除，且无法恢复。",
      okButtonProps: { danger: true },
      onOk: async () => {
        await deleteSession(session.id);
        message.success("会话已删除。");
        if (selectedSessionId === session.id) {
          setActiveSessionId(null);
          resetMessages();
          navigate("/chat?new=1");
        }
        await loadSessions();
      },
    });
  };

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
                  <div
                    key={item.id}
                    className={`sidebar-history-item ${selectedSessionId === item.id ? "active" : ""}`.trim()}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/chat?session=${item.id}`)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        navigate(`/chat?session=${item.id}`);
                      }
                    }}
                  >
                    <span className="history-item-icon">
                      <HistoryOutlined />
                    </span>
                    <span className="history-item-copy">
                      <span className="history-item-title">
                        {item.title}
                        {item.pinned ? <PushpinOutlined className="history-pin-icon" /> : null}
                      </span>
                      <span className="history-item-time">
                        {item.message_count} 条消息 · {new Date(item.updated_at).toLocaleString()}
                      </span>
                    </span>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "rename", icon: <EditOutlined />, label: "修改名称" },
                          {
                            key: "pin",
                            icon: <PushpinOutlined />,
                            label: item.pinned ? "取消置顶" : "置顶会话",
                          },
                          { key: "delete", icon: <DeleteOutlined />, label: "删除会话", danger: true },
                        ],
                        onClick: ({ key, domEvent }) => {
                          domEvent.stopPropagation();
                          if (key === "rename") handleRenameSession(item);
                          if (key === "pin") handleTogglePin(item);
                          if (key === "delete") handleDeleteSession(item);
                        },
                      }}
                    >
                      <Button
                        type="text"
                        size="small"
                        icon={<MoreOutlined />}
                        className="history-item-action"
                        onClick={(event) => event.stopPropagation()}
                      />
                    </Dropdown>
                  </div>
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
