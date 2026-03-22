import { CheckCircleOutlined, InboxOutlined, LoadingOutlined } from "@ant-design/icons";
import { Button, Form, Input, Space, Steps, Tag, Typography, Upload, message } from "antd";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadDocument } from "../api/documents";
import { SectionCard } from "../components/SectionCard";

const uploadSteps = [
  { title: "上传文件", description: "提交文档标题与文件" },
  { title: "解析内容", description: "提取文本并完成切片" },
  { title: "建立索引", description: "生成向量并写入知识库" },
];

export function UploadPage() {
  const navigate = useNavigate();
  const [fileList, setFileList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState(-1);
  const [form] = Form.useForm();

  const isMultiFile = fileList.length > 1;
  const selectedCount = fileList.length;

  const helperText = useMemo(() => {
    if (!selectedCount) return "当前支持 TXT、PDF、DOCX 文件。";
    if (selectedCount === 1) return `已选择 1 个文件：${fileList[0].name}`;
    return `已选择 ${selectedCount} 个文件，多文件上传时将默认使用文件名作为标题。`;
  }, [fileList, selectedCount]);

  const handleSubmit = async (values) => {
    if (!fileList.length) {
      message.warning("请先选择文件。");
      return;
    }

    const formData = new FormData();
    const title = (values.title || "").trim();
    if (!isMultiFile && title) {
      formData.append("title", title);
    }
    fileList.forEach((file) => {
      formData.append("files", file.originFileObj);
    });

    setLoading(true);
    setStepIndex(0);

    try {
      setStepIndex(1);
      setStepIndex(2);
      const result = await uploadDocument(formData);
      const count = result?.items?.length || 0;
      message.success(count > 1 ? `已完成 ${count} 个文件上传并建立索引。` : "文档上传完成，已写入索引。");
      setFileList([]);
      form.resetFields();
      setStepIndex(3);
      setTimeout(() => navigate("/documents"), 800);
    } catch (error) {
      const detail = error.response?.data?.detail;
      message.error(detail || "上传失败，请稍后重试。");
      setStepIndex(-1);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="workspace-page-shell upload-shell">
      <div className="page-topbar upload-topbar">
        <div className="page-title-group">
          <Space size="middle" wrap>
            <Typography.Title level={4}>上传文档</Typography.Title>
            <Tag bordered={false} className="subtle-tag">上传</Tag>
            <Tag bordered={false} className="subtle-tag">解析</Tag>
            <Tag bordered={false} className="subtle-tag">索引</Tag>
          </Space>
        </div>

        <div className="page-topbar-actions">
          <Button onClick={() => navigate("/documents")}>返回文档列表</Button>
        </div>
      </div>

      <div className="upload-layout refined fill-mode">
        <SectionCard
          className="page-fill-card upload-main-card"
          title="上传资料"
          subtitle="支持一次选择多个文件并批量建立索引"
        >
          <Form form={form} layout="vertical" onFinish={handleSubmit} className="upload-form">
            <Form.Item
              label="文档标题"
              name="title"
              rules={
                isMultiFile
                  ? []
                  : [{ required: true, message: "请输入文档标题。" }]
              }
              extra={isMultiFile ? "多文件上传时将自动使用文件名作为标题。" : "单文件上传时可自定义标题。"}
            >
              <Input placeholder="例如：季度安全制度汇编" disabled={isMultiFile} />
            </Form.Item>

            <Form.Item label="上传文件">
              <Upload.Dragger
                multiple
                fileList={fileList}
                beforeUpload={() => false}
                onChange={({ fileList: nextList }) => setFileList(nextList)}
                className="upload-dropzone"
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <Typography.Text strong>拖拽文件到此处，或点击选择多个文件</Typography.Text>
                <Typography.Paragraph>{helperText}</Typography.Paragraph>
              </Upload.Dragger>
            </Form.Item>

            <div className="upload-form-footer">
              <Button type="primary" htmlType="submit" loading={loading}>
                上传并建立索引
              </Button>
            </div>
          </Form>
        </SectionCard>

        <SectionCard
          className="page-fill-card upload-side-card"
          title="处理状态"
          subtitle="当前接入阶段"
          bodyClassName="upload-side-body"
        >
          <Space direction="vertical" size="large" style={{ width: "100%" }}>
            <Steps
              direction="vertical"
              current={Math.min(stepIndex, 2)}
              items={uploadSteps.map((item, index) => ({
                ...item,
                icon:
                  stepIndex > index ? (
                    <CheckCircleOutlined />
                  ) : stepIndex === index ? (
                    <LoadingOutlined />
                  ) : undefined,
              }))}
            />

            <div className="note-group">
              <Typography.Text strong>适合上传的内容</Typography.Text>
              <Space wrap>
                <Tag bordered={false} className="chip-tag">制度规范</Tag>
                <Tag bordered={false} className="chip-tag">员工手册</Tag>
                <Tag bordered={false} className="chip-tag">操作流程</Tag>
                <Tag bordered={false} className="chip-tag">标准说明</Tag>
              </Space>
            </div>
          </Space>
        </SectionCard>
      </div>
    </div>
  );
}
