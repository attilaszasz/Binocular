"""ASGI entrypoint for Uvicorn."""

from binocular.app import create_app

app = create_app()
