"""Vector Store Lifecycle Manager.

Manages the lifetime of the in-memory vector index and associated document session.
Default behavior is session-scoped — index and chunk text are dropped when the
document view is closed.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.models import DocumentSession
from src.embed_index.index import LocalVectorIndex


class VectorStoreManager:
    """Manages document sessions and their associated vector stores.

    Handles creation, lookup, and cleanup of document analysis sessions.
    """

    def __init__(self, session_timeout_minutes: int | None = None):
        """Initialize the lifecycle manager.

        Args:
            session_timeout_minutes: if set, sessions auto-expire after this duration.
                If None, sessions persist until explicitly cleared.
        """
        self._sessions: dict[str, DocumentSession] = {}
        self._session_timeout = session_timeout_minutes

    def create_session(self, document_id: str) -> DocumentSession:
        """Create a new session for a document.

        If a session already exists for this document_id, it is cleared first.
        """
        if document_id in self._sessions:
            self.clear_session(document_id)

        expires_at = None
        if self._session_timeout is not None:
            expires_at = datetime.now() + timedelta(minutes=self._session_timeout)

        session = DocumentSession(
            document_id=document_id,
            expires_at=expires_at,
        )
        self._sessions[document_id] = session
        return session

    def get_session(self, document_id: str) -> DocumentSession | None:
        """Retrieve a session by document ID.

        Returns None if the session doesn't exist or has expired.
        """
        session = self._sessions.get(document_id)
        if session is None:
            return None

        if session.is_expired():
            self.clear_session(document_id)
            return None

        return session

    def clear_session(self, document_id: str) -> bool:
        """Clear a session and its associated resources.

        Returns True if the session existed and was cleared.
        """
        session = self._sessions.pop(document_id, None)
        if session is None:
            return False

        session.clear()
        return True

    def clear_all(self) -> int:
        """Clear all sessions. Returns the number of sessions cleared."""
        count = len(self._sessions)
        for session in self._sessions.values():
            session.clear()
        self._sessions.clear()
        return count

    def list_sessions(self) -> list[str]:
        """List all active document IDs."""
        self._cleanup_expired()
        return list(self._sessions.keys())

    def _cleanup_expired(self) -> None:
        """Remove all expired sessions."""
        expired = [
            doc_id for doc_id, session in self._sessions.items()
            if session.is_expired()
        ]
        for doc_id in expired:
            self.clear_session(doc_id)

    @property
    def active_count(self) -> int:
        """Number of active (non-expired) sessions."""
        self._cleanup_expired()
        return len(self._sessions)
