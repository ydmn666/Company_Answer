# 企业知识检索与智能问答系统 V3.3

这是一个面向企业内部知识库场景的 RAG 应用，支持文档上传、混合检索、问答引用展示、多角色访问以及 Docker 化部署。

## 项目亮点

- 混合检索：`embedding + BM25 + reranker`
- 大模型接入：支持 `DeepSeek / Kimi / local`
- 文档解析：支持 `TXT / PDF / DOCX`
- 文档管理：支持查看、搜索、详情查看、源文件下载
- 角色能力：
  - 管理员：上传、修改、删除文档
  - 员工：只读访问文档管理，支持查看、搜索、下载
- 会话管理：新建、重命名、置顶、删除
- 引用展示：回答时展示命中的证据切片
- 容器部署：`frontend + backend + postgres + redis + nginx`

## V3.3 更新内容

- 新增 Nginx 反向代理，对外统一使用 `80` 端口访问
- 员工也可以进入“文档管理”，但只保留查看、搜索、详情、下载能力
- 新增第二个演示管理员账号：`admin2 / password`
- 补充服务器部署、健康检查和模型目录说明
- 支持从 `.hf-cache` 中加载本地检索模型目录

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
- `python-docx`
- `RapidOCR`

## 目录结构

```text
backend/
  app/
  scripts/
  tests/
frontend/
docker/
docker-compose.yml
README.md
```

## 本地启动

### 1. 准备环境变量

```powershell
Copy-Item .env.example .env
Copy-Item .env.llm.example .env.llm
```

至少需要检查以下配置：

- `DATABASE_URL`
- `REDIS_URL`
- `DEEPSEEK_API_KEY`
- `KIMI_API_KEY`

### 2. 启动服务

```powershell
docker compose up -d --build
```

默认访问地址：

- 前端：`http://localhost:5173`
- 后端文档：`http://localhost:8000/docs`

## 服务器部署注意事项

### 1. 模型目录

当前部署使用项目根目录下的：

```text
.hf-cache/
```

服务器中实际模型目录为：

- `.hf-cache/bge-m3`
- `.hf-cache/bge-reranker-v2-m3`

### 2. 检索模型路径配置

如果服务器使用的是手动上传后的普通模型目录，需要在 `.env.llm` 中显式指定：

```env
RETRIEVAL_EMBEDDING_MODEL=/models/hf/bge-m3
RETRIEVAL_RERANKER_MODEL=/models/hf/bge-reranker-v2-m3
```

否则程序会继续按默认 Hugging Face 模型名进行查找。

## 常用运维命令

重新构建并启动：

```bash
docker compose up -d --build
```

仅重启前后端：

```bash
docker compose restart backend
docker compose restart frontend
```

运行后端测试：

```bash
docker compose exec backend sh -lc "cd /app && python -m unittest discover -s tests"
```

健康检查：

```bash
curl http://127.0.0.1/health
```

查看后端日志：

```bash
docker compose logs --tail=200 backend
```

## 默认演示账号

- 管理员：`admin / password`
- 管理员：`admin2 / password`
- 员工：`employee / password`

## 当前版本边界

当前版本重点已经覆盖 AI 应用的核心闭环：

- 文档上传与知识库构建
- 检索增强问答
- 基础角色访问控制
- 容器化部署与服务器验证

登录安全、审批流和完整企业级权限治理仍然有继续完善空间，因此当前账号体系更适合作为演示与项目验证版本。
