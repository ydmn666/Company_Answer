# 企业知识检索系统 V3.0

这是一个面向企业内部知识问答场景的 RAG 项目。`V3.0` 在 `V2` 的混合检索、流式回答、文档解析和会话管理基础上，补上了多轮问答的核心能力，并对上传、检索稳定性和前端交互做了收口。

## V3.0 核心能力

- 混合检索：`embedding（文本向量） + BM25（关键词检索） + reranker（精排模型）`
- 多轮问答增强：支持轻量问题改写、上下文继承、连续追问
- 流式回答：支持 `DeepSeek / Kimi / local`
- 文档解析：支持 `TXT / PDF / DOCX`，PDF 失败时支持 OCR 回退
- 文档管理：查看、编辑、删除、批量上传
- 会话管理：新建、重命名、置顶、删除
- 引用面板：回答时展示对应证据切片
- 本地模型缓存：支持 Hugging Face 模型目录持久化和离线运行

## V3.0 相比 V2 的更新

- 增加问题理解：对短追问做轻量 `query rewrite（问题改写）`
- 增加上下文处理：回答时继承最近多轮消息
- 增加多轮问答能力：同一主题下支持连续追问
- 修复新会话首问时的时序问题，避免会话瞬间消失
- 上传页支持一次选择多个文件并批量建立索引
- 启动时不再注入默认 demo 文档，文档管理默认保持空库
- 支持本地模型缓存目录 `.hf-cache/`，避免重复下载模型

## 技术栈

### 前端

- React
- React Router
- Zustand
- Ant Design
- Axios
- Vite

### 后端

- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- pgvector
- Redis

### 检索与解析

- `BAAI/bge-m3`
- `BAAI/bge-reranker-v2-m3`
- `rank-bm25`
- `PyMuPDF`
- `pypdf`
- `python-docx`
- `RapidOCR`

## 目录结构

```text
backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
  eval_data/
  scripts/
frontend/
docker-compose.yml
README.md
```

## 本地启动

### 1. 准备环境变量

```powershell
Copy-Item .env.example .env
Copy-Item .env.llm.example .env.llm
```

按需填写：

- `DATABASE_URL`
- `REDIS_URL`
- `DEEPSEEK_API_KEY`
- `KIMI_API_KEY`

`.env` 和 `.env.llm` 已被 `.gitignore` 忽略，不会进入仓库。

### 2. 启动服务

```powershell
docker compose up -d --build
```

前端：`http://localhost:5173`  
后端文档：`http://localhost:8000/docs`

## 模型缓存与离线运行

推荐把 Hugging Face 模型缓存落到项目根目录：

```text
.hf-cache/
```

当前 `docker-compose.yml` 已支持：

- `HF_HOME`
- `HUGGINGFACE_HUB_CACHE`
- `SENTENCE_TRANSFORMERS_HOME`
- `HF_HUB_OFFLINE=1`
- `TRANSFORMERS_OFFLINE=1`

推荐流程：

1. 首次联网下载 `BAAI/bge-m3`
2. 首次联网下载 `BAAI/bge-reranker-v2-m3`
3. 之后默认离线读取本地缓存，不再重复联网拉模型

## 文档上传说明

- 支持 `txt / pdf / docx`
- 支持一次选择多个文件上传
- 单文件上传时可以自定义标题
- 多文件上传时默认使用文件名作为标题

删除文档时：

- 对应 `document_chunks` 会一起删除
- 对应向量也会一起删除
- 不会保留孤立切片

## 检索与问答链路

1. 用户提问
2. 轻量问题改写与上下文继承
3. 混合检索召回候选切片
4. reranker 精排
5. LLM 结合引用生成回答
6. 前端展示回答与证据

## 当前版本边界

V3.0 当前保持偏保守回答策略：

- 证据不足时优先拒答或收缩回答范围
- 不做“超出文档范围”的自由扩写
- 更重的局部归纳、源文件精准定位、引用样式增强，留到后续版本继续迭代

## 后续方向

- 引用展示与右侧证据统一优化
- 源文件回溯与原文定位
- 更自然的标题总结
- 更稳的多轮语义承接
- 更细粒度的证据片段命中展示
