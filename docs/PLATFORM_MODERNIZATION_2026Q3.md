# SENTINEL Platform Modernization — 2026 Q3

**Status:** ACTIVE ENGINEERING BASELINE  
**Evidence rule:** a version is accepted only after repository tests, security checks and the exact-SHA CI appropriate to that component succeed. A numerically newer release is not automatically accepted when the vendor compatibility matrix marks the combination unsupported or pre-release.

## Android platform baseline

The supported modernization target is:

| Layer | Baseline |
| --- | --- |
| Kotlin / KGP | 2.4.20 |
| Compose compiler plugin | 2.4.20 |
| Android Gradle Plugin | 9.4.1 |
| Gradle | 9.7.1 |
| Gradle/CI JDK | 25 LTS |
| Android Java/Kotlin bytecode target | JVM 17 |
| compileSdk | 37 |
| targetSdk | 36 |
| minSdk | 29 |
| Compose BOM | 2026.09.00 |
| AndroidX Core | 1.19.1 |
| Lifecycle Runtime Compose | 2.11.0 |
| Activity Compose | 1.13.0 |
| Navigation Compose | 2.10.2 |
| Credentials | 1.6.0 |
| Google ID | 1.2.1 |
| Play Integrity | 1.6.0 |
| kotlinx.coroutines Android | 1.11.0 |

AGP 9 built-in Kotlin is used. The legacy `org.jetbrains.kotlin.android` plugin is intentionally absent. KGP 2.4.20 is supplied on the build classpath to keep the built-in Kotlin compiler explicitly pinned and Compose compiler version-aligned with Kotlin. Compose compiler stays version-aligned with Kotlin.

The build JDK and application bytecode level are deliberately separate. Gradle executes on JDK 25 LTS while Android output remains JVM 17 until an independently justified runtime-bytecode migration is accepted.

AGP 9.4.1 is accepted as the baseline because the supported AGP 9.4/Kotlin 2.4.20/Gradle 9.7.1 combination is validated by exact-SHA CI, not merely because 9.4.1 is numerically newer. Preview AGP lines remain excluded until separately justified and validated.

## Android API policy

Google Play requires current app updates to target API 36 or later. SENTINEL therefore targets API 36 and compiles against API 37. Moving targetSdk beyond 36 is a separate behavior-change acceptance decision, not a mechanical dependency refresh.

## PostgreSQL baseline

Repository development, integration, migration, backup/restore and deployment-smoke evidence use PostgreSQL 18. PostgreSQL 19 is pre-release and is not an accepted production baseline.

Production-database migration remains an Owner/environment deployment gate. Updating CI/local images does not itself migrate a production database.

## Accepted runtime baseline

The repository-wide modernization pass uses stable supported software and immutable provenance:

| Surface | Accepted baseline |
| --- | --- |
| Native Node runtime | 24.21.0 LTS via `.node-version` |
| Web | Next.js 16.3.8, React/React DOM 19.3.0, TypeScript 6.0.3, Vitest 5.0.2 |
| Web lint | ESLint 9.39.5 with eslint-config-next 16.3.8; ESLint 10 is intentionally excluded because the current Next plugin graph does not declare compatible peer support |
| Companion | Electron 44.4.5 on Node 24 LTS |
| Native Python runtime | 3.14.7 via `.python-version` |
| Core | FastAPI 0.141.1, Uvicorn 0.53.0, Pydantic 2.13.5, SQLAlchemy 2.0.54, psycopg 3.3.6, cryptography 50.0.1, websockets 17.1 |
| Core test tooling | pytest 9.1.1, pytest-cov 7.1.0, httpx2 2.13.1 |
| PostgreSQL repository baseline | 18 |
| Android observability/test refresh | Sentry Android 8.58.0, AndroidX Test ext.junit 1.3.0, runner 1.7.0, Espresso 3.7.0 |

Web and Core container bases are pinned by immutable SHA-256 digest. The Web lockfile is regenerated under Node 24.21.0 and is required to remain consistent with `package.json`.

The Windows Companion packaging path remains dependency-install independent: it downloads the exact official Electron 44.4.5 Win32 x64 archive and verifies SHA-256 `11c395820a5aaa8ebcc0686b476d0ac98a730274ebfbdc8cf5538a7c2815cb5d` before staging the application payload.

The connected Neon pre-release source was re-observed on 2026-09-19 as PostgreSQL 17.11 even though repository integration/recovery/reference evidence is on PostgreSQL 18. The source contains migration `014_account_mfa` with checksum `572183e9e60ded7c2847fd6b8ea614f1fd51dbcacec0d11cf7d0c00c47e3cf4b`, matching the repository migration exactly; all three MFA tables have RLS and FORCE RLS enabled with the expected service-role policies.

A read-only 17→18 compatibility assessment against the source found only the built-in `plpgsql` and `pgcrypto` extensions, no custom collations, no event triggers, no prepared transactions, no function/expression indexes, no `PUBLIC CREATE` privilege on schema `public`, and no public tables without a primary key. These findings remove several common migration blockers but are not cutover evidence.

On 2026-09-21 the pre-release strategy was simplified to a clean PostgreSQL 18 reset rather than preserving the small historical PG17 application dataset. Render Core was switched to the prepared PostgreSQL 18.6 project/database and the resulting deployment reached `live` with application startup completing successfully. The PG18 project is now named `sentinel-pre-release`; its 15 repository migrations and 39/39 FORCE-RLS application-table baseline are retained. Historical PG17 identities/users/devices/sessions are intentionally not part of the new pre-release baseline. The former PostgreSQL 17.11 project remains intact as `sentinel-pre-release-pg17-rollback` for rollback/evidence and is not an active runtime.

GitHub Actions used by the active workflows are pinned to immutable commit SHAs. The modernization pass moved checkout/setup/runtime, Gradle, Docker, CodeQL, OSV, artifact and emulator actions to their audited stable release lines while retaining existing security gates.

## Supply-chain rule

Version upgrades must preserve or improve the existing SENTINEL supply-chain controls:

- immutable GitHub Action SHAs;
- Gradle distribution checksum verification;
- deterministic npm lockfiles;
- pinned container images where the canonical build requires them;
- SCA, CodeQL, Trivy and OSV gates;
- reproducibility comparisons;
- exact-SHA release evidence.

A dependency update is incomplete until its lockfile, checksum, image digest or equivalent provenance record is updated and CI verifies it.

## Acceptance sequence

1. Establish supported Android/Gradle/JDK and PostgreSQL baseline.
2. Run exact-SHA routine CI and fix every incompatibility without weakening gates.
3. Modernize Node/Web/launcher with deterministic lockfile updates.
4. Modernize Python/Core and its pinned runtime image after wheel/image provenance validation.
5. Audit remaining actions, scanners, container images and libraries.
6. Run the full exact-SHA evidence suite.
7. Merge only when all required checks pass on the exact PR HEAD SHA.
8. Verify staging runtime from the resulting protected-main merge.
9. Physical-device, production credentials, signing, publication and live deployment remain their existing Owner/environment gates.


## Final upstream recheck — 2026-09-25

A second upstream check was performed immediately before the final RC consolidation pass. The rule remains: newer is accepted only when it improves the release candidate without introducing an unproven compatibility migration.

### Confirmed current/stable baselines

- Node 24.21.0 remains the selected LTS runtime line.
- Python 3.14.7 remains the current Python 3.14 maintenance release used by the repository.
- Kotlin 2.4.20 remains the latest supported 2.4 release.
- Gradle 9.7.1 remains the recommended stable 9.7 patch; 9.8 is still milestone/pre-release.
- Android Gradle Plugin 9.4.1 remains the current stable AGP release.
- AndroidX Core 1.19.1, Lifecycle 2.11.0 and Activity 1.13.0 remain the current stable lines used by SENTINEL.
- AndroidX Navigation 2.10.2 supersedes 2.10.1 and is accepted in this pass as a patch-level stable update.
- PostgreSQL 18.6 remains the current PG18 maintenance baseline; PostgreSQL 19 is still beta and is not an RC target.
- FastAPI 0.141.1, Uvicorn 0.53.0, Pydantic 2.13.5, psycopg 3.3.6, cryptography 50.0.1 and websockets 17.1 remain current for their selected release lines.
- httpx2 2.13.1 supersedes 2.13.0 and is accepted as a test-only patch update.
- React 19.3.0 and Vitest 5.0.1 remain current.
- Next.js 16.3.6 remains the current Active LTS security release as of this check.

### Deliberate compatibility holds

- **Historical Next.js announcement:** the planned version in the 2026-09-25 note was superseded by the actual September 30 security release, 16.3.8. The October 1 reconciliation below is current.
- **TypeScript 7.0.2:** latest major exists, but SENTINEL stays on validated TypeScript 6.0.3 for this RC. A TypeScript 7 move requires a dedicated compatibility migration proving Next, eslint-config-next, ESLint, Vitest, declarations, build and CI together; a major compiler transition is not folded into the final RC without that evidence.
- **SQLAlchemy 2.1.0:** released 2026-09-24, one day before this recheck. SENTINEL retains 2.0.54 for the RC because the new minor ORM line requires deliberate migration validation across FORCE-RLS transaction handling, migrations, worker leasing and PostgreSQL recovery behavior. This is a compatibility hold, not a claim that 2.0.54 is numerically latest.
- **ESLint 10:** remains outside the validated Next toolchain for this RC; ESLint 9.39.5 is retained.
- **setuptools:** 80.9.0 remains intentionally pinned after prior compatibility review; do not jump release-build tooling solely for version freshness.

Any one of these holds may be reopened after the exact RC physical/environment gates without weakening existing security or provenance checks.

## Coordinated Web tooling update — 2026-10-01

Vitest and its V8 coverage provider move together to 5.0.2 in both Web and Public Site. Separate Dependabot updates had violated the exact Vitest peer dependency and the shared tooling contract. The regenerated lockfiles, unchanged coverage thresholds, and coordinated dependency group preserve deterministic validation. Dependabot now monitors both `/web` and `/site` under the same npm update entry.

## Release-readiness dependency reconciliation — 2026-10-01

- **Next.js / eslint-config-next 16.3.8:** accepted atomically in Web and Public Site. The actual [September 30 security release](https://nextjs.org/blog/september-2026-security-release) supersedes the earlier planned-version note and fixes seven disclosed vulnerabilities. Deterministic lockfiles and repository version gates move together. Current App Router/Turbopack/static-export configuration limits several advisory paths, but that is not a reason to retain the older framework. Future Next tooling updates are coupled across both surfaces.
- **Sentry Android 8.58.0:** accepted for the manifest-version-detection resource-handle fix. Existing `sendDefaultPii(false)`, privacy scrubbing and fail-closed deployment identity remain unchanged. Do not partially configure the new `dataCollection` API: opting in changes defaults for unspecified fields. [Upstream release](https://github.com/getsentry/sentry-java/releases/tag/8.58.0).
- **setup-gradle 6.4.0:** all seven workflow invocations use immutable `3f5f9adaf7d9fecd50b5935e54106014257a94e6`, verified against the signed release tag. Gradle runtime and checksum/bootstrap validation remain unchanged. [Upstream release](https://github.com/gradle/actions/releases/tag/v6.4.0).
- **Node declarations 26 / PR #405:** rejected; Node runtime remains 24.21.0, with 24.x declarations and matching Web/Public Site tooling. A new declaration major can admit APIs absent from the selected runtime. Dependabot excludes >=25 until a deliberate runtime migration.
- **Gradle 9.8 / PR #406:** rejected for this candidate. Current PR replaces the verified bootstrap with a script invoking an absent wrapper JAR. Java 27/mirror additions have no demonstrated benefit for JDK 25. Retain 9.7.1 and its checked distribution digest; exclude >=9.8 pending a deliberate validated toolchain migration.
- **SQLAlchemy 2.1.1 / PR #400:** retains the 2.0.54 RC hold. The 2.1 migration changes autoflush for all `Session.execute` calls, including Core/text statements; FORCE-RLS transaction sequencing/recovery requires deliberate compatibility validation. 2.1.1's packaging fix does not remove that migration. [Migration guide](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html).
- **Uvicorn 0.54 / PR #401:** retains 0.53.0. New trailers/Early Hints apply to opt-in experimental zttp HTTP/2; Core does not enable that path. No current release benefit. [Release notes](https://uvicorn.dev/release-notes/).

Dependency exclusions are explicit RC compatibility decisions, not claims that retained versions are numerically latest. Revisit Gradle/SQLAlchemy/Uvicorn after the exact physical candidate is accepted; security fixes on retained lines remain actionable. Superseded #402/#403 are covered by merged #420. #419/#404 are reconciled by this coherent security/compatibility pass, rather than independent uncoordinated merges.
