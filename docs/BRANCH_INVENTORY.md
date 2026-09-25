# SENTINEL — Active Remote Branch Inventory

**Status:** ACTIVE  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Post-cleanup baseline:** protected `main` at `6f85186404b7b71e41a94ad75f8c97f38ce297d9`

## Current durable state

After PR #349 merged, the protected-main Branch Hygiene job `108131226210` revalidated every reviewed live ref and removed all 40 remaining non-main historical branches. The job reported:

`BRANCH_HYGIENE deleted=40 already_absent=0`

A live GitHub branch enumeration after the job completed contained only protected `main`.

Temporary branches carrying an in-flight PR may exist while work is active. They are not durable project state; after an exact-SHA guarded merge, the same workflow may self-delete the merged same-repository PR head only after proving `base=main`, exact PR head, merged state and exact merge-commit identity.

## Classification rules

- `ACTIVE` — intentionally retained current branch.
- `MERGED_EXACT` — live branch tip equals the stored exact head SHA of a merged PR.
- `PURE_BEHIND` — live branch tip is an ancestor of protected `main` and has no branch-only commit.
- `CONTENT_SUPERSEDED` — branch-only content was explicitly reconciled and no unique useful implementation/evidence remains.
- `UNIQUE_RECONCILE` — useful or uncertain branch-only content remains; deletion prohibited.
- `UNKNOWN` — deletion prohibited.

Deletion requires full live-tip revalidation. `MERGED_EXACT` additionally requires live PR-head equality. `CONTENT_SUPERSEDED` requires explicit reviewed reconciliation evidence. Protected refs are never deletion targets and any ref mutation aborts cleanup.

## Durable inventory

| Branch | Classification | Evidence |
| --- | --- | --- |
| `main` | ACTIVE | protected production source of truth |

The detailed 2026-09-23/2026-09-25 reconciliation history remains preserved in Git history and `BRANCH_DELETION_MANIFEST_2026-09-23.md` as historical evidence; it is not a live branch list.
