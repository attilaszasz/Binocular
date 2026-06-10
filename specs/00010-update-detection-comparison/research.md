# Research: Update Detection and Version Comparison

## Version Comparison Strategies
We need to compare version strings from diverse hardware/firmware manufacturers (e.g., `v1.2.3`, `20260304-01`, `12.4.0-build54`, or simple numeric/date formats). Since Python's standard library does not have a robust, tolerant, multi-format version parser, we can use a custom parser or `packaging.version` (though standard SemVer is too strict for many firmware versions). A hybrid parser that attempts SemVer/PEP440 parsing via standard patterns and falls back to component-by-component numeric comparison, and ultimately a string comparison, is the most robust approach.

## Error Isolation and Resiliency
To satisfy Core Principle VI (Set-and-Forget Reliability), module execution must be wrapped in error boundaries. If a module execution fails, times out, or throws an unhandled exception, the check service must capture the error and generate a failed `CheckResult` with `success=False` and the error message, ensuring the core process does not crash.

## Database Integration
When a check successfully detects a newer version (based on the version compare utility returning `latest > current`), we must update the device's `has_update` to `True` and its `latest_detected_version` to the new version. The check's timestamp must update `last_checked`.
