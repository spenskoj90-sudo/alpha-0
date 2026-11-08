# Shattered Pixel Dungeon 4.0.2 source-rule replay

Upstream commit: `57a4e06a4caf162446d1c28caa7983f0493fecf0`.
Official package: `com.shatteredpixel.shatteredpixeldungeon`; source versionCode
922 / versionName 4.0.2. Independently reread using GitHub at that exact source:

| Source | Git blob |
| --- | --- |
| build.gradle | 70d287fa2fc6e10f6eb7be79f94a422dd1587485 |
| PotionOfHealing.java | 7c685cc18ad411639d0a919a1e30ffc71486ca8d |
| Challenges.java | 59cea989c947fa2d408b9fc237d633e166bccc70 |
| Healing.java | 00cd8f2d859327c40c7bd6c701e22e7dfb0ce494 |

Source links are retained in the data-only test pack. No upstream code, artwork,
frames or raw OCR is redistributed. Reviewed rule prose and synthetic replay
signals are authored for these tests. Upstream source is GPL-3.0-or-later; these
mechanical rule facts do not authorize copying its game assets or code.

`PotionOfHealing.heal` branches on NO_HEALING=4: Pharmacophobia invokes Poison
instead of Healing. Thus low health alone never authorizes potion-specific advice.
The reviewed pack requires separately known challenge=false and known healing
inventory >=1 for an explained advisory option; challenge=true produces a poison
warning. Missing/unknown/wrong-type challenge or inventory never permits that option.
HP <=25% is a conservative reviewer policy, not evidence of optimal play.

`app/src/test/resources/knowledge/shattered-v4.0.2.json` is a **test-only** pack,
SHA256 `55ea5f25547af1bd119e2f6dbd002b73d2cb554b93e70b57838c4b3756a8f310`.
`status=validated` is the existing codec's schema field; it does not claim live
calibration, ground truth, distribution approval or owner acceptance. JVM replays
exercise the actual production KnowledgeCodec parser/evaluator, RU/EN explanations,
exact profile/digest, unknown signals and poison behavior. They are synthetic,
not the earlier inaccessible ZIP's tests and not real-game outcome evaluation.

The service-owned Android binding/observation closures remain null. MediaProjection
callbacks, installed package metadata, OCR pixels and user statements do not prove
the selected window's package, signer, version or exact source identity. No
supported service/OS/game attestor for that identity exists in this package.
Local consent-only observation is now source-enabled for signed_feed non-Play
release builds on Android 14+ (in addition to existing debug/diagnostic builds).
The Play release service remains disabled. Both the UI and service enforce the
same channel/OS policy and the signed_feed manifest enables only this non-exported
MediaProjection foreground service. The user still must acknowledge disclosure
and grant Android system capture consent; session, screen lock, sign-out, elapsed
five-minute limit and notification/in-app Stop retain their existing fail-closed
handling. HUD OCR and local counts remain **INFERENCE / UNVERIFIED**, not claims
of selected content identity; neither recognized text nor frames are persisted
or uploaded. Source compilation/CI cannot claim real device/consent/runtime
coverage. Trusted knowledge adapters remain null; no advice, game:write,
action authority or background capture is activated by this source change.
OFF/Advisory/Confirm/Bounded consent, permission, Stop, action-grade proof and
outcome gates remain independent and default-deny.

The service binding now requires exact package, certificate digest, versionName,
versionCode and upstream source SHA in addition to target profile/source/session.
These are immutable service-owned values; their type validation never grants trust.
No shipped producer creates them from installed metadata or OCR.

The consumer now additionally binds ordered frame ID/sequence and frame/OCR
monotonic timestamps. Future, stale, reordered, changed duplicate-frame and
inconsistent OCR records yield no advice. Stop/revoke/session changes retain cache
invalidation; visibility loss/resize also stop the knowledge consumer immediately.
None of these freshness checks can create source identity. Enabling a real adapter
still requires independently supportable exact target/package/signer/version/source/
session proof plus licensed real frames, calibration, reviewed challenge/inventory
recognition and actual outcome evaluation. Do not substitute synthetic fixture proof.

The presentation passes every non-null observation through the cache fence; a
foreign source cannot bypass invalidation and revive an older recommendation.
Before the first observation it reports a waiting state; loss after an accepted
observation latches the epoch unavailable until the session is cleared. These
are synthetic lifecycle guarantees, not proof of selected-game identity.

The Android observation screen displays a locally observed, fully preserved
installed-APK certificate SHA-256 in spaced groups when structurally valid,
otherwise UNKNOWN. This is diagnostic provenance for a future independent
publisher/channel check, **not** proof of game publisher, selected projection
window, exact runtime source, trusted profile or permission for advice/actions.

The user-initiated local binary-evidence check on Android 14+ does not contact
GitHub at runtime and does not upload APK contents. Its fixed reference is the
upstream 2026-10-07 v4.0.2 release at
`https://github.com/00-Evan/shattered-pixel-dungeon/releases/tag/v4.0.2`:

- `ShatteredPD-v4.0.2-Android.apk`: 30,275,058 bytes, SHA-256
  `ceef4cdd4beddcb3d85379ac004cb4ab5d918b89dc7366b4ce9c4a3585a5e78e`;
- `ShatteredPD-v4.0.2-GPlay.apk`: 31,318,705 bytes, SHA-256
  `b7be54496503b613e241a7b67021fb6ed152ccf93f28c131a6af25daa3c30483`.

The checker reads only the installed base APK (versionName 4.0.2, versionCode
922) through PackageManager's publicly readable source path, caps input at
32 MiB, hashes with SHA-256 in cancellable 64-KiB chunks, and rechecks local
package version/certificate/source path before reporting. It cancels on screen
Stop and returns NOT_CHECKED/UNAVAILABLE/OTHER_OR_SPLIT as appropriate. Split
APK installations, inaccessible files and other legitimate distribution
channels may not match those specific whole APK assets and are **not** labelled
malicious. A binary match supports only observed base-APK file identity against
GitHub-published digest metadata; it does **not** attest upstream publisher
certificate custody, the selected MediaProjection window, live game frames,
calibration, knowledge authority, entitlement or any action. On-device success,
latency, resource use and official-signature custody remain NOT_RUN until actual
installed APK/device evidence exists. No original game binary or artwork is
redistributed.


## Manual offline healing-rule reference (source-only until Android validation)

The Android game-observation screen exposes a **separate user-entered, hypothetical**
healing-potion reference for the installed Shattered 4.0.2 / build 922 profile.
The reference evaluates three explicit tri-state answers (UNKNOWN / YES / NO):
health at or below 25%, Pharmacophobia challenge, and a known Potion of Healing
in inventory. Defaults are UNKNOWN. The exact source branch at upstream commit
`57a4e06a4caf162446d1c28caa7983f0493fecf0`,
`PotionOfHealing.java` blob `7c685cc18ad411639d0a919a1e30ffc71486ca8d`,
switches to Poison when NO_HEALING is active. Without that challenge, an actual
known potion and low self-reported health permit only a conditional *possible*
option. This 25% threshold is a conservative local reference, not a claim of
gameplay optimality. Other/unknown conditions never produce potion advice.

This view **does not consume OCR, verified knowledge binding, projection frames,
credentials, AI-generated live state or remote network calls**. It retains no
persistent history, resets manual answers across installed-game and capture state
transitions, and hides entry while capture is active. It cannot issue game input,
grant execution authority, bypass permission, or assert the observed window's
identity. The public upstream source's game-mechanic facts are described in
original prose; no game assets/code are copied. JVM tests exercise all 27
tri-state combinations and unsupported-version guards; Compose instrumentation
covers warning/option/unknown, reset and wrong-version UI. This is SOURCE/CI
coverage only until target-device visibility, 200% font scale and owner UX
acceptance are actually checked.

The local APK inspection and capture operations now share an additional
lifecycle fence. Beginning Android system capture consent cancels and clears
any in-flight binary hash and its provisional UI result; a pending consent
or active capture hides the APK inspection action. The runtime callback also
checks the latest process-local capture status before starting a hash, not only
the previously composed button's enabled state. Negative UI tests cover
pending/active disabled states, and a source-contract regression asserts
hash cancellation precedes the system capture intent. The check still cannot
attest the projected game's identity or authorize actions.

## Manual Burning / water reference (offline source facts, not gameplay authority)

At official upstream Shattered 4.0.2 commit `57a4e06a4caf162446d1c28caa7983f0493fecf0`,
`Burning.java` blob `7533b54985c39f80fdd13b2f20fa6c1df0566eb1`,
`act()` detaches Burning in water only when the character is not flying
(lines 99–101, 178–182). A first Burning tick may still deal damage before
detachment; this is NOT a damage-free rule.

The collapsed-by-default Android reference collects four manual YES/NO/UNKNOWN
facts: Burning active, flying, already in water, and a reachable water route
with no known hazards. Unsupported version/build, unknown relevant facts, and
unknown route safety cannot produce a moving suggestion. Flying produces an
explicit exception; water while grounded only a cautious mechanistic note;
a user-reported safe route produces a *conditional possible option* and a
warning to check current threats. Nothing is extracted from OCR, persisted,
uploaded or authorized for game input. Manual answers reset on installed-game/
capture changes and are hidden during capture. Shared accessible choice chips
announce the question context. Kotlin JUnit covers 81 tri-state combinations
and three unsupported version cases (324 assertions); Compose tests cover
unknown/conditional/flying/water/reset and capture pause. Source/CI tests are
not real player evidence, selected-window identity, measured safety, owner
visual acceptance or action permissions.

## Universal offline manual reference route without capture escalation

The Games card now independently exposes `game-reference` for authenticated
Android users on **all distribution channels**, including Play and Android
below API34; no game-entitlement flag or MediaProjection capability is needed
to view manually entered source-review rules. The separate existing
`game-observer` path is *still* exposed only when
`ObservationCapturePolicy.supports(DEBUG, channel, SDK)`, with the unchanged
service/manifest/OS permission/consent/Stop boundaries. The new reference
screen performs only local PackageManager installed-version lookup on resume,
renders reused Healing/Burning hypothetical cards, never calls capture,
network, OCR, privileged operations or game input, and shows UNKNOWN when the
matching game version is unavailable. Safe local reference is not a claim of
gameplay authority or a reason to waive user acceptance. RU/EN navigation
labels are now explicit about the two routes. Android instrumentation tests
check absence of capture controls and manually available reference; product
shell contract checks route separation and service guards. The existing APK
check touch regression now asserts enabled/displayed and reports the exact
callback count to better diagnose the **one observed API34 test flake**;
no semantic click fallback or retry is inserted to manufacture a PASS.
