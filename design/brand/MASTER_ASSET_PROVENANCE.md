# SENTINEL master artwork provenance

**Production design authority:** SENTINEL Design System v3.0  
**Design laboratory:** `spenskoj90-sudo/sentinel-aware-companion@60629603299fd8af035c6f05991482cde0363c33`

## Approved source

- Full-color 1024 px master: `src/assets/sentinel-master-icon.png`
- Source Git blob: `bc0fe93d932023798291c45602100f025341d884`
- Studio 512 px production derivative: `public/brand/icon-512.png`
- 512 px Git blob: `e4e4dad49fd9522605e1c1018d175f8ea0973fee`
- 192 px Git blob: `a1c8025f752dc2da3439779670170321a31805fa`
- 64 px Git blob: `fbc47c2736b688df645e7851a9a7395786b63d0f`
- favicon Git blob: `3c01d69713f9c184e92b74f5799e6dff2f500825`

The 512/192/64 raster assets and favicon in `alpha-0` are imported by exact Git object identity from the design-reference commit; they are not screenshots, redraws or generated approximations. The larger 1024 px source remains immutable provenance in the design repository and is not duplicated in production because the connector cannot transfer that object directly.

## Reduced glyph

`design/brand/sentinel-glyph.svg` and `sentinel-glyph-mono.svg` are exact studio reduced geometry from `public/brand/glyph*.svg`. Compact/system contexts use this reduced shield + S + signal DNA rather than attempting to flatten the material master.

## Production mapping

- Android system splash: byte-exact 512 px studio raster.
- Android adaptive/themed/notification contexts: reduced studio geometry calibrated for masks and monochrome constraints.
- Web favicon/PWA: byte-exact favicon + 192/512 raster derivatives.
- Companion package: byte-exact 512/64 raster derivatives + reduced SVG glyphs.
- Final optical acceptance at 16/20/24/32/48/64/192/512 px and target Android/Windows shells remains **ENVIRONMENT-UNVERIFIED** until physical inspection.
