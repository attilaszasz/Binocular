---
adr_id: ADR-0009
status: accepted
date: 2026-06-04
tags: [data-model, domain-model, device-inventory, modules]
supersedes: []
superseded_by: ""
related_artifacts: ["specs/prd.md#CAP-001", "specs/prd.md#CAP-002", "specs/project-plan.md epic E005"]
---

# ADR-0009: Module-Derived Device Type — Remove Standalone Device Type Field, Derive from Linked Module

## Status

Accepted.

## Context

The Binocular project currently has a standalone "Device Type" concept — a user-visible field on the device creation form where the operator groups devices by type (e.g., "Sony E-Mount Lenses"). The device type is an independent entity that also links to extension modules for scheduled checking.

The proposed change removes the standalone device type field from the device form. Instead, the device creation form presents a module selector. Users explicitly link each device to an extension module at creation time. The device type is then derived from the linked module — the module defines its device type, and the device inherits it. This simplifies the data model (one less entity/relationship) and eliminates the possibility of type/module mismatches.

## Decision Drivers

- Data model simplicity — fewer entities and relationships reduce surface area for bugs
- Consistency guarantee — deriving device type from the linked module eliminates type/module mismatch
- User workflow clarity — explicit module selection makes the device→module relationship visible and intentional
- Implementation simplicity — removing the standalone DeviceType entity reduces CRUD surface and migration complexity

## Considered Options

### Option A: Module selector on device form, derive device type from module

Replace the device type field with a module selector. Device type is a derived property of the module link. No standalone DeviceType CRUD needed.

- **Pros**: Eliminates the DeviceType entity entirely, eliminates type/module mismatch, makes device→module relationship explicit, cleaner creation form (one selector instead of two).
- **Cons**: Device grouping by type requires a JOIN through modules rather than a direct FK; existing feature-level implementation work for CAP-001 needs revision.

### Option B: Keep standalone device type with optional module link

Maintain DeviceType as an independent entity. Devices belong to a type; modules optionally linked to types. Requires reconciliation logic when a module's type and a device's type differ.

- **Pros**: Preserves existing data model; no migration cost; device type is materialized as a column for fast grouping.
- **Cons**: Two sources of truth for the type relationship; requires reconciliation surface; operator must manage DeviceType as a separate entity.

### Option C: Hybrid — type selector filters available modules

Keep device type as a selector, but use it as a filter to show only compatible modules. Still requires standalone DeviceType entity and the reconciliation surface.

- **Pros**: Guided workflow — type selection narrows module options; preserves existing entity model.
- **Cons**: Retains DeviceType entity and reconciliation complexity; two-step form (type then module) is more work for the operator; still possible to create type/module inconsistencies if both are independently mutable.

## Decision Outcome

Chosen option: **Option A: Module selector on device form, derive device type from module** — Option A eliminates the DeviceType entity entirely from the CRUD surface, reducing the number of domain concepts the operator must manage. Deriving type from the module is a single source of truth — there is no possibility of a device being assigned to one type while its linked module claims another. This simplifies the data model (Device gains a `module_id` FK, loses `device_type_id` FK), reduces API endpoints, and makes the device creation form a single step rather than a two-step (first pick type, then link to module). The cost is that device type grouping is computed at query time rather than materialized as a column, but this is a trivial GROUP BY for a single-user app with 50+ devices.

## Consequences

### Positive

- Fewer domain entities to maintain (DeviceType removed from CRUD)
- Impossible to create type/module mismatch
- Device→module relationship is explicit and visible to the operator
- Cleaner creation form: one selector instead of two

### Negative

- Device grouping by type requires a JOIN through modules rather than a direct FK
- Existing feature-level implementation work for CAP-001 (epic E005) needs revision
- Future migration from standalone DeviceType to module-derived type requires careful data handling

### Neutral

- Module becomes a required field at device creation time (device cannot exist without a module)

## Links

- [specs/prd.md](../prd.md) — CAP-001 (Device Inventory Management)
- [specs/prd.md](../prd.md) — CAP-002 (Extension Module Engine)
- [specs/project-plan.md](../project-plan.md) — epic E005
