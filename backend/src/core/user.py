from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

async def get_by_username_or_email(
    session: Session, username: Optional[str] = None, email: Optional[str] = None
) -> Optional[m.User]:
    """Get a user instance from its username"""
    stmt = select(m.User)
    if username is not None:
        stmt = stmt.where(m.User.username == username)
    elif email is not None:
        stmt = stmt.where(m.User.email == email)
    else:
        return None

    # TODO Don't do first here
    return (await session.scalars(stmt)).first()
