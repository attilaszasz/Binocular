## Research Report

**Context**: Investigation of manufacturer firmware endpoints and HTML structures for Panasonic Lumix cameras, Panasonic Lumix lenses, and Godox flashes to support robust scraping and automatic seeding.

## Panasonic Lumix MFT Cameras scraping
- **Key findings**: Panasonic publishes Micro Four Thirds (MFT) camera updates on a single index page with model numbers in the table rows. The download links use specific JavaScript handlers in the format `javascript:OpenWinX()`.
- **Recommended**: Fetch from the main index URL, extract table cell contents, match model names using regex, and resolve the JavaScript handlers to their corresponding popup window URLs.
- **Avoid**: Relying on static IDs or assuming table column layouts remain completely unchanged; search cells sequentially for valid model patterns.
### Sources
- https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html — Official Panasonic Lumix camera firmware index

## Panasonic Lumix Lenses scraping
- **Key findings**: Panasonic lens firmware is hosted on a separate page (index5.html) but shares the exact same table structure and JavaScript window-opening handler conventions as the camera page.
- **Recommended**: Reuse the table cell parsing logic and popup resolver from the camera module. Model regex matches lens patterns starting with `H-` or `S-`.
- **Avoid**: Merging cameras and lenses into a single module; keep separate modules to align with the core inventory design.
### Sources
- https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index5.html — Official Panasonic Lumix lens firmware index

## Godox Flashes scraping
- **Key findings**: Godox firmware lists are paginated, containing five entries per page in reverse chronological order. Pagination is checked using next-page link class selectors, terminating when next links are inert (`javascript:;`).
- **Recommended**: Implement multi-page pagination with a safety limit of 30 pages and early termination. Normalize model names by removing non-alphanumeric characters for reliable matching.
- **Avoid**: Unlimited page fetching or failing when page structure slightly changes on downstream pages; apply a strict circuit breaker.
### Sources
- https://www.godox.com/firmware-flash/ — Official Godox flash firmware index

### Summary
Panasonic uses single-page HTML tables with JavaScript popups for firmware links. Godox utilizes paginated lists requiring multi-page traversal. All modules must run their HTTP requests within a dedicated event loop when called in worker threads.

### Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html | Panasonic Lumix MFT Cameras scraping | 2026-06-11 |
| https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index5.html | Panasonic Lumix Lenses scraping | 2026-06-11 |
| https://www.godox.com/firmware-flash/ | Godox Flashes scraping | 2026-06-11 |
