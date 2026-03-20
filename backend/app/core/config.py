from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 统一收口后端环境变量配置。
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

    # .env 放基础配置，.env.llm 单独放模型密钥。
    model_config = SettingsConfigDict(env_file=(".env", ".env.llm"), extra="ignore")

    @property
    def normalized_cors_origins(self) -> list[str]:
        if isinstance(self.cors_origins, str):
            return [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return self.cors_origins


settings = Settings()
settings.cors_origins = settings.normalized_cors_origins
