## Research Report

**Context**: Add a version-search button next to the Module dropdown on the Add Device form. It is clickable when a module is selected and Model is not empty. When clicked, it performs a version search using the selected module for the set Model.

## On-demand Checking UX in Forms
- **Key findings**: Users expect immediate feedback when validating input values. Disabling the validate button when the input is empty or invalid avoids waste.
- **Recommended**: Keep the button disabled until both the module and model inputs are non-empty. Use a loading spinner and clear success/error indicators.
- **Avoid**: Performing automatic validation on typing, which can trigger excessive network requests and rate limits.
### Sources
- https://react.dev — React state management and form input handling

## Safe Ad-hoc Scraper Execution
- **Key findings**: Running scraped requests directly from user input requires handling timeouts and preventing resource exhaustion.
- **Recommended**: Wrap execution in an async timeout. Return standard HTTP 400 errors if the module fails or is not found.
- **Avoid**: Storing side-effects or logging checking statistics as if a real device check occurred.
### Sources
- https://fastapi.tiangolo.com — FastAPI error handling and path/query parameters

### Summary
On-demand version checking enhances UX by providing immediate feedback. The validate button must remain disabled until necessary inputs are present, and the backend must run checks safely with timeouts and no persistent database side-effects.

### Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://react.dev | On-demand Checking UX in Forms | 2026-06-16 |
| https://fastapi.tiangolo.com | Safe Ad-hoc Scraper Execution | 2026-06-16 |
