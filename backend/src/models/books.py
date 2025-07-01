from models import Base
from sqlalchemy.orm import Mapped, mapped_column


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(nullable=False)
    link: Mapped[str] = mapped_column(nullable=False)
    image_links: Mapped[list[str]] = mapped_column(nullable=False)
