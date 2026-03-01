# Research: Inventory API (CRUD)

## Research Report

**Context**: Domain best practices for designing Binocular's CRUD Inventory API — RESTful resource design for device types and devices, version confirmation patterns, error handling, and self-hosted tool API UX. Focus is on user-facing patterns and best practices to inform specification priorities, acceptance criteria, and edge cases.

---

### 1. CRUD API Best Practices for Inventory Management

#### Resource-Based REST Patterns

- **Key findings**: REST APIs for inventory systems converge on a standard verb-to-action mapping: `POST` (create), `GET` (read), `PUT`/`PATCH` (update), `DELETE` (remove). Resources are nouns (e.g., `/devices`, `/device-types`), not verbs. Successful modern APIs use plural resource names consistently (e.g., `/devices` not `/device`).
- **Recommended patterns**:
  - `GET /resources` → list (with pagination/filtering)
  - `GET /resources/{id}` → single item
  - `POST /resources` → create (returns 201 + Location header)
  - `PATCH /resources/{id}` → partial update (returns 200 + updated resource)
  - `DELETE /resources/{id}` → remove (returns 204 No Content)
- **PATCH vs PUT**: For a homelab tool with many optional fields, **PATCH (partial update)** is strongly preferred. PUT requires the client to send the entire resource representation on every update, which is error-prone and poor UX when a user only wants to change one field (e.g., notes, firmware URL). PATCH allows sending only changed fields. This is the dominant pattern in modern API design (GitHub API, Stripe, etc.).
- **Response enveloping**: For a single-user tool, flat responses (no `{ data: ..., meta: ... }` wrapper) are simpler and more ergonomic. Reserve enveloping for paginated list endpoints where metadata (total count, page info) is needed.
- **Sources**: [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md), [Google API Design Guide](https://cloud.google.com/apis/design), [JSON:API spec](https://jsonapi.org/)

#### Pagination, Filtering, and Sorting

- **Key findings**: For Binocular's expected scale (5–50 devices, 2–10 device types), full pagination infrastructure is likely unnecessary for V1. However, basic sorting and filtering are high-value for usability.
- **Recommended for V1**:
  - **Filtering**: `GET /devices?device_type_id=X` and `GET /devices?status=update_available` are the two most useful filters. Use query parameters, not path segments.
  - **Sorting**: Default sort by name (alphabetical) or by update status (updates first). Accept `?sort=name` or `?sort=-updated_at` (prefix `-` for descending). A single `sort` parameter is sufficient for V1.
  - **Pagination**: Defer cursor/offset pagination to a later version. With <100 items, returning all results is acceptable and simpler. If added later, offset-based (`?limit=25&offset=0`) is simplest for SQLite.
- **Sources**: [Stripe API pagination](https://stripe.com/docs/api/pagination), [Zalando RESTful API Guidelines](https://opensource.zalando.com/restful-api-guidelines/)

#### Bulk Operations

- **Key findings**: Homelab tools commonly surface "Check All" and "Confirm All Updates" as bulk actions. Batch endpoints for actions where the user wants a single-click experience are recommended. Return a summary response listing per-item outcomes (successes and failures).
- **Idempotency for bulk**: Bulk confirm-all should be idempotent — confirming a device that's already up-to-date is a no-op, not an error.
- **Sources**: [Google API Design Guide — Custom Methods](https://cloud.google.com/apis/design/custom_methods), [Stripe bulk operations pattern](https://stripe.com/docs/api)

---

### 2. Hierarchical Resource Management

#### Parent-Child Resource Patterns (DeviceType → Device)

- **Recommended**: **Hybrid approach** — use nested routes for creation (explicit parent-child) and flat routes with filtering for listing/querying (enables cross-type views).
- **Why hybrid**: The main dashboard needs "all devices grouped by type" which is best served by listing all devices. Individual device operations don't need the parent in the URL once created.
- **Sources**: [GitHub API](https://docs.github.com/en/rest), [Stripe API](https://stripe.com/docs/api)

#### Cascade Deletion UX

- **Informative preview**: Include a `device_count` field in DeviceType responses to power confirmation dialogs ("This will also delete 5 devices. Continue?").
- **Confirmation gating**: The API should require an explicit confirmation signal for cascading deletes. Deleting a device type with zero devices should succeed without confirmation.
- **Sources**: [Portainer](https://docs.portainer.io/), [AWS resource deletion patterns](https://docs.aws.amazon.com/)

---

### 3. Version Confirmation / State Transition Patterns

- The "one-click confirmation" is a **state transition**, not a standard CRUD update. Model as a custom action endpoint rather than a generic PATCH.
- **Idempotency**: If `current_version` already equals `latest_seen_version`, the endpoint returns success with the unchanged device. No error, no side effects.
- **Rejection**: Endpoint must reject confirmation on a device that has never been checked (`latest_seen_version` is NULL).
- **Bulk confirm**: A "Confirm All Updates" action confirms all eligible devices. Lower priority than individual confirmation.
- **Sources**: [Google Custom Methods](https://cloud.google.com/apis/design/custom_methods), [Stripe idempotency](https://stripe.com/docs/api/idempotent_requests), [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110)

---

### 4. Error Handling & Validation

- **Consistent error envelope**: `detail` (human-readable), `error_code` (machine-readable), `field` (optional). Extends FastAPI's native `{ "detail": "..." }`.
- **Conflict handling**: Rely on DB UNIQUE constraints and translate `IntegrityError` to 409 Conflict with human-readable messages.
- **Input validation**: Non-empty trimmed names, URL format validation (not reachability), version strings accepted as-is, positive check frequency.
- **Sources**: [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457), [OWASP Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)

---

### 5. Self-Hosted Tool API UX Patterns

- **Discoverability**: FastAPI's auto-generated `/docs` (Swagger UI) is the key API UX advantage. Ensure it is tagged and browsable.
- **Predictable responses**: Always include `id`, `created_at`, `updated_at`. Timestamps in ISO 8601.
- **Immediate feedback**: Mutating endpoints return the updated/created resource in the response body.
- **Health endpoint**: Expected by Docker HEALTHCHECK and monitoring tools.
- **Reference tools**: Uptime Kuma (tri-state status model), Portainer (cascade deletion UX), Mealie (FastAPI + OpenAPI reference).
- **Sources**: [FastAPI docs](https://fastapi.tiangolo.com/features/#automatic-docs), [Mealie API](https://nightly.mealie.io/api/), [Uptime Kuma](https://github.com/louislam/uptime-kuma)

---

## Key Takeaways for Specification

### Priority Guidance

1. **P1**: Core CRUD + single-device confirm + error handling/validation — minimum viable API powering the dashboard.
2. **P2**: Filtering/sorting, cascade deletion safety, grouped inventory views.
3. **P3**: Bulk operations (confirm-all) — valuable but not MVP-blocking.

### Critical Edge Cases

- Creating a device under a non-existent device type.
- Renaming a device to a name that already exists within the same device type.
- Deleting a device type with zero devices (no confirmation needed).
- Confirming a device that was deleted between page load and button click.
- Concurrent rapid confirms (double-click) — must be idempotent.
- Empty/whitespace-only names, extremely long strings.
- No-op partial update (empty body).
- GET for non-existent ID.
