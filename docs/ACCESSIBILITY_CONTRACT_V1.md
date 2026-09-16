# SENTINEL Accessibility Contract v1

Status: repository-internal baseline contract for implemented Android, Web and packaged Companion surfaces.

## Purpose

SENTINEL accessibility behavior must be part of the executable product contract rather than an untested design convention. This document defines the minimum repository-level guarantees that can be validated without claiming physical assistive-technology acceptance.

The contract is intentionally compatible with the existing visual language and the canonical Figma foundations file. Figma is a visual anchor, not runtime evidence; repository code/tests remain authoritative for implemented semantics.

## General invariants

Interactive behavior must remain available through semantic native controls or explicit platform semantics. Keyboard/switch/screen-reader users must not depend on color, shape, animation or pointer-only behavior to identify an operation or runtime state.

Dynamic status updates use non-interrupting announcements by default. Errors that require immediate user awareness use assertive/error semantics. Bounded asynchronous account operations expose a busy state on the owning surface so assistive technology does not have to infer progress only from disabled controls. Accessibility metadata must not expose Core tokens, refresh tokens, peer identity, private realm identifiers, microphone payloads, transcripts or other secrets.

Accessibility changes must not weaken the existing authorization, consent, entitlement, kill-switch, recommendation or action-gateway boundaries.

## Android Compose

The shared `AccessibilitySemantics.kt` boundary provides reusable semantics for:

- polite live status updates;
- assertive error updates;
- progress announcements with a bounded human-readable description;
- interactive card surfaces with explicit `Role.Button` and an action description.

The current authentication flow announces validation/authentication failures assertively and provides a progress description while sign-in or account creation is running.

The dashboard announces loading progress, announces load failures assertively and gives device/game cards explicit button semantics rather than relying only on card shape and click handling.

`AccessibilitySemanticsTest` exercises the actual Compose semantics tree in Android instrumentation CI.

## Web control plane

The primary Web surface provides:

- a keyboard-visible skip link targeting a focusable main landmark;
- an explicit page `h1` and bounded heading hierarchy for major runtime sections;
- high-visibility `:focus-visible` treatment for keyboard navigation;
- a forced-colors fallback that preserves focus and control boundaries;
- decorative status dots hidden from assistive technology when the adjacent text already carries the meaning;
- live recommendation loading/result announcements;
- assertive recommendation-error announcements;
- `aria-busy` while live recommendation or account operations are pending;
- an accessible textual confidence label;
- a programmatic password-requirement relationship on the sign-in/register form;
- plan-specific accessible names for repeated checkout/free-activation buttons;
- status-vs-alert announcement tone for account operation outcomes.

Existing native forms/labels/buttons remain the preferred Web interaction boundary. No custom role may replace a native control where a native element already exists.

The Vitest source-contract test prevents removal of these structural guarantees during refactoring. Routine Web lint/build continues to validate the rendered source path.

## Packaged Companion launcher

The Electron launcher provides:

- document language and viewport metadata;
- a skip link and focusable main landmark;
- visible keyboard focus including a forced-colors fallback;
- native labeled form controls and buttons;
- polite atomic live regions for account, Companion, WoW checkpoint, voice provider and voice-result state;
- an account-operation `aria-busy` boundary for sign-in/sign-out work;
- a bounded accessibility runtime layer that upgrades `.err` runtime states to assertive alert semantics and restores ordinary states to polite status semantics.

These announcements are presentation-only. They do not grant permissions, start the Companion, enable microphone capture, authorize voice behavior or execute game actions.

Launcher Node regression tests validate both static markup and the accessibility runtime contract. The Windows packaging allowlist includes `accessibility-runtime.js`, so the same semantics participate in packaged reproducibility and runtime smoke evidence instead of existing only in source checkout.

## Figma relationship

The connected canonical Figma file currently exposes the `00 Foundations` page only. Exact known foundation node IDs are recorded in `design/sentinel-design-system.v1.json`. Reusable runtime components are explicitly marked `UNAUTHORED` in Figma until concrete component nodes exist; repository code/tests do not fabricate a visual-completion claim.

This distinction is deliberate: accessibility acceptance for implemented controls is not blocked by an absent mockup page, while design-system documentation is prevented from claiming Figma inventory that cannot be inspected.

## Evidence levels and non-claims

Repository tests prove the declared semantic structure and Android Compose semantics on the GitHub emulator. They do **not** establish:

- certification against a particular accessibility standard;
- physical TalkBack, VoiceOver, NVDA, JAWS or switch-device acceptance;
- target-PC high-contrast behavior beyond the deterministic CSS contract;
- final visual/component completeness in Figma;
- release-candidate physical-device acceptance.

Those claims require the corresponding real assistive-technology/device environment and remain environment evidence rather than CI assertions.

## Change rule

A UI change that removes or materially alters a control, status surface, runtime announcement or keyboard path must preserve these guarantees or update this contract and its tests in the same PR. Security and authorization controls must never be weakened to satisfy accessibility behavior.
