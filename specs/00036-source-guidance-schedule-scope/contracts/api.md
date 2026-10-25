# API Contracts: Sources

## Compatible Surface

| Method / path | Request | Response additions / behavior |
|---|---|---|
| GET /api/v1/modules | None | Existing ModuleResponse[] plus display_name, coverage_notes, model_examples, help_url, guidance_provenance, linked_device_count. |
| GET /api/v1/modules/{module_id}/devices | Positive module ID | 200 ScopeResponse; 404 unknown module; exact current members, not a broad inventory link. |
| POST /api/v1/modules | Existing multipart file/run_phase2 | Existing NDJSON progress envelope; validated optional guidance included in final module object; wrong type/limits produce existing failed event with field/limit/fix guidance; never success after failed persistence. |
| PUT /api/v1/modules/{module_id} | Existing status field, active/inactive/error allowlist | Existing ModuleResponse with additions; inactive commits and automatic entry gate closes before 200; failures return error, not saved state. |
| GET /api/v1/schedules | None | Existing ScheduleResponse[] remains compatible; inactive schedules retained. |
| PUT /api/v1/schedules | Existing module_id and interval_hours >0 | Existing ScheduleResponse; preserves module status; active-only job registration; no implicit resume. |
| POST /api/v1/checks/search-version | Existing module_id/model | Existing stateless manual response/errors; paused modules allowed, no alerts or resume. |

## Module Addition Schema

| Field | JSON type | Default / semantics |
|---|---|---|
| display_name | string | Empty allowed; consumers use readable existing name fallback, stable name remains unchanged. Max 120. |
| coverage_notes | string | Empty allowed; plain text max 1000; examples do not guarantee firmware. |
| model_examples | string[] | [] when absent; max 10, each nonblank ≤120. |
| help_url | string | Empty if absent/unsafe; validated absolute HTTP(S), max 2048. Canonical source_url unchanged. |
| guidance_provenance | enum | verified_official, custom or legacy; server-derived and read-only. |
| linked_device_count | integer | ≥0 on successful query only; failed request does not manufacture zero. |

## Scope Schema

```json
{"module_id": 7, "linked_device_count": 1, "devices": [{"id": 42, "name": "Main Camera", "model": "EOS R5"}]}
```

- **Snapshot**: Count equals devices.length from one membership SELECT, sorted id. Opening/refetching detail replaces summary count with same-query count; concurrent changes afterward require refresh, not implied permanent snapshot.
- **Errors**: Existing HTTPException detail contract retained; 404 missing module, 422 invalid status/interval; unexpected DB failures non-2xx. NDJSON upload keeps HTTP streaming envelope with failed terminal event, not fake HTTP 422 after headers.
- **Caching**: Device create/update/delete/relink invalidates modules plus member query keys for old/new module IDs (or entire module-scope family), devices and relevant schedules; status/upload invalidate modules/schedules/devices. Refetch on window focus and user refresh; fetching/stale counts are visibly updating, failure unknown, true [] zero.
- **Auth**: Existing trusted-LAN optional basic auth applies unchanged; no new account/auth endpoints.
- **Links**: UI independently validates canonical/help URLs, opens with target=_blank and rel="noopener noreferrer"; labels distinguish Source page and Model help. No new vendor requests merely to read fields.
