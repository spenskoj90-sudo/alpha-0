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
Production capture stays DEBUG-gated; no mechanistic DEBUG replacement or action
authority is introduced. OFF/Advisory/Confirm/Bounded consent, permission, Stop,
action-grade proof and outcome gates remain independent and default-deny.

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
