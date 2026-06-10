# Testing: Official Godox Flashes Module
**Created**: 2026-06-07 | **Feature**: [spec.md](../spec.md)

## Fixture Coverage

- [ ] CHK001 Are all six fixture HTML files committed — page-1-hit, multi-page-hit, product-not-found traversal, parse-error, page-limit-exceeded, and case-insensitive match — as mandated by the Clarifications section? [Completeness, Spec §Clarifications (Session 2026-06-07)]
- [ ] CHK002 Does the page-1 fixture (`page_1.html`) reflect the actual HTML structure from `godox.com/firmware-flash/` — including `.Firmware .items .item` containers with `.tit` titles and `<span>` version elements — rather than a hand-crafted synthetic page? [Completeness, Spec §FR-001, Plan §Source Code Structure]
- [ ] CHK003 Does the multi-page fixture set (pages 1–3) include an inert next-link (`a_next` href `javascript:;`) on the last page to simulate real pagination termination? [Completeness, Spec §FR-002, Spec §Glossary]
- [ ] CHK004 Does the parse-error fixture (`parse_error.html`) genuinely contain zero parseable firmware entries from the `.Firmware .items` container, making `parse_error` a deterministic outcome? [Completeness, Spec §Edge Cases, Plan §Source Code Structure]
- [ ] CHK005 Does the empty-page fixture (`empty_page.html`) contain no firmware entries, enabling testing of both the solo-empty-page (transient gap) and consecutive-empty-pages (termination) behaviors? [Completeness, Spec §Edge Cases, Plan §Source Code Structure]
- [ ] CHK006 Are fixture entries present with version format variations — uppercase `V1.17`, lowercase `v2.6`, `V1.02` (leading zero), and `V1.3` (single decimal digit) — to exercise the full range of version normalization? [Completeness, Spec §FR-004, Spec §Edge Cases]

## Golden Test Coverage

- [ ] CHK007 Is there a golden test for the page-1 hit scenario — model "iT32" against `page_1.html` — asserting `latest_version: "1.17"`, `status: "success"`, and `diagnostics.matched_page: 1`? [Consistency, Spec §SC-001, Spec §US1 AC1]
- [ ] CHK008 Is there a golden test for the multi-page hit scenario — model "V100S" against the page-3 fixture — asserting `latest_version: "1.06"`, `status: "success"`, and `diagnostics.pages_checked: 3`? [Consistency, Spec §SC-001, Spec §US1 AC2]
- [ ] CHK009 Does every golden success test assert that `source_url` in the result is a valid, absolute firmware download URL (not an empty string or JavaScript function name)? [Completeness, Spec §Clarifications, Spec §SC-007]
- [ ] CHK010 Are the golden tests exact — asserting specific version strings like `"1.17"` and `"1.06"` — rather than loose checks that only verify the version is non-empty or matches a pattern? [Consistency, Spec §SC-001, Plan §Testing Strategy]
- [ ] CHK011 Are all golden tests fully offline — with the `ScrapeClient` dependency replaced by a multi-URL `FakeScrapeClient` that injects fixture HTML, and zero live HTTP calls made during test execution? [Testability, Spec §FR-009, Plan §Testing Strategy]
- [ ] CHK012 Is the multi-page golden test specifically verifying that the module fetches exactly N pages (and no more) when the model is found on page N — e.g., V100S on page 3 triggers exactly 3 `fetch()` calls and no fourth? [Completeness, Spec §SC-003, Spec §US2]
- [ ] CHK013 Does the plan ensure that golden tests produce zero false positives and zero false negatives against captured fixtures, as required by the Compliance Check? [Correctness, Spec §SC-001, Spec §Compliance Check V]

## Failure Mode Testing

- [ ] CHK014 Is each of the four defined `error_type` values — `product_not_found`, `parse_error`, `firmware_page_unavailable`, `page_limit_exceeded` — exercised by at least one dedicated test case? [Completeness, Spec §FR-005, Plan §Error Handling Strategy]
- [ ] CHK015 Is the `parse_error` path tested specifically for the page-1-zero-entries condition — distinct from the `product_not_found` path that applies to full-traversal exhaustion — with a non-empty `detail` message? [Completeness, Spec §Edge Cases, Spec §SC-004]
- [ ] CHK016 Is the `product_not_found` path tested with a full-traversal scenario where the model is absent from all pages and the inert next-link terminates traversal, asserting `diagnostics.pages_checked` matches the total page count? [Completeness, Spec §SC-005, Spec §US2 AC1]
- [ ] CHK017 Is the `firmware_page_unavailable` path tested with a `FakeScrapeClient` that raises a transport-level error on a page request, and does the test assert `diagnostics.http_status` is present — using `0` as sentinel for non-HTTP failures? [Completeness, Spec §Clarifications, Plan §Error Handling Strategy]
- [ ] CHK018 For each failure test, are both `status` (must be `"failed"`) and `error_type` asserted, and is `detail` verified to be a non-empty, human-readable string? [Clarity, Spec §FR-005, Plan §Error Handling Strategy]
- [ ] CHK019 Does every failure test verify that the `detail` field contains only a human-readable message with no raw HTML, page source fragments, or internal HTTP headers? [Clarity, Spec §SC-004, Plan §Error Handling Strategy]
- [ ] CHK020 Is the unsuffixed-model-not-found scenario tested — requesting model "V100" (no camera-brand suffix) against a fixture containing V100C, V100N, V100S — asserting `error_type: "product_not_found"`? [Completeness, Spec §SC-002, Spec §US1 AC3]
- [ ] CHK021 Is the empty/whitespace-only `check_input.model` scenario tested, confirming it returns `product_not_found` without raising an exception, consistent with the edge case definition? [Completeness, Spec §Edge Cases]

## Pagination Traversal Verification

- [ ] CHK022 Is the multi-page URL construction tested — verifying that page 1 uses `/firmware-flash/` (no underscore) while pages 2+ use `/firmware-flash_N/` with underscore? [Correctness, Spec §FR-002, Plan §HINT-002]
- [ ] CHK023 Is early termination tested — confirming that when the model is found on page N, the module returns immediately without fetching page N+1? [Completeness, Spec §FR-002, Spec §Scope]
- [ ] CHK024 Is the pagination continuation tested — confirming the module correctly parses the `a_next` href from the pagination widget to construct the next page URL? [Correctness, Spec §FR-002, Plan §AD-002]
- [ ] CHK025 Is the inert next-link termination tested — confirming the module stops traversal when `a_next` href is `javascript:;`, even when the model has not been found? [Completeness, Spec §FR-002, Spec §Edge Cases]
- [ ] CHK026 Is the consecutive-empty-pages termination tested — confirming the module returns `product_not_found` after two consecutive empty pages, and `pages_checked` reflects only pages actually fetched? [Completeness, Spec §Edge Cases, Plan §Error Handling Strategy]

## Circuit Breaker Testing

- [ ] CHK027 Is the hard page limit of 30 pages tested with a FakeScrapeClient serving 30 dummy pages — asserting `error_type: "page_limit_exceeded"` with `diagnostics.pages_checked: 30`, and confirming page 31 is never fetched? [Completeness, Spec §FR-006, Spec §SC-008]
- [ ] CHK028 Is the circuit breaker priority tested — confirming that `page_limit_exceeded` is returned even when other termination conditions (inert next-link, consecutive-empty pages) would also trigger at or before page 30? [Completeness, Spec §FR-006, Spec §STF-001]
- [ ] CHK029 For the circuit breaker test, is the `detail` message descriptive about why the limit was reached, distinguishing `page_limit_exceeded` from `product_not_found`? [Clarity, Spec §FR-006, Spec §SC-008]

## Version Normalization & Model Matching

- [ ] CHK030 Is version normalization tested with the full range of observed formats — `V1.17` (uppercase, two-digit minor), `v2.6` (lowercase), `V1.02` (leading zero), `V1.3` (single-digit minor), `V2.2` — asserting the correct stripped result in each case? [Completeness, Spec §FR-004, Spec §Edge Cases]
- [ ] CHK031 Is the version normalization fallback tested for non-standard formats (e.g., `V10` with no dot, `V1.0.1` triple-dotted) — confirming the module strips the `V`/`v` prefix and passes through the remainder without rejecting or crashing? [Completeness, Spec §FR-004, Spec §STF-002]
- [ ] CHK032 Is model matching tested with case-insensitive input — requesting `"v100s"` against a fixture entry for `"V100S"` — asserting a successful match? [Completeness, Spec §US2 AC4, Spec §Clarifications]
- [ ] CHK033 Is model matching tested with the aggressive normalization algorithm — stripping non-alphanumeric characters and uppercasing both the page title and user input — including inputs with extra whitespace, dashes, and hyphens? [Completeness, Spec §FR-001, Spec §STF-004, Plan §AD-005]
- [ ] CHK034 Is exact-match-only behavior tested — confirming that an unsuffixed model (e.g., "V100") does NOT match any camera-brand variant (V100C, V100N, V100S)? [Completeness, Spec §SC-002, Spec §US1 AC3]
- [ ] CHK035 Is model matching tested to confirm that a model with a specific suffix (e.g., "V100S") does NOT accidentally match a different suffix variant (e.g., "V100C")? [Completeness, Spec §Edge Cases, Spec §Scope]

## Contract Compliance

- [ ] CHK036 Is there a contract-load test that uses `ModuleLoader` to verify the module loads without errors, `module_id` matches `"official.godox_flashes"`, and `display_name` matches `"Godox Flashes"`? [Completeness, Spec §US3, Plan §Testing Strategy]
- [ ] CHK037 Is there a source-code string check in the test suite that verifies no banned HTTP import patterns (`import httpx`, `from httpx`, `import requests`, `from urllib.request`) appear in the module source? [Completeness, Spec §FR-007, Plan §Testing Strategy]
- [ ] CHK038 Is there a test confirming that the module's public API surface exports exactly the required symbols — `MODULE_METADATA` dict and `async def check_firmware(check_input, scrape_client)` — matching the existing module engine contract? [Consistency, Spec §FR-008, Plan §Brownfield Notes]
- [ ] CHK039 Does a dry-run integration test invoke `check_firmware` with a `FakeScrapeClient` against a fixture and assert that no direct HTTP connections bypass the provided scrape client? [Completeness, Spec §US3 AC3, Spec §FR-007]
- [ ] CHK040 Does the test suite cover the parsing helpers (`parse_page_entries`, `extract_next_page_url`, `normalize_version`) as synchronous unit tests in addition to the async `check_firmware` integration tests? [Completeness, Plan §Testing Strategy (Unit tier), Plan §Source Code Structure]
