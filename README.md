# Enterprise Knowledge Retrieval System V1

V1 scaffold for an enterprise knowledge retrieval system.

## Stack

- Frontend: React, React Router, Axios, Zustand, Ant Design
- Backend: FastAPI, SQLAlchemy, Pydantic, python-multipart
- Database: PostgreSQL + pgvector
- Deployment: Docker Compose

## Local startup

1. Copy the environment file:

   ```powershell
   Copy-Item .env.example .env
   Copy-Item .env.llm.example .env.llm
   ```

2. Start the stack:

   ```powershell
   docker compose up --build
   ```

3. Open the apps:

- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`

## V1 scope

- Upload content
- Parse content with placeholder extraction
- Build mock embeddings / retrieval
- Ask questions
- Return answer with citations

## LLM providers

- Edit `.env.llm` to configure `DeepSeek` or `Kimi`
- `LLM_DEFAULT_PROVIDER` supports `local`, `deepseek`, `kimi`
- The chat page lets users switch the answer provider per question
- If the selected provider has no API key configured, the backend falls back to `local`
