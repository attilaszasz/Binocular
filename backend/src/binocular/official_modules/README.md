# Official Modules

Official modules are bundled extension modules that implement the same trusted in-process authoring contract as user-managed modules. They are not sandboxed.

## Sony Alpha

`sony_alpha.py` supports Sony cameras and lenses listed on the Alpha Universe firmware index at `https://alphauniverse.com/firmware/`. The Sony A7CII / `ILCE-7CM2` fixture is a regression case, not the module's supported-scope boundary.

Rules for maintainers and module authors:

- Use only the injected host `ScrapeClient` for outbound fetches.
- Return failed `ModuleCheckResult` values for unsupported models or unparseable pages.
- Keep fixtures deterministic; do not depend on live manufacturer pages in CI.
- Preserve vendor source URLs in successful and failed results when available.