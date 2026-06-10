# Research: Manual On-Demand Checks

## Topic 1: Concurrent Check Execution
- **Finding**: Running multiple HTTP scraping requests concurrently using `asyncio.gather` on the backend prevents blocking the event loop.
- **Trade-off**: High concurrency can trigger rate limiting on target servers. Resolved by reusing the `ScrapeClient` which enforces per-domain rate limiting.
- **Source**: Python `asyncio` documentation, FastAPI concurrency guidelines.

## Topic 2: Frontend Loading and Comparison State
- **Finding**: Tracking active checking status per device ID allows the UI to show localized spinner animations and disable trigger buttons individually.
- **Trade-off**: Bulk check triggers all cards to show loading state simultaneously. Managed by maintaining a set/list of `checkingDeviceIds` or a boolean `isBulkChecking` in the React component state.
- **Source**: React State Management best practices.
