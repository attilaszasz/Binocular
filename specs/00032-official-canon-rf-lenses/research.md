# Research: Official Canon RF Lenses
> E029 | 2026-09-07 | Source correctness and implementation planning

## Source and Classification
- **Decision**: Use Canon Asia English RF and RF-S catalogue membership plus explicit lens-name classification.
- **Rationale**: The RF catalogue includes accessories, while the RF-S catalogue establishes membership without proving firmware availability.
- **Rejected**: Mount inference, adapters, extenders, cinema lenses, unrelated mounts, and regional fallback.
- **Pitfalls**: Follow product links verbatim; unusual source encoding exists.
- **Sources**: https://asia.canon/en/support/models?series=14, https://asia.canon/en/support/models?series=86

## Discovery and Releases
- **Decision**: Discover each product page's firmware form action; group operating-system packages by model/version and return release-detail links.
- **Rationale**: Canon responses are HTML fragments and duplicate one release across operating systems.
- **Rejected**: Constructed slugs, binary routes, and inferred positive RF-S releases.
- **Pitfalls**: RF24-105mm F4 L IS USM `2.0.7` is fixture evidence, not a permanently latest claim; RF-S18-45mm has explicit no-firmware evidence.
- **Sources**: https://asia.canon/asia/en/support/RF24-105mm%20F4L%20IS%20USM/get-search-result-content?fileType=FA, https://asia.canon/en/support/0401117302?model=RF24-105mm+F4L+IS+USM

## Failure and Politeness
- **Decision**: Use only the scoped host client; expose unsupported, unavailable, and drift failures; test shared 30-second pacing with injected time.
- **Rationale**: Canon publishes a 30-second delay and project policy forbids direct requests or late work after cancellation.
- **Rejected**: Live-sleep tests, module-local clients, fallback rotation, and inferred successes.
- **Pitfalls**: Every retry shares the Canon-origin timeline; no-firmware is distinct from unknown or malformed source.
- **Sources**: https://asia.canon/robots.txt, https://www.rfc-editor.org/rfc/rfc9309

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Coverage | Classified RF/RF-S catalogue lenses | Exclude accessories and unsupported mounts |
| Discovery | Product link → discovered action | Avoid inferred routes |
| Reliability | Scoped client + fixtures | Polite, bounded, visible |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://asia.canon/en/support/models?series=14 | RF coverage | 2026-09-06 |
| https://asia.canon/en/support/models?series=86 | RF-S coverage | 2026-09-06 |
| https://asia.canon/robots.txt | Politeness | 2026-09-06 |
| https://asia.canon/en/support/0401117302?model=RF24-105mm+F4L+IS+USM | Release | 2026-09-06 |
