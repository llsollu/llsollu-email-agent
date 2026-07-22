"""arq 큐 연결 및 잡 투입 헬퍼."""

from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def enqueue_run(agent_id: str, trigger: str, payload: dict | None = None) -> None:
    """워커의 run_agent 태스크를 큐에 투입."""
    pool = await create_pool(redis_settings())
    try:
        await pool.enqueue_job("run_agent", agent_id, trigger, payload or {})
    finally:
        await pool.close()


async def enqueue_setup(agent_id: str) -> None:
    """워커의 setup_agent 태스크(on_setup 프로비저닝)를 큐에 투입."""
    pool = await create_pool(redis_settings())
    try:
        await pool.enqueue_job("setup_agent", agent_id)
    finally:
        await pool.close()


async def enqueue_teardown(agent_id: str, config: dict) -> None:
    """워커의 teardown_agent 태스크(구독 해제 등 정리)를 큐에 투입."""
    pool = await create_pool(redis_settings())
    try:
        await pool.enqueue_job("teardown_agent", agent_id, config)
    finally:
        await pool.close()
