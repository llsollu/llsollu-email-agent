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
    admin_emails: str = ""  # 쉼표 구분. 부트스트랩 관리자(항상 관리자 권한 유지)

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
    mail_poll_top: int = 50          # 폴링 1회당 최대 메일 수(버스트 대비)
    mail_poll_overlap_sec: int = 120  # 커서 경계 유실 방지용 겹침(재분석은 멱등)

    # 장기 운용(정리·아카이브)
    run_retention_days: int = 90      # agent_runs 보존 기간(경과분 삭제)
    project_archive_days: int = 30    # 완료 카드 자동 아카이브까지 경과일
    projects_page_limit: int = 500    # projects API 기본 반환 상한

    @property
    def allowed_networks_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_networks.split(",") if x.strip()]

    @property
    def allowed_ips_set(self) -> set[str]:
        return {x.strip() for x in self.allowed_ips.split(",") if x.strip()}

    @property
    def graph_configured(self) -> bool:
        return bool(self.graph_tenant_id and self.graph_client_id and self.graph_client_secret)

    @property
    def admin_emails_set(self) -> set[str]:
        return {x.strip().lower() for x in self.admin_emails.split(",") if x.strip()}

    def is_bootstrap_admin(self, email: str | None) -> bool:
        return bool(email) and email.lower() in self.admin_emails_set


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
