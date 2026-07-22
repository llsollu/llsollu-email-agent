from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # server
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    allowed_networks: str = ""
    allowed_ips: str = ""

    # auth
    allowed_email_domain: str = "llsollu.com"
    jwt_secret: str = "change-me"
    jwt_expire_hours: int = 720
    secret_enc_key: str = ""

    # data
    database_url: str = "postgresql+asyncpg://llsollu:llsollu@postgres:5432/llsollu_email_agent"
    redis_url: str = "redis://redis:6379/0"

    # llm
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: str = "not-needed"
    llm_max_concurrency: int = 4

    # graph
    graph_tenant_id: str = ""
    graph_client_id: str = ""
    graph_client_secret: str = ""
    graph_webhook_base_url: str = ""
    graph_webhook_client_state: str = "change-me"

    # scheduler
    scheduler_tz: str = "Asia/Seoul"
    mail_poll_interval_sec: int = 60

    @property
    def allowed_networks_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_networks.split(",") if x.strip()]

    @property
    def allowed_ips_set(self) -> set[str]:
        return {x.strip() for x in self.allowed_ips.split(",") if x.strip()}

    @property
    def graph_configured(self) -> bool:
        return bool(self.graph_tenant_id and self.graph_client_id and self.graph_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
