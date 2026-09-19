# SENTINEL Platform Modernization — 2026 Q3

**Status:** ACTIVE ENGINEERING BASELINE  
**Evidence rule:** a version is accepted only after repository tests, security checks and the exact-SHA CI appropriate to that component succeed. A numerically newer release is not automatically accepted when the vendor compatibility matrix marks the combination unsupported or pre-release.

## Android platform baseline

The supported modernization target is:

| Layer | Baseline |
| --- | --- |
| Kotlin / KGP | 2.4.20 |
| Compose compiler plugin | 2.4.20 |
| Android Gradle Plugin | 9.3.1 |
| Gradle | 9.7.1 |
| Gradle/CI JDK | 25 LTS |
| Android Java/Kotlin bytecode target | JVM 17 |
| compileSdk | 37 |
| targetSdk | 36 |
| minSdk | 29 |
| Compose BOM | 2026.09.00 |
| AndroidX Core | 1.19.0 |
| Activity Compose | 1.13.0 |
| Navigation Compose | 2.10.1 |
| Credentials | 1.6.0 |
| Google ID | 1.2.1 |
| Play Integrity | 1.6.0 |
| kotlinx.coroutines Android | 1.11.0 |

AGP 9 built-in Kotlin is used. The legacy `org.jetbrains.kotlin.android` plugin is intentionally absent. KGP 2.4.20 is supplied on the build classpath so the built-in Kotlin compiler is inside Kotlin's documented AGP 9.3.1 compatibility range. Compose compiler stays version-aligned with Kotlin.

The build JDK and application bytecode level are deliberately separate. Gradle executes on JDK 25 LTS while Android output remains JVM 17 until an independently justified runtime-bytecode migration is accepted.

AGP 9.4 is newer but is not the baseline merely because of its version number. It is evaluated only after the fully supported AGP 9.3.1/Kotlin 2.4.20 baseline is green and only if the resulting toolchain has no unsupported compatibility state.

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
| Web | Next.js 16.3.5, React/React DOM 19.3.0, TypeScript 6.0.3, Vitest 5.0.1 |
| Web lint | ESLint 9.39.5 with eslint-config-next 16.3.5; ESLint 10 is intentionally excluded because the current Next plugin graph does not declare compatible peer support |
| Companion | Electron 44.4.2 on Node 24 LTS |
| Native Python runtime | 3.14.7 via `.python-version` |
| Core | FastAPI 0.141.1, Uvicorn 0.53.0, Pydantic 2.13.5, SQLAlchemy 2.0.54, psycopg 3.3.6, cryptography 50.0.1, websockets 17.1 |
| Core test tooling | pytest 9.1.1, pytest-cov 7.1.0, httpx2 2.13.0 |
| PostgreSQL repository baseline | 18 |
| Android observability/test refresh | Sentry Android 8.57.0, AndroidX Test ext.junit 1.3.0, runner 1.7.0, Espresso 3.7.0 |

Web and Core container bases are pinned by immutable SHA-256 digest. The Web lockfile is regenerated under Node 24.21.0 and is required to remain consistent with `package.json`.

The Windows Companion packaging path remains dependency-install independent: it downloads the exact official Electron 44.4.2 Win32 x64 archive and verifies SHA-256 `6aae435b6cd5c0eedf9fd38824bae4045ffdaecd029f0b8c8328bac3f5b71f03` before staging the application payload.

The managed Neon pre-release database was re-observed on 2026-09-19 as PostgreSQL 17.11 even though repository integration/recovery/reference evidence is on PostgreSQL 18. The same runtime already contains migration `014_account_mfa` with checksum `572183e9e60ded7c2847fd6b8ea614f1fd51dbcacec0d11cf7d0c00c47e3cf4b`, matching the repository migration exactly; all three MFA tables have RLS and FORCE RLS enabled with the expected service-role policies. This confirms schema parity for the current feature set, not PostgreSQL-major parity. A managed-database 17→18 migration remains a separate environment operation and must not be inferred from repository image changes.

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
