"""Email renderer for HTML notifications.

Jinja2-based template rendering with input sanitization (html.escape,
Unicode bidi-stripping, truncation) for firmware update alerts.

Exports: EmailRenderer
"""

import html
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import jinja2

# ---------------------------------------------------------------------------
# Compile regex once at module level
# ---------------------------------------------------------------------------
_BIDI_RE = re.compile("[\u202A-\u202E\u2066-\u2069]")

# ---------------------------------------------------------------------------
# Hardcoded color tokens (FR-010) — never sourced from user input
# ---------------------------------------------------------------------------
COLOR_TOKENS: dict[str, str] = {
    "accent_color": "#0A8478",
    "surface_color": "#F4F1EA",
    "card_color": "#FFFFFF",
    "heading_color": "#1F2937",
    "metadata_color": "#5B6875",
    "success_bg": "#ECFDF5",
    "success_text": "#047857",
}

# ---------------------------------------------------------------------------
# Truncation limits (FR-014)
# ---------------------------------------------------------------------------
LIMIT_DEVICE_NAME = 128
LIMIT_SOURCE_URL = 2048
LIMIT_VERSION = 64
LIMIT_TIMESTAMP = 256  # reasonable bound for ISO-8601 timestamps


class EmailRenderer:
    """Renders email templates using Jinja2.

    Provides HTML and plain-text rendering for firmware update
    notifications with sanitization of user-origin data fields.

    All helper methods are static so they can be called both on the
    class and from within the instance render pipeline.
    """

    def __init__(self) -> None:
        template_dir = Path(__file__).parent.parent / "templates"
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

    # ------------------------------------------------------------------
    # Static helpers — tested directly by test_email_renderer.py
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate(value: str, max_length: int) -> str:
        """Unicode-safe truncation with horizontal ellipsis (…).

        * Preserves codepoint boundaries (no surrogate splits).
        * Normalises NFC so combining characters are composed when
          possible, then backtracks at the cut point if the last
          codepoint is a combining mark (to prevent orphaned marks).
        * Returns the original string unchanged when its length does
          not exceed *max_length*.
        """
        if not value:
            return ""
        # Compose combining characters into precomposed forms where possible
        s: str = unicodedata.normalize("NFC", str(value))
        if len(s) <= max_length:
            return s

        ELLIPSIS = "\u2026"  # horizontal ellipsis: one codepoint
        keep = max_length - 1
        if keep < 0:
            keep = 0

        truncated = s[:keep]

        # Back off if the last kept codepoint is a combining mark
        # (Unicode category starts with 'M' — Mn, Mc, Me).
        while truncated and unicodedata.category(truncated[-1]).startswith("M"):
            truncated = truncated[:-1]

        return truncated + ELLIPSIS

    @staticmethod
    def _strip_bidi(value: str) -> str:
        """Strip Unicode bidi-override characters.

        Removes U+202A–U+202E (embedding / override / pop) and
        U+2066–U+2069 (isolate / pop) from the string.
        Returns an empty string when the input is falsy.
        """
        if not value:
            return ""
        return _BIDI_RE.sub("", str(value))

    @staticmethod
    def _validate_url(url: str | None) -> str | None:
        """Validate that *url* uses http or https scheme with a non-empty
        host (netloc).

        Returns the original URL string on success, or ``None`` when
        the URL is missing, empty, or uses a disallowed scheme
        (javascript, data, file, ftp, etc.).
        """
        if not url:
            return None
        try:
            parsed = urlparse(str(url))
        except Exception:
            return None
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return str(url)
        return None

    @classmethod
    def _sanitize(cls, value: object, max_length: int) -> str:
        """Full sanitization pipeline per spec / FR-003 / FR-014.

        Order: 1) coerce via ``str()`` → 2) strip bidi chars →
        3) truncate at Unicode boundary → 4) ``html.escape(s, quote=True)``.
        """
        s: str = str(value)
        s = cls._strip_bidi(s)
        s = cls._truncate(s, max_length)
        s = html.escape(s, quote=True)
        return s

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self,
        device_name: object,
        device_type: object,
        current_version: object,
        latest_version: object,
        source_url: object,
        timestamp: object = None,
    ) -> str:
        """Render the HTML firmware-update email.

        All user-origin data fields are sanitised before template
        insertion.  Source URLs that fail validation are omitted from
        the body (the template's ``{% if source_url %}`` block handles
        this).
        """
        template = self._env.get_template("email_update.html")

        # Validate URL before sanitising — invalid URLs produce ''.
        valid_url = self._validate_url(source_url) if source_url else None  # type: ignore[arg-type]

        context: dict[str, object] = {
            # Color tokens (hardcoded, never from user input)
            **COLOR_TOKENS,
            # User-origin fields — fully sanitised
            "device_name": self._sanitize(device_name, LIMIT_DEVICE_NAME),
            "device_type": self._sanitize(device_type, LIMIT_DEVICE_NAME),
            "current_version": self._sanitize(current_version, LIMIT_VERSION),
            "latest_version": self._sanitize(latest_version, LIMIT_VERSION),
            "source_url": self._sanitize(valid_url, LIMIT_SOURCE_URL) if valid_url else "",
            "timestamp": self._sanitize(timestamp, LIMIT_TIMESTAMP),
        }
        return template.render(**context)

    def render_plain_text(
        self,
        device_name: object,
        device_type: object,
        current_version: object,
        latest_version: object,
        source_url: object,
        timestamp: object = None,
    ) -> str:
        """Render the plain-text multipart/alternative fallback.

        Per FR-006, HTML-specific escaping is not required for the
        ``text/plain`` MIME part.  Bidi stripping and truncation are
        still applied.
        """
        template = self._env.get_template("email_update.txt")

        def _sanitize_text(v: object, limit: int) -> str:
            s: str = str(v)
            s = EmailRenderer._strip_bidi(s)
            s = EmailRenderer._truncate(s, limit)
            return s

        valid_url = self._validate_url(source_url) if source_url else None  # type: ignore[arg-type]

        context = {
            "device_name": _sanitize_text(device_name, LIMIT_DEVICE_NAME),
            "device_type": _sanitize_text(device_type, LIMIT_DEVICE_NAME),
            "current_version": _sanitize_text(current_version, LIMIT_VERSION),
            "latest_version": _sanitize_text(latest_version, LIMIT_VERSION),
            "source_url": _sanitize_text(valid_url, LIMIT_SOURCE_URL) if valid_url else "",
            "timestamp": _sanitize_text(timestamp, LIMIT_TIMESTAMP),
        }
        return template.render(**context)
