from fastapi import FastAPI
from fastapi.routing import APIRoute

from binocular.app import create_app
from binocular.config import Settings


def test_create_app_returns_fastapi_instance() -> None:
    app = create_app(Settings(environment="test"))

    assert isinstance(app, FastAPI)
    assert app.state.settings.port == 8000


def test_create_app_registers_health_route() -> None:
    app = create_app(Settings(environment="test"))
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}

    assert "/healthz" in paths