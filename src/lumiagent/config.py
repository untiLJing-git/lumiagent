"""Application configuration with Pydantic Settings."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderConfig(BaseSettings):
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


class PlatformConfig(BaseSettings):
    cmd_enabled: bool = True
    web_enabled: bool = True
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    web_secret_key: str = "change-me"
    feishu_enabled: bool = False
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""
    dingtalk_enabled: bool = False
    dingtalk_client_id: str = ""
    dingtalk_client_secret: str = ""
    wechat_enabled: bool = False
    wechat_corp_id: str = ""
    wechat_corp_secret: str = ""
    wechat_agent_id: str = ""
    wechat_token: str = ""
    wechat_aes_key: str = ""


class MemoryConfig(BaseSettings):
    short_term_max_turns: int = 20
    short_term_backend: str = "memory"  # memory / redis
    long_term_backend: str = "sqlite"
    db_path: str = "./data/memory.db"
    compression_enabled: bool = True
    compression_threshold_turns: int = 50
    redis_url: Optional[str] = None


class RAGConfig(BaseSettings):
    enabled: bool = True
    vector_store: str = "chroma"  # chroma / milvus
    chroma_path: str = "./data/chroma"
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5
    rerank_enabled: bool = True


class ToolConfig(BaseSettings):
    bash_enabled: bool = True
    bash_timeout: int = 30
    mcp_servers: list[dict] = Field(default_factory=list)


class EvalConfig(BaseSettings):
    enabled: bool = False
    eval_sets_dir: str = "./evals"
    judge_model: str = "gpt-4o"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "LumiAgent"
    debug: bool = False
    log_level: str = "INFO"
    data_dir: Path = Path("./data")

    # LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    primary_llm_provider: str = "openai"
    fallback_llm_provider: str = "deepseek"

    # Sub-configs
    platform: PlatformConfig = Field(default_factory=PlatformConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    tools: ToolConfig = Field(default_factory=ToolConfig)
    evaluation: EvalConfig = Field(default_factory=EvalConfig)

    # Agent
    max_react_iterations: int = 10
    system_prompt_path: Optional[str] = None
    max_context_tokens: int = 128000

    def get_llm_config(self, provider: str) -> LLMProviderConfig:
        configs = {
            "openai": LLMProviderConfig(
                provider="openai",
                model=self.openai_model,
                api_key=self.openai_api_key,
                base_url=self.openai_base_url,
            ),
            "anthropic": LLMProviderConfig(
                provider="anthropic",
                model=self.anthropic_model,
                api_key=self.anthropic_api_key,
            ),
            "deepseek": LLMProviderConfig(
                provider="deepseek",
                model=self.deepseek_model,
                api_key=self.deepseek_api_key,
                base_url=self.deepseek_base_url,
            ),
        }
        if provider not in configs:
            raise ValueError(f"Unknown LLM provider: {provider}")
        return configs[provider]

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    return Settings()
