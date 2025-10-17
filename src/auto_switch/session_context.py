"""Multi-session context manager with background cleanup.

This module provides session isolation for the workflow-mcp server, enabling
multiple Claude Code projects to safely share a single MCP server instance
without data contamination.

Constitutional Compliance:
- Principle III: Async-safe with proper locking mechanisms
- Principle V: Production-grade lifecycle management
- Principle VIII: Complete type annotations with mypy --strict compliance
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Per-session context (isolated from other sessions).

    Attributes:
        session_id: Unique session identifier from FastMCP Context
        working_directory: Absolute path to client's working directory
        config_path: Path to .workflow-mcp/config.json (if found)
        project_id: Active project UUID for this session
        set_at: Timestamp when session was first created
        last_used: Timestamp of last access for stale cleanup
    """
    session_id: str
    working_directory: Optional[str] = None
    config_path: Optional[str] = None
    project_id: Optional[str] = None
    set_at: Optional[float] = None
    last_used: Optional[float] = None


class SessionContextManager:
    """Async-safe session context manager with lifecycle.

    Manages isolated session contexts with automatic background cleanup
    of stale sessions (inactive >24 hours).

    Constitutional Compliance:
        - Async-safe operations with asyncio.Lock
        - Background cleanup task with proper lifecycle management
        - Production-grade error handling and logging

    Lifecycle:
        1. Create manager instance
        2. Call start() to begin background cleanup
        3. Use set/get methods for session operations
        4. Call stop() before shutdown

    Example:
        >>> manager = SessionContextManager()
        >>> await manager.start()
        >>> await manager.set_working_directory("session_1", "/path/to/project")
        >>> working_dir = await manager.get_working_directory("session_1")
        >>> await manager.stop()
    """

    def __init__(self) -> None:
        """Initialize session context manager."""
        self._sessions: Dict[str, SessionContext] = {}
        self._lock: asyncio.Lock = asyncio.Lock()  # Async-safe
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._running: bool = False

    async def start(self) -> None:
        """Start background cleanup task.

        Idempotent - safe to call multiple times.
        Starts hourly cleanup loop for stale sessions.
        """
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("SessionContextManager started with background cleanup")

    async def stop(self) -> None:
        """Stop background cleanup task.

        Idempotent - safe to call multiple times.
        Gracefully cancels cleanup task and waits for completion.
        """
        if not self._running:
            return

        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("SessionContextManager stopped")

    async def _cleanup_loop(self) -> None:
        """Periodically clean up stale sessions (>24 hours).

        Runs every hour while manager is running.
        Handles cancellation and errors gracefully.
        """
        while self._running:
            try:
                await asyncio.sleep(3600)  # Every hour
                await self._cleanup_stale_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_stale_sessions(self) -> None:
        """Remove sessions inactive for >24 hours.

        Protected by lock to ensure thread-safe cleanup.
        Logs cleanup activity for monitoring.
        """
        async with self._lock:
            now = time.time()
            stale_sessions = [
                sid for sid, ctx in self._sessions.items()
                if ctx.last_used and (now - ctx.last_used) > 86400  # 24 hours
            ]

            for sid in stale_sessions:
                del self._sessions[sid]
                logger.info(f"Cleaned up stale session: {sid}")

            if stale_sessions:
                logger.info(f"Cleaned up {len(stale_sessions)} stale sessions")

    async def set_working_directory(
        self,
        session_id: str,
        directory: str
    ) -> None:
        """Set working directory for this session only.

        Creates new session if doesn't exist.
        Updates last_used timestamp for stale cleanup.

        Args:
            session_id: From FastMCP Context.session_id
            directory: Absolute path to working directory
        """
        async with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionContext(
                    session_id=session_id,
                    set_at=time.time()
                )

            self._sessions[session_id].working_directory = directory
            self._sessions[session_id].last_used = time.time()

            logger.debug(f"Set working directory for session {session_id}: {directory}")

    async def get_working_directory(
        self,
        session_id: str
    ) -> Optional[str]:
        """Get working directory for this session only.

        Updates last_used timestamp on access.

        Args:
            session_id: From FastMCP Context.session_id

        Returns:
            Working directory string or None if not set
        """
        async with self._lock:
            if session_id not in self._sessions:
                return None

            session = self._sessions[session_id]
            session.last_used = time.time()
            return session.working_directory

    async def get_session_count(self) -> int:
        """Get count of active sessions (for monitoring).

        Returns:
            Number of currently active sessions
        """
        async with self._lock:
            return len(self._sessions)


# Global singleton (initialized in FastMCP lifespan)
_session_context_manager: Optional[SessionContextManager] = None


def get_session_context_manager() -> SessionContextManager:
    """Get global session context manager instance.

    Creates singleton on first call.

    Note: Must be started via FastMCP lifespan hooks to enable cleanup.

    Returns:
        Global SessionContextManager instance
    """
    global _session_context_manager
    if _session_context_manager is None:
        _session_context_manager = SessionContextManager()
    return _session_context_manager
