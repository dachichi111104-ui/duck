from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.models import User, Role
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_username(self, session: Session, username: str) -> User | None:
        stmt = (
            select(User)
            .options(joinedload(User.role))
            .where(User.username == username)
        )
        return session.execute(stmt).scalar_one_or_none()

    def get_all_with_roles(self, session: Session) -> list[User]:
        stmt = select(User).options(joinedload(User.role)).order_by(User.username)
        return list(session.execute(stmt).scalars().all())


class RoleRepository(BaseRepository[Role]):
    model = Role

    def get_by_name(self, session: Session, name: str) -> Role | None:
        return session.execute(select(Role).where(Role.name == name)).scalar_one_or_none()

    def get_all(self, session: Session) -> list[Role]:
        return list(session.execute(select(Role).order_by(Role.name)).scalars().all())
