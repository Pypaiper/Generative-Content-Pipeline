import models as m
from schemas.user import NewUser, UserResponse, User, LoginUser
from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db_session
from utils.security import (
    OAUTH2_SCHEME,
    authenticate_user,
    create_access_token,
    get_password_hash
)

router = APIRouter()

@router.post("/users", response_model=UserResponse)
async def register(
    user: NewUser = Body(..., embed=True),
    db_session: AsyncSession = Depends(get_db_session),
    # matrix_token: str = Depends(store_matrix_credentials)
):
    dump = user.model_dump()
    password = dump.pop("password")
    # print(matrix_token,"matrix_token2")
    instance = m.User(
        **dump,
        hashed_password=get_password_hash(password),
    )
    db_session.add(instance)
    await db_session.commit()
    token = create_access_token(instance)
    return UserResponse(user=User(token=token, **dump))


@router.post("/users/login", response_model=UserResponse)
async def login(
    user_input: LoginUser = Body(..., embed=True, alias="user"),
    db_session: AsyncSession = Depends(get_db_session),
):
    user = await authenticate_user(
        db_session, user_input.email, user_input.password.get_secret_value()
    )
    if user is None:
        raise ValueError("Invalid credentials")

    token = create_access_token(user)
    return UserResponse(user=User.from_user(token, user))