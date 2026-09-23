# Platform and dependency audit — 2026-09-23

**Status:** ACTIVE AUDIT RECORD  
**Evidence model:** repository pins + official upstream release sources + exact-SHA CI vulnerability scans.

This audit prefers stable releases and security/reproducibility over version churn. Alpha/beta/RC releases are not adopted merely because their version number is newer.

## Android / JVM

| Component | Repository pin | Upstream status on 2026-09-23 | Decision |
| --- | --- | --- | --- |
| Android Gradle Plugin | 9.4.1 | current stable 9.4 patch; supports API 37 and requires Gradle >=9.6 | UPDATE 9.4.0 → 9.4.1 |
| Gradle wrapper | 9.7.1 + distribution SHA-256 | current 9.7 patch; upstream recommends 9.7.1 over 9.7.0 | KEEP |
| Kotlin / Compose plugin | 2.4.20 | latest supported 2.4 release | KEEP |
| Compose BOM | 2026.09.00 | official Android guidance names 2026.09.00 as latest stable BOM | KEEP |
| AndroidX Core | 1.19.0 | current stable | KEEP |
| Activity Compose | 1.13.0 | current stable; 1.14 is alpha | KEEP |
| Navigation | 2.10.1 | current stable | KEEP |
| Credentials | 1.6.0 | current stable; 1.7 is alpha | KEEP |
| Play Integrity | 1.6.0 | current documented stable | KEEP |
| kotlinx.coroutines | 1.11.0 | current stable release | KEEP |

AGP 9.4.1 is the current stable 9.4 patch and remains compatible with the existing Gradle 9.7.1/JDK 17 baseline. SENTINEL keeps Java/Kotlin JVM target 17 rather than changing toolchain solely for novelty.

Official references:
- https://developer.android.com/reference/tools/gradle-api
- https://developer.android.com/studio/releases/fixed-bugs/studio/2026.1.4
- https://docs.gradle.org/9.7.1/release-notes.html
- https://kotlinlang.org/docs/whatsnew2420.html
- https://developer.android.com/develop/ui/compose/bom
- https://developer.android.com/jetpack/androidx/releases/core
- https://developer.android.com/jetpack/androidx/releases/activity
- https://developer.android.com/jetpack/androidx/releases/navigation
- https://developer.android.com/jetpack/androidx/releases/credentials
- https://developer.android.com/google/play/integrity/reference/com/google/android/play/core/release-notes
- https://github.com/Kotlin/kotlinx.coroutines/releases

## Web

| Component | Repository pin | Upstream status | Decision |
| --- | --- | --- | --- |
| Node | 24.21.0 | current Node 24 Krypton line | KEEP |
| Next.js | 16.3.6 | latest stable listed; includes security fix for GHSA-vcvr-r3jv-pc5j | KEEP — security-sensitive |
| React / React DOM | 19.3.0 | current stable React 19.3 | KEEP |
| TypeScript | 6.0.3 | stable repository pin; validated by Web build/lint/test | KEEP |
| ESLint | 9.39.5 | stable repository pin; validated by Web lint | KEEP |
| Vitest | 5.0.1 | stable repository pin; validated by Web tests | KEEP |

Official references:
- https://nodejs.org/en/download/archive/v24.21.0
- https://github.com/vercel/next.js/releases
- https://react.dev/blog/2026/09/09/react-19-3

The Web lockfile remains authoritative for the transitive graph. CI installs with `npm ci --ignore-scripts --no-audit`, then performs a separate `npm audit --audit-level=high` plus repository-wide OSV scanning. No unsafe auto-fix or dependency lifecycle script is introduced.

## Core / Python

| Component | Repository pin | Upstream status | Decision |
| --- | --- | --- | --- |
| Python | 3.14.7 | current 3.14 maintenance release | KEEP |
| FastAPI | 0.141.1 | current official release-notes head | KEEP |
| Uvicorn | 0.53.0 | current stable release | KEEP |
| websockets | 17.1 | current stable release | KEEP |
| Pydantic | 2.13.5 | stable pinned line; CI compatibility validated | KEEP |
| SQLAlchemy | 2.0.54 | current stable 2.0 release; 2.1 is pre-release | KEEP |
| psycopg | 3.3.6 | current stable | KEEP |
| cryptography | 50.0.1 | current stable, PyPI provenance available | KEEP |
| pytest | 9.1.1 | current stable | KEEP |
| pytest-cov | 7.1.0 | current stable | KEEP |
| setuptools | 80.9.0 | 84.0.0 is stable but crosses pkg_resources/distutils removals in intervening majors | KEEP — deliberate compatibility hold |

Official/package-index references:
- https://www.python.org/downloads/release/python-3147/
- https://fastapi.tiangolo.com/release-notes/
- https://pypi.org/project/uvicorn/0.53.0/
- https://pypi.org/project/websockets/
- https://pypi.org/project/SQLAlchemy/2.0.54/
- https://pypi.org/project/psycopg/3.3.6/
- https://pypi.org/project/cryptography/
- https://pypi.org/project/pytest/
- https://pypi.org/project/pytest-cov/

Core transitive packages are audited by `pip-audit` and OSV on the exact checked-out SHA.

## Companion

| Component | Repository pin | Upstream status | Decision |
| --- | --- | --- | --- |
| Node | 24.x / CI 24.21.0 | current LTS line used by Electron 44.4.3 | KEEP |
| Electron | 44.4.3 | current stable 44 line release on 2026-09-18 | KEEP |
| Windows runtime archive | exact SHA-256 `790a355b684d5c7cc8dc3cdd8c4cca7c4b2d054685427c7554a956879a82e70b` | package workflow verifies downloaded official archive before extraction | KEEP |

Reference: https://releases.electronjs.org/release?channel=stable

## PostgreSQL

PostgreSQL 18.6 is the current 18.x patch release (2026-08-13). Upstream reports security and bug fixes and notes that 18.5 was never released. SENTINEL now pins:

`postgres:18.6-alpine@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873`

The same exact image identity is used by Compose/CI/recovery paths where the workflow references PostgreSQL. This removes floating `18-alpine` drift without changing the major database contract.

References:
- https://www.postgresql.org/docs/release/18.6/
- https://www.postgresql.org/about/news/postgresql-186-1711-1615-1519-1424-and-19-beta-3-released-3365/

## CI / supply chain

GitHub Actions remain pinned to immutable commit SHAs. CodeQL Action is updated from 4.38.0 to 4.38.1 (`1c5b675653bb5c22dbe9b12b556ec555138e09fd`) after the official 2026-09-18 patch release. Security workflow includes CodeQL, pip-audit, npm audit, OSV and Trivy. Supply-chain workflows preserve SBOM/provenance/digest/reproducibility evidence. Dependency automation is restored through `.github/dependabot.yml` for GitHub Actions, Web npm, Companion npm, Gradle and server pip, with **no automatic merge**.

## Dependency-automation findings after restoration

The first Dependabot scan surfaced additional candidates after the consolidated v3 merge. This pass adopts only stable, directly justified changes:

- AGP 9.4.1: adopted as the current official stable patch.
- CodeQL Action 4.38.1: adopted for both init/analyze using the exact immutable release commit.
- `org.json:json` test dependency: moved from 20250517 to the official 20260719 release, which includes the upstream CVE-2026-59171 fixes. It remains test-only.

The following are intentionally not adopted in this pass:

- TypeScript 7.x and ESLint 10.x: major toolchain transitions, not patch maintenance.
- `@types/node` 26.x: does not match SENTINEL's Node 24 runtime baseline.
- setuptools 84.x: stable, but intervening major versions remove/deprecate legacy behaviors; no current build/security failure justifies that compatibility churn.
- Dependabot's `org.json:json:20260814` candidate: upstream release documentation identifies 20260719 as the latest published release; SENTINEL therefore pins the documented release rather than a newer unexplained coordinate.

Official references:
- https://github.com/github/codeql-action/blob/main/CHANGELOG.md
- https://github.com/stleary/JSON-java/releases
- https://github.com/stleary/JSON-java/blob/master/docs/RELEASES.md
- https://setuptools.pypa.io/en/latest/history.html

## Warning cleanup

The previous Core run reported only two warnings:

1. Pytest attempted to collect `TestEmailTransport` as a test class. The deterministic transport is now explicitly marked `__test__ = False`.
2. The TLS hardening test deliberately constructs an invalid TLS 1.1 context. The test now captures the expected Python `DeprecationWarning` with `pytest.warns` while still asserting that SENTINEL rejects TLS below 1.2. Security behavior is not weakened.

The earlier AnyIO BlockingPortal warning is not present in the latest inspected 439-test run.

## Conclusion

No broad dependency upgrade is justified beyond the PostgreSQL exact patch/digest pin, current Next.js security patch, AGP 9.4.1, CodeQL Action 4.38.1 and the official org.json test-only security update. Current direct pins are stable and compatible with the repository's target architecture. Final transitive-vulnerability acceptance is bound to the exact PR HEAD by the Security workflow; this document does not substitute for that green exact-SHA result.
