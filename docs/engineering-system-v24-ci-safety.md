# Engineering system v2.4: CI safety batch / 2026-10-25

Status: PREPARED; this document is a scoped plan and evidence index, not completion of system gates.
Canonical approved specification: https://docs.google.com/document/d/1xwjebcbxbJcGjli2twTkmW2XNpXVZ8y8wQoL_CjMvgs/edit
Canonical workstream: https://github.com/spenskoj90-sudo/alpha-0/issues/532

## Implementation plan and acceptance

Goal: prevent unapproved branch deletion and preserve main/manual/release CI runs while keeping superseded PR cancellation.
Architecture: the branch workflow has only contents:read, no persisted checkout credentials, no mutation command and no apply switch. A paginated GET produces a REVIEW_REQUIRED inventory. Any future deletion requires a new reviewed implementation after independent restore, fresh inventory and explicit Owner authorization.
The Owner's v2.4 instruction supersedes the former automatic deletion contract. Keeping the destructive path behind a boolean was rejected because it retains an unnecessary mutation path and token authority.
Tech stack: existing GitHub Actions YAML, Bash, Python standard library.
Execution: one isolated source snapshot, one branch/PR, no production secrets or signing.

- [x] Read exact main, root governance, open PRs and workflow sources before edits.
- [x] Run new branch safety tests against old workflow: 4 failures, including write/deletion authority and missing review behavior.
- [x] Replace destructive workflow with read-only paginated review; test API failure propagation, all pages and untrusted branch text.
- [x] Update the existing repository verifier for the approved safety boundary. Existing unrelated security, release and coverage assertions remain.
- [x] Restrict cancellation to PR events. Isolate non-PR validation runs by run ID; retain serialization for shared release/staging resources with queue:max.
- [x] Independent review found no introduced blockers; harden the noted manual-rerun concurrency edge and recheck locally.
- [x] Verify Action pins and workflow boundaries locally. FULL application tests and exact new-SHA CI are separate evidence.
- [ ] Exact PR HEAD required checks PASS, independent review, then controlled merge and main readback. Do not mark this complete for a draft PR.

## Concurrency and rollback

GitHub's default concurrency queue replaces an existing pending run even with cancel-in-progress:false. Therefore:
- Initial PR validation uses workflow + event + PR number and permits cancellation. Manual reruns use their unique run ID, have cancellation disabled and cannot cancel a newer PR head.
- Non-PR validation uses a unique run ID and cannot replace another validation run.
- Existing serialized release, signed-update, final acceptance, MFA and staging-synthetic workflows use cancel-in-progress:false plus queue:max. This retains up to 100 pending runs; queue saturation remains a platform limit, not an unlimited-delivery guarantee. Check queued/manual work before additional dispatches.
- No trigger, job, mandatory check name, artifact consumer, signer or release authorization is removed by this batch.
- No backup workflow is added or activated here; PR #527 remains separate.
- Rollback concurrency independently if platform validation rejects it. Do not restore automatic branch deletion without the v2.4 restore/inventory/Owner gates. No deleted branch or migrated data is created by this batch.

Official syntax verified on 2026-10-25: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency
Queue feature: https://github.blog/changelog/2026-05-07-github-actions-concurrency-groups-now-allow-larger-queues/

## Live baseline and unclosed gates

- Sentinel main f81f70da743fa1528b919f198f1a34cf9fdaf5c5, PUBLIC, protected:true. Ten configured required contexts read from branches/main; configuration must not be confused with this batch's successful CI.
- Sentinel #527 head 0a9f1467687b9d7f3a82b82dd6122354feb54115 remains draft; API34 failure at https://github.com/spenskoj90-sudo/alpha-0/actions/runs/40108693526/job/120917358452 . Log confirms connectedDebugAndroidTest failure; individual test report still requires diagnosis.
- Sentinel #531 head a26be4def7aa74f3cb9c9aea238e1b2ac4425ee5 remains draft; observed checks succeed except expected skipped main-only attestations. This does not create GitHub Projects or prove an offsite restore.
- Existing open #524/#525/#526 remain independent; existing governance-v22-ci-budget branch contains an unmerged estimator, preserved without copying it into this safety batch.
- Forma main 6eeb6f5e1060dfd011df8d8cd18316942da08a72, PRIVATE, protected:false, no configured required contexts from branches/main. Existing draft #6 head d16af329bf181cbe0bd9b96531b6a89276d95764; API26 failure: https://github.com/spenskoj90-sudo/forma-fitness-android/actions/runs/40097981189/job/120885472400 . This batch changes no Forma source or CI.
- Branch readback before batch: 13 Sentinel refs, 9 Forma refs (each response below 100); nothing classified as disposable. The source providers retain full names/tips; no deletion is authorized.
- Four linked project documents exist as v2.4 plans/instructions; they must be updated at final handoff. The obsolete wait-until-complete rule does not apply.
- Linear list readback: 14 entries, 9 Done/1 Todo/4 Canceled. List descriptions are truncated, so full-body/comment/attachment reconciliation is NOT_VERIFIED. No disconnect, issue duplication or history deletion.
- Neon project metadata readback confirms separate PG18 and PG17 rollback projects, 21600-second history. Metadata/active-time is not account Billing and not independent recovery.
- Owner selected Render My Workspace (tea-dal2fcoae00c73faqelg). Readback confirms 5 Sentinel services: 2 static sites and 3 web services with plan:free. Four staging services auto-deploy main commits; the static preview has auto-deploy off. Metadata says not_suspended; this is not a health/SLO or Billing proof. No deployment, configuration or secret was changed.
- GitHub connection exposes repository reads/writes, but no Projects-management or account Billing API. No authenticated gh executable/session is available locally. Three boards, private access readback and actual billing remain NOT_VERIFIED.
- R2/age/Infisical/Firebase provisioning and independent offsite restore remain NOT_VERIFIED. This batch does not create accounts, credentials, backups or restores.
- Gate 1 remains PARTIAL (billing, provider inventories and permissions incomplete). Gates 2-8 are not closed.

## Workflow/artifact dependency map

Baseline is exact main above. PR #527/#531 extra workflows are not main. All artifact producers and consumers below are preserved; TTL changes require a later exact consumer/gate review. "default" means no explicit workflow retention, not infinite or verified account retention. User/device acceptance and external script consumers also need review before removing any output.


| Workflow | Baseline events | Baseline uploads / explicit TTL days | In-workflow download consumer |
| --- | --- | --- | --- |
| android-build.yml | pull_request, workflow_dispatch | build: 14 | none; external gate review required |
| android-update-e2e.yml | pull_request, workflow_dispatch | none | none; external gate review required |
| branch-hygiene.yml | push | none | none; external gate review required |
| build.yml | push, pull_request | android: default; android-instrumentation: 7; android-api34-compat: 7; block-d-evidence: default; browser-acceptance: 30 | none; external gate review required |
| change-classification.yml | workflow_call | none | none; external gate review required |
| deploy.yml | release, workflow_dispatch | none | none; external gate review required |
| final-release-acceptance.yml | workflow_dispatch | validate-final-acceptance: 90 | attest-final-acceptance |
| h-design-preview.yml | pull_request | preview: 30 | none; external gate review required |
| p1-evidence.yml | push, pull_request, workflow_dispatch | p1-evidence: 14 | none; external gate review required |
| packaged-companion.yml | push, pull_request | packaged-companion: 90 | attest-packaged-companion |
| physical-test-apk.yml | push, pull_request, workflow_dispatch | physical-test-apk: 90 | none; external gate review required |
| physical-test-update-apk.yml | workflow_dispatch | build-update-apk: 90 | none; external gate review required |
| release-candidate.yml | workflow_dispatch | presecret: 90; release-candidate: 90 | attest-release-candidate |
| release-evidence.yml | push, pull_request | release-evidence: 90 | attest-release-evidence |
| release.yml | push tag v*.*.* | presecret: 90; verify-candidate: 90 | publish |
| security.yml | push, pull_request, schedule, workflow_dispatch | none | none; external gate review required |
| staging-mfa-acceptance.yml | workflow_dispatch | none | none; external gate review required |
| staging-synthetic.yml | push, workflow_dispatch | staging-synthetic: 30; staging-browser: 30 | none; external gate review required |
| supply-chain-evidence.yml | push, pull_request | supply-chain-evidence: 90 | attest-supply-chain |

Attested upstream chains (release-evidence, packaged-companion, supply-chain) are consumed by release presecret/lineage/final-acceptance validation. Candidate and publication handoffs remain exact-source artifacts, not interchangeable debug APKs. Android instrumentation/browser outputs carry failure/device evidence. This table alone does not authorize output removal.
