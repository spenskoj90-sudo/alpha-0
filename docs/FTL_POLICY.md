# SENTINEL — Firebase Test Lab Policy

Status: RETIRED AS A DEPENDENCY / OPTIONAL ONLY

Firebase Test Lab is not a product-correctness, CI, release-readiness, publication, deployment, or production-traffic gate for SENTINEL. GitHub-hosted Android Emulator instrumentation is the routine automated Android device gate; final physical Android acceptance remains part of the exact-candidate pre-release acceptance profile.

Issue #59 was closed as `not planned` after the Human Owner explicitly authorized removing or replacing Firebase Test Lab provided the project was not weakened. No Firebase/GCP credential or IAM repair is therefore required to complete repository engineering or reach the final real-device acceptance stage.

Current acceptance model:
- Backend/core tests: gating.
- PostgreSQL integration/recovery: gating.
- Android build/JVM tests and GitHub Emulator instrumentation: gating.
- Web/container/reproducibility/deployment smoke: gating.
- Security, P1, supply-chain and release-evidence workflows: gating where applicable.
- Firebase Test Lab: optional informational evidence only; absence or failure is non-blocking.
- Real physical Android validation: required only at the final exact-candidate acceptance stage defined by `docs/FINAL_RELEASE_ACCEPTANCE_V1.md`.

If Firebase Test Lab is voluntarily reintroduced later, it must add independent evidence without replacing or weakening existing GitHub Emulator or physical-device gates. No fake credentials are permitted, and no product/security code may be changed solely to make FTL/GCP infrastructure green.
