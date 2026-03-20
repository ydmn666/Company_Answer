# 企业知识检索系统 V1

这是一个面向企业内部场景的知识检索系统 `V1` 版本。

当前版本已经打通最小闭环：

- 上传内容
- 解析内容
- 文本切片
- 建立索引
- 用户提问
- 返回答案与引用

## 技术栈

- 前端：React、React Router、Axios、Zustand、Ant Design
- 后端：FastAPI、SQLAlchemy、Pydantic、python-multipart
- 数据库：PostgreSQL + pgvector
- 部署：Docker Compose

## 本地启动

1. 复制环境变量文件

```powershell
Copy-Item .env.example .env
Copy-Item .env.llm.example .env.llm
```

2. 启动项目

```powershell
docker compose up --build
```

3. 访问地址

- 前端：`http://localhost:5173`
- 后端接口文档：`http://localhost:8000/docs`

## V1 功能范围

- 支持文档上传
- 支持文本解析与切片
- 支持基础索引与检索
- 支持知识问答
- 支持返回引用依据
- 支持管理员 / 员工两种角色入口

## 模型配置

项目支持以下回答提供方：

- `local`
- `deepseek`
- `kimi`

请编辑 `.env.llm.example` 对应的环境变量，并复制为本地 `.env.llm` 后使用。

说明：

- `LLM_DEFAULT_PROVIDER` 可选：`local`、`deepseek`、`kimi`
- 前端问答页支持按问题切换模型
- 如果所选模型没有配置 `API Key`，后端会自动回退到 `local`

## 当前说明

当前 `V1` 更侧重于：

- 可运行
- 可演示
- 可继续迭代

它已经具备企业知识系统的基本骨架，但仍适合继续往更真实的检索、权限、索引和模型能力上扩展。
