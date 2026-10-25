# Research: Sources
> #12 | 2026-10-07 | Offline code/fixture evidence at b1b8b99; no vendor requests

## Verified guidance
- **Decision**: Ship exactly eight labels/types/coverage/examples/help links from [official-guidance.md](official-guidance.md), preserving stable names and canonical URLs.
- **Rationale**: Fixtures establish examples, not exhaustive firmware guarantees; full matching/exclusion/help evidence is in [official-guidance.md](official-guidance.md).
- **Rejected**: Broader coverage, regional parity and fuzzy Canon matching lack evidence.
- **Pitfalls**: Canon Asia English only; exclude Cinema EOS/EOS R5 C, adapters/extenders/cinema/other mounts; RF-S catalogue membership has no verified positive release; Panasonic MFT excludes DC-S5, H-FS14140 lacks handler; Nikon excludes DSLR/lenses/speedlights; preserve mount suffixes and Viltrox Document Download boundary.
- **Sources**: [Matchers](../../backend/src/binocular/official_modules/), [fixtures](../../backend/tests/fixtures/).

## Typed metadata and provenance
- **Decision**: Optional bounded V1 fields flow loader → repository → seeder/upload → API/UI; validate types/lengths/items on server, escape plain-text output; host-owned hashes prove shipped provenance, not filenames/authors.
- **Rationale**: Existing optional SOURCE_URL flow supports compatible persistence without frontend maps.
- **Rejected**: Required constants, frontend-only registry and filename-based official claims.
- **Pitfalls**: Identical hash/version currently skips DB refresh; same-version changes overwrite custom files, newer versions are protected, upgrades/uploads force active; migration supplies defaults, not proof of provenance.
- **Sources**: [seeder.py](../../backend/src/binocular/services/seeder.py), https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html (fetched 2026-10-07).

## Schedule execution and writes
- **Decision**: Preserve status/interval/IDs using additive SQLite columns with non-null literal defaults; active-only registration/worker admission; manual single/bulk/search remain available.
- **Rationale**: Startup filters active modules but registration/rescheduling/execution do not; pending thread workers need a start-boundary guard.
- **Rejected**: Removing jobs alone, cancelling running checks, or independent transaction locks.
- **Pitfalls**: One shared connection, repository commits each write and cache/services commit independently; avoid multi-await transactions; migrations do not seed module names, seeder imports all .py files and rejects helpers by validation.
- **Sources**: [repository.py](../../backend/src/binocular/db/repository.py), https://www.sqlite.org/lang_altertable.html (fetched 2026-10-07; ADD COLUMN/default/CHECK restrictions).

## UI and QC
- **Decision**: Source-first free text/request-generation reset/exact-member lists; WCAG 2.2 keyboard/focus/labels/status guidance informs FR-018; existing QC tools, planned TS5.9.3/strict node, Playwright smoke and v8 coverage per quickstart.md.
- **Rationale**: Shared add/edit form and TanStack Query invalidation provide local integration; no inventory filter exists.
- **Rejected**: Live help crawling, guessed model pickers and zero-on-error counts.
- **Pitfalls**: Nikon XML is not human help; preserve SOURCE_URL; kit/card/status currently hide errors/lack keyboard semantics; TS6 remains unrepaired until Implement. V8 includes unimported production files with 80% thresholds; browser library failures cannot be silently skipped.
- **Sources**: https://www.w3.org/WAI/WCAG22/quickref/ (fetched 2026-10-07), https://vitest.dev/guide/coverage (fetched 2026-10-07; browser install evidence in quickstart.md).
