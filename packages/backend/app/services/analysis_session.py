"""Service layer for analysis session management."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models.analysis_session import AnalysisSession
from ..repositories.analysis_session import AnalysisSessionRepository
from .events import SessionEventManager


class AnalysisSessionService:
    """Service for managing analysis sessions."""

    def __init__(
        self,
        session: AsyncSession,
        event_manager: SessionEventManager,
    ):
        self.repository = AnalysisSessionRepository(session)
        self.event_manager = event_manager

    async def create_session(
        self,
        *,
        session_id: str,
        ticker: str,
        trade_date: str,
        selected_analysts: Optional[List[str]] = None,
    ) -> AnalysisSession:
        """Create a new analysis session record.

        Args:
            session_id: UUID string for the session
            ticker: Ticker symbol being analyzed
            trade_date: Trading date in ISO format (YYYY-MM-DD)
            selected_analysts: Optional list of selected analyst names

        Returns:
            The created analysis session
        """
        selected_analysts_json = None
        if selected_analysts:
            selected_analysts_json = json.dumps(selected_analysts)

        analysis_session = AnalysisSession(
            id=session_id,
            ticker=ticker,
            trade_date=trade_date,
            status="running",
            selected_analysts_json=selected_analysts_json,
            created_at=datetime.utcnow(),
        )

        return await self.repository.create(analysis_session)

    async def update_status(
        self,
        session_id: str,
        status: str,
        summary: Optional[Dict[str, Any]] = None,
    ) -> Optional[AnalysisSession]:
        """Update the status of an analysis session.

        Args:
            session_id: The session UUID string
            status: New status (pending, running, completed, failed)
            summary: Optional summary data to store

        Returns:
            The updated session if found, None otherwise
        """
        session = await self.repository.get_by_id(session_id)
        if not session:
            return None

        update_data: Dict[str, Any] = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }

        if summary:
            update_data["summary_json"] = json.dumps(summary)

        return await self.repository.update(db_obj=session, obj_in=update_data)

    async def get_session(self, session_id: str) -> Optional[AnalysisSession]:
        """Get an analysis session by ID.

        Args:
            session_id: The session UUID string

        Returns:
            The analysis session if found, None otherwise
        """
        return await self.repository.get_by_id(session_id)

    async def list_sessions(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        ticker: Optional[str] = None,
    ) -> List[AnalysisSession]:
        """List analysis sessions with optional filters.

        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            status: Optional status filter
            ticker: Optional ticker filter

        Returns:
            List of analysis sessions
        """
        if ticker:
            return await self.repository.get_by_ticker(
                ticker, skip=skip, limit=limit
            )
        return await self.repository.get_recent(skip=skip, limit=limit, status=status)

    def get_session_events(self, session_id: str) -> List[dict]:
        """Get recent events for a session from the event buffer.

        Args:
            session_id: The session UUID string

        Returns:
            List of event dictionaries with timestamps
        """
        return self.event_manager.get_recent_events(session_id)
