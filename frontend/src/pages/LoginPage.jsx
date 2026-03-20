import { ArrowRightOutlined, LockOutlined, UserOutlined } from "@ant-design/icons";
import { Button, Form, Input, Space, Tag, Typography, message } from "antd";
import { Link, useNavigate } from "react-router-dom";
import { login } from "../api/auth";
import { useAuthStore } from "../store/auth";

export function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  const handleSubmit = async (values) => {
    try {
      const result = await login(values);
      setAuth(result);
      navigate(result.user.role === "admin" ? "/documents" : "/chat");
    } catch (error) {
      const detail = error.response?.data?.detail;
      message.error(detail || "登录失败，请检查账号、密码或后端服务。");
    }
  };

  return (
    <div className="login-screen">
      <div className="login-screen-inner">
        <section className="login-intro-panel">
          <Typography.Text className="eyebrow">企业知识工作台</Typography.Text>
          <Typography.Title level={1}>
            让内部知识更容易被检索、被问到、被引用
          </Typography.Title>
          <Typography.Paragraph>
            面向企业内部知识场景，强调知识接入、可追溯问答、角色分工与专业可读的操作体验。
          </Typography.Paragraph>

          <div className="login-highlight-grid">
            <div className="metric-box">
              <span className="metric-box-value">管理员</span>
              <span className="metric-box-label">负责上传、查看文档与管理知识来源</span>
            </div>
            <div className="metric-box">
              <span className="metric-box-value">员工</span>
              <span className="metric-box-label">负责提问、查看回答与引用依据</span>
            </div>
            <div className="metric-box">
              <span className="metric-box-value">V1</span>
              <span className="metric-box-label">最小闭环：上传 - 索引 - 问答 - 引用</span>
            </div>
          </div>

          <Space wrap>
            <Tag bordered={false} className="chip-tag">专业克制</Tag>
            <Tag bordered={false} className="chip-tag">角色分流</Tag>
            <Tag bordered={false} className="chip-tag">中文界面</Tag>
          </Space>
        </section>

        <section className="login-form-panel">
          <div className="login-form-head">
            <div className="login-head-top">
              <Typography.Text className="eyebrow">账号登录</Typography.Text>
              <Link to="/welcome" className="back-to-landing-link">
                <span>返回引导页</span>
                <ArrowRightOutlined />
              </Link>
            </div>
            <Typography.Title level={3}>进入系统</Typography.Title>
            <Typography.Paragraph>
              管理员和员工都已预置演示账号，可直接验证不同角色入口。
            </Typography.Paragraph>
          </div>

          <div className="demo-account-box stacked">
            <Typography.Text strong>演示账号</Typography.Text>
            <Typography.Text className="muted-text">管理员：admin / password</Typography.Text>
            <Typography.Text className="muted-text">员工：employee / password</Typography.Text>
          </div>

          <Form
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{ username: "admin", password: "password" }}
          >
            <Form.Item
              label="用户名"
              name="username"
              rules={[{ required: true, message: "请输入用户名" }]}
            >
              <Input prefix={<UserOutlined />} placeholder="请输入用户名" />
            </Form.Item>
            <Form.Item
              label="密码"
              name="password"
              rules={[{ required: true, message: "请输入密码" }]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
            </Form.Item>
            <Button type="primary" htmlType="submit" block>
              登录系统
            </Button>
          </Form>
        </section>
      </div>
    </div>
  );
}
