# Research: Official Canon RF Cameras
> E028 | 2026-09-07 | Source correctness and implementation planning

## Source and Coverage
- **Decision**: Use Canon Asia English EOS R catalogue membership as the exact camera boundary.
- **Rationale**: The verified catalogue exposed 17 bodies and does not establish Cinema EOS/EOS R5 C coverage.
- **Rejected**: Regional fallback and RF-mount inference; neither proves the same product/action flow.
- **Pitfalls**: Follow catalogue links verbatim; source encoding varies.
- **Sources**: https://asia.canon/en/support, https://asia.canon/en/support/models?series=3

## Discovery and Releases
- **Decision**: Discover each product page's firmware form action; group OS packages by model/version and return release-detail links.
- **Rationale**: Canon responses are HTML fragments and duplicate one release across operating systems.
- **Rejected**: Constructed slugs and binary routes; both bypass source authority.
- **Pitfalls**: EOS R5 `2.2.1` is fixture evidence, not a permanently latest claim.
- **Sources**: https://asia.canon/asia/en/support/EOS%20R5/get-search-result-content?fileType=FA, https://asia.canon/en/support/0401103802?model=EOS+R5

## Failure and Politeness
- **Decision**: Use only the scoped host client; expose unsupported/drift failures and test shared 30-second pacing with injected time.
- **Rationale**: Canon publishes a 30-second delay and project policy forbids direct requests or late work after cancellation.
- **Rejected**: Live-sleep tests, module-local clients, and inferred successes.
- **Pitfalls**: Every retry shares the Canon-origin timeline; no-firmware is distinct from malformed source.
- **Sources**: https://asia.canon/robots.txt, https://www.rfc-editor.org/rfc/rfc9309

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Coverage | EOS R catalogue only | Verified regional authority |
| Discovery | Product link → discovered action | Avoid inferred routes |
| Reliability | Scoped client + fixtures | Polite, bounded, visible |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://asia.canon/en/support/models?series=3 | Coverage | 2026-09-06 |
| https://asia.canon/robots.txt | Politeness | 2026-09-06 |
| https://asia.canon/asia/en/support/EOS%20R5/get-search-result-content?fileType=FA | Releases | 2026-09-06 |
| https://asia.canon/en/support/0401103802?model=EOS+R5 | Releases | 2026-09-06 |
