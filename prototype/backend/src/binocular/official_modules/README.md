# Official Modules

Official modules are bundled extension modules that implement the same trusted in-process authoring contract as user-managed modules. They are not sandboxed.

## Sony Alpha

`sony_alpha.py` supports Sony cameras and lenses listed on the Alpha Universe firmware index at `https://alphauniverse.com/firmware/`. The Sony A7CII / `ILCE-7CM2` fixture is a regression case, not the module's supported-scope boundary.

## Panasonic Lumix MFT Cameras

`panasonic_lumix.py` supports Panasonic Lumix Micro Four Thirds camera bodies listed on Panasonic's global DSC firmware index at `https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html`. Fixture tests cover current GH and G body rows, grouped aliases such as `DC-G90/G91/G95`, and visible failure cases.

Rules for maintainers and module authors:

- Use only the injected host `ScrapeClient` for outbound fetches.
- Return failed `ModuleCheckResult` values for unsupported models or unparseable pages.
- Keep fixtures deterministic; do not depend on live manufacturer pages in CI.
- Preserve vendor source URLs in successful and failed results when available.