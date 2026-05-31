"""Optional HTTP basic authentication middleware."""

import secrets
from collections.abc import Awaitable, Callable

from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from binocular.config import Settings

PUBLIC_PATHS = ("/healthz",)


class BasicAuthMiddleware:
    """Guard requests with HTTP Basic authentication when enabled."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.settings.auth_enabled:
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path", ""))
        if path in PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        if self._credentials_are_valid(request.headers):
            await self.app(scope, receive, send)
            return

        response = Response(status_code=401, headers={"WWW-Authenticate": "Basic"})
        await response(scope, receive, send)

    def _credentials_are_valid(self, headers: Headers) -> bool:
        credentials = headers.get("authorization")
        if credentials is None:
            return False

        try:
            scheme, encoded = credentials.split(" ", 1)
            if scheme.lower() != "basic":
                return False
            import base64

            decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
            username, password = decoded.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return False

        expected_password = self.settings.auth_password or ""
        username_matches = secrets.compare_digest(username, self.settings.auth_username)
        password_matches = secrets.compare_digest(password, expected_password)
        return username_matches and password_matches


MiddlewareFactory = Callable[[ASGIApp], Awaitable[ASGIApp]]
