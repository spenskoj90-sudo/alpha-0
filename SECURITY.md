# Security Policy

SENTINEL treats security failures as release blockers.

## Reporting a vulnerability

Do not disclose exploitable vulnerabilities in public issues or pull requests.
Report them privately to the repository owner through the private GitHub security reporting mechanism when enabled.

Include:

- affected component and version/commit;
- reproducible steps or proof of concept;
- expected versus actual security behavior;
- impact assessment;
- logs or traces with secrets and personal data removed.

## Security principles

- Default Deny
- Least Privilege
- Server-side authorization as the source of truth
- Android Keystore-backed private keys
- Replay protection for authentication challenges
- Explicit device binding
- Mandatory auditability for successful security decisions
- Fail closed on malformed input and evaluation failures
- No secrets or production signing material in source control

## Release rule

A security-sensitive change is not accepted from source inspection alone. It requires execution evidence and regression coverage according to the Sentinel acceptance rule:

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`
