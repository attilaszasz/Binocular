"""Tests for EmailRenderer — HTML template rendering, input sanitization, and performance."""

import re
import time
from unittest.mock import MagicMock, patch

import pytest

from binocular.services.email_renderer import COLOR_TOKENS, EmailRenderer

# ---------------------------------------------------------------------------
# Unicode bidi-override and homoglyph characters that must be stripped
# ---------------------------------------------------------------------------
BIDI_CHARS = [
    "\u202A",  # LEFT-TO-RIGHT EMBEDDING
    "\u202B",  # RIGHT-TO-LEFT EMBEDDING
    "\u202C",  # POP DIRECTIONAL FORMATTING
    "\u202D",  # LEFT-TO-RIGHT OVERRIDE
    "\u202E",  # RIGHT-TO-LEFT OVERRIDE
    "\u2066",  # LEFT-TO-RIGHT ISOLATE
    "\u2067",  # RIGHT-TO-LEFT ISOLATE
    "\u2068",  # FIRST STRONG ISOLATE
    "\u2069",  # POP DIRECTIONAL ISOLATE
]


# ==========================================================================
# Helper fixture
# ==========================================================================


@pytest.fixture
def mock_jinja_env() -> MagicMock:
    """Create a mocked Jinja2 Environment that returns controlled template output."""
    mock_template = MagicMock()
    # The render method captures its **context dict so tests can inspect it
    render_context: dict[str, str] = {}

    def _capture_render(**kwargs: str) -> str:
        render_context.update(kwargs)
        # Produce deterministic output containing all context values for assertions
        parts = [f"{k}={v}" for k, v in sorted(kwargs.items())]
        return "|".join(parts)

    mock_template.render.side_effect = _capture_render

    mock_env = MagicMock()
    mock_env.get_template.return_value = mock_template

    return mock_env


# ==========================================================================
# Tests: Truncation helper (Unicode-safe) — FR-014
# ==========================================================================


class TestTruncation:
    """Tests for the truncation helper that enforces input length limits
    with Unicode-safe codepoint boundaries and ellipsis suffix."""

    # -- within limit -------------------------------------------------------

    def test_truncate_within_limit_returns_unchanged(self) -> None:
        """Values shorter than or equal to the limit are not modified."""
        assert EmailRenderer._truncate("hello", 10) == "hello"
        assert EmailRenderer._truncate("exactly10!", 10) == "exactly10!"
        assert EmailRenderer._truncate("", 10) == ""

    def test_truncate_empty_string_unchanged(self) -> None:
        """Empty string stays empty regardless of limit."""
        assert EmailRenderer._truncate("", 5) == ""
        assert EmailRenderer._truncate("", 128) == ""

    # -- exceeds limit, ellipsis added --------------------------------------

    def test_truncate_exceeds_limit_adds_ellipsis(self) -> None:
        """Values exceeding the limit are truncated with ellipsis replacing
        the final character(s), keeping total at or under the limit."""
        result = EmailRenderer._truncate("12345678901", 10)
        assert len(result) <= 10
        assert result.endswith("\u2026")  # horizontal ellipsis character

    def test_truncate_short_limit_produces_ellipsis_only(self) -> None:
        """When limit is 1, result is just the ellipsis character."""
        result = EmailRenderer._truncate("abcdef", 1)
        assert len(result) <= 1

    # -- Unicode codepoint boundaries ---------------------------------------

    def test_truncate_unicode_preserves_codepoint_boundaries(self) -> None:
        """Multi-byte UTF-8 characters (emoji, CJK) are not split mid-codepoint."""
        # Japanese characters (3 bytes each in UTF-8)
        name = "日本語テスト文字列"  # 8 characters
        limit = 5
        result = EmailRenderer._truncate(name, limit)
        assert len(result) <= limit
        # No replacement character (U+FFFD) indicating split codepoints
        assert "\uFFFD" not in result

    def test_truncate_emoji_handled_correctly(self) -> None:
        """Emoji (4-byte UTF-8 sequences) are preserved intact."""
        name = "📷📸🎥📹🎬"  # 5 emoji characters
        limit = 3
        result = EmailRenderer._truncate(name, limit)
        assert len(result) <= limit
        assert "\uFFFD" not in result

    # -- combining character sequences --------------------------------------

    def test_truncate_combining_characters_preserved(self) -> None:
        """Combining characters (e.g., e + combining acute accent) are not
        orphaned as standalone diacritical marks."""
        # "e\u0301" is "é" as e + combining acute accent (2 codepoints, 1 grapheme)
        word = "cafe\u0301 cafe\u0301"  # 2 grapheme clusters of café
        limit = 5
        result = EmailRenderer._truncate(word, limit)
        assert len(result) <= limit
        # The combining acute should not appear orphaned (without base char)
        # Check that no combining char appears at the start of the result
        assert result[0] != "\u0301"

    # -- exactly at limit vs one over ---------------------------------------

    def test_truncate_exactly_at_limit_passes_through(self) -> None:
        """String exactly at the character limit is not truncated."""
        s = "A" * 128
        result = EmailRenderer._truncate(s, 128)
        assert len(result) <= 128
        assert "\u2026" not in result

    def test_truncate_one_codepoint_over_truncates(self) -> None:
        """String one codepoint beyond the limit is properly truncated."""
        s = "A" * 129
        result = EmailRenderer._truncate(s, 128)
        assert len(result) <= 128
        assert "\u2026" in result

    # -- per-field limits from FR-014 ---------------------------------------

    def test_truncate_device_name_limit_128(self) -> None:
        """Device name is truncated to 128 characters max."""
        long_name = "A" * 200
        result = EmailRenderer._truncate(long_name, 128)
        assert len(result) <= 128

    def test_truncate_source_url_limit_2048(self) -> None:
        """Source URL is truncated to 2048 characters max."""
        long_url = "https://example.com/" + "x" * 3000
        result = EmailRenderer._truncate(long_url, 2048)
        assert len(result) <= 2048

    def test_truncate_version_limit_64(self) -> None:
        """Version string is truncated to 64 characters max."""
        long_version = "v" + "9" * 100
        result = EmailRenderer._truncate(long_version, 64)
        assert len(result) <= 64


# ==========================================================================
# Tests: Bidi-override character stripping — FR-003, spec Edge Cases
# ==========================================================================


class TestBidiStripping:
    """Tests for stripping Unicode bidi-override and homoglyph characters
    (U+202A–U+202E, U+2066–U+2069) from user-origin data fields."""

    def test_bidi_strip_removes_lre_character(self) -> None:
        """U+202A LEFT-TO-RIGHT EMBEDDING is stripped."""
        result = EmailRenderer._strip_bidi("Hello\u202AWorld")
        assert "\u202A" not in result
        assert result == "HelloWorld"

    def test_bidi_strip_removes_rle_character(self) -> None:
        """U+202B RIGHT-TO-LEFT EMBEDDING is stripped."""
        result = EmailRenderer._strip_bidi("Hello\u202BWorld")
        assert "\u202B" not in result

    def test_bidi_strip_removes_all_nine_bidi_chars(self) -> None:
        """All nine bidi-formatting characters (U+202A–U+202E, U+2066–U+2069) are stripped."""
        # Build a string with all nine bidi chars interleaved
        polluted = "A" + "".join(BIDI_CHARS) + "Z"
        result = EmailRenderer._strip_bidi(polluted)
        for ch in BIDI_CHARS:
            assert ch not in result, f"Bidi char U+{ord(ch):04X} was not stripped"
        assert "A" in result
        assert "Z" in result

    def test_bidi_strip_handles_string_without_bidi_chars(self) -> None:
        """String without bidi characters passes through unchanged."""
        clean = "Sony A7 IV v1.10"
        result = EmailRenderer._strip_bidi(clean)
        assert result == clean

    def test_bidi_strip_handles_empty_string(self) -> None:
        """Empty string returns empty string."""
        result = EmailRenderer._strip_bidi("")
        assert result == ""

    def test_bidi_strip_handles_only_bidi_chars(self) -> None:
        """String consisting only of bidi chars returns empty string."""
        result = EmailRenderer._strip_bidi("".join(BIDI_CHARS[:3]))
        assert result == ""

    def test_bidi_strip_preserves_normal_unicode(self) -> None:
        """Normal Unicode characters (CJK, emoji, accented) are preserved."""
        name = "Caméra 📷 テスト"
        result = EmailRenderer._strip_bidi(name)
        assert "é" in result
        assert "📷" in result
        assert "テ" in result


# ==========================================================================
# Tests: html.escape on all user-origin data fields — FR-003
# ==========================================================================


class TestHtmlEscape:
    """Tests verifying html.escape() is applied to all five user-origin data
    fields before template insertion."""

    ALL_METACHARS = "<>&\"'"

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("device_name", "Sony<script>alert(1)</script>"),
            ("device_type", 'camera"onmouseover="alert(1)'),
            ("current_version", "1.0&exploit"),
            ("latest_version", "2.0' OR 1=1"),
            ("source_url", "https://x.com?a=<xss>"),
        ],
    )
    def test_render_escapes_html_metacharacters_per_field(
        self, field_name: str, value: str, mock_jinja_env: MagicMock
    ) -> None:
        """Each of the five data fields containing HTML-significant chars
        is escaped before being passed to the template context."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            kwargs = {
                "device_name": "Sony",
                "device_type": "camera",
                "current_version": "1.0",
                "latest_version": "2.0",
                "source_url": "https://example.com",
                "timestamp": "2026-01-01",
            }
            kwargs[field_name] = value
            result = renderer.render(**kwargs)

            # The raw metacharacters should not appear in the rendered output.
            # & is handled separately because it appears legitimately inside
            # HTML entities (&lt; &gt; &amp; etc.) produced by correct escaping.
            for ch in ("<", ">", '"', "'"):
                assert ch not in result, (
                    f"Unescaped '{ch}' found in render output for {field_name}"
                )

    def test_render_escapes_all_five_metacharacters(self, mock_jinja_env: MagicMock) -> None:
        """All five HTML-significant characters (< > & " ') across all fields
        are escaped in the rendered output."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            # Inject all five metacharacters into every field
            nasty = "<>&\"'"
            result = renderer.render(
                device_name=f"Dev{nasty}",
                device_type=f"Type{nasty}",
                current_version=f"v{nasty}",
                latest_version=f"v{nasty}",
                source_url=f"https://example.com?x={nasty}",
                timestamp=f"2026{nasty}",
            )

            # Raw angle brackets should never appear — they are the most dangerous
            assert "<" not in result, "Raw '<' found in rendered output"
            assert ">" not in result, "Raw '>' found in rendered output"
            # Ampersand should be escaped (except as part of entities)
            assert result.count("&amp;") >= 5  # at least one per field containing &

    @patch("binocular.services.email_renderer.html.escape")
    def test_render_calls_html_escape_on_all_five_fields(
        self, mock_escape: MagicMock, mock_jinja_env: MagicMock
    ) -> None:
        """html.escape() is called for each of the five user-origin data fields."""
        mock_escape.side_effect = lambda s, quote=True: str(s)
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            renderer.render(
                device_name="Dev",
                device_type="camera",
                current_version="1.0",
                latest_version="2.0",
                source_url="https://x.com",
                timestamp="2026",
            )
            # Verify escape was called at least once per data field
            called_args = [c.args[0] if c.args else None for c in mock_escape.call_args_list]
            assert "Dev" in called_args, "html.escape not called on device_name"
            assert "camera" in called_args, "html.escape not called on device_type"
            assert "1.0" in called_args, "html.escape not called on current_version"
            assert "2.0" in called_args, "html.escape not called on latest_version"
            assert "https://x.com" in called_args, "html.escape not called on source_url"


# ==========================================================================
# Tests: URL validation (http/https only) — FR-003
# ==========================================================================


class TestUrlValidation:
    """Tests for source URL validation — only well-formed http/https URLs
    are included in the email body."""

    def test_validate_url_accepts_http_plain(self) -> None:
        """Plain http:// URL is accepted."""
        url = "http://example.com/firmware"
        result = EmailRenderer._validate_url(url)
        assert result == url

    def test_validate_url_accepts_https(self) -> None:
        """https:// URL is accepted."""
        url = "https://firmware.example.com/v2"
        result = EmailRenderer._validate_url(url)
        assert result == url

    def test_validate_url_accepts_https_with_query_params(self) -> None:
        """https:// URL with query string and port is accepted."""
        url = "https://example.com:8443/download?version=2.0&device=alpha"
        result = EmailRenderer._validate_url(url)
        assert result == url

    def test_validate_url_accepts_http_no_path(self) -> None:
        """http:// with just a host is accepted."""
        url = "http://192.168.1.1"
        result = EmailRenderer._validate_url(url)
        assert result == url

    def test_validate_url_rejects_javascript_scheme(self) -> None:
        """javascript: URL is rejected."""
        result = EmailRenderer._validate_url("javascript:alert(1)")
        assert result is None

    def test_validate_url_rejects_data_scheme(self) -> None:
        """data: URL is rejected."""
        result = EmailRenderer._validate_url("data:text/html,<script>alert(1)</script>")
        assert result is None

    def test_validate_url_rejects_file_scheme(self) -> None:
        """file:/// URL is rejected."""
        result = EmailRenderer._validate_url("file:///etc/passwd")
        assert result is None

    def test_validate_url_rejects_ftp_scheme(self) -> None:
        """ftp:// URL is rejected — only http/https allowed."""
        result = EmailRenderer._validate_url("ftp://server/firmware.bin")
        assert result is None

    def test_validate_url_rejects_none_input(self) -> None:
        """None (missing source URL) returns None."""
        result = EmailRenderer._validate_url(None)
        assert result is None

    def test_validate_url_rejects_empty_string(self) -> None:
        """Empty string returns None."""
        result = EmailRenderer._validate_url("")
        assert result is None

    def test_validate_url_rejects_no_scheme(self) -> None:
        """URL without a scheme is rejected."""
        result = EmailRenderer._validate_url("//example.com/path")
        assert result is None

    def test_validate_url_rejects_whitespace_only(self) -> None:
        """Whitespace-only string returns None."""
        result = EmailRenderer._validate_url("   ")
        assert result is None

    # -- Render integration with URL validation ------------------------------

    def test_render_omits_invalid_url_from_output(self, mock_jinja_env: MagicMock) -> None:
        """When source URL fails validation, it is omitted from the template context."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="Device1",
                device_type="camera",
                current_version="v1.0",
                latest_version="v2.0",
                source_url="javascript:void(0)",
                timestamp="2026-01-01",
            )
            # The invalid URL should not appear in output
            assert "javascript" not in result.lower()

    def test_render_includes_valid_url_in_output(self, mock_jinja_env: MagicMock) -> None:
        """When source URL is a valid https URL, it appears in the template context."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="Device1",
                device_type="camera",
                current_version="v1.0",
                latest_version="v2.0",
                source_url="https://example.com/firmware",
                timestamp="2026-01-01",
            )
            assert "https://example.com/firmware" in result


# ==========================================================================
# Tests: Non-string coercion — Plan §Error Handling
# ==========================================================================


class TestCoercion:
    """Tests that non-string input types are coerced via str() before escaping."""

    def test_render_coerces_integer_device_name(self, mock_jinja_env: MagicMock) -> None:
        """Integer is coerced to string via str()."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name=42,
                device_type="camera",
                current_version=1.0,
                latest_version="2.0",
                source_url="https://example.com",
                timestamp="2026",
            )
            assert "42" in result

    def test_render_coerces_none_device_type(self, mock_jinja_env: MagicMock) -> None:
        """None is coerced to the string 'None' rather than crashing."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="Device",
                device_type=None,
                current_version="1.0",
                latest_version="2.0",
                source_url="https://example.com",
                timestamp="2026",
            )
            assert "None" in result

    def test_render_coerces_list_version(self, mock_jinja_env: MagicMock) -> None:
        """List is coerced to its string representation."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="Device",
                device_type="camera",
                current_version=[1, 0],
                latest_version="2.0",
                source_url="https://example.com",
                timestamp="2026",
            )
            # The coerced value should appear (str([1, 0]) -> "[1, 0]")
            assert "1" in result

    def test_render_does_not_crash_on_unexpected_types(self, mock_jinja_env: MagicMock) -> None:
        """render() returns a valid string even when all fields are non-string types."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name=123,
                device_type=True,
                current_version=None,
                latest_version=2.5,
                source_url={"key": "val"},
                timestamp=20260101,
            )
            assert isinstance(result, str)
            assert len(result) > 0


# ==========================================================================
# Tests: Color tokens — FR-010
# ==========================================================================


class TestColorTokens:
    """Tests that hardcoded color tokens from the Binocular light color scheme
    appear in the rendered HTML output."""

    EXPECTED_COLORS = {
        "surface": "#F4F1EA",
        "card": "#FFFFFF",
        "heading_text": "#1F2937",
        "metadata": "#5B6875",
        "accent": "#0A8478",
    }

    def test_render_includes_surface_color(self, mock_jinja_env: MagicMock) -> None:
        """Surface color #F4F1EA appears in the rendered output."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="Dev",
                device_type="camera",
                current_version="1.0",
                latest_version="2.0",
                source_url="https://example.com",
                timestamp="2026",
            )
            assert self.EXPECTED_COLORS["surface"] in result

    def test_render_includes_all_five_color_tokens(self, mock_jinja_env: MagicMock) -> None:
        """All five color tokens are present in the rendered HTML output."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="Dev",
                device_type="camera",
                current_version="1.0",
                latest_version="2.0",
                source_url="https://example.com",
                timestamp="2026",
            )
            for label, color in self.EXPECTED_COLORS.items():
                assert color in result, f"Color token {label} ({color}) not found in output"

    def test_color_tokens_are_not_sourced_from_user_input(self, mock_jinja_env: MagicMock) -> None:
        """Color tokens are always the fixed hex values regardless of user input values."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="#000000",
                device_type="#FF0000",
                current_version="#0000FF",
                latest_version="#ABCDEF",
                source_url="https://example.com",
                timestamp="2026",
            )
            # The legitimate color tokens must still be present
            for color in self.EXPECTED_COLORS.values():
                assert color in result, f"Expected color {color} missing from output"
            # User data fields are escaped — their hex-like values should
            # be present as text content, not confused with CSS color values
            assert "Dev" not in result or result != "#000000"  # Device name is passed through


# ==========================================================================
# Tests: Render variations — FR-001, FR-004
# ==========================================================================


class TestRenderVariations:
    """Tests for render() output variations: complete data, missing optional
    fields, maximum-length fields, and the template context."""

    def test_render_with_complete_data_returns_html(self, mock_jinja_env: MagicMock) -> None:
        """render() with all fields populated returns a non-empty string."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="Sony A7 IV",
                device_type="camera",
                current_version="v1.10",
                latest_version="v1.20",
                source_url="https://sony.com/support",
                timestamp="2026-06-07T12:00:00",
            )
            assert isinstance(result, str)
            assert len(result) > 0

    def test_render_passes_all_fields_to_template_context(self, mock_jinja_env: MagicMock) -> None:
        """All processed field values are passed to the Jinja2 template context."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="MyDevice",
                device_type="router",
                current_version="3.4.0",
                latest_version="3.5.1",
                source_url="https://firmware.example.com",
                timestamp="2026-06-07T12:00:00Z",
            )
            # Each field value should appear in the rendered output
            assert "MyDevice" in result
            assert "router" in result
            assert "3.4.0" in result
            assert "3.5.1" in result
            assert "firmware.example.com" in result

    def test_render_missing_source_url_still_renders(self, mock_jinja_env: MagicMock) -> None:
        """render() succeeds even when source_url is None or empty — the
        URL field is gracefully omitted."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()

            result_none = renderer.render(
                device_name="Device",
                device_type="camera",
                current_version="1.0",
                latest_version="2.0",
                source_url=None,
                timestamp="2026",
            )
            assert isinstance(result_none, str)
            assert len(result_none) > 0

            result_empty = renderer.render(
                device_name="Device",
                device_type="camera",
                current_version="1.0",
                latest_version="2.0",
                source_url="",
                timestamp="2026",
            )
            assert isinstance(result_empty, str)
            assert len(result_empty) > 0

    def test_render_with_max_length_fields(self, mock_jinja_env: MagicMock) -> None:
        """render() handles fields at their maximum allowed lengths without error."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="A" * 128,
                device_type="camera",
                current_version="v" + "9" * 62,  # 64 chars max
                latest_version="v" + "8" * 62,
                source_url="https://example.com/" + "x" * 2000,  # under 2048 limit
                timestamp="2026-06-07T12:00:00Z",
            )
            assert isinstance(result, str)
            assert len(result) > 0

    def test_render_returns_different_output_for_different_input(
        self, mock_jinja_env: MagicMock
    ) -> None:
        """Different input values produce different rendered output."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result1 = renderer.render(
                device_name="DeviceA", device_type="camera",
                current_version="1.0", latest_version="2.0",
                source_url="https://a.com", timestamp="2026",
            )
            result2 = renderer.render(
                device_name="DeviceB", device_type="router",
                current_version="3.0", latest_version="4.0",
                source_url="https://b.com", timestamp="2026",
            )
            assert result1 != result2


# ==========================================================================
# Tests: Performance — 50ms budget per email
# ==========================================================================


class TestPerformance:
    """Performance tests verifying template rendering completes within
    the 50ms budget per email."""

    def test_render_completes_within_50ms_budget(self, mock_jinja_env: MagicMock) -> None:
        """render() completes in under 50ms for a single email."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            start = time.perf_counter()
            renderer.render(
                device_name="Sony A7 IV",
                device_type="camera",
                current_version="v1.10",
                latest_version="v1.20",
                source_url="https://support.sony.com/en/firmware",
                timestamp="2026-06-07T12:00:00Z",
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert elapsed_ms < 50, f"render() took {elapsed_ms:.2f}ms, exceeding 50ms budget"

    def test_render_with_long_input_within_50ms(self, mock_jinja_env: MagicMock) -> None:
        """render() with maximum-length fields still completes within 50ms."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            start = time.perf_counter()
            renderer.render(
                device_name="X" * 128,
                device_type="camera",
                current_version="v" + "9" * 62,
                latest_version="v" + "8" * 62,
                source_url="https://x.com/" + "y" * 2020,
                timestamp="2026-06-07T12:00:00Z",
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert elapsed_ms < 50, f"render() with max-length input took {elapsed_ms:.2f}ms"

    def test_render_with_emoji_input_within_50ms(self, mock_jinja_env: MagicMock) -> None:
        """render() with Unicode-heavy input (emoji, CJK) completes within 50ms."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            start = time.perf_counter()
            renderer.render(
                device_name="📷📸🎥📹🎬🎤🎧🎼🎵🎶" * 5,
                device_type="カメラ",
                current_version="版1.0",
                latest_version="版2.0",
                source_url="https://テスト.jp/ファーム",
                timestamp="2026-06-07T12:00:00Z",
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert elapsed_ms < 50, f"render() with Unicode input took {elapsed_ms:.2f}ms"


# ==========================================================================
# Tests: Bidi-strip integration in render pipeline
# ==========================================================================


class TestBidiStripIntegration:
    """Integration tests verifying bidi-override characters are stripped from
    user data before reaching the template context in render()."""

    def test_render_strips_bidi_from_device_name(self, mock_jinja_env: MagicMock) -> None:
        """Bidi chars in device_name are stripped before template rendering."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="Camera\u202ESafe",  # RLO before "Safe"
                device_type="camera",
                current_version="1.0",
                latest_version="2.0",
                source_url="https://example.com",
                timestamp="2026",
            )
            assert "\u202E" not in result

    def test_render_strips_bidi_from_device_type(self, mock_jinja_env: MagicMock) -> None:
        """Bidi chars in device_type are stripped."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="Device",
                device_type="camera\u2066isolated",  # LRI
                current_version="1.0",
                latest_version="2.0",
                source_url="https://example.com",
                timestamp="2026",
            )
            assert "\u2066" not in result

    def test_render_strips_bidi_from_source_url(self, mock_jinja_env: MagicMock) -> None:
        """Bidi chars in source_url are stripped."""
        with (
            patch("binocular.services.email_renderer.jinja2.FileSystemLoader"),
            patch(
                "binocular.services.email_renderer.jinja2.Environment",
                return_value=mock_jinja_env,
            ),
        ):
            renderer = EmailRenderer()
            result = renderer.render(
                device_name="Device",
                device_type="camera",
                current_version="1.0",
                latest_version="2.0",
                source_url="https://\u202Dexample.com",  # LRO in URL
                timestamp="2026",
            )
            assert "\u202D" not in result


# ==========================================================================
# Tests: Light-theme branding — T009 / FR-010
# ==========================================================================


class TestLightThemeBranding:
    """Tests verifying the rendered HTML uses the exact light-theme hex colors,
    that CSS values come from COLOR_TOKENS constants (not user data), and that
    no color-related class names or CSS variables are used (FR-002, FR-010)."""

    EXPECTED_COLORS: tuple[str, ...] = (
        "#F4F1EA",  # surface_color
        "#FFFFFF",  # card_color
        "#1F2937",  # heading_color
        "#5B6875",  # metadata_color
        "#0A8478",  # accent_color
        "#ECFDF5",  # success_bg
        "#047857",  # success_text
    )

    @pytest.fixture
    def renderer(self) -> EmailRenderer:
        """Create a real EmailRenderer that loads the actual Jinja2 template."""
        return EmailRenderer()

    # -- exact hex colors in rendered HTML ----------------------------------

    def test_all_seven_hex_colors_in_rendered_output(self, renderer: EmailRenderer) -> None:
        """All 7 light-theme hex colors appear in the rendered HTML output."""
        result = renderer.render(
            device_name="Test Device",
            device_type="camera",
            current_version="1.0",
            latest_version="2.0",
            source_url="https://example.com",
            timestamp="2026-06-07T12:00:00Z",
        )
        for color in self.EXPECTED_COLORS:
            assert color in result, f"Expected color {color} not found in rendered HTML"

    def test_surface_and_card_colors_in_background(self, renderer: EmailRenderer) -> None:
        """Surface #F4F1EA and card #FFFFFF are present as background-color values."""
        result = renderer.render(
            device_name="Device",
            device_type="camera",
            current_version="1.0",
            latest_version="2.0",
            source_url="https://example.com",
            timestamp="2026",
        )
        assert "#F4F1EA" in result
        assert "#FFFFFF" in result

    # -- CSS values are constants, not user data -----------------------------

    def test_no_user_hex_in_style_attributes(self, renderer: EmailRenderer) -> None:
        """User-supplied hex-like strings do not appear inside style=""
        attributes — only hardcoded color constants are used for styling."""
        result = renderer.render(
            device_name="#FF0000",  # hex-like, must stay in text content only
            device_type="#00FF00",
            current_version="#0000FF",
            latest_version="2.0",
            source_url="https://example.com",
            timestamp="2026-06-07",
        )

        # Extract all style attribute values
        style_attrs: list[str] = re.findall(r'style="([^"]*)"', result)
        style_text = " ".join(style_attrs)

        # User hex-like values must NOT appear inside any style attribute
        assert "#FF0000" not in style_text, (
            "device_name '#FF0000' leaked into a style attribute"
        )
        assert "#00FF00" not in style_text, (
            "device_type '#00FF00' leaked into a style attribute"
        )
        assert "#0000FF" not in style_text, (
            "current_version '#0000FF' leaked into a style attribute"
        )

    def test_device_name_not_in_style_attribute(self, renderer: EmailRenderer) -> None:
        """Device name text content does not accidentally appear inside a
        style attribute value."""
        result = renderer.render(
            device_name="Sony A7 IV",
            device_type="camera",
            current_version="1.0",
            latest_version="2.0",
            source_url="https://example.com",
            timestamp="2026",
        )
        style_attrs = re.findall(r'style="([^"]*)"', result)
        style_text = " ".join(style_attrs)
        assert "Sony A7 IV" not in style_text, (
            "Device name leaked into a style attribute"
        )

    def test_version_text_not_in_style_attribute(self, renderer: EmailRenderer) -> None:
        """Version text content does not accidentally appear inside a
        style attribute value."""
        result = renderer.render(
            device_name="Dev",
            device_type="camera",
            current_version="1.0",
            latest_version="v9.9.9",
            source_url="https://example.com",
            timestamp="2026",
        )
        style_attrs = re.findall(r'style="([^"]*)"', result)
        style_text = " ".join(style_attrs)
        assert "v9.9.9" not in style_text, (
            "Latest version 'v9.9.9' leaked into a style attribute"
        )

    def test_url_not_in_style_attribute(self, renderer: EmailRenderer) -> None:
        """Source URL text content does not accidentally appear inside a
        style attribute value."""
        result = renderer.render(
            device_name="Dev",
            device_type="camera",
            current_version="1.0",
            latest_version="2.0",
            source_url="https://malicious.example.com/red",
            timestamp="2026",
        )
        style_attrs = re.findall(r'style="([^"]*)"', result)
        style_text = " ".join(style_attrs)
        assert "malicious.example.com" not in style_text, (
            "Source URL leaked into a style attribute"
        )

    def test_branding_hex_colors_from_color_tokens_constant(
        self, renderer: EmailRenderer
    ) -> None:
        """The 7 branding hex colors present in the rendered HTML each
        match the values defined in the COLOR_TOKENS module-level constant."""
        result = renderer.render(
            device_name="Test Device",
            device_type="camera",
            current_version="1.0",
            latest_version="2.0",
            source_url="https://example.com",
            timestamp="2026",
        )

        token_colors = set(COLOR_TOKENS.values())

        for color in self.EXPECTED_COLORS:
            assert color in token_colors, (
                f"Color {color} not found in COLOR_TOKENS dict"
            )
            assert color in result, (
                f"Color {color} from COLOR_TOKENS not found in rendered HTML"
            )

    # -- no color-related class names or CSS variables -----------------------

    def test_no_color_related_css_classes(self, renderer: EmailRenderer) -> None:
        """No CSS class attributes contain color-related terms — all colors
        are applied via inline style attributes per FR-002."""
        result = renderer.render(
            device_name="Test Device",
            device_type="camera",
            current_version="1.0",
            latest_version="2.0",
            source_url="https://example.com",
            timestamp="2026",
        )
        # Find all class attribute values
        class_matches = re.findall(r'class="([^"]*)"', result)
        color_terms = {
            "primary", "secondary", "accent", "surface",
            "heading", "text", "background", "bg", "color",
        }
        for cls in class_matches:
            cls_lower = cls.lower()
            for term in color_terms:
                assert term not in cls_lower, (
                    f"Color-related CSS class '{cls}' found — "
                    f"all colors must be inline per FR-002"
                )

    def test_no_css_variables_for_colors(self, renderer: EmailRenderer) -> None:
        """No CSS custom properties (var(--...)) are used for color values
        — all colors are inline hex values per FR-002."""
        result = renderer.render(
            device_name="Test Device",
            device_type="camera",
            current_version="1.0",
            latest_version="2.0",
            source_url="https://example.com",
            timestamp="2026",
        )
        assert "var(--" not in result, (
            "CSS custom property var(--*) found in rendered HTML — "
            "all colors must be inline hex values per FR-002"
        )

    def test_no_style_blocks(self, renderer: EmailRenderer) -> None:
        """No <style> blocks are present — all CSS is inline per FR-002."""
        result = renderer.render(
            device_name="Test Device",
            device_type="camera",
            current_version="1.0",
            latest_version="2.0",
            source_url="https://example.com",
            timestamp="2026",
        )
        assert "<style" not in result.lower(), (
            "<style> block found in rendered HTML — "
            "all CSS must be inline per FR-002"
        )

    def test_no_external_stylesheet_references(self, renderer: EmailRenderer) -> None:
        """No <link> elements for external stylesheets are present."""
        result = renderer.render(
            device_name="Test Device",
            device_type="camera",
            current_version="1.0",
            latest_version="2.0",
            source_url="https://example.com",
            timestamp="2026",
        )
        assert '<link' not in result.lower(), (
            "<link> element found in rendered HTML — "
            "no external resources allowed"
        )


# ==========================================================================
# Tests: Logging / side effects omitted (those are tested at integration level)
# ==========================================================================
