import { Card, Space, Typography } from "antd";

export function SectionCard({ title, subtitle, extra, children, className = "", bodyClassName = "" }) {
  return (
    <Card
      className={`section-card ${className}`.trim()}
      title={
        title ? (
          <Space direction="vertical" size={2}>
            <Typography.Text className="section-title">{title}</Typography.Text>
            {subtitle ? <Typography.Text className="section-subtitle">{subtitle}</Typography.Text> : null}
          </Space>
        ) : null
      }
      extra={extra}
      classNames={{ body: bodyClassName }}
    >
      {children}
    </Card>
  );
}
