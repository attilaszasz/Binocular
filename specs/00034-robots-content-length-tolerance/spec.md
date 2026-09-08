---
feature_branch: "00034-robots-content-length-tolerance"
created: "2026-09-08"
input: "Fix Sony Alpha firmware checks rejected by a mismatched robots.txt Content-Length header"
spec_type: "technical"
spec_maturity: "ready"
---

# Feature Specification: Robots Content-Length Tolerance

## Problem Statement

The scraper rejects a valid Sony Alpha Universe robots policy because the site's declared Content-Length does not match its downloaded body. This reports the firmware page as robots-disallowed even though the policy explicitly allows it.

## Scope

### Included

- Accept a syntactically valid robots.txt policy when its downloaded body is within the configured size limit, despite an inaccurate Content-Length response header.
- Preserve fail-closed behavior for empty, malformed, oversized, unavailable, or server-error robots responses.
- Add a deterministic regression test for a valid policy with a mismatched Content-Length header.

### Excluded

- Changes to Sony's firmware module or its source URL.
- Relaxing robots directives or the maximum downloaded-body limit.

## Technical Objectives

### Objective 1 - Honor Valid Policies (Priority: P1)

The centralized scraper evaluates the downloaded robots body rather than rejecting an otherwise valid policy because a server supplied an inaccurate length header.

**Independent Test**: Resolve a policy from a valid `User-agent: *` and `Allow: /` body with a mismatched Content-Length header and verify the target URL is allowed.

## Integration Points

- `RobotsChecker._resolve`: validates the downloaded robots response before parsing it.

## Requirements

- **TR-001**: The scraper MUST accept a non-empty, valid robots.txt body whose actual size is at most `max_body_bytes`, regardless of a mismatched Content-Length header.
- **TR-002**: The scraper MUST continue to deny empty, malformed, oversized, unavailable, and server-error robots responses.
- **TR-003**: The scraper MUST have a deterministic regression test for a valid robots policy with a mismatched Content-Length header.

## Assumptions & Risks

### Assumptions

- The fully downloaded response body is authoritative for enforcing the configured maximum size.

### Risks

- Removing header equality validation could accept a proxy-modified response. The existing actual-body limit and parse validation retain bounded, fail-closed handling.

## Implementation Signals

- `MODIFY` — `backend/src/binocular/scraping/robots.py`
- `MODIFY` — `backend/tests/scraping/test_robots.py`

## Success Criteria

- **SC-001** [OBJ1]: A valid allow-all policy with an inaccurate Content-Length permits its target URL.
- **SC-002** [OBJ1]: Existing invalid and oversized robots-policy tests remain passing.
