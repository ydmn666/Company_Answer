from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/knowledge_v1"
    cors_origins: list[str] | str = ["http://localhost:5173"]

    llm_default_provider: str = "local"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_chat_model: str = "deepseek-chat"

    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_chat_model: str = "moonshot-v1-8k"

    retrieval_embedding_backend: str = "sentence_transformers"
    retrieval_embedding_model: str = "BAAI/bge-m3"
    retrieval_embedding_fallback_dim: int = 8
    retrieval_semantic_top_k: int = 24
    retrieval_keyword_top_k: int = 24
    retrieval_final_top_k: int = 5
    retrieval_neighbor_window: int = 1
    retrieval_reranker_enabled: bool = True
    retrieval_reranker_model: str = "BAAI/bge-reranker-v2-m3"
    retrieval_reranker_top_k: int = 10

    redis_url: str = "redis://redis:6379/0"
    redis_cache_enabled: bool = True
    redis_cache_ttl_seconds: int = 21600

    ocr_enabled: bool = True
    ocr_backend: str = "rapidocr"
    ocr_languages: str = "ch,en"

    eval_dataset_path: str = "eval_data/knowledge_eval.json"
    eval_recall_k: list[int] = Field(default_factory=lambda: [1, 3, 5])

    model_config = SettingsConfigDict(env_file=(".env", ".env.llm"), extra="ignore")

    @property
    def normalized_cors_origins(self) -> list[str]:
        if isinstance(self.cors_origins, str):
            return [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return self.cors_origins


settings = Settings()
settings.cors_origins = settings.normalized_cors_origins
