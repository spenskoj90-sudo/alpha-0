# Asset provenance and export contract

All brand/icon/illustration SVG geometry in this directory was authored specifically
for this SENTINEL study by GPT during the Owner-authorized 2026-10-24 H pass.
No stock art, game screenshots, Blizzard logos, external character art or previous
Lovable iteration was imported. Game titles identify compatibility contexts only.
These are unselected design candidates under the repository's existing LICENSE.
No trademark-clearance or legal acceptance is claimed.

- Brand source: `brands.json` and `assets/brand/*.svg`, 32-unit construction.
- Domain icon source: `icons.json`, 24 units, 1.65 stroke, round joins and caps.
- Illustrations: `assets/illustrations/*.svg`, editable 960×720 vector diagrams.
  Labels state DEMO / UNVERIFIED / EXECUTION DISABLED. No chart is live data.
- PNG icon exports: Chromium SVG rendering on a neutral background, 16/20/24/32/48/
  72/108/192/512px. Windows ICO and favicon are containers generated from the same
  candidate render using Pillow; they are not approved shipping assets.
- Android candidate foreground: 108 viewport, 2.25 scale with 18-unit translation;
  main geometry stays within the adaptive icon safe region. Foreground/background,
  monochrome and notification sources need Android build/device mask acceptance.
  Android 13 monochrome entry requires the appropriate resource qualifier when adopted.
- Desktop installer/tray and PWA platform-specific packages/compositions are pending;
  reusing an exported PNG/ICO does not prove those platform integrations.

Fonts are redistributed under their included SIL Open Font License texts in
`assets/fonts/`. Source: the named @fontsource packages, versions recorded in
`assets/fonts/sources.json`; only normal Latin/Cyrillic subsets used by the preview
are bundled. Onest 600/700, Inter 400/600, JetBrains Mono 400. No remote font service.

Editable Figma is a parallel design source; exact node IDs and authoring outputs
are stored under `figma/`. The preview is not a pixel-perfect automatic Figma export.
Further convergence and platform-specific art direction are explicitly required.
