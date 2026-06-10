# Research: Official Sony Alpha Module
> Feature E011 | 2026-06-10 | Purpose: Sony Alpha update scraping

## Sony Alpha Universe Scraper
- **Decision**: Read `window.firmwareProducts` JSON object embedded in the script tag of the Alpha Universe HTML.
- **Rationale**: The official Sony Alpha page embeds all camera and lens products and firmware metadata in a single JSON block, which is much more robust than parsing HTML table rows directly.
- **Rejected**: Parsing table rows via BeautifulSoup. Rejected because table layouts change more frequently than the underlying JSON data store.
- **Pitfalls**: JSON parsing might break if Javascript string escaping is complex. Use python `json.loads` after extracting matching brackets.
- **Sources**: https://alphauniverse.com/firmware/

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Sony Alpha Universe Scraper | Read embedded JSON | Embedded JSON is structured and more robust than HTML layout |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://alphauniverse.com/firmware/ | Sony Alpha Universe Scraper | 2026-06-10 |
