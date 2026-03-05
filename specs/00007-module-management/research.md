# Research: Module Management (API & UI)

**Feature**: 00007-module-management
**Date**: 2026-03-05

## 1. File Upload UX Patterns

Drag-and-drop + click-to-browse is the modern standard for developer-tool file upload (used by Vercel, Netlify, GitHub). Enforce client-side extension filtering (`.py` only) for immediate feedback, but always re-validate server-side. Single-file mode (no batch) keeps the validation feedback model simple and reduces race conditions. Progress indicators beyond a spinner are unnecessary for small files (< 100 KB uploads are nearly instantaneous on localhost).

- https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API/File_drag_and_drop
- https://www.nngroup.com/articles/drag-drop/

## 2. Module/Plugin Management UI Patterns

Self-hosted tools (Home Assistant, Grafana, Vaultwarden) surface plugin lists as tables with name, version, status badge, and actions column. Status badges (Active/Inactive) should use color + text + icon for accessibility — never color alone. Inline error messages on inactive rows are preferred over modal dialogs to minimize context switching. Empty state with call-to-action drives first-time setup without needing documentation.

- Pattern observed in Home Assistant Add-on Store, Grafana Plugin Catalog

## 3. Validation Error Display Patterns

Inline error blocks adjacent to the upload zone outperform toasts for file validation: errors persist while the user edits and re-selects, reducing re-submission friction. Display all errors at once (never stop at the first). Group errors by phase (structural / runtime) so users understand the sequence. Each error should include: error type code (for support), human-readable description, and optionally a line number for syntax errors.

- Pattern referenced in React Hook Form error handling docs; FormKit

## 4. Delete Confirmation UI Patterns

Browser `confirm()` dialogs are inaccessible and unstyled — use an in-page confirmation dialog or inline confirmation. "Type the name to confirm" is over-engineered for single-record deletes; a two-step "Delete → Confirm" button pattern is standard for low-risk deletions in self-hosted tools. After deletion, automatically refresh the adjacent list rather than requiring a manual reload.

- https://design.gitlab.com/patterns/confirmations

## 5. Filename Sanitization for Upload APIs

OWASP upload guidance: allowlist extension (`.py`), reject null bytes and path traversal characters (`/`, `\`, `..`), strip leading dots or underscores when needed (or reject them). Filename should be stored and used exactly as uploaded (no UUID renaming) so users can correlate file names with module identifiers. Restrict to ASCII alphanumeric + underscore + hyphen + dot for maximum filesystem portability.

- https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
