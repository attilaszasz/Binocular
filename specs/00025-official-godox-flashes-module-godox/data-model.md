# Data Model: Official Godox Flashes Module

**Feature Branch**: `00025-official-godox-flashes-module-godox`
**Spec**: `specs/00025-official-godox-flashes-module-godox/spec.md`
**Plan**: `specs/00025-official-godox-flashes-module-godox/plan.md`
**Created**: 2026-06-07
**Status**: Draft

---

## 1. Summary

This is a **brownfield** feature that adds a single extension module file (`backend/src/binocular/official_modules/godox_flashes.py`). No new database tables, columns, indexes, or migrations are introduced. The module is a stateless scraper: it parses the Godox flash firmware listing into in-memory entities, compares against the requested model, and returns a result through the existing module engine contract.

---

## 2. No Schema Changes

| Aspect | Verdict |
|--------|---------|
| New tables | None |
| New columns on existing tables | None |
| New indexes | None |
| New migrations | None |
| Modified tables | None |

The existing `modules` table (migration `003_modules.sql`) records module metadata at seed time via `ModuleRepository`. The seeder auto-discovers the new `.py` file from `binocular/official_modules/` and inserts a row — no schema change required. All module state is derived by the seeder from the in-file `MODULE_METADATA` dict.

---

## 3. In-Memory Entities

### 3.1 `FirmwareEntry` (dataclass)

A frozen dataclass representing one parsed flash firmware listing entry from the Godox firmware page. This entity lives entirely in memory during a single `check_firmware` invocation and is never persisted.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `model` | `str` | `.item .tit` text (before "Firmware" keyword) | Flash model name as it appears on the page (e.g., "iT32", "V100S"). Used for normalized matching against `check_input.model`. |
| `firmware_version` | `str` | `.item .tit span` text, V/v prefix stripped | Latest published firmware version in dotted format (e.g., "1.17", "2.6"). Non-standard formats passed through as-is. |
| `firmware_date` | `str` | `.text` metadata block | Release date string extracted from the entry's `.text` container. Included in result diagnostics. |
| `firmware_download_url` | `str` | Download link `href` within the `.item` | Absolute URL to the firmware download page for this specific model. Passed as `source_url` in the check result. |
| `page_number` | `int` | Loop context (1-indexed page counter) | The paginated page number on which this entry was found. Included in result diagnostics as `matched_page`. |

**Definition** (mirrors `panasonic_lumix_lenses.py:FirmwareEntry`):

```python
@dataclass(frozen=True)
class FirmwareEntry:
    model: str
    firmware_version: str
    firmware_date: str
    firmware_download_url: str
    page_number: int
```

**Lifecycle**: Created by `parse_page_entries()` for each `.item` container on each fetched page. Entries from all traversed pages are folded into a single lookup. Discarded when `check_firmware` returns.

**Invariants**:

- `model` is never empty (entries with unparseable model names are skipped by the parser).
- `firmware_version` has its leading `V` or `v` stripped during parsing; the remainder preserves its exact casing and dot structure.
- `page_number` is always ≥ 1 and corresponds to the 1-indexed paginated page where the entry appeared.

### 3.2 `MODULE_METADATA` (dict)

Not a database entity — a plain dict at module top level consumed by the module loader and seeder at startup. Inserted as one row in the existing `modules` table via `ModuleRepository`.

| Key | Type | Value |
|-----|------|-------|
| `module_id` | `str` | `"official.godox_flashes"` |
| `display_name` | `str` | `"Godox Flashes"` |
| `version` | `str` | `"1.0.0"` |
| `author` | `str` | `"Binocular"` |
| `supported_device_hints` | `tuple[str, ...]` | `("Godox", "Flash")` |

**No** other module-level state exists — the module is stateless across invocations.

---

## 4. Existing Tables (Unchanged)

The feature relies on these existing tables with zero modifications:

### 4.1 `modules` (Migration `003_modules.sql`)

The seeder inserts or updates one row for `module_id = "official.godox_flashes"` at startup. All columns are populated from `MODULE_METADATA` and automatic derivation (`source_path`, `source_hash`).

| Relevant Column | Populated From |
|-----------------|----------------|
| `module_id` | `MODULE_METADATA["module_id"]` |
| `display_name` | `MODULE_METADATA["display_name"]` |
| `author` | `MODULE_METADATA["author"]` |
| `version` | `MODULE_METADATA["version"]` |
| `source_path` | File path within `official_modules/` directory |
| `source_hash` | Computed SHA-256 of module file |
| `status` | `"installed"` (default) |
| `validation_status` | Set by module loader's static+runtime validation |

### 4.2 `devices` (Migration `002_inventory.sql`)

No changes. Devices that link to this module reference it via `devices.module_id` → `modules.id` (resolved at device creation through the existing `InventoryService`). The `check_firmware` function receives `ModuleCheckInput.model` and `ModuleCheckInput.current_version` from the linked device's row, and the host persists the returned `ModuleCheckResult.latest_version` onto the device row after a successful check.

### 4.3 Other Tables

`device_type_schedules`, `notification_channels`, `activity_log`, `app_metadata`, `schema_version` — all unchanged.

---

## 5. Data Flow (Check Execution)

```
operator / scheduler
        │
        ▼
┌───────────────────┐
│   CheckService    │  reads device row (model, current_version)
│   (checks.py)     │  resolves module_id → module file
└────────┬──────────┘
         │ invokes check_firmware(check_input, scrape_client)
         ▼
┌───────────────────────────────┐
│  godox_flashes.check_firmware │
│                               │
│  page = 1                     │
│  LOOP:                        │
│    fetch /firmware-flash[_N]/ │──── scrape_client.fetch() ────► www.godox.com
│    parse_page_entries(html)   │◄──── HTML response ────────────
│    → FirmwareEntry[]          │
│    find by model match        │
│    if found → success result  │────► ModuleCheckResult(status="success", ...)
│    extract next page URL      │
│    if inert → product_not_found
│    page++                     │
│    if page > 30 → page_limit_exceeded
│  END LOOP                     │
└───────────────────────────────┘
         │
         ▼
┌───────────────────┐
│   CheckService    │  persists latest_version, last_checked_at,
│   (checks.py)     │  last_check_status onto device row
└───────────────────┘
```

---

## 6. Error Result Types (No Persistence)

The following `ModuleCheckResult` error types are returned on failure. None are persisted as separate entities — they are ephemeral return values consumed by the host's check workflow.

| `error_type` | `status` | `diagnostics` | Trigger |
|-------------|----------|---------------|---------|
| `product_not_found` | `"failed"` | `{"pages_checked": int}` | Model not found after full traversal or consecutive-empty termination |
| `parse_error` | `"failed"` | `{}` | Page 1 yields zero parseable firmware entries (structure change) |
| `firmware_page_unavailable` | `"failed"` | `{"http_status": int, "url": str}` | HTTP error, timeout, or transport-level scrape failure on any page |
| `page_limit_exceeded` | `"failed"` | `{"pages_checked": 30}` | Hard 30-page circuit breaker triggered before model found |

For `firmware_page_unavailable`, non-HTTP transport failures (DNS, connection refused) use `http_status: 0` as sentinel.

---

## 7. Design Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | FirmwareEntry is a frozen dataclass, not a database row | The Godox module is a stateless scraper. Firmware listings are parsed per-invocation and discarded — there is no value in persisting volatile third-party page data that could be stale minutes later. |
| D2 | No new migration file | The existing `modules` schema (003_modules.sql) handles module registration. The new `.py` file in `official_modules/` is discovered by the existing seeder at startup with zero schema changes. |
| D3 | page_number on FirmwareEntry is a diagnostic field, not an identity field | Two entries on different pages could represent the same model (though the paginated listing is reverse-chronological and typically unique). `page_number` exists solely for `diagnostics.matched_page` reporting. |
| D4 | Version normalization strips V/v prefix only — no parsing, no rejection | The host's version comparison pipeline handles all format variations (single-segment, multi-segment, non-numeric). The module's responsibility is extraction and pass-through, not semantic analysis. |
| D5 | All outbound HTTP through `scrape_client` parameter | The module has no direct dependency on `httpx`, `requests`, or `aiohttp`. The host-provided `ScrapeClient` bundles robots.txt compliance, User-Agent, timeouts, and rate limiting. |

---

## 8. Test Fixture Data (In-Memory Only)

Six fixture HTML files committed for deterministic offline validation. These are not data model entities — they are filesystem artifacts loaded by `FakeScrapeClient` during pytest execution. All fixture files must be sanitized of any captured credentials, API keys, authentication tokens, session cookies, or personally identifiable information before commit — they contain only the HTML structure and firmware entry data needed for parsing validation.

| Fixture File | Simulates | Used By Test Scenarios |
|-------------|-----------|----------------------|
| `page_1.html` | Page 1 with iT32 at V1.17 | Page-1 hit, case-insensitive match |
| `page_2.html` | Page 2 entries | Multi-page traversal |
| `page_3.html` | Page 3 with V100S at V1.06 | Multi-page detection, early termination |
| `parse_error.html` | Page with zero parseable entries | parse_error on page 1 |
| `empty_page.html` | Page with no firmware entries | Consecutive-empty termination |
| (circuit breaker) | 30 pages of dummy pages via FakeScrapeClient | page_limit_exceeded at page 30 |

---

## 9. Summary

| What | New? | Schema Impact |
|------|------|---------------|
| `FirmwareEntry` dataclass | Yes | None (in-memory only) |
| `MODULE_METADATA` dict | Yes | None (seeded into existing `modules` table) |
| `godox_flashes.py` module file | Yes | None |
| Database tables | No | None |
| Migrations | No | None |
| Existing `modules` table | No (reused) | Existing row inserted via seeder |
