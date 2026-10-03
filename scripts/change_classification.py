#!/usr/bin/env python3
"""Conservative PR impact routing. Unknown inputs select full verification."""
from __future__ import annotations
import json
import os
import re
import subprocess
from pathlib import Path

KEYS = ('core', 'postgres', 'android', 'instrumentation', 'web', 'site', 'companion', 'bridge', 'games', 'design', 'dependencies', 'release', 'container', 'supply_chain', 'physical', 'p1', 'codeql_python', 'codeql_javascript', 'audit_python', 'audit_javascript')
ALL = set(KEYS)
PROTOCOL = {'core', 'postgres', 'android', 'instrumentation', 'web', 'companion', 'bridge', 'games', 'physical', 'p1'}
DESIGN = {'android', 'instrumentation', 'web', 'site', 'companion', 'design', 'physical'}
CONTRACT = re.compile(r'(API|AUTH|ENTITLEMENT|SESSION|ACTION|GAME[_-]|UNIFIED_|CONTROL_BRIDGE|PROVIDER|RUNTIME|KNOWLEDGE|INTELLIGENCE|COMPANION|RECOMMENDATION|ACCOUNT|DEVICE|BILLING|ROUTES|INTERACTION|POLICY|SECURITY)', re.I)
SECURITY = re.compile(r'(SECURITY|RELEASE|SIGNING|SUPPLY_CHAIN|ATTESTATION|EVIDENCE|ACCEPTANCE|RLS|DATABASE)', re.I)
BUILD_FILES = {'VERSION', '.node-version', '.python-version', 'settings.gradle.kts', 'build.gradle.kts', 'gradle.properties', 'gradlew', 'gradlew.bat', 'docker-compose.yml', 'render.yaml', 'verify.sh', 'AGENTS.md', '.env.example', '.dockerignore', '.gitattributes'}


def classify(paths: list[str], event: str = 'pull_request') -> dict[str, bool]:
    if event != 'pull_request' or not paths:
        return dict.fromkeys(KEYS, True)
    selected: set[str] = set()
    for path in paths:
        if not path or path.startswith('/') or '..' in Path(path).parts:
            return dict.fromkeys(KEYS, True)
        name = Path(path).name
        if path.startswith(('.github/', 'gradle/', 'scripts/')) or path in BUILD_FILES or name in {'AGENTS.md', 'pyproject.toml', 'requirements.txt', 'package.json', 'package-lock.json'} or name.endswith(('.gradle', '.gradle.kts', '.lock', '.lockfile')):
            selected |= ALL
        elif path.startswith('docs/'):
            if SECURITY.search(name): selected |= ALL
            elif 'DESIGN' in name.upper(): selected |= DESIGN
            elif CONTRACT.search(name): selected |= PROTOCOL
        elif path.startswith(('design/', 'shared/', 'assets/')):
            selected |= DESIGN
            if path.startswith('shared/'): selected |= PROTOCOL
        elif path.startswith('server/'):
            selected |= {'core', 'postgres', 'container', 'p1', 'codeql_python', 'audit_python'}
            # API/schema/provider changes can invalidate every protocol consumer.
            if any(part in path for part in ('/api/', '/schemas', '/auth', '/federated', '/providers', '/migrations/', '/data/')) or CONTRACT.search(name) or name in {'models.py', 'main.py', 'entrypoint.py'}:
                selected |= PROTOCOL
        elif path.startswith('app/'): selected |= {'android', 'instrumentation', 'physical'}
        elif path.startswith('web/'): selected |= {'web', 'codeql_javascript', 'audit_javascript'}
        elif path.startswith('site/'): selected |= {'site', 'codeql_javascript', 'audit_javascript'}
        elif path.startswith('launcher/'): selected |= {'companion', 'games', 'codeql_javascript', 'audit_javascript'}
        elif path.startswith('control-bridge/'): selected |= {'bridge', 'codeql_python', 'audit_python'}
        elif path.startswith(('wow-addon/', 'games/', 'knowledge/')): selected |= {'games', 'core', 'companion', 'p1'}
        elif path.startswith('observability/'): selected |= PROTOCOL
        elif path in {'README.md', 'LICENSE', '.gitignore', '.editorconfig'}: pass
        else: selected |= ALL
        if path.endswith('.py'): selected.add('codeql_python')
        if path.endswith(('.js', '.cjs', '.mjs', '.ts', '.tsx', '.jsx')): selected.add('codeql_javascript')
    return {key: key in selected for key in KEYS}


def event_paths(event: dict) -> list[str]:
    """Diff both sides of renames/deletions, with no API pagination or text parsing."""
    pr = event['pull_request']
    base, head = pr['base']['sha'], pr['head']['sha']
    if not all(re.fullmatch('[0-9a-f]{40}', value) for value in (base, head)):
        raise ValueError('INVALID_DIFF_SHA')
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if actual != head: raise ValueError('CLASSIFIER_HEAD_MISMATCH')
    raw = subprocess.check_output(['git', 'diff', '--name-only', '--no-renames', '-z', f'{base}...{head}', '--'])
    return [path.decode('utf-8', errors='strict') for path in raw.split(b'\0') if path]


def main() -> None:
    event_name = os.environ.get('GITHUB_EVENT_NAME', 'workflow_dispatch')
    paths = event_paths(json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())) if event_name == 'pull_request' else []
    result = classify(paths, event_name)
    # Fixed output keys/values only; never interpolate untrusted filenames into shell/output.
    lines = [f'{key}={str(value).lower()}' for key, value in result.items()]
    languages = [lang for lang, key in [('python', 'codeql_python'), ('javascript', 'codeql_javascript')] if result[key]]
    lines += [f'codeql_any={str(bool(languages)).lower()}', 'codeql_languages=' + json.dumps(languages or ['python'])]
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output: output.write('\n'.join(lines) + '\n')
    summary = {'event': event_name, 'changed_file_count': len(paths), 'selected': result}
    print(json.dumps(summary, sort_keys=True))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as output: output.write('## Change classification\n```json\n' + json.dumps(summary, indent=2) + '\n```\n')

if __name__ == '__main__': main()
