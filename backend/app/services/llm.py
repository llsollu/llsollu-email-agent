"""사내 Gemma-4 (OpenAI 호환) 클라이언트 + Redis 동시성 게이트."""

import json
from dataclasses import dataclass

import redis.asyncio as aioredis
from openai import AsyncOpenAI

from app.config import settings

_SEM_KEY = "llm:concurrency"


@dataclass
class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int
    model: str


class LLMClient:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
        self._redis = aioredis.from_url(settings.redis_url)

    async def _acquire(self) -> None:
        # 단순 동시성 게이트: INCR 후 한도 초과면 잠시 대기.
        import asyncio

        while True:
            n = await self._redis.incr(_SEM_KEY)
            if n <= settings.llm_max_concurrency:
                await self._redis.expire(_SEM_KEY, 120)
                return
            await self._redis.decr(_SEM_KEY)
            await asyncio.sleep(0.5)

    async def _release(self) -> None:
        await self._redis.decr(_SEM_KEY)

    async def complete(self, system: str, user: str, temperature: float = 0.2) -> LLMResult:
        await self._acquire()
        try:
            resp = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
        finally:
            await self._release()
        usage = resp.usage
        return LLMResult(
            text=resp.choices[0].message.content or "",
            tokens_in=getattr(usage, "prompt_tokens", 0) or 0,
            tokens_out=getattr(usage, "completion_tokens", 0) or 0,
            model=settings.llm_model,
        )

    async def complete_json(self, system: str, user: str) -> dict:
        """JSON 응답을 강제하고 파싱. 모델이 코드펜스를 붙여도 견고하게 처리."""
        result = await self.complete(
            system + "\n반드시 유효한 JSON 하나만 출력하라. 설명 금지.", user, temperature=0.1
        )
        return _extract_json(result.text)


def _extract_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if t.count("```") >= 2 else t.strip("`")
        if t.startswith("json"):
            t = t[4:]
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1:
        t = t[start : end + 1]
    return json.loads(t)
