import { EyeOutlined, FileTextOutlined, SearchOutlined, UploadOutlined } from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import { Button, Drawer, Empty, Input, Space, Tag, Typography, message } from "antd";
import { useNavigate } from "react-router-dom";
import { fetchDocument, fetchDocuments } from "../api/documents";
import { SectionCard } from "../components/SectionCard";

export function DocumentsPage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [keyword, setKeyword] = useState("");
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);

  useEffect(() => {
    fetchDocuments()
      .then((data) => setDocuments(data.items || []))
      .catch(() => message.error("文档列表加载失败。"));
  }, []);

  const filtered = useMemo(() => {
    const q = keyword.trim().toLowerCase();
    if (!q) return documents;
    return documents.filter((item) =>
      [item.title, item.summary, item.filename].some((field) => field?.toLowerCase().includes(q)),
    );
  }, [documents, keyword]);

  const totalChunks = documents.reduce((sum, item) => sum + item.chunk_count, 0);

  const openDetail = async (documentId) => {
    try {
      const detail = await fetchDocument(documentId);
      setSelectedDocument(detail);
      setDetailOpen(true);
    } catch {
      message.error("文档详情加载失败。");
    }
  };

  return (
    <div className="workspace-page-shell documents-shell">
      <div className="page-topbar documents-topbar">
        <div className="page-title-group">
          <Space size="middle" wrap>
            <Typography.Title level={4}>管理文档</Typography.Title>
            <Tag bordered={false} className="subtle-tag">文档数 {documents.length}</Tag>
            <Tag bordered={false} className="subtle-tag">切片数 {totalChunks}</Tag>
          </Space>
        </div>

        <div className="page-topbar-actions">
          <Button type="primary" icon={<UploadOutlined />} onClick={() => navigate("/documents/upload")}>
            上传文档
          </Button>
        </div>
      </div>

      <SectionCard className="page-fill-card documents-card" bodyClassName="documents-card-body">
        <div className="documents-toolbar">
          <Input
            prefix={<SearchOutlined />}
            placeholder="按标题、文件名或摘要筛选"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            className="table-filter wide"
          />
        </div>

        <div className="content-scroll-area documents-list-area">
          {filtered.length ? (
            <div className="documents-list">
              {filtered.map((item) => (
                <article key={item.id} className="document-record">
                  <div className="document-record-top">
                    <Space size="middle" wrap>
                      <div className="item-icon">
                        <FileTextOutlined />
                      </div>
                      <Typography.Text strong>{item.title}</Typography.Text>
                      <Tag bordered={false} className="chip-tag">{item.status}</Tag>
                    </Space>

                    <Button icon={<EyeOutlined />} onClick={() => openDetail(item.id)}>
                      查看详情
                    </Button>
                  </div>

                  <Typography.Paragraph className="document-record-summary">
                    {item.summary}
                  </Typography.Paragraph>

                  <div className="document-meta-line">
                    <span>{item.filename}</span>
                    <span>{item.chunk_count} 个切片</span>
                    <span>{new Date(item.created_at).toLocaleString()}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <Empty description="没有符合条件的文档。" />
          )}
        </div>
      </SectionCard>

      <Drawer
        title={selectedDocument?.title || "文档详情"}
        width={720}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      >
        {selectedDocument ? (
          <Space direction="vertical" size="large" style={{ width: "100%" }}>
            <div className="detail-meta-grid">
              <div className="metric-box">
                <span className="metric-box-value">{selectedDocument.status}</span>
                <span className="metric-box-label">当前状态</span>
              </div>
              <div className="metric-box">
                <span className="metric-box-value">{selectedDocument.chunk_count}</span>
                <span className="metric-box-label">切片数量</span>
              </div>
            </div>

            <SectionCard title="基础信息" subtitle="来源与摘要">
              <Space direction="vertical" size="small" style={{ width: "100%" }}>
                <Typography.Text>文件名：{selectedDocument.filename}</Typography.Text>
                <Typography.Text>文件类型：{selectedDocument.content_type || "未知"}</Typography.Text>
                <Typography.Paragraph>{selectedDocument.summary}</Typography.Paragraph>
              </Space>
            </SectionCard>

            <SectionCard title="切片内容" subtitle="文档切片明细">
              <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                {selectedDocument.chunks.map((chunk) => (
                  <div className="reference-card" key={chunk.id}>
                    <Typography.Text strong>切片 {chunk.chunk_index + 1}</Typography.Text>
                    <Typography.Paragraph>{chunk.content}</Typography.Paragraph>
                  </div>
                ))}
              </Space>
            </SectionCard>
          </Space>
        ) : null}
      </Drawer>
    </div>
  );
}
