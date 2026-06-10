"""Robots.txt parser and checker."""

import urllib.parse
import urllib.robotparser

import httpx
import structlog

logger = structlog.get_logger("binocular.scraping.robots")


class RobotsChecker:
    """Checks and caches robots.txt rules asynchronously per origin."""

    def __init__(self, user_agent: str) -> None:
        """Initialize RobotsChecker with the target User-Agent."""
        self.user_agent = user_agent
        self._cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    async def is_allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        """Determine if a URL is allowed to be fetched under robots.txt."""
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            # Fall back to allowed if the URL is not fully qualified/parsable
            return True

        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

        if origin not in self._cache:
            robots_url = f"{origin}/robots.txt"
            logger.debug("fetching_robots_txt", url=robots_url)
            try:
                response = await client.get(robots_url)
                if response.status_code == 404:
                    logger.debug("robots_txt_not_found", origin=origin)
                    self._cache[origin] = None
                elif response.status_code == 403:
                    logger.debug("robots_txt_forbidden", origin=origin)
                    parser = urllib.robotparser.RobotFileParser()
                    parser.parse(["User-agent: *", "Disallow: /"])
                    self._cache[origin] = parser
                elif 400 <= response.status_code < 500:
                    logger.debug(
                        "robots_txt_other_4xx_allowed",
                        origin=origin,
                        status=response.status_code,
                    )
                    self._cache[origin] = None
                elif response.status_code >= 500:
                    logger.warning(
                        "robots_txt_server_error_disallowed",
                        origin=origin,
                        status=response.status_code,
                    )
                    parser = urllib.robotparser.RobotFileParser()
                    parser.parse(["User-agent: *", "Disallow: /"])
                    self._cache[origin] = parser
                else:
                    parser = urllib.robotparser.RobotFileParser()
                    parser.parse(response.text.splitlines())
                    self._cache[origin] = parser
            except httpx.RequestError as e:
                logger.warning(
                    "robots_txt_fetch_error_disallowed",
                    origin=origin,
                    error=str(e),
                )
                parser = urllib.robotparser.RobotFileParser()
                parser.parse(["User-agent: *", "Disallow: /"])
                self._cache[origin] = parser
            except Exception as e:
                logger.error(
                    "robots_txt_unexpected_error_disallowed",
                    origin=origin,
                    error=str(e),
                )
                parser = urllib.robotparser.RobotFileParser()
                parser.parse(["User-agent: *", "Disallow: /"])
                self._cache[origin] = parser

        cached_parser = self._cache[origin]
        if cached_parser is None:
            return True

        return bool(cached_parser.can_fetch(self.user_agent, url))
