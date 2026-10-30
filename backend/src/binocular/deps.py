"""Shared FastAPI dependency types.

Extracted to avoid circular imports between ``app.py`` and route modules.
"""

from typing import Annotated

import aiosqlite
from fastapi import Depends, Request


async def get_db(request: Request) -> aiosqlite.Connection:
    """Return the read-only lifespan connection, never a request transaction.

    Writers must open a dedicated WriteUnit or use a repository's standalone
    write adapter. Do not BEGIN/commit on this shared runtime input.

    Args:
        request: The incoming HTTP request.

    Returns:
        The shared :class:`aiosqlite.Connection` from app state.
    """
    conn: aiosqlite.Connection = request.app.state.db
    return conn


# Type alias for use in route handlers
DBDep = Annotated[aiosqlite.Connection, Depends(get_db)]
