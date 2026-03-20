import { ArrowRightOutlined, DatabaseOutlined, FileSearchOutlined, FolderOpenOutlined } from "@ant-design/icons";
import { Button, Space, Typography } from "antd";
import { Link } from "react-router-dom";

const featureCards = [
  {
    icon: <FileSearchOutlined />,
    title: "知识检索",
    description: "快速定位内部知识内容，支持问题查询与结果引用",
  },
  {
    icon: <DatabaseOutlined />,
    title: "上传文档",
    description: "上传制度、手册、流程资料，沉淀统一知识来源",
  },
  {
    icon: <FolderOpenOutlined />,
    title: "管理文档",
    description: "集中维护知识文档，保证内容清晰、可控、可追溯",
  },
];

const scenarioItems = [
  "制度与流程查询",
  "员工培训与入职知识",
  "IT 与运维支撑手册",
  "内部规范与知识沉淀",
];

const advantageItems = [
  "统一知识入口，减少重复沟通与信息散落",
  "问题、答案与引用同屏可见，提升可信度",
  "面向企业场景设计，兼顾文档管理与知识检索",
];

const flowItems = [
  { step: "01", title: "上传资料", description: "接入制度、手册、流程等内部文档" },
  { step: "02", title: "建立索引", description: "解析内容并形成统一可检索知识来源" },
  { step: "03", title: "问答引用", description: "面向员工提问并返回答案与引用依据" },
];

export function HomeLandingPage() {
  return (
    <div className="landing-page">
      <header className="landing-header">
        <div className="landing-brand">
          <span className="landing-brand-mark">EK</span>
          <div>
            <Typography.Text className="landing-brand-label">企业知识检索系统</Typography.Text>
            <Typography.Text className="landing-brand-sub">Enterprise Knowledge Retrieval</Typography.Text>
          </div>
        </div>
        <Space size="middle">
          <Link to="/login" className="landing-link">登录</Link>
          <Link to="/login">
            <Button type="primary">进入系统</Button>
          </Link>
        </Space>
      </header>

      <main className="landing-main">
        <section className="landing-hero">
          <div className="landing-hero-copy">
            <Typography.Text className="landing-eyebrow landing-fade-in">企业内部知识中台</Typography.Text>
            <Typography.Title className="landing-title landing-fade-in">
              让企业知识更容易被检索、被问到、被引用
            </Typography.Title>
            <Typography.Paragraph className="landing-subtitle landing-fade-in">
              面向企业内部知识场景，提供知识检索、文档上传与文档管理能力。
            </Typography.Paragraph>
          </div>

          <div className="landing-feature-grid">
            {featureCards.map((item, index) => (
              <article
                key={item.title}
                className={`landing-feature-card landing-slide-in delay-${index + 1}`}
              >
                <div className="landing-feature-icon">{item.icon}</div>
                <Typography.Title level={4}>{item.title}</Typography.Title>
                <Typography.Paragraph>{item.description}</Typography.Paragraph>
              </article>
            ))}
          </div>

          <div className="landing-hero-cta landing-fade-in late">
            <Link to="/login">
              <Button type="primary" size="large" icon={<ArrowRightOutlined />}>
                进入系统
              </Button>
            </Link>
          </div>
        </section>

        <section className="landing-section">
          <div className="landing-section-head">
            <Typography.Text className="landing-eyebrow">适用场景</Typography.Text>
            <Typography.Title level={2}>围绕内部知识协作的典型工作场景</Typography.Title>
          </div>
          <div className="landing-scenario-grid">
            {scenarioItems.map((item) => (
              <div key={item} className="landing-scenario-item">
                <span className="landing-scenario-dot" />
                <Typography.Text>{item}</Typography.Text>
              </div>
            ))}
          </div>
        </section>

        <section className="landing-section muted">
          <div className="landing-section-head">
            <Typography.Text className="landing-eyebrow">产品优势</Typography.Text>
            <Typography.Title level={2}>更像正式企业工具，而不是通用聊天壳</Typography.Title>
          </div>
          <div className="landing-advantage-grid">
            {advantageItems.map((item, index) => (
              <div key={item} className="landing-advantage-card">
                <span className="landing-advantage-index">0{index + 1}</span>
                <Typography.Paragraph>{item}</Typography.Paragraph>
              </div>
            ))}
          </div>
        </section>

        <section className="landing-section">
          <div className="landing-section-head">
            <Typography.Text className="landing-eyebrow">系统流程</Typography.Text>
            <Typography.Title level={2}>从资料接入到知识问答的简单闭环</Typography.Title>
          </div>
          <div className="landing-flow-grid">
            {flowItems.map((item) => (
              <div key={item.step} className="landing-flow-card">
                <span className="landing-flow-step">{item.step}</span>
                <Typography.Title level={4}>{item.title}</Typography.Title>
                <Typography.Paragraph>{item.description}</Typography.Paragraph>
              </div>
            ))}
          </div>
        </section>

        <section className="landing-footer-cta">
          <Typography.Title level={2}>让企业知识真正成为可检索、可引用的资产</Typography.Title>
          <Typography.Paragraph>
            在统一入口下管理文档、沉淀来源并支撑内部问答。
          </Typography.Paragraph>
          <Link to="/login">
            <Button type="primary" size="large" icon={<ArrowRightOutlined />}>
              进入系统
            </Button>
          </Link>
        </section>
      </main>
    </div>
  );
}
