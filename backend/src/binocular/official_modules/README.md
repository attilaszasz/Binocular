# Official Modules

Official modules are bundled extension modules that implement the same trusted in-process authoring contract as user-managed modules. They are not sandboxed.

## Sony Alpha

`sony_alpha.py` supports Sony cameras and lenses listed on the Alpha Universe firmware index at `https://alphauniverse.com/firmware/`. The Sony A7CII / `ILCE-7CM2` fixture is a regression case, not the module's supported-scope boundary.

Rules for maintainers and module authors:

- Use only the injected host `ScrapeClient` for outbound fetches.
- Return failed states (raise ValueErrors) for unsupported models or unparseable pages.
- Keep fixtures deterministic; do not depend on live manufacturer pages in CI.
- Preserve vendor source URLs in successful and failed results when available.

## Canon RF Cameras

`canon_rf_cameras.py` supports exact camera names from Canon Asia English's EOS R catalogue. It needs only a model name: the module follows the catalogue's product link verbatim, discovers that product page's firmware action, deduplicates equivalent operating-system packages by firmware version, and returns the official release-detail page.

- Verified region: Canon Asia English; regional parity or fallback is not implied.
- Coverage boundary: EOS R catalogue bodies only. Cinema EOS and EOS R5 C are unsupported pending a separately verified catalogue/product/action flow.
- Release semantics: fixture versions are captured evidence, not permanently latest claims; binary download routes are not fetched.
- Politeness: every request uses the host-provided scoped `ScrapeClient`. Canon's valid 30-second crawl delay is shared across camera/lens requests and every retry.
- Failure behavior: unknown/ambiguous models, no firmware, changed markup, denied access, timeout, and cancellation remain visible unsuccessful checks.

## Canon RF Lenses

`canon_rf_lenses.py` supports exact classified lens names from Canon Asia English's RF and RF-S catalogues. It requires only a model name, follows catalogue product links verbatim, discovers firmware actions, deduplicates operating-system packages by version, and returns official release-detail pages.

- Verified region: Canon Asia English; regional parity and fallback are not implied.
- Coverage boundary: RF/RF-S lenses only. Adapters, extenders, cinema products, and unrelated mounts are excluded even when the RF catalogue lists them.
- RF-S evidence: catalogue lookup is supported, but the captured RF-S18-45mm source reports no firmware; no positive RF-S release coverage is claimed.
- Release semantics: fixture version `2.0.7` for RF24-105mm F4 L IS USM is captured evidence, not a permanently latest claim; binaries are not fetched.
- Politeness: every request uses the host-provided scoped `ScrapeClient`; Canon's valid 30-second crawl delay is shared across camera/lens requests and retries.
- Failure behavior: unsupported/ambiguous products, no firmware, changed markup, denial, timeout, and cancellation remain visible unsuccessful checks.
