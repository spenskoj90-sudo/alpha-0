#!/usr/bin/env bash
# Owner-operated GitHub Projects v2 bootstrap. NO service token is stored here.
# Run locally with GitHub CLI after 'gh auth refresh -s project'.
set -euo pipefail
umask 077
OWNER='spenskoj90-sudo'
if [[ "${1:-}" != '--apply' || $# -ne 1 ]]; then
  echo 'Usage: bash scripts/bootstrap_project_boards_v21.sh --apply' >&2
  echo 'Requires gh CLI owner login (with project scope) and jq. Never paste credentials.' >&2
  exit 2
fi
command -v gh >/dev/null || { echo 'Missing GitHub CLI' >&2; exit 1; }
command -v jq >/dev/null || { echo 'Missing jq' >&2; exit 1; }
current="$(gh api user --jq '.login')"
[[ "$current" == "$OWNER" ]] || { echo 'Wrong GitHub account; refusing modifications' >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo 'GitHub CLI authentication unavailable' >&2; exit 1; }

find_or_create() {
  local title="$1" data n count
  data="$(gh project list --owner "$OWNER" --format json --limit 100)"
  count="$(jq -r --arg t "$title" '[.projects[] | select(.title == $t)] | length' <<<"$data")"
  [[ "$count" =~ ^[0-9]+$ && "$count" -le 1 ]] || { echo 'Duplicate/ambiguous project title; stop for review' >&2; return 1; }
  if [[ "$count" == '0' ]]; then
    n="$(gh project create --owner "$OWNER" --title "$title" --format json --jq '.number')"
  else
    n="$(jq -r --arg t "$title" '.projects[] | select(.title == $t) | .number' <<<"$data")"
  fi
  [[ "$n" =~ ^[0-9]+$ ]] || { echo 'Invalid GitHub Project number' >&2; return 1; }
  # Force explicit private visibility BEFORE repository linking or adding Issues.
  gh project edit "$n" --owner "$OWNER" --visibility PRIVATE >/dev/null
  local visible
  visible="$(gh project view "$n" --owner "$OWNER" --format json --jq '.public')"
  [[ "$visible" == 'false' ]] || { echo 'Project is not verified private; refusing to add items' >&2; return 1; }
  printf '%s\n' "$n"
}

add_item_once() {
  local n="$1" url="$2" existing
  existing="$(gh project item-list "$n" --owner "$OWNER" --format json --limit 500 | jq -r --arg u "$url" '[.items[] | select(.content.url? == $u)] | length')"
  [[ "$existing" =~ ^[0-9]+$ ]] || { echo 'Could not verify project items' >&2; return 1; }
  if [[ "$existing" == '0' ]]; then
    gh project item-add "$n" --owner "$OWNER" --url "$url" >/dev/null
  fi
}

sentinel="$(find_or_create 'SENTINEL · Engineering')"
forma="$(find_or_create 'FORMA · Engineering')"
portfolio="$(find_or_create 'PROJECTS · Portfolio')"

link_once() {
  local n="$1" repo="$2" output
  if ! output="$(gh project link "$n" --owner "$OWNER" --repo "$repo" 2>&1)"; then
    if [[ "$output" != *"already linked"* ]]; then
      echo "Unable to link GitHub Project to repository; stop for review" >&2
      return 1
    fi
  fi
}
link_once "$sentinel" "$OWNER/alpha-0"
link_once "$forma" "$OWNER/forma-fitness-android"
link_once "$portfolio" "$OWNER/alpha-0"
link_once "$portfolio" "$OWNER/forma-fitness-android"

for issue in 528 529 530; do
  url="https://github.com/$OWNER/alpha-0/issues/$issue"
  add_item_once "$sentinel" "$url"
  add_item_once "$portfolio" "$url"
done
add_item_once "$sentinel" "https://github.com/$OWNER/alpha-0/pull/527"
for issue in 7 8 9; do
  url="https://github.com/$OWNER/forma-fitness-android/issues/$issue"
  add_item_once "$forma" "$url"
done
add_item_once "$forma" "https://github.com/$OWNER/forma-fitness-android/pull/6"
for issue in 7 8; do
  add_item_once "$portfolio" "https://github.com/$OWNER/forma-fitness-android/issues/$issue"
done

echo 'Three PRIVATE GitHub Projects verified and seeded with linked existing Issues/PRs:'
for n in "$sentinel" "$forma" "$portfolio"; do
  gh project view "$n" --owner "$OWNER" --format json --jq '"#\(.number) \(.title) \(.url) PRIVATE=\(.public|not)"'
done
echo 'Next: configure Boards/Roadmaps and reconcile all 14 Linear issues separately.'
echo 'Do not disconnect Linear or delete Drive archives on the basis of this bootstrap.'
