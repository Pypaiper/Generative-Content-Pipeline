from pydantic import Field
from pydantic.types import SecretStr
from pydantic_settings import BaseSettings
import os


class _Settings(BaseSettings):
    SECRET_KEY: SecretStr = Field(os.getenv("SECRET_KEY"))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DB_PASSWORD_AWS_KMS_URI: str = os.getenv("AWS_KMS_DB_PASSWORD_URI", "")
    DB_PASSWORD_AWS_KMS_REGION: str = os.getenv("AWS_KMS_DB_PASSWORD_REGION", "")
    OS_PASSWORD_AWS_KMS_URI: str = os.getenv("AWS_KMS_OS_PASSWORD_URI", "")


# Make this a singleton to avoid reloading it from the env everytime
SETTINGS = _Settings()
