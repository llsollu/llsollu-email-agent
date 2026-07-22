"""최초 부트스트랩용 테이블 생성(create_all). 실행: python -m app.tools.init_db

이후 스키마 변경은 alembic autogenerate 를 사용:
  alembic revision --autogenerate -m "change"
  alembic upgrade head
"""

import asyncio

from app.db import engine
from app.models import Base


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("테이블 생성 완료")


if __name__ == "__main__":
    asyncio.run(main())
