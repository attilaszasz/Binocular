---
feature_branch: "00028-html-email-notification-design"
created: "2026-06-07"
input: "E027 HTML Email Notification Design — responsive HTML email, light-themed, mobile-friendly"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E027"
epic_sources: "{PRD:CAP-007}"
---

# Feature Specification: HTML Email Notification Design

**Feature Branch**: `00028-html-email-notification-design`
**Created**: 2026-06-07
**Status**: Clarified
**Spec Type**: product
**Spec Maturity**: clarified
**Epic ID**: E027
**Epic Sources**: {PRD:CAP-007}
**Product Document**: specs/prd.md

## Problem Statement

Current email notifications are plain text with no visual hierarchy, making firmware update alerts hard to scan on mobile devices and visually inconsistent with the Binocular web interface. Operators receiving update alerts on their phones see unstyled monospace text that buries the critical version-delta information. Converting to responsive HTML email improves scanability, matches the product's polished light-themed visual identity, and maintains the set-and-forget reliability promise by making alerts immediately actionable.

## Scope

### Included

- Responsive HTML email template for firmware update alert notifications with single-column layout
- Light color scheme matching the Binocular web interface (warm surface, white card, teal accent)
- Mobile-friendly design that renders correctly on screens 375px–600px wide
- Version comparison display (current → latest) with visual emphasis on the update
- Device name, device type, source URL, and notification timestamp in the email body
- Plain-text multipart/alternative fallback for non-HTML email clients
- Conditional HTML body format applied to SMTP channels only; Gotify notifications unchanged

### Excluded

- HTML email for Gotify (uses text-only display, no HTML support) — channel-specific format
- Interactive elements (buttons, forms, JavaScript) — unsupported in email clients
- Email template customization UI — out of scope for this epic
- HTML formatting for test notifications — test notifications remain plain text
- Dark mode email variant — light theme only, consistent with PRD scope

### Edge Cases & Boundaries

- Email client strips CSS in `<head>`: fallback inline styles on every element must maintain readability
- Plain-text fallback for clients that don't render HTML (text-only readers, accessibility tools)
- Long device names or URLs: must wrap without breaking the single-column layout
- Missing optional fields (source URL not available): the URL row is removed entirely and adjacent spacing collapses to prevent visible gaps in the card layout
- Very small screens (<375px): fluid widths prevent horizontal scroll; content remains legible but may require zoom
- HTML special characters in device names or versions (`<`, `>`, `&`, `"`, `'`): escaped via `html.escape(s, quote=True)` before template insertion to prevent rendering breakage or attribute injection
- Unicode bidi-override and homoglyph characters in device names (U+202A–U+202E, U+2066–U+2069): stripped or replaced to prevent visual reordering or spoofing of email content by the email client
- Template construction failure at dispatch time: fall back to plain-text email body and log error in activity log
- SMTP channel not configured: HTML template exists but is never invoked; no error

## User Scenarios & Testing

### User Story 1 - Receive Readable Firmware Alert on Mobile (Priority: P1)

As a homelab operator checking email on my phone, I want firmware update alerts formatted as a clean, scannable HTML card so I can immediately see which device has an update and what versions are involved without squinting at plain text.

**Why this priority**: Core value proposition — the entire point of converting to HTML is making alerts readable and actionable on mobile, where most operators first see them. Without mobile readability the feature has no utility.

**Independent Test**: Trigger a firmware update detection for a device, verify the received email displays as a styled HTML card with device name prominently visible on a 375px-wide mobile viewport.

**Acceptance Scenarios**:

1. **Given** a firmware update is detected for "Sony A7 IV" (current: v1.10, latest: v1.20), **When** the email notification is dispatched, **Then** the received email renders as HTML with a single-column card showing the device name, current version, arrow indicator, and latest version in a visually scannable layout.
2. **Given** the operator opens the email on a mobile device (viewport width ≤ 600px), **When** the email renders, **Then** the card spans the full viewport width without horizontal scrolling and all text remains readable at 14px+ font size.
3. **Given** the operator's email client does not support HTML, **When** the email is opened, **Then** a plain-text multipart/alternative fallback displays the same information in a readable text format.
4. **Given** the notification email dispatches successfully (HTML or plain text), **When** the operator views the activity log in the Binocular UI, **Then** the detection result and dispatch status are recorded regardless of which email format was used.
5. **Given** an HTML email is dispatched, **When** the raw email source is inspected, **Then** every HTML element has a `style` attribute with inline CSS and no `<style>` blocks or `<link>` elements are present.
6. **Given** a device name containing `\r\n` control characters, **When** the email subject line is constructed, **Then** the control characters are stripped and the subject reads "Binocular: Firmware update for {sanitized_name}".
7. **Given** 25 firmware detections occur in one check cycle, **When** notifications dispatch, **Then** exactly 20 emails are sent and the remaining 5 detections produce activity-log entries recording the detection with "skipped" status.
8. **Given** HTML template construction throws an error at dispatch time, **When** the notification dispatches, **Then** a plain-text email body is sent instead and the activity log records the error type, the device identifier, and an indication that the plain-text fallback path was taken.
9. **Given** an SMTP password is present in the Apprise connection URL, **When** the activity log entry is written, **Then** the password portion is replaced with `***` and the redacted URL is logged.
10. **Given** a device name exceeds 128 characters, **When** the notification is processed, **Then** the name is truncated to 128 characters with a trailing ellipsis and the HTML email renders without layout overflow.

### User Story 2 - Consistent Light-Themed Branding (Priority: P1)

As a Binocular user, I want the email notification to reflect the same light color scheme as the web interface so the product feels cohesive and professionally maintained end-to-end.

**Why this priority**: Brand consistency builds trust in a set-and-forget tool. The PRD explicitly requires the light color scheme. Without it, the HTML email is visually disconnected from the product.

**Independent Test**: Compare a screenshot of the received HTML email against the Binocular light-themed web UI; verify color palette matches (warm surface background, white card, teal accent, slate text).

**Acceptance Scenarios**:

1. **Given** the Binocular light theme uses surface `#F4F1EA`, card `#FFFFFF`, text `#1F2937`, and accent `#0A8478`, **When** an email notification is rendered, **Then** the email uses these same colors for background, content card, headings, and accent elements.
2. **Given** the operator has the web UI set to light mode, **When** they receive an email notification, **Then** the visual identity (colors, typography hierarchy, spacing) is recognizably consistent with the web interface.

### User Story 3 - Gotify Notifications Unchanged (Priority: P2)

As an operator using Gotify for push notifications, I want Gotify alerts to remain in their current text format so my existing notification workflow is not disrupted by the email HTML changes.

**Why this priority**: Non-breaking change is table stakes. Gotify is a separate channel with different formatting expectations. P2 because it's a constraint, not a user-facing enhancement.

**Independent Test**: Trigger a firmware update detection, verify the Gotify notification body matches the existing plain-text format character-for-character with no HTML tags.

**Acceptance Scenarios**:

1. **Given** both SMTP and Gotify channels are configured, **When** a firmware update is detected, **Then** the Gotify notification body is plain text (matching the pre-HTML format) while the email notification is HTML.
2. **Given** only a Gotify channel is configured (no SMTP), **When** a firmware update is detected, **Then** the notification dispatches successfully with the existing plain-text body and no HTML content is generated.

## Requirements

### Functional Requirements

- **FR-001**: System MUST format firmware-update email notifications as responsive HTML using a single-column layout with a maximum width of 600px.
- **FR-002**: System MUST apply inline CSS on all HTML elements for email client compatibility.
- **FR-003**: System MUST HTML-escape all user-origin data fields (device name, device type, current version string, latest version string, source URL) before inserting into the HTML template to prevent rendering breakage or injection. Source URLs MUST be validated as well-formed `http` or `https` scheme URLs before inclusion in the email body. Source URLs that fail validation (missing or non-http/https scheme) are omitted from the email body; the omission is logged at INFO level.
- **FR-004**: System MUST include device name, device type, current firmware version, latest firmware version, and source URL in the HTML email body.
- **FR-005**: System MUST display the version change as a directional comparison (current version → latest version) with visual emphasis on the new version.
- **FR-006**: System MUST include a plain-text multipart/alternative body presenting the same device name, device type, current version, latest version, and source URL fields as the HTML version in a readable text-only format (field-per-line with labels). Plain-text bodies do not interpret HTML metacharacters; HTML-specific escaping is not required for the `text/plain` MIME part.
- **FR-007**: System MUST set the email subject line to the fixed format "Binocular: Firmware update for {device_name}" for HTML and plain-text emails. Device name values MUST be stripped of CRLF sequences (`\r\n`), null bytes, and all control characters (ASCII 0x00–0x1F, 0x7F; Unicode C1 0x80–0x9F) before header insertion to prevent email header injection per RFC 5322.
- **FR-008**: System MUST dispatch Gotify notifications with the same plain-text body format as before HTML support was added, without HTML tags or styling.
- **FR-009**: System MUST dispatch one email notification per detected device update; a batch of N simultaneous detections produces N separate emails, capped at 20 emails per check cycle with excess detections logged as individual activity-log entries.
- **FR-010**: System MUST use the Binocular light color scheme in the HTML email (surface `#F4F1EA`, card `#FFFFFF`, heading text `#1F2937`, metadata `#5B6875`, accent `#0A8478`).
- **FR-011**: System MUST conditionally apply HTML body format for firmware-update notifications on SMTP channels only; test notifications always use plain text regardless of channel type.
- **FR-012**: System MUST fall back to plain-text email dispatch and log the error in the activity log if HTML template construction fails at dispatch time. The log entry MUST include the error type, the affected device identifier, and an indication that the plain-text fallback path was taken, to differentiate template failures from SMTP transport failures during incident investigation.
- **FR-013**: System MUST preserve the detection result in the activity log regardless of email formatting choices. Each activity log entry MUST record the dispatch format used (HTML, plain text, or fallback) to enable post-incident determination of the active format path. SMTP passwords, Apprise URL userinfo credentials, and API keys passed via configuration MUST be redacted from all log output (activity log, error messages, debug traces, stack traces). Activity log entries MUST sanitize device name values by escaping or stripping newline characters (`\n`, `\r`) to prevent log injection. The notification library version and dispatch method MUST be recorded in the activity log for traceability when dependency regressions alter HTML body handling.
- **FR-014**: System MUST enforce input length limits (device name ≤128, source URL ≤2048, version ≤64) at the application boundary (the first point where external data enters the notification subsystem — the dispatch function entry) before any processing or template rendering. Truncation, when applied, MUST preserve character integrity and not produce garbled text. Truncated values are suffixed with an ellipsis character.
- **FR-015**: System MUST apply CSS word-break and overflow-wrap rules to all user-origin data fields in the HTML template to prevent layout overflow at narrow viewports.

### Key Entities

- **EmailTemplate**: The HTML and plain-text body structure for firmware update notifications. Constructed at dispatch time from a parameterized template with named content slots for device data fields and color tokens matching the light color scheme. Not persisted.
- **Notification (extended)**: The existing notification dispatch extended with a per-channel format discriminator (HTML body for email, text body for push). Each firmware detection triggers one email per device; N detections produce N emails.

## Assumptions & Risks

### Assumptions

- Operators' SMTP servers support `multipart/alternative` MIME messages with HTML body parts.
- Major email clients (Gmail, Apple Mail, Outlook) will render inline-CSS HTML emails as intended; minor rendering differences in fringe clients are acceptable.
- The light color scheme defined in the web interface translates acceptably to email-safe hex colors.
- The notification dispatch library correctly handles HTML body format for email channels.

### Risks

- **Email client rendering variance** *(likelihood: medium, impact: low)*: Some email clients may strip inline CSS or render colors differently. Mitigation: use only email-safe CSS properties; accept minor cosmetic differences in legacy clients.
- **Notification dispatch library HTML body regression** *(likelihood: low, impact: medium)*: A library update could change HTML handling. Mitigation: verify HTML body format handling on dependency upgrades through acceptance testing.
- **Gotify receiving HTML by mistake** *(likelihood: low, impact: medium)*: If channel dispatch is not properly separated, Gotify could receive HTML content. Mitigation: explicit format check per channel type in dispatch code; test that Gotify body contains no HTML tags.

## Implementation Signals

- `NEW-API` — Notification dispatch gains per-channel format selection (HTML for email, plain text for push channels)
- `NEW-ENTITY` — EmailTemplate structure (not persisted) for HTML body generation with color tokens and content slots
- `EXTERNAL-SERVICE` — Email channel dispatch uses HTML body format; push channel dispatch unchanged

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: HTML email notification displays device name, versions, and source URL in a scannable single-column card on a 375px-wide viewport with no horizontal scrolling.
- **SC-002** [US1]: Plain-text fallback email contains the same information as the HTML version, accessible to text-only email clients.
- **SC-003** [US2]: The rendered email source uses the exact hex colors specified in the light color scheme (surface `#F4F1EA`, card `#FFFFFF`, heading text `#1F2937`, metadata `#5B6875`, accent `#0A8478`), matching the Binocular light-themed web interface palette.
- **SC-004** [US3]: Gotify notifications appear unchanged to the operator, displaying the same readable text format as before HTML support was added, with no visible markup or styling artifacts.
- **SC-005** [US1]: Email renders without horizontal scrollbar, all text at ≥14px, and no overlapping elements (card width ≤ viewport) in Gmail (web), Apple Mail (iOS), and Outlook (web) on both 375px and 1440px viewports.
- **SC-006** [US1]: Activity log records the detection result and dispatch status regardless of whether the email was formatted as HTML or plain text.

## Clarifications

### Session 2026-06-07

- Q: How is the HTML email template constructed at dispatch time? → A: Jinja2 template string with `render()` at dispatch time.
- Q: What should the HTML email subject line contain? → A: Fixed format "Binocular: Firmware update for {device_name}".
- Q: Should the system send one email per device or batch multiple updates into a single email? → A: One email per device (each detection triggers its own notification).
- Q: How should data values be sanitized before insertion into the HTML template? → A: Apply `html.escape()` to all user-origin data fields before template insertion.
- Q: Are color tokens CSS custom properties, named substitution placeholders, or something else? → A: Named placeholder strings in a Jinja2 template (e.g., `{{ device_name }}`, `{{ accent_color }}`).
- Q: What happens if HTML template construction itself fails at dispatch time? → A: Fall back to plain-text email body and log the template error in the activity log.
- Q: How should the template handle scenarios that could produce large emails? → A: Template design ensures fixed-size content; no special size limit enforcement needed.
- Q: What specific measurable criteria define "without layout breakage" for SC-005? → A: No horizontal scrollbar AND all text ≥ 14px AND no element overlap; card width ≤ viewport.

### Session 2026-06-07 — Security Checklist Evaluation

- Q: Does Jinja2 autoescape apply universally without opt-out paths? → A: Yes — Jinja2 `Environment` is configured with `autoescape=True`; no `|safe` filter overrides are used in the email template (plan.md HINT-002, AD-004).
- Q: Are user-supplied values ever concatenated into raw template strings? → A: No — all user data passes through Jinja2 template variables (dictionary context) after `html.escape()` is applied. No code path concatenates user data into the template source string.
- Q: Does the fallback path construct HTML strings manually? → A: No — the fallback path produces a plain-text body only, not HTML, so no injection risk from fallback construction (plan.md Error Handling).
- Q: Are color tokens sourced from user input? → A: No — color tokens (`{{ accent_color }}`, `{{ surface_color }}`, etc.) are hardcoded hex constants, never from user input (FR-010, plan FR-010 mapping).
- Q: Do templates contain executable code blocks or custom filters? → A: No — the HTML template uses only Jinja2 markup, named placeholders, and standard control-flow constructs per AD-001. No custom filters, extensions, or Python code blocks.
- Q: Are external resources (images, fonts, stylesheets) referenced in the email? → A: No — all CSS is inline (FR-002); no remote images, web fonts, or external stylesheets are referenced, preventing tracking beacons.
- Q: Are inline CSS style values constructed from user input? → A: No — all `style` attribute values are hardcoded in the template from trusted constant strings. User data goes only into text content slots, never into attribute values.
- Q: Does the 20-email cap include a mechanism to prevent resource exhaustion? → A: Yes — the detection loop short-circuits after 20 dispatches per cycle, with excess detections logged as activity-log entries with "skipped" status (FR-009, plan Error Handling).
- Q: Is the fallback guarantee testable under induced failure? → A: Yes — the plan Testing Strategy includes a Security-tier test specifically for the template error path with induced failure conditions.

## Stress-Test Findings

### Session 2026-06-07

- **STF-001** [CRITICAL — resolved]: Duplicate requirement IDs FR-006, FR-007, FR-009. Renumbered Gotify requirement to FR-008, removed exact duplicates. Requirements now FR-001 through FR-015 with unique IDs.
- **STF-002** [HIGH — resolved]: No upper bound or rate limiting on simultaneous email dispatch. Added 20-emails-per-cycle cap to FR-009 with excess detections logged as activity-log entries.
- **STF-003** [MEDIUM — resolved]: User-origin data fields have no maximum length, risking layout overflow at narrow viewports. Added FR-014 (character limits with truncation) and FR-015 (CSS word-break/overflow-wrap rules).
- **STF-004** [HIGH — resolved]: FR-010 conflicted with Excluded section on test notification format. Refined FR-011 to scope HTML to firmware-update notifications only; test notifications always plain text.
- **STF-005** [MEDIUM — resolved]: 320px viewport boundary claimed in scope but never tested. Narrowed scope to 375px–600px to match SC-001/SC-005 test coverage; edge case updated to <375px.

## Glossary

| Term | Definition |
|------|------------|
| Check cycle | One complete polling interval across all configured firmware sources (typically 10 minutes), encompassing detection of updates across all monitored devices and subsequent notification dispatch. |
| Multipart/alternative | A MIME message structure where email contains both HTML and plain-text versions; the client renders whichever it supports. |
| Inline CSS | CSS styles applied directly to HTML elements via the `style` attribute, required for email client compatibility as `<style>` blocks are often stripped. |
| Email-safe CSS | A subset of CSS properties known to render consistently across major email clients (Gmail, Outlook, Apple Mail). |
| Color token | A named placeholder in the Jinja2 template (e.g., `{{ accent_color }}`) that resolves to a hex color value from the light color scheme at render time. |
| Content slot | A named placeholder in the Jinja2 template (e.g., `{{ device_name }}`) into which a device data value is substituted at render time. |
