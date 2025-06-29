from models import Base
import functools
import itertools
from typing import Optional, Union, Iterable
from sqlalchemy import Column,DateTime,ForeignKey, Table, UniqueConstraint, func, Enum
from sqlalchemy.orm import Mapped, mapped_column,relationship,query_expression,with_expression
from sqlalchemy.orm.strategy_options import _AbstractLoad
from sqlalchemy.sql.expression import exists
from sqlalchemy_utils import generic_repr
from datetime import datetime


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(nullable=False)
    link: Mapped[str] = mapped_column(nullable=False)
    image_links: Mapped[list[str]] = mapped_column(nullable=False)