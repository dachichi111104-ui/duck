from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import AIAnalysisSession, AIDetectionResult, AIAlert
from app.repositories.base_repository import BaseRepository


class AISessionRepository(BaseRepository[AIAnalysisSession]):
    model = AIAnalysisSession

    def get_all(self, session: Session) -> list[AIAnalysisSession]:
        stmt = select(AIAnalysisSession).order_by(AIAnalysisSession.started_at.desc())
        return list(session.execute(stmt).scalars().all())


class AIDetectionRepository(BaseRepository[AIDetectionResult]):
    model = AIDetectionResult

    def get_for_session(self, session: Session, session_id: int) -> list[AIDetectionResult]:
        stmt = select(AIDetectionResult).where(AIDetectionResult.session_id == session_id)
        return list(session.execute(stmt).scalars().all())


class AIAlertRepository(BaseRepository[AIAlert]):
    model = AIAlert

    def get_for_session(self, session: Session, session_id: int) -> list[AIAlert]:
        stmt = select(AIAlert).where(AIAlert.session_id == session_id)
        return list(session.execute(stmt).scalars().all())
