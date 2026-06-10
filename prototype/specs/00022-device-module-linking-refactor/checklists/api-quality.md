# API Quality Checklist: Device-Module Linking & Refactor
**Created**: 2026-06-04 | **Feature**: [spec.md](../spec.md)

## Breaking Change Documentation

- [ ] CHK001 Are all renamed request fields documented with old→new field name mappings? [Clarity, Contract §6.1]
- [ ] CHK002 Are all renamed response fields documented with old→new field name mappings? [Clarity, Contract §6.2-6.3]
- [ ] CHK003 Are type changes for each renamed field explicitly stated (e.g., `deviceTypeId`: `number` → `moduleId`: `string | null`)? [Completeness, Contract §6.2]
- [ ] CHK004 Is the removal of `deviceType` from the request payload (`DevicePayload`) clearly documented as a breaking change? [Completeness, Contract §6.1]
- [ ] CHK005 Is the removal of `deviceTypeId` from the response object (`DeviceResponse`) clearly documented? [Completeness, Contract §6.2]
- [ ] CHK006 Are endpoint-level behavioral changes (e.g., confirm-update now requires a request body) documented alongside field-level changes? [Completeness, Contract §6.4]
- [ ] CHK007 Is the DELETE endpoint response change (200 with body → 204 No Content) documented? [Completeness, Contract §6.4]
- [ ] CHK008 Are all removed concepts (`DeviceType` entity, free-text type input, `get_or_create_device_type()`) listed in the breaking changes summary? [Completeness, Contract §6.5]

## Request Validation

- [ ] CHK009 Is `moduleId` documented as required on the POST create-device payload? [Completeness, Contract §2.2]
- [ ] CHK010 Is `moduleId` documented as required on the PATCH update-device payload? [Completeness, Contract §2.3]
- [ ] CHK011 Is the `moduleId` field-level validation (`min_length=1`, stripped non-blank check) specified for the Pydantic model? [Clarity, Contract §3.1]
- [ ] CHK012 Are the exact criteria for a valid module (`status='installed'` AND `validation_status='valid'`) documented in the API contract? [Clarity, Contract §7, Spec FR-001]
- [ ] CHK013 Is the validation order specified — i.e., required/missing check before existence check before validity check? [Consistency, Contract §2.2 error table]
- [ ] CHK014 Is the error response for a missing `moduleId` (`module_id_required`) distinct from the error for a non-existent module (`module_not_found`)? [Completeness, Contract §5.2]
- [ ] CHK015 Is there a defined error code for the "no valid modules installed" condition that blocks device creation? [Completeness, Contract §7, Spec FR-007]
- [ ] CHK016 Does the PATCH endpoint reuse the same `moduleId` validation rules as the POST endpoint? [Consistency, Contract §2.2 vs §2.3]

## Error Response Completeness

- [ ] CHK017 Are error responses defined for every inventory endpoint (GET, POST, PATCH, DELETE, confirm-update)? [Completeness, Contract §2.1-2.5]
- [ ] CHK018 Are the error response body shapes documented — distinguishing the FastAPI validation array (`detail[]`) from the application error object (`code` + `detail`)? [Clarity, Contract §5.1-5.2]
- [ ] CHK019 Is the 404 `device_not_found` error defined for the PATCH endpoint (including archived devices)? [Completeness, Contract §2.3]
- [ ] CHK020 Is the 404 `device_not_found` error defined for the DELETE endpoint (including already-archived devices)? [Completeness, Contract §2.4]
- [ ] CHK021 Is the 404 `device_not_found` error defined for the confirm-update endpoint? [Completeness, Contract §2.5]
- [ ] CHK022 Is the 409 `no_latest_version` conflict error documented for the confirm-update endpoint? [Completeness, Contract §2.5]
- [ ] CHK023 Does the GET inventory endpoint specify its error states (e.g., database unavailable, empty result)? [Completeness, Contract §2.1]
- [ ] CHK024 Is the application-level error code convention (snake_case codes: `module_not_found`, `module_not_valid`, `module_id_required`) consistent across all endpoints? [Consistency, Contract §5.2]

## Backward Compatibility

- [ ] CHK025 Is a migration guide or upgrade path documented for API consumers affected by the breaking field renames? [Completeness, Contract §6]
- [ ] CHK026 Are the old field names (`deviceType`, `deviceTypeId`) explicitly listed alongside their replacement fields (`moduleId`)? [Clarity, Contract §6.1-6.2]
- [ ] CHK027 Is the group `id` field type change (`number` → `string | null`) documented as a breaking change with rationale? [Completeness, Contract §6.3, Plan §API Surface]
- [ ] CHK028 Is the API contract versioned to distinguish pre-E022 from post-E022 shapes? [Completeness, Contract §9]
- [ ] CHK029 Is there guidance for API consumers on how to handle the new `null` value for `moduleId` (unlinked devices)? [Completeness, Contract §7, Spec US4]
- [ ] CHK030 Is the "Unlinked" sentinel value (`deviceType: "Unlinked"`, `name: "Unlinked"`) documented as a stable contract string? [Clarity, Contract §6.2-6.3, Spec Glossary]

## Contract Consistency

- [ ] CHK031 Do the TypeScript types in Contract §4 match the Pydantic model field types in Contract §3 (e.g., `moduleId: string | null` in both)? [Consistency, Contract §3 vs §4]
- [ ] CHK032 Is the `DevicePayload.module_id` type consistent between the API contract (§3.1: `str`) and the data-model documentation (data-model §7.1: `int`)? [Consistency, Contract §3.1 vs Data-Model §7.1]
- [ ] CHK033 Is the `DeviceResponse.module_id` type consistent between the API contract (§3.2: `str | null`) and the data-model documentation (data-model §7.2: `int | null`)? [Consistency, Contract §3.2 vs Data-Model §7.2]
- [ ] CHK034 Is the `DeviceGroupResponse.module_id` type consistent between the API contract (§3.3: `str | null`) and the plan's group-by key (plan AD-001: integer FK)? [Consistency, Contract §3.3 vs Plan AD-001]
- [ ] CHK035 Are field aliases (camelCase JSON keys) consistent between the contract Pydantic definitions and the TypeScript interfaces? [Consistency, Contract §3 vs §4]
- [ ] CHK036 Is the `ConfirmUpdatePayload` documented consistently in the Pydantic model (§3.5) and TypeScript type (§4)? [Consistency, Contract §3.5 vs §4]
- [ ] CHK037 Are optional/nullable fields (`moduleId`, `latestVersion`, `lastCheckedAt`, `lastSuccessAt`) marked identically in both backend and frontend type definitions? [Consistency, Contract §3.2 vs §4]
- [ ] CHK038 Is the top-level response wrapper (`InventoryResponse` with `groups` array) consistent between the backend Pydantic model (§3.4) and frontend TypeScript type (§4)? [Consistency, Contract §3.4 vs §4]
- [ ] CHK039 Is the plan's assertion that the API `moduleId` is `modules.module_id` (string) consistent with the contract's Pydantic type definition (`str`)? [Consistency, Plan §API Surface vs Contract §3.1]
- [ ] CHK040 Is the error handling strategy for module deletion (devices become unlinked, `moduleId` set to null) documented in the API contract's behavior notes? [Completeness, Contract §7, Spec FR-008]
