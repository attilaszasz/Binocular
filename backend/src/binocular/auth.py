"""Optional HTTP Basic Authentication middleware."""

import base64

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = structlog.get_logger("binocular.auth")


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Optional HTTP Basic Authentication middleware.

    Protects all endpoints except ``/healthz`` when enabled.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        settings = request.app.state.settings

        if not settings.basic_auth_enabled:
            return await call_next(request)

        if request.url.path == "/healthz":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.debug("basic_auth_missing_header", path=request.url.path)
            return self._unauthorized_response()

        try:
            auth_type, credentials = auth_header.split(" ", 1)
            if auth_type.lower() != "basic":
                logger.debug("basic_auth_invalid_type", type=auth_type)
                return self._unauthorized_response()

            decoded = base64.b64decode(credentials).decode("utf-8")
            username, password = decoded.split(":", 1)

            if (
                username == settings.basic_auth_username
                and password == settings.basic_auth_password
            ):
                return await call_next(request)

            logger.warning("basic_auth_invalid_credentials", username=username)
        except Exception as e:
            logger.exception("basic_auth_error", error=str(e))

        return self._unauthorized_response()

    def _unauthorized_response(self) -> Response:
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Binocular"'},
        )
