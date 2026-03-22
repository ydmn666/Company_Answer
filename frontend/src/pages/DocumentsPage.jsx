import {
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  FileTextOutlined,
  SearchOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import { Button, Drawer, Empty, Form, Input, Modal, Space, Tag, Typography, message } from "antd";
import { useNavigate } from "react-router-dom";
import { deleteDocument, fetchDocument, fetchDocuments, updateDocument } from "../api/documents";
import { SectionCard } from "../components/SectionCard";

function isAbortError(error) {
  return error?.name === "AbortError" || error?.code === "ERR_CANCELED";
}

export function DocumentsPage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [keyword, setKeyword] = useState("");
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [editingDocument, setEditingDocument] = useState(null);
  const [form] = Form.useForm();

  const loadDocuments = async (query = "", signal) => {
    try {
      const data = await fetchDocuments(query, { signal });
      setDocuments(data.items || []);
    } catch (error) {
      if (isAbortError(error)) return;
      message.error("文档列表加载失败。");
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    loadDocuments("", controller.signal);
    return () => controller.abort();
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
    } catch (error) {
      if (isAbortError(error)) return;
      message.error("文档详情加载失败。");
    }
  };

  const openEdit = (document) => {
    setEditingDocument(document);
    form.setFieldsValue({
      title: document.title,
      summary: document.summary,
    });
  };

  const handleSaveDocument = async () => {
    try {
      const values = await form.validateFields();
      const updated = await updateDocument(editingDocument.id, values);
      setEditingDocument(null);
      setSelectedDocument((current) => (current?.id === updated.id ? updated : current));
      message.success("文档信息已更新。");
      await loadDocuments(keyword);
    } catch (error) {
      if (error?.errorFields) return;
      message.error("文档更新失败。");
    }
  };

  const handleDeleteDocument = (document) => {
    Modal.confirm({
      title: "删除文档",
      content: "删除后该文档及其切片会被移除，相关历史引用可能无法继续查看。",
      okButtonProps: { danger: true },
      onOk: async () => {
        await deleteDocument(document.id);
        message.success("文档已删除。");
        if (selectedDocument?.id === document.id) {
          setSelectedDocument(null);
          setDetailOpen(false);
        }
        await loadDocuments(keyword);
      },
    });
  };

  return (
    <div className="workspace-page-shell documents-shell">
      <div className="page-topbar documents-topbar">
        <div className="page-title-group">
          <Space size="middle" wrap>
            <Typography.Title level={4}>文档管理</Typography.Title>
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

                    <Space wrap>
                      <Button icon={<EyeOutlined />} onClick={() => openDetail(item.id)}>
                        查看详情
                      </Button>
                      <Button icon={<EditOutlined />} onClick={() => openEdit(item)}>
                        修改
                      </Button>
                      <Button danger icon={<DeleteOutlined />} onClick={() => handleDeleteDocument(item)}>
                        删除
                      </Button>
                    </Space>
                  </div>

                  <Typography.Paragraph className="document-record-summary">{item.summary}</Typography.Paragraph>

                  <div className="document-meta-line">
                    <span>{item.filename}</span>
                    <span>{item.chunk_count} 个切片</span>
                    <span>创建于 {new Date(item.created_at).toLocaleString()}</span>
                    <span>更新于 {new Date(item.updated_at).toLocaleString()}</span>
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
        width={760}
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

            <SectionCard title="基础信息" subtitle="来源、摘要与更新时间">
              <Space direction="vertical" size="small" style={{ width: "100%" }}>
                <Typography.Text>文件名：{selectedDocument.filename}</Typography.Text>
                <Typography.Text>文件类型：{selectedDocument.content_type || "未知"}</Typography.Text>
                <Typography.Text>更新时间：{new Date(selectedDocument.updated_at).toLocaleString()}</Typography.Text>
                <Typography.Paragraph>{selectedDocument.summary}</Typography.Paragraph>
              </Space>
            </SectionCard>

            <SectionCard title="切片内容" subtitle="文档切片明细">
              <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                {selectedDocument.chunks.map((chunk) => (
                  <div className="reference-card" key={chunk.id}>
                    <Space wrap>
                      <Typography.Text strong>切片 {chunk.chunk_index + 1}</Typography.Text>
                      <Tag bordered={false} className="subtle-tag">{chunk.chunk_type}</Tag>
                      {chunk.section_title ? (
                        <Tag bordered={false} className="subtle-tag">{chunk.section_title}</Tag>
                      ) : null}
                      {chunk.page_no ? (
                        <Tag bordered={false} className="subtle-tag">第 {chunk.page_no} 页</Tag>
                      ) : null}
                      <Tag bordered={false} className="subtle-tag">{chunk.token_count} tokens</Tag>
                    </Space>
                    <Typography.Paragraph>{chunk.content}</Typography.Paragraph>
                  </div>
                ))}
              </Space>
            </SectionCard>
          </Space>
        ) : null}
      </Drawer>

      <Modal
        title="修改文档信息"
        open={Boolean(editingDocument)}
        onCancel={() => setEditingDocument(null)}
        onOk={handleSaveDocument}
        okText="保存"
      >
        <Form form={form} layout="vertical">
          <Form.Item label="文档标题" name="title" rules={[{ required: true, message: "请输入文档标题。" }]}>
            <Input />
          </Form.Item>
          <Form.Item label="文档摘要" name="summary" rules={[{ required: true, message: "请输入文档摘要。" }]}>
            <Input.TextArea rows={5} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
