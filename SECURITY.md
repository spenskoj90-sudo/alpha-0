# Security Policy

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in public issues, pull requests, or discussions.

Until a dedicated private security reporting channel is configured, report security-sensitive findings privately to the repository owner through GitHub's private contact mechanisms. Include enough detail to reproduce the issue, but do not include live credentials, private keys, or personal data.

## Secrets

Never commit real credentials, signing keys, keystores, tokens, passwords, production connection strings, or private certificates.

CI secrets are supplied through GitHub Actions secrets and are never required for ordinary pull-request validation.

If a real secret is exposed, treat it as compromised immediately: rotate/revoke it first, then remove it from the repository and history.

## Security boundary

Sentinel treats server-side authorization as the security boundary. Client-side checks are not trusted for authorization.

Security fixes must preserve Default Deny, Least Privilege, RBAC + Scope, entitlement-aware authorization, policy/context evaluation, auditability, and fail-closed behavior.
