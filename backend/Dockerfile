FROM python:3.12-slim

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 의존성 먼저 (레이어 캐시)
COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

EXPOSE 8000

# 기본 CMD 는 API. worker 는 compose 에서 command 오버라이드.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
