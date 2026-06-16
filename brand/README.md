# Brand icon

The icon shown on Home Assistant's *Devices & Services* page is **not** loaded from this
repository — Home Assistant fetches it from the central
[home-assistant/brands](https://github.com/home-assistant/brands) repo by domain
(`dienstplan_import`). Until an icon is published there, HA shows "icon not available".

`icon.svg` here is the source artwork. To publish it:

1. Convert `icon.svg` to PNG with a transparent background:
   - `icon.png` — **256×256**
   - `icon@2x.png` — **512×512**
   (e.g. with Inkscape: `inkscape icon.svg -w 512 -h 512 -o icon@2x.png`, and `-w 256 -h 256`
   for `icon.png`; or any SVG→PNG converter.)
2. Fork [home-assistant/brands](https://github.com/home-assistant/brands) and add the files at:
   ```
   custom_integrations/dienstplan_import/icon.png
   custom_integrations/dienstplan_import/icon@2x.png
   ```
   (Optionally a wider `logo.png` / `logo@2x.png`.)
3. Open a pull request. Once merged, restart Home Assistant — the icon appears
   automatically (no integration change needed).

See the brands repo README for the exact size/trim rules.
