# 企业知识检索系统 V2

这是一个面向企业内部知识问答场景的 RAG 应用项目。`V2` 在 `V1` 最小可运行原型的基础上，补齐了检索底座、缓存、流式回答、文档管理和会话管理等核心能力，已经可以作为一版完整的阶段成果继续向 `V3` 演进。

## V2 核心升级

- 混合检索：`embedding（文字转向量数字）` + `BM25（关键词检索）` + `reranker（精排模型）`
- 向量检索开始下推到数据库侧，减少 Python 层全量扫描
- Redis 问答缓存，重复问题命中后可直接返回
- DeepSeek / Kimi / local 三种回答 provider，支持流式输出
- PDF / DOCX / TXT 基础解析，PDF 失败时支持 OCR 回退
- 更贴近真实场景的会话管理：重命名、置顶、删除
- 更贴近真实场景的文档管理：查看、编辑、删除
- 离线评测脚本与评测集初版，支持 `Recall@K / MRR / nDCG / Answer Hit Rate`

## 当前定位

`V2` 的重点是把系统从“能演示的原型”升级成“检索链路、交互链路和工程底座更完整的版本”。

当前更适合：

- 企业制度、手册、简历、FAQ 类文档
- 明确事实型问题
- 单轮或轻量多轮问答

当前仍待 `V3` 继续增强：

- 更强的问题理解
- 多轮上下文继承
- 长文档 / 论文类问答
- 回答中的引用与右侧证据更强绑定

## 技术栈

### 前端

- React
- React Router
- Axios
- Zustand
- Ant Design
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

### 1. 复制环境变量

```powershell
Copy-Item .env.example .env
Copy-Item .env.llm.example .env.llm
```

### 2. 按需填写模型配置

编辑 `.env.llm`：

- `LLM_DEFAULT_PROVIDER`
- `DEEPSEEK_API_KEY`
- `KIMI_API_KEY`
- 检索与 OCR 相关参数

说明：

- `.env` 和 `.env.llm` 已被 `.gitignore` 忽略，不应上传到仓库
- 未配置远程模型时，会自动回退到 `local`

### 3. 启动项目

```powershell
docker compose up --build
```

### 4. 访问地址

- 前端：`http://localhost:5173`
- 后端文档：`http://localhost:8000/docs`

## 关键配置

示例配置文件：

- [.env.example](/d:/Company_Answer/.env.example)
- [.env.llm.example](/d:/Company_Answer/.env.llm.example)

当前关键项包括：

- `DATABASE_URL`
- `REDIS_URL`
- `RETRIEVAL_EMBEDDING_MODEL`
- `RETRIEVAL_RERANKER_MODEL`
- `REDIS_CACHE_ENABLED`
- `OCR_ENABLED`

## V2 功能范围

### 文档处理

- 支持上传 `txt / pdf / docx`
- 支持基础文档解析与切片
- 保留页码、章节标题、前后相邻切片等元信息
- 支持 OCR 回退处理图片型 PDF

### 检索与问答

- 混合检索
- 相邻切片扩展
- 精排重排序
- 流式回答
- 引用依据展示
- Redis 精确缓存

### 会话与文档管理

- 新建会话
- 会话重命名 / 置顶 / 删除
- 文档查看 / 编辑 / 删除
- 文档详情与切片内容查看

## 离线评测

评测数据与脚本位置：

- [backend/eval_data/knowledge_eval.json](/d:/Company_Answer/backend/eval_data/knowledge_eval.json)
- [backend/scripts/evaluate_retrieval.py](/d:/Company_Answer/backend/scripts/evaluate_retrieval.py)

Docker 中执行：

```powershell
docker compose exec backend python scripts/evaluate_retrieval.py
```

当前输出：

- `Recall@K`
- `MRR`
- `nDCG`
- `Answer Hit Rate`

## 版本演进

### V1

- 最小闭环原型
- 文档上传、解析、切片、问答、引用展示跑通

### V2

- 检索底座升级
- 缓存、流式、文档管理、会话管理增强
- 基础 OCR 与离线评测接入

### V3 计划

- 问题理解
- 多轮上下文处理
- 长文档问答增强
- 更强的引用与证据绑定

## 注意事项

- 首次加载 `embedding` / `reranker` 模型时会更慢
- 长 PDF 文档解析耗时通常高于 Word / TXT
- 论文、报告类 PDF 因排版复杂，抽取文本与原文可能存在差异
- 当前版本不建议把复杂长文档问答能力视为最终形态，这部分放在 `V3` 持续增强
