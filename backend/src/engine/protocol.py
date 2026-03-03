"""Structural interface contract for extension modules (PEP 544).

This protocol is used for **static analysis only** — runtime validation
is performed via ``hasattr()`` + ``inspect.signature()`` in the Module
Loader.  Module authors never import this file.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx


@runtime_checkable
class ModuleProtocol(Protocol):
    """Structural type describing a conforming extension module."""

    MODULE_VERSION: str
    SUPPORTED_DEVICE_TYPE: str

    def check_firmware(
        self, url: str, model: str, http_client: httpx.Client
    ) -> dict[str, Any]: ...
