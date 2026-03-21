import {
  DownOutlined,
  EyeOutlined,
  LoadingOutlined,
  PlusOutlined,
  SendOutlined,
} from "@ant-design/icons";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Drawer, Dropdown, Empty, Input, Space, Tag, Typography, message } from "antd";
import { useSearchParams } from "react-router-dom";
import { askQuestionStream, fetchSession, fetchSessions } from "../api/chat";
import { fetchDocument } from "../api/documents";
import { SectionCard } from "../components/SectionCard";
import { useChatStore } from "../store/chat";

function summarizeCitation(snippet) {
  const cleaned = (snippet || "").replace(/\s+/g, " ").trim();
  if (cleaned.length <= 88) return cleaned;
  return `${cleaned.slice(0, 88)}...`;
}

export function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [provider, setProvider] = useState(localStorage.getItem("knowledge-provider") || "local");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [attachedFile, setAttachedFile] = useState(null);
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const [streamingProvider, setStreamingProvider] = useState("");
  const [pendingCitations, setPendingCitations] = useState([]);
  const fileInputRef = useRef(null);
  const streamRef = useRef(null);
  const messagesEndRef = useRef(null);
  const sendingRef = useRef(false);

  const messages = useChatStore((state) => state.messages);
  const activeSessionId = useChatStore((state) => state.activeSessionId);
  const appendMessage = useChatStore((state) => state.appendMessage);
  const setMessages = useChatStore((state) => state.setMessages);
  const resetMessages = useChatStore((state) => state.resetMessages);
  const setActiveSessionId = useChatStore((state) => state.setActiveSessionId);

  const citations = useMemo(() => {
    if (loading && pendingCitations.length) {
      return pendingCitations;
    }
    const latestAssistant = [...messages]
      .reverse()
      .find((item) => item.role === "assistant" && item.citations?.length);
    return latestAssistant?.citations || [];
  }, [loading, messages, pendingCitations]);

  useEffect(() => {
    const container = streamRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, loading]);

  useEffect(() => {
    const isNewSession = searchParams.get("new");
    const sessionId = searchParams.get("session");

    if (isNewSession) {
      resetMessages();
      setActiveSessionId(null);
      return;
    }

    if (sessionId) {
      fetchSession(sessionId)
        .then((detail) => {
          setActiveSessionId(detail.id);
          setMessages(detail.messages);
        })
        .catch(() => message.error("会话详情加载失败。"));
      return;
    }

    fetchSessions()
      .then((data) => {
        if (!data?.length) {
          resetMessages();
          setActiveSessionId(null);
          return null;
        }

        return fetchSession(data[0].id).then((detail) => {
          setActiveSessionId(detail.id);
          setMessages(detail.messages);
        });
      })
      .catch(() => message.error("会话加载失败。"));
  }, [searchParams, resetMessages, setActiveSessionId, setMessages]);

  const handleAsk = async () => {
    const trimmed = question.trim();
    if (!trimmed || sendingRef.current || loading) return;

    sendingRef.current = true;
    setLoading(true);
    setStreamingAnswer("");
    setStreamingProvider("");
    setPendingCitations([]);
    appendMessage({ role: "user", content: trimmed });
    setQuestion("");

    try {
      await askQuestionStream(
        { question: trimmed, session_id: activeSessionId, provider },
        {
          onSession: ({ session_id: sessionId }) => {
            if (!sessionId) return;
            setActiveSessionId(sessionId);
            setSearchParams({ session: sessionId });
          },
          onCitations: (citationsPayload) => {
            setPendingCitations(citationsPayload);
          },
          onToken: (content) => {
            setStreamingProvider(provider);
            setStreamingAnswer((current) => current + content);
          },
          onDone: (result) => {
            appendMessage({
              role: "assistant",
              content: result.answer,
              citations: result.citations,
              provider_used: result.provider_used,
            });
            setStreamingAnswer("");
            setStreamingProvider("");
            setPendingCitations([]);
          },
          onError: ({ detail }) => {
            throw new Error(detail || "提问失败，请稍后重试。");
          },
        },
      );
      setAttachedFile(null);
    } catch (error) {
      message.error(error.message || "提问失败，请稍后重试。");
      setQuestion(trimmed);
      setStreamingAnswer("");
      setStreamingProvider("");
      setPendingCitations([]);
    } finally {
      sendingRef.current = false;
      setLoading(false);
    }
  };

  const providerItems = [
    { key: "local", label: "本地回退模型" },
    { key: "deepseek", label: "DeepSeek" },
    { key: "kimi", label: "Kimi" },
  ];

  const openCitationDetail = async (citation) => {
    setSelectedCitation(citation);
    try {
      const detail = await fetchDocument(citation.document_id);
      setSelectedDocument(detail);
      setDetailOpen(true);
    } catch {
      message.error("引用详情加载失败。");
    }
  };

  return (
    <div className="workspace-page-shell knowledge-chat-shell">
      <div className="knowledge-chat-grid">
        <SectionCard className="page-fill-card knowledge-chat-card" bodyClassName="knowledge-chat-card-body">
          <div className="knowledge-chat-stream" ref={streamRef}>
            {messages.length || loading ? (
              <div className="message-thread">
                {messages.map((item, index) => (
                  <div key={`${item.role}-${index}`} className={`chat-row ${item.role}`}>
                    {item.role === "user" ? (
                      <article className="chat-bubble user-bubble">
                        <Typography.Paragraph>{item.content}</Typography.Paragraph>
                      </article>
                    ) : (
                      <article className="assistant-block">
                        <div className="assistant-meta">
                          <Typography.Text className="assistant-label">回答</Typography.Text>
                          {item.provider_used ? (
                            <Tag bordered={false} className="subtle-tag subtle-model-tag">
                              {item.provider_used}
                            </Tag>
                          ) : null}
                        </div>
                        <Typography.Paragraph>{item.content}</Typography.Paragraph>
                      </article>
                    )}
                  </div>
                ))}

                {loading ? (
                  <div className="chat-row assistant">
                    <article className="assistant-block pending-answer">
                      <div className="assistant-meta">
                        <Typography.Text className="assistant-label">处理中</Typography.Text>
                        {streamingProvider ? (
                          <Tag bordered={false} className="subtle-tag subtle-model-tag">
                            {streamingProvider}
                          </Tag>
                        ) : null}
                        <Tag bordered={false} className="subtle-tag subtle-model-tag icon-tag">
                          <LoadingOutlined spin />
                        </Tag>
                      </div>
                      <Typography.Paragraph>
                        {streamingAnswer || "正在检索文档并生成回答，请稍候。首次提问会更慢一些。"}
                      </Typography.Paragraph>
                    </article>
                  </div>
                ) : null}

                <div ref={messagesEndRef} />
              </div>
            ) : (
              <div className="chat-empty-state">
                <Empty
                  description="从左侧新建会话，或直接在下方输入问题开始检索企业知识。"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              </div>
            )}
          </div>

          <div className="knowledge-chat-composer">
            <div className="composer-shell">
              <Input.TextArea
                className="composer-textarea"
                autoSize={{ minRows: 2, maxRows: 5 }}
                value={question}
                disabled={loading}
                onChange={(event) => setQuestion(event.target.value)}
                onPressEnter={(event) => {
                  if (event.shiftKey || loading || sendingRef.current) return;
                  event.preventDefault();
                  handleAsk();
                }}
                placeholder={loading ? "正在生成回答，请稍候..." : "开始知识问答..."}
              />

              {attachedFile ? (
                <div className="composer-attachment">
                  <Tag bordered={false} className="subtle-tag">
                    {attachedFile.name}
                  </Tag>
                </div>
              ) : null}

              <div className="composer-actions">
                <div className="composer-tools">
                  <input
                    ref={fileInputRef}
                    type="file"
                    hidden
                    disabled={loading}
                    onChange={(event) => {
                      const file = event.target.files?.[0] || null;
                      setAttachedFile(file);
                    }}
                  />
                  <Button
                    type="text"
                    className="composer-tool-btn icon-only"
                    icon={<PlusOutlined />}
                    disabled={loading}
                    onClick={() => fileInputRef.current?.click()}
                  />
                  <Dropdown
                    menu={{
                      items: providerItems,
                      selectedKeys: [provider],
                      onClick: ({ key }) => {
                        setProvider(key);
                        localStorage.setItem("knowledge-provider", key);
                      },
                    }}
                    trigger={["click"]}
                    disabled={loading}
                  >
                    <Button type="text" className="composer-tool-btn" disabled={loading}>
                      <Space size={6}>
                        {providerItems.find((item) => item.key === provider)?.label || "模型"}
                        <DownOutlined />
                      </Space>
                    </Button>
                  </Dropdown>
                </div>

                <Button
                  type="primary"
                  shape="circle"
                  className="composer-send"
                  icon={loading ? <LoadingOutlined spin /> : <SendOutlined />}
                  loading={loading}
                  disabled={loading || sendingRef.current || !question.trim()}
                  onClick={handleAsk}
                />
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          className="page-fill-card knowledge-citation-panel"
          title="引用依据"
          subtitle={`当前 ${citations.length} 条引用`}
          bodyClassName="knowledge-citation-body"
        >
          <div className="knowledge-citation-list">
            {citations.length ? (
              citations.map((citation) => (
                <article key={citation.chunk_id} className="reference-card evidence-card">
                  <div className="reference-card-head">
                    <Typography.Text strong>{citation.document_title}</Typography.Text>
                    <Button type="text" icon={<EyeOutlined />} onClick={() => openCitationDetail(citation)}>
                      查看
                    </Button>
                  </div>
                  <Typography.Paragraph>
                    {summarizeCitation(citation.snippet)}
                    {citation.page_no ? ` 第 ${citation.page_no} 页` : ""}
                  </Typography.Paragraph>
                </article>
              ))
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="回答命中文档后，这里会展示对应的引用依据。" />
            )}
          </div>
        </SectionCard>
      </div>

      <Drawer
        title={selectedCitation ? `引用详情：${selectedCitation.document_title}` : "引用详情"}
        width={760}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      >
        {selectedDocument ? (
          <Space direction="vertical" size="large" style={{ width: "100%" }}>
            <SectionCard title="命中片段" subtitle="当前回答直接引用的文本内容">
              <Typography.Paragraph>
                {selectedCitation?.snippet}
                {selectedCitation?.page_no ? `（第 ${selectedCitation.page_no} 页）` : ""}
              </Typography.Paragraph>
            </SectionCard>

            <SectionCard title="文档详情" subtitle="原始文档摘要与切片内容">
              <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                <Typography.Text>文件名：{selectedDocument.filename}</Typography.Text>
                <Typography.Paragraph>{selectedDocument.summary}</Typography.Paragraph>
                {selectedDocument.chunks.map((chunk) => (
                  <div key={chunk.id} className="reference-card">
                    <Space wrap>
                      <Typography.Text strong>切片 {chunk.chunk_index + 1}</Typography.Text>
                      {chunk.page_no ? (
                        <Tag bordered={false} className="subtle-tag">
                          第 {chunk.page_no} 页
                        </Tag>
                      ) : null}
                      {chunk.section_title ? (
                        <Tag bordered={false} className="subtle-tag">
                          {chunk.section_title}
                        </Tag>
                      ) : null}
                    </Space>
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
