# SENTINEL — Firebase Test Lab Policy

Status: OPTIONAL / NON-BLOCKING

FTL/GCP authentication is not a product-correctness gate at the current project stage. A Firebase Test Lab failure caused by missing or unavailable GCP credentials is classified as infrastructure and does not block acceptance when all product/code/build/security checks are green.

Current acceptance model:
- Backend/core tests: gating.
- PostgreSQL integration/recovery: gating.
- Android build/tests and release validation: gating.
- Web/container/reproducibility/deployment smoke: gating.
- Security and P1 evidence workflows: gating.
- Firebase Test Lab: informational/non-blocking until explicitly restored.
- Real-device Android validation: Human Owner performs cumulative manual acceptance after sufficient functionality has accumulated.

FTL remains a planned later hardening block. No fake credentials are permitted, and no product code should be changed solely to mask an FTL/GCP infrastructure failure.
