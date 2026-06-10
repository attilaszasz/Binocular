# Research: Responsible Scraping Client

## Async Robots.txt Compliance
Using python standard library `urllib.robotparser.RobotFileParser` provides RFC 9309 compliant parsing. Because its network fetch method `read()` is blocking, the optimal async pattern is fetching `robots.txt` asynchronously using `httpx.AsyncClient` and passing the text split by lines to `parse()`. Caching parsed rules per origin prevents redundant network calls.
- **Avoid**: Blocking network methods like `RobotFileParser.read()`.
- **Sources**: Python `urllib.robotparser` standard library documentation; Scrapy robots compliance guidelines.

## Per-Origin Rate Limiting
Polite scraping requires rate limits scoped to the target origin (scheme, host, and port) rather than a global limit. Using an in-memory dictionary of timestamps or token buckets combined with `asyncio.sleep` guarantees minimum pacing (default 1.0 second delay) is maintained per target site.
- **Avoid**: Global locks that choke requests to independent servers.
- **Sources**: MDN HTTP Rate Limiting; Web crawling polite pacing guidelines.

## Exponential Backoff with Jitter
For temporary errors (HTTP 429, 5xx), exponential backoff scales retries safely. Implementing `wait = backoff_factor * (2 ** attempt) + random.uniform(0, 1)` prevents synchronized retry spikes (thundering herd) against target servers.
- **Avoid**: Constant retry intervals or unbounded retry counts.
- **Sources**: AWS Architecture Blog: Exponential Backoff and Jitter.

## Typed Diagnostics
To avoid silent failures or obscure stack traces in extension modules, the HTTP client should translate raw HTTP or connection errors into structured, typed exceptions (e.g., `RobotsDisallowed`, `HTTPStatusError`, `ConnectTimeout`). This allows the module engine to categorize issues cleanly in the activity log.
- **Avoid**: Raising generic `Exception` or raw `httpx.HTTPError`.
- **Sources**: FastAPI custom error handling practices; PEP 3134 exception chaining.
