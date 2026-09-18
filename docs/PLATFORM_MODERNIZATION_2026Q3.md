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

## Runtime modernization frontier

The whole repository is audited, not only Android. The active audit includes:

- Node.js / Next.js / React / TypeScript / ESLint / Vitest;
- Python / FastAPI / Uvicorn / Pydantic / SQLAlchemy / psycopg / cryptography / pytest;
- PostgreSQL;
- Docker base images and their immutable provenance;
- GitHub Actions and security scanners;
- AndroidX, Google Play SDKs, Sentry and Kotlin ecosystem libraries.

The intended runtime direction is stable LTS/current-supported software, not pre-release software:

- Node 24 LTS is the candidate Web/launcher runtime baseline.
- Python 3.14 is the candidate Core runtime baseline only after dependency-wheel compatibility and an exact pinned official container image are validated.
- PostgreSQL 18 is the active database test/runtime baseline.
- Pre-release PostgreSQL 19 and other RC/beta dependencies are excluded from the normal baseline.

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
