import datetime
from typing import Optional

from pydantic import EmailStr, SecretStr,field_validator


import models as m

from .base import BaseSchema


class LoginUser(BaseSchema):
    email: EmailStr
    password: SecretStr


class NewUser(BaseSchema):
    username: str
    email: EmailStr
    password: str
