# Research: Device Model Identifier for Firmware Lookup

**Feature**: 00004-add-device-model  
**Date**: 2026-03-02  
**Purpose**: Inform user story priorities, acceptance criteria, and edge case identification for adding a "model" property to the device entity.

## 1. Manufacturer Firmware Page Identification Patterns

Camera and device manufacturers use distinct internal model codes on their firmware download pages — these do **not** match the marketing/display names users commonly know.

| Manufacturer | Marketing Name | Firmware Page Identifier | Source Pattern |
|---|---|---|---|
| Sony | A7 IV | ILCE-7M4 | `alphauniverse.com/firmware/` lists by internal code |
| Sony | FE 70-200mm f/2.8 GM II | SEL70200GM2 | Same page, lens models use SEL prefix |
| Panasonic | Lumix GH6 | DC-GH6 | `av.jpn.support.panasonic.com/...` lists by DC-/DMC- codes |
| Panasonic | Lumix S 50mm f/1.8 | S-S50 | Lens models use S- prefix |
| Canon | EOS R5 | EOS R5 | Canon often uses marketing name directly |
| Nikon | Z 8 | Z 8 | Nikon also uses marketing name |
| Fujifilm | X-T5 | X-T5 | Fujifilm uses marketing name |

**Key insight**: Some manufacturers (Sony, Panasonic) require a machine-readable model code that differs from the user-friendly name. Others (Canon, Nikon, Fujifilm) use the marketing name as the identifier. The extension module must receive the correct identifier to search the firmware page.

## 2. Relationship Between Model and Device Hierarchy

- **Model belongs on the device, not the device type.** A device type like "Sony Alpha Bodies" groups many different product models (ILCE-7M4, ILCE-7RM5, ILCE-1, etc.). Each individual device has its own model identifier.
- **Model is NOT unique per user inventory.** A user may own two copies of the same camera body (e.g., two ILCE-7M4 units). Both share the same model but are distinct devices with potentially different firmware versions.
- **Model IS the lookup key for extension modules.** When the extension module scrapes the firmware page at the device type's `firmware_source_url`, it searches for the device's `model` value to find the matching firmware entry.

## 3. Required vs. Optional

**Recommendation: Model should be optional (nullable).**

Rationale:
- Users may not know the manufacturer's internal model code when first adding a device.
- Some manufacturers use marketing names that match the device's display name — in those cases, model may be redundant.
- A device without a model can still exist in the inventory for manual version tracking — it just cannot be automatically checked.
- This matches the project's progressive enhancement philosophy: basic inventory first, automated checking later.

When model is missing, the device should show as ineligible for automated firmware checks (similar to "never checked" state).

## 4. UX Best Practices

- **Separate fields**: "Name" (user-chosen display name) and "Model" (manufacturer identifier) should be distinct fields.
- **Help text with examples**: Show contextual examples like "e.g., ILCE-7M4 for Sony A7IV" near the model field.
- **Optional but encouraged**: Mark model as optional, but show a visual nudge (info icon, muted hint) when it's empty, explaining that automated checks require it.
- **No strict format validation**: Model identifiers vary wildly across manufacturers (alphanumeric, dashes, no consistent pattern). Validate only for reasonable length and non-empty-when-provided.

## 5. Migration Strategy

- Non-breaking schema change: `ALTER TABLE device ADD COLUMN model TEXT NULL`
- Existing devices get `model = NULL` — no data loss, no breaking change.
- The API and UI can be updated to accept and display the new field incrementally.

## 6. Edge Cases

1. **User enters model in the name field**: Users accustomed to entering "ILCE-7M4" as the device name may now need to enter it in the model field instead. Help text should clarify.
2. **Multiple devices with the same model**: Two "ILCE-7M4" bodies — both should be able to have the same model value. No uniqueness constraint on model.
3. **Model contains special characters**: Some model codes include slashes, dots, or parentheses (e.g., "DMC-G85/G80"). Store and search as-is.
4. **Model is empty string vs. null**: Empty string after trimming should be treated as null (no model set).
5. **Extension module receives null model**: Module should skip the device or return a clear "no model configured" status rather than crashing.
6. **User changes model after checks have run**: Historical check data remains valid — it was correct at the time. Future checks use the new model.
7. **Same model across different device types**: Unlikely but possible (manufacturer reorganizes product lines). No cross-type uniqueness needed.
8. **Very long model strings**: Apply the same 100-character limit as `current_version` for safety.
9. **Case sensitivity**: Model lookup may be case-sensitive depending on the firmware page. Store as-is, let the extension module handle case matching.
10. **Leading/trailing whitespace**: Trim on input, consistent with existing string field canonicalization (FR-008b in Feature 00002).
