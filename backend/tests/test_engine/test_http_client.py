"""Tests for the HTTP client factory."""

from __future__ import annotations

import httpx
import pytest

from backend.src.engine.http_client import create_http_client, get_user_agent


class TestUserAgent:
    """User-Agent string format per AD-4 / FR-015."""

    def test_user_agent_format(self) -> None:
        ua = get_user_agent()
        assert ua.startswith("Binocular/")
        assert "+https://github.com/aristidesneto/binocular" in ua

    def test_user_agent_in_client_headers(self) -> None:
        client = create_http_client()
        try:
            assert client.headers["User-Agent"] == get_user_agent()
        finally:
            client.close()


class TestClientTimeouts:
    """Connection and read timeouts per AD-4."""

    def test_default_connection_timeout(self) -> None:
        client = create_http_client()
        try:
            assert client.timeout.connect == 10.0
        finally:
            client.close()

    def test_default_read_timeout(self) -> None:
        client = create_http_client()
        try:
            assert client.timeout.read == 20.0
        finally:
            client.close()

    def test_custom_timeouts(self) -> None:
        client = create_http_client(connect_timeout=5.0, read_timeout=15.0)
        try:
            assert client.timeout.connect == 5.0
            assert client.timeout.read == 15.0
        finally:
            client.close()

    def test_client_follows_redirects(self) -> None:
        client = create_http_client()
        try:
            assert client.follow_redirects is True
        finally:
            client.close()
