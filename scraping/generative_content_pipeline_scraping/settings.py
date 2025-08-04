from pydantic import Field
from pydantic.types import SecretStr
from pydantic_settings import BaseSettings
import os


class _Settings(BaseSettings):
    # RDS
    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_NAME: str = os.getenv("DB_NAME", "")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PORT: str = os.getenv("DB_PORT", "")
    DB_PASSWORD: SecretStr = Field(os.getenv("DB_PASSWORD", ""))

    # S3
    S3_HOST: str = os.getenv("S3_HOST", "")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    S3_REGION: str = os.getenv("S3_REGION", "")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")

    SECRET_KEY: SecretStr = Field(os.getenv("SECRET_KEY", ""))

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DB_PASSWORD_AWS_KMS_URI: str = os.getenv("AWS_KMS_DB_PASSWORD_URI", "")
    DB_PASSWORD_AWS_KMS_REGION: str = os.getenv("AWS_KMS_DB_PASSWORD_REGION", "")
    OS_PASSWORD_AWS_KMS_URI: str = os.getenv("AWS_KMS_OS_PASSWORD_URI", "")


# Make this a singleton to avoid reloading it from the env everytime
SETTINGS = _Settings()
