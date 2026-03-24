import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FilePdfOutlined,
  FileTextOutlined,
  FileWordOutlined,
  SearchOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Checkbox,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Tag,
  Tabs,
  Typography,
  message,
} from "antd";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import {
  batchDeleteDocuments,
  deleteDocument,
  downloadDocumentSource,
  fetchDocument,
  fetchDocuments,
  updateDocument,
} from "../api/documents";
import { SectionCard } from "../components/SectionCard";

const FILE_TYPE_OPTIONS = [
  { label: "全部类型", value: "" },
  { label: "PDF", value: "PDF" },
  { label: "DOCX", value: "DOCX" },
  { label: "TXT", value: "TXT" },
];

const STATUS_META = {
  indexed: {
    label: "已完成",
    color: "success",
    description: null,
  },
  processing: {
    label: "处理中",
    color: "processing",
    description: "文档处理中，暂不可查看完整内容。完成后会自动刷新状态。",
  },
  failed: {
    label: "处理失败",
    color: "error",
    description: "文档处理失败，请重新上传或删除后重试。",
  },
};

const STATUS_ORDER = {
  indexed: 0,
  processing: 1,
  failed: 2,
};

function isAbortError(error) {
  return error?.name === "AbortError" || error?.code === "ERR_CANCELED";
}

function getFileTypeIcon(fileType) {
  if (fileType === "PDF") return <FilePdfOutlined />;
  if (fileType === "DOCX") return <FileWordOutlined />;
  return <FileTextOutlined />;
}

function getStatusMeta(status) {
  return STATUS_META[status] || {
    label: status || "未知",
    color: "default",
    description: "当前状态暂不可识别。",
  };
}

export function DocumentsPage() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const canManageDocuments = user?.role === "admin";
  const [documents, setDocuments] = useState([]);
  const [keyword, setKeyword] = useState("");
  const [fileType, setFileType] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [editingDocument, setEditingDocument] = useState(null);
  const [loadingList, setLoadingList] = useState(false);
  const [form] = Form.useForm();

  const loadDocuments = async (nextQuery = keyword, nextFileType = fileType, signal) => {
    try {
      setLoadingList(true);
      const data = await fetchDocuments(nextQuery, { signal, fileType: nextFileType });
      setDocuments(data.items || []);
      setSelectedIds((current) => current.filter((id) => (data.items || []).some((item) => item.id === id)));
    } catch (error) {
      if (isAbortError(error)) return;
      message.error("文档列表加载失败。");
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    loadDocuments("", "", controller.signal);
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      loadDocuments(keyword, fileType);
    }, 2000);

    return () => window.clearInterval(timer);
  }, [keyword, fileType]);

  const filtered = useMemo(() => {
    const q = keyword.trim().toLowerCase();
    const matched = !q
      ? documents
      : documents.filter((item) =>
          [item.title, item.summary, item.filename, item.file_type].some((field) =>
            field?.toLowerCase().includes(q),
          ),
        );

    return [...matched].sort((a, b) => {
      const statusGap = (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99);
      if (statusGap !== 0) return statusGap;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [documents, keyword]);

  const totalChunks = documents.reduce((sum, item) => sum + item.chunk_count, 0);
  const allChecked = Boolean(filtered.length) && filtered.every((item) => selectedIds.includes(item.id));
  const indeterminate = filtered.some((item) => selectedIds.includes(item.id)) && !allChecked;

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
      await loadDocuments();
    } catch (error) {
      if (error?.errorFields) return;
      message.error("文档更新失败。");
    }
  };

  const handleDeleteDocument = (document) => {
    Modal.confirm({
      title: "删除文档",
      content: "删除后会同时清理文档、切片、向量索引和源文件。",
      okButtonProps: { danger: true },
      onOk: async () => {
        await deleteDocument(document.id);
        message.success("文档已删除。");
        if (selectedDocument?.id === document.id) {
          setSelectedDocument(null);
          setDetailOpen(false);
        }
        await loadDocuments();
      },
    });
  };

  const handleBatchDelete = () => {
    if (!selectedIds.length) {
      message.warning("请先选择要删除的文档。");
      return;
    }

    Modal.confirm({
      title: "批量删除文档",
      content: `确认删除 ${selectedIds.length} 个文档吗？这会同时删除切片、向量索引和源文件。`,
      okButtonProps: { danger: true },
      onOk: async () => {
        const result = await batchDeleteDocuments(selectedIds);
        message.success(`已删除 ${result.deleted_count} 个文档。`);
        setSelectedIds([]);
        if (selectedDocument && result.ids.includes(selectedDocument.id)) {
          setSelectedDocument(null);
          setDetailOpen(false);
        }
        await loadDocuments();
      },
    });
  };

  const sourceItems = selectedDocument?.source_pages?.length
    ? selectedDocument.source_pages.map((page) => ({
        key: String(page.page_no),
        label: `第 ${page.page_no} 页`,
        children: <Typography.Paragraph style={{ whiteSpace: "pre-wrap" }}>{page.content}</Typography.Paragraph>,
      }))
    : [
        {
          key: "source-text",
          label: selectedDocument?.file_type === "PDF" ? "解析原文" : "原文",
          children: (
            <Typography.Paragraph style={{ whiteSpace: "pre-wrap" }}>
              {selectedDocument?.source_text || "暂无解析原文。"}
            </Typography.Paragraph>
          ),
        },
      ];

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
          {canManageDocuments ? (
            <>
              <Button
                danger
                disabled={!selectedIds.length}
                icon={<DeleteOutlined />}
                onClick={handleBatchDelete}
              >
                {"\u6279\u91cf\u5220\u9664"} {selectedIds.length ? `(${selectedIds.length})` : ""}
              </Button>
              <Button type="primary" icon={<UploadOutlined />} onClick={() => navigate("/documents/upload")}>
                {"\u4e0a\u4f20\u6587\u6863"}
              </Button>
            </>
          ) : null}
        </div>
      </div>

      <SectionCard className="page-fill-card documents-card" bodyClassName="documents-card-body">
        <div className="documents-toolbar">
          <Input
            prefix={<SearchOutlined />}
            placeholder="按标题、文件名、摘要搜索"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            className="table-filter wide"
          />
          <Select
            value={fileType}
            options={FILE_TYPE_OPTIONS}
            className="documents-type-select"
            onChange={(value) => {
              setFileType(value);
              loadDocuments(keyword, value);
            }}
          />
        </div>

        {canManageDocuments ? (
          <div className="documents-selection-bar">
            <Checkbox
              checked={allChecked}
              indeterminate={indeterminate}
              onChange={(event) => {
                if (event.target.checked) {
                  setSelectedIds(Array.from(new Set([...selectedIds, ...filtered.map((item) => item.id)])));
                  return;
                }
                setSelectedIds((current) => current.filter((id) => !filtered.some((item) => item.id === id)));
              }}
            >
              {"\u5168\u9009\u5f53\u524d\u5217\u8868"}
            </Checkbox>
            <Typography.Text type="secondary">
              {"\u5df2\u9009"} {selectedIds.length} {"\u4e2a\u6587\u6863"}
            </Typography.Text>
          </div>
        ) : null}

        <div className="content-scroll-area documents-list-area">
          {filtered.length ? (
            <div className="documents-list">
              {filtered.map((item) => {
                const statusMeta = getStatusMeta(item.status);
                const statusDescription = item.status === "indexed" ? item.summary : statusMeta.description;

                return (
                  <article key={item.id} className="document-record">
                    <div className="document-record-top">
                      <Space size="middle" wrap>
                        {canManageDocuments ? (
                          <Checkbox
                            checked={selectedIds.includes(item.id)}
                            onChange={(event) => {
                              setSelectedIds((current) =>
                                event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id),
                              );
                            }}
                          />
                        ) : null}
                        <div className="item-icon">{getFileTypeIcon(item.file_type)}</div>
                        <Typography.Text strong>{item.title}</Typography.Text>
                        <Tag bordered={false} className="chip-tag">{item.file_type}</Tag>
                        <Tag color={statusMeta.color}>{statusMeta.label}</Tag>
                      </Space>

                      <Space wrap>
                        <Button icon={<EyeOutlined />} onClick={() => openDetail(item.id)}>
                          {"\u67e5\u770b\u8be6\u60c5"}
                        </Button>
                        {canManageDocuments ? (
                          <>
                            <Button icon={<EditOutlined />} onClick={() => openEdit(item)}>
                              {"\u4fee\u6539"}
                            </Button>
                            <Button danger icon={<DeleteOutlined />} onClick={() => handleDeleteDocument(item)}>
                              {"\u5220\u9664"}
                            </Button>
                          </>
                        ) : null}
                      </Space>
                    </div>

                    <Typography.Paragraph className="document-record-summary">
                      {statusDescription}
                    </Typography.Paragraph>

                    <div className="document-meta-line">
                      <span>{item.filename}</span>
                      <span>{item.chunk_count} 个切片</span>
                      <span>{item.source_file_exists ? "已保存源文件" : "源文件缺失"}</span>
                      <span>创建于 {new Date(item.created_at).toLocaleString()}</span>
                      <span>更新于 {new Date(item.updated_at).toLocaleString()}</span>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <Empty description={loadingList ? "正在加载文档..." : "没有符合条件的文档。"} />
          )}
        </div>
      </SectionCard>

      <Drawer
        title={selectedDocument?.title || "文档详情"}
        width={860}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      >
        {selectedDocument ? (
          <Space direction="vertical" size="large" style={{ width: "100%" }}>
            <div className="detail-meta-grid">
              <div className="metric-box">
                <span className="metric-box-value">{getStatusMeta(selectedDocument.status).label}</span>
                <span className="metric-box-label">当前状态</span>
              </div>
              <div className="metric-box">
                <span className="metric-box-value">{selectedDocument.chunk_count}</span>
                <span className="metric-box-label">切片数量</span>
              </div>
            </div>

            <SectionCard title="基础信息" subtitle="文件类型、源文件状态和摘要">
              <Space direction="vertical" size="small" style={{ width: "100%" }}>
                <Typography.Text>文件名：{selectedDocument.filename}</Typography.Text>
                <Typography.Text>文件类型：{selectedDocument.file_type}</Typography.Text>
                <Typography.Text>内容类型：{selectedDocument.content_type || "未知"}</Typography.Text>
                <Typography.Text>源文件状态：{selectedDocument.source_file_exists ? "可下载" : "已缺失"}</Typography.Text>
                <Typography.Text>更新时间：{new Date(selectedDocument.updated_at).toLocaleString()}</Typography.Text>
                <Typography.Paragraph>
                  {selectedDocument.status === "indexed"
                    ? selectedDocument.summary
                    : getStatusMeta(selectedDocument.status).description}
                </Typography.Paragraph>
                <Space wrap>
                  <Button
                    icon={<DownloadOutlined />}
                    disabled={!selectedDocument.source_file_exists}
                    onClick={() => downloadDocumentSource(selectedDocument.id, selectedDocument.filename)}
                  >
                    下载源文件
                  </Button>
                </Space>
              </Space>
            </SectionCard>

            {selectedDocument.status === "indexed" ? (
              <>
                <SectionCard
                  title="原文查看"
                  subtitle={selectedDocument.file_type === "PDF" ? "PDF 优先按页回溯" : "解析原文视图"}
                >
                  <Tabs items={sourceItems} />
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
              </>
            ) : (
              <SectionCard title={getStatusMeta(selectedDocument.status).label} subtitle="等待文档状态更新">
                <Typography.Paragraph>{getStatusMeta(selectedDocument.status).description}</Typography.Paragraph>
              </SectionCard>
            )}
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
