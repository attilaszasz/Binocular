"""Shared FastAPI dependency types.

Extracted to avoid circular imports between ``app.py`` and route modules.
"""

from typing import Annotated

import aiosqlite
from fastapi import Depends, Request


async def get_db(request: Request) -> aiosqlite.Connection:
    """FastAPI dependency returning the lifespan-managed DB connection.

    Args:
        request: The incoming HTTP request.

    Returns:
        The shared :class:`aiosqlite.Connection` from app state.
    """
    conn: aiosqlite.Connection = request.app.state.db
    return conn


# Type alias for use in route handlers
DBDep = Annotated[aiosqlite.Connection, Depends(get_db)]
