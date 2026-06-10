# Research — Official Panasonic Lumix Module

## Source Discovery

- User-provided URL: `https://alphauniverse.com/firmware/` contains `PANASONIC_CAMERAS` picker entries for Lumix bodies but no Panasonic firmware version, date, or download URL fields. It cannot support latest-version detection.
- Canonical source selected for implementation: `https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html`, Panasonic's global digital still camera firmware index.
- The Panasonic page lists MFT camera bodies in table rows with model, latest `Ver.x`, release date, and JavaScript download-detail links.

## Parsing Approach

- Parse only table rows that contain Panasonic MFT camera model codes (`DC-G*`, `DMC-G*`, `DC-BGH*`) and firmware versions.
- Resolve download links by mapping `OpenWinNN()` handlers to relative `window.open("fts/dl/...html")` targets declared in the page scripts.
- Match devices by normalized model aliases, including slash-separated variants such as `DC-G90`, `DC-G91`, and `DC-G95`.

## Validation Approach

- Use captured Panasonic fixture rows for GH and G bodies, including grouped alias rows and an entry without firmware.
- Verify the module loads through the extension contract and uses only the injected `ScrapeClient`.
- Include visible failure tests for unparseable pages, unknown models, and listed models without firmware.