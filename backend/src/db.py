import json
import logging
import os

import boto3
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import scoped_session

from settings import SETTINGS

logger = logging.getLogger(__name__)


def aws_kms_secret(secret_name: str, region_name: str) -> str:
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    return str(client.get_secret_value(SecretId=secret_name)["SecretString"])


def connection_url() -> URL:
    host = os.getenv("DB_HOST", "db")
    if host == "":
        return URL.create("sqlite+aiosqlite")

    msg_source = ""
    if os.getenv("DB_PASSWORD", "postgres") is not None:
        msg_source = "environment"
        username = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "postgres")
    else:
        msg_source = "AWS Secrets Manager"
        secret = json.loads(
            aws_kms_secret(
                SETTINGS.DB_PASSWORD_AWS_KMS_URI, SETTINGS.DB_PASSWORD_AWS_KMS_REGION
            )
        )

        username = secret["username"]
        password = secret["password"]

    url = URL.create(
        "postgresql+asyncpg",
        username=username,
        password=password,
        host=host,
        port=int(os.getenv("DB_PORT", "5432")),
        database="qna_system",
    )

    logger.info(
        f"Using DB credentials supplied by: {msg_source}. "
        f"Connection string: {url.render_as_string(hide_password=True)}."
    )

    return url


engine = create_async_engine(connection_url(), echo=False)

async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncSession:
    session = scoped_session(async_session)
    try:
        yield session
    finally:
        await session.close()
