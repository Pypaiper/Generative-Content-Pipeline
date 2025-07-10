from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Text(Base):
    __tablename__ = "text"
    id: Mapped[int] = mapped_column(primary_key=True)
    text_i: Mapped[int]
    book_id: Mapped[int]
    text: Mapped[str]
    author: Mapped[str]
    subject: Mapped[str]
    book_title: Mapped[str]
    image_path: Mapped[str]
