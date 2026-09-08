# Implementation Plan: Robots Content-Length Tolerance

**Branch**: `main` | **Date**: 2026-09-08 | **Spec**: [spec.md](spec.md)

## Summary

Evaluate the actual downloaded robots.txt body against the configured bound; do not convert a valid policy into a denial because its Content-Length header is inaccurate.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: httpx, urllib.robotparser  
**Storage**: N/A  
**Testing**: pytest  
**Target Platform**: Linux Docker container  
**Project Type**: web  
**Project Mode**: brownfield  
**Constraints**: Preserve centralized, fail-closed robots enforcement and bounded response handling.

## Instructions Check

- Honest Failure: Invalid, unavailable, and oversized policies remain explicit denials.
- Polite by Default: The centralized client continues to parse and enforce source robots directives.
- Type Safety: The minimal condition change retains strict typing.

## Architecture

Remove only the Content-Length equality condition from `RobotsChecker._resolve`. The downloaded `response.content` remains subject to the existing 512 KiB bound before decoding and parsing.

## Architecture Decisions

| ID | Decision | Chosen | Rationale |
|----|----------|--------|-----------|
| AD-001 | Policy body size authority | Actual downloaded body | Servers can publish inaccurate Content-Length headers; the received body is directly bounded and parsed. |

## Data Model Summary

N/A

## API Surface Summary

N/A

## Testing Strategy

| Tier | Tool | Scope |
|------|------|-------|
| Unit | pytest | Valid robots body with mismatched Content-Length remains allowed. |
| Regression | pytest | Existing malformed and oversized policy denials. |

## Error Handling Strategy

| Error Category | Response |
|------|----------|
| Actual body empty or oversized | Deny policy |
| Body lacks robots directives or cannot decode | Deny policy |
| Content-Length disagrees with body | Parse and enforce actual body |

## Integration Points

| Spec Reference | Component | Approach |
|------|-----------|----------|
| TR-001 | `RobotsChecker` | Bound `response.content`, then decode and parse it. |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Oversized response acceptance | Continue checking actual content length against `max_body_bytes`. |

## Requirement Coverage Map

| Req ID | File Path | Notes |
|--------|-----------|-------|
| TR-001 | `backend/src/binocular/scraping/robots.py` | Remove header-equality rejection. |
| TR-002 | `backend/src/binocular/scraping/robots.py` | Keep existing actual-body and parse checks. |
| TR-003 | `backend/tests/scraping/test_robots.py` | Add mismatched-header regression coverage. |

## Project Structure

```text
backend/
  src/binocular/scraping/robots.py
  tests/scraping/test_robots.py
```
