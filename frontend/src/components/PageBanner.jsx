import { Typography } from "antd";

export function PageBanner({ eyebrow, title, description, metrics = [], className = "" }) {
  return (
    <section className={`page-banner ${className}`.trim()}>
      <div className="page-banner-copy">
        <Typography.Text className="eyebrow">{eyebrow}</Typography.Text>
        <Typography.Title level={2}>{title}</Typography.Title>
        <Typography.Paragraph>{description}</Typography.Paragraph>
      </div>
      <div className="page-banner-metrics">
        {metrics.map((item) => (
          <div className="metric-box" key={item.label}>
            <span className="metric-box-value">{item.value}</span>
            <span className="metric-box-label">{item.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
