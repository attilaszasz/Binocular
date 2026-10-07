# Official Guidance Evidence

| Stable name | Display name | Contract type / coverage | Examples | Human help URL | Verified matching / exclusions |
|---|---|---|---|---|---|
| sony_alpha | Sony Alpha cameras & lenses | camera / cameras & lenses | ILCE-7CM2; SEL2470GM | https://alphauniverse.com/firmware/ | Index model/name/SKU; normalization, Alpha/A aliases; not every Sony product. |
| panasonic_lumix | Panasonic Lumix MFT cameras | camera / MFT cameras | DC-GH7; DC-G91 | https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html | DC/DMC MFT codes, grouped aliases, punctuation/case normalization; no full-frame DC-S5. |
| panasonic_lumix_lenses | Panasonic Lumix lenses | lens (correct existing camera constant) / L-mount & MFT lenses | S-R1635; H-ES12035 | https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index5.html | S-/H- normalized exact codes; H-FS14140 lacks handler and must fail visibly. |
| godox_flashes | Godox flashes | flash / flashes | iT32; V100S | https://www.godox.com/firmware-flash/ | Firmware flash pages; punctuation/case normalization; suffix identifies mount variant. |
| viltrox_lenses | Viltrox lenses & teleconverters | lens / lenses & teleconverters | AF 50/1.2 FE; TC-2.0X FE | https://viltrox.com/pages/download-center-1 | Index text/slug matching; mount suffix required; Document Download only, companion app excluded. |
| nikon_z_series | Nikon Z-series cameras | camera / Z-series mirrorless cameras | Z 30; Z 6II | https://downloadcenter.nikonimglib.com/en/index.html | XML Mirrorless/Z Series; spacing/underscore/case aliases; exclude DSLR, lenses, speedlights. |
| canon_rf_cameras | Canon EOS R cameras | camera / EOS R cameras, Canon Asia English | EOS R5 | https://asia.canon/en/support/models?series=3 | Exact case/whitespace-normalized names; exclude Cinema EOS/EOS R5 C; no regional parity. |
| canon_rf_lenses | Canon RF/RF-S lenses | lens / RF/RF-S lenses, Canon Asia English | RF24-105mm F4 L IS USM | https://asia.canon/en/support/models?series=4 | Exact normalized names; exclude adapters/extenders/cinema/other mounts; RF-S18-45 has no firmware, no positive RF-S release verified. |

## Evidence and Preservation

- **Source**: `backend/src/binocular/official_modules/<stable name>.py`; matching `backend/tests/test_official_<stable name>_module.py` and `backend/tests/fixtures/<stable name>/` inspected at `b1b8b99`.
- **Link evidence**: Godox `_build_page_url(1)`; Panasonic lens `_DEFAULT_INDEX_URL`; Nikon consumer download centre from existing research (not XML); other human links reuse existing `SOURCE_URL`.
- **Canonical URLs**: Preserve all eight existing `SOURCE_URL` values verbatim, including Panasonic lens `index.html`, Godox home page, Nikon `product_data.xml`, Canon lens `series=4` distinct from catalogue discovery 14/86.
- **Claims**: Examples are captured identifiers, not permanently latest versions or exhaustive supported inventories; no firmware/version cache or matching change.
- **Custom modules**: Declared guidance is author-provided, never verified official coverage merely because its name matches this table.
