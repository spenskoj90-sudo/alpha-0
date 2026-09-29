# SENTINEL delivery roadmap

- [x] Study the approved icon, brief, and current repository.
- [x] Establish visual foundations, refined icon, compact glyph, themes, and reusable interaction controls.
- [x] Voice UX and Admin console surfaces added.
- [x] Access (auth/MFA/recovery), Billing (plans & lifecycle), and Resilience (offline→restored) flows added.
- [x] Build a responsive interactive product prototype across Web, Android, Companion, Overlay, and design-system views (10 surfaces).
- [x] Document cross-platform tokens, component/status grammar, inventory, UX flows, and implementation handoff (docs/SENTINEL-FOUNDATIONS.md).
- [x] Verify desktop/mobile rendering, light theme, and core interactions; package reusable brand assets (public/brand/, favicon, manifest, master icon).

## External dependencies (blocked, not deliverable from this repo)
- Native Android (Compose), Windows Companion, and Figma production files require their respective source projects or an active desktop Figma connection; this repository is a fresh web template, not the named existing product repository.
- glyph.svg / glyph-mono.svg are implementation studies; they need an optical sign-off against the approved master icon before store submission.
- App Store / Google Play / Windows ICO / system-tray assets must be exported from an approved optical vector master in native packaging.
