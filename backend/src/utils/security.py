from datetime import datetime, timedelta
from typing import Optional, cast

import bcrypt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.openapi.models import OAuthFlows
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from starlette.requests import Request

import requests
import core.user
import models as m
from db import get_db_session
from settings import SETTINGS



class Token(BaseModel):
    access_token: str
    token_type: str


class TokenContent(BaseModel):
    username: str


class OAuth2PasswordToken(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[dict] = None,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlows(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=False)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            return None
        return cast(str, param)
    

def get_password_hash(password: str) -> bytes:
    return bytes(
        bcrypt.hashpw(password=password.encode("utf-8"), salt=bcrypt.gensalt())
    )

def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    return bool(
        bcrypt.checkpw(
            password=plain_password.encode("utf-8"), hashed_password=hashed_password
        )
    )


async def authenticate_user(
    session: Session, email: str, password: str
) -> Optional[m.User]:
    """Verify the User/Password pair against the DB content"""
    user = await core.user.get_by_username_or_email(session, email=email)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(user: m.User) -> str:
    token_content = TokenContent(username=user.username)
    expire = datetime.utcnow() + timedelta(minutes=SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": token_content.model_dump_json()}
    encoded_jwt = jwt.encode(
        to_encode, SETTINGS.SECRET_KEY.get_secret_value(), algorithm=SETTINGS.ALGORITHM
    )
    return str(encoded_jwt)