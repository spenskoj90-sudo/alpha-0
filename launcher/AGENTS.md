# Companion / Overlay / Voice scoped agent instructions

Scope: launcher/.

- Follow root AGENTS.md.
- Preserve main-process token authority, bounded worker/socket lifecycle, kill switch, and explicit microphone consent.
- Overlay remains presentation-only unless an approved architecture decision changes that boundary.
- Node contract is 24.x.
- Default validation: npm test; run packaging/smoke workflow when package/runtime behavior changes.
- CI packaging is not physical Windows-host acceptance.
- Voice network/provider and real microphone/acoustic behavior remain environment evidence until exercised.
