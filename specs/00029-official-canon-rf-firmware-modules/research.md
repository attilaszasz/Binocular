# Canon Source Research

**Verified**: 2026-09-06 through live official-source requests. Examples are observations, not a promise that versions remain latest.

## Source Selection

| Source | Verified result | Decision |
|---|---|---|
| Canon Asia | Public server-rendered catalogues, firmware fragments and release details; no credentials or OS filter required | Primary source |
| Canon Australia | Firmware HTML available; Cloudflare scripts present; pagination POST not verified | No fallback |
| Canon Europe / USA | Europe support/robots and USA robots returned 403 in research environment | Not proven globally unavailable; not selected |

## Discovery

- Taxonomy: https://asia.canon/en/support
- EOS R: https://asia.canon/en/support/models?series=3 (17 entries observed).
- RF: https://asia.canon/en/support/models?series=14 (53 entries observed, including non-lens accessories).
- RF-S: https://asia.canon/en/support/models?series=86 (7 entries observed).
- Follow returned model links verbatim; unusual `%26%26` encoding exists. Discover the firmware form action on product pages instead of manufacturing URL slugs.
- EOS R catalogue does not establish coverage of R5 C/Cinema EOS. Catalogue membership does not establish firmware availability.

## Verified Firmware Requests

| Product | Public GET | Observed version / Last Updated |
|---|---|---|
| EOS R5 | https://asia.canon/asia/en/support/EOS%20R5/get-search-result-content?fileType=FA | 2.2.1 / 06-Nov-2025 |
| RF24-105mm F4 L IS USM | https://asia.canon/asia/en/support/RF24-105mm%20F4L%20IS%20USM/get-search-result-content?fileType=FA | 2.0.7 / 05-Jan-2026 |

- Responses are HTML fragments with titles, versions, update dates and detail links, not JSON.
- Camera detail: https://asia.canon/en/support/0401103802?model=EOS+R5
- Lens detail: https://asia.canon/en/support/0401117302?model=RF24-105mm+F4L+IS+USM
- Details contain explicit file versions and product-specific changes. Deduplicate OS packages by model/version.
- RF-S18-45mm's published endpoint returned an explicit no-firmware message without an OS filter. No positive RF-S release verified.

## Access Constraints

- https://asia.canon/robots.txt publishes `Crawl-delay: 30` for `User-agent: *`.
- Disallows `*/support/get-search-result-content*`, `*/support/download?*` and search-query routes. Model-specific `/support/{model}/get-search-result-content` is structurally distinct and not matched by that generic restriction. Revalidate against current robots before release.
- Crawl-delay is an additional politeness directive, not an RFC 9309 requirement; this design honors it explicitly.
- Do not scrape download routes, rotate regions to evade denial, or download firmware binaries.

## Repository Constraints

- `scraping/robots.py` uses Python `urllib.robotparser`; RFC wildcard/longest-match behavior requires regression tests, not assumptions.
- `scraping/rate_limit.py` applies only a fixed 1-second default; `scraping/client.py` acquires once before its retry loop. Neither currently enforces Canon's 30-second per-attempt interval.
- `extensions/runner.py` and `services/checks.py` use a 30-second default. A cold multi-page Canon check necessarily exceeds it. Cancelling `asyncio.to_thread` does not terminate its worker thread.
- Therefore, shipping two module files alone is insufficient for compliant, reliable zero-configuration checks.
