import asyncio
import os
from collections.abc import AsyncGenerator

import asyncpg
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.api import dependencies
from app.api.dependencies import get_db_session
from app.core.config import settings
from app.main import app

test_session_factory = None

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://habit_user:habit_password@localhost:5432/habit_tracker_test",
)


async def create_test_database() -> None:
    parts = TEST_DATABASE_URL.rsplit("/", 1)
    maintenance_url = f"{parts[0]}/postgres"
    connection = await asyncpg.connect(maintenance_url.replace("+asyncpg", "", 1))
    try:
        exists = await connection.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'habit_tracker_test'"
        )
        if not exists:
            await connection.execute("CREATE DATABASE habit_tracker_test")
    finally:
        await connection.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def prepare_test_database() -> AsyncGenerator[None, None]:
    global test_session_factory
    await create_test_database()
    settings.database_url = TEST_DATABASE_URL
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    await asyncio.to_thread(command.upgrade, alembic_config, "head")

    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    test_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    dependencies.async_session_factory = test_session_factory

    yield

    async with test_engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE TABLE users, habits, habit_weekdays, check_ins, habit_freezes CASCADE")
        )
    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_database() -> AsyncGenerator[None, None]:
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    async with test_engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE TABLE users, habits, habit_weekdays, check_ins, habit_freezes CASCADE")
        )
    await test_engine.dispose()
    yield


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def override_db_session():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db_session, None)
