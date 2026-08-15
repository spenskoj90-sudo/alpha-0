# Contributing

## Workflow

1. Create a focused branch from `main`.
2. Keep security-sensitive changes small and reviewable.
3. Add or update regression tests for every behavioral change.
4. Run Core tests, Android tests and web build locally when possible.
5. Open a pull request and wait for all required GitHub Actions checks.

## Required gates

- Build and test.
- Security / CodeQL / dependency audit.
- No committed secrets.
- Documentation updated for public behavior or deployment changes.
- Release changes must preserve migration compatibility and fail closed.

## Commit style

Use conventional prefixes where practical: `feat`, `fix`, `security`, `test`, `docs`, `build`, `ci`, `chore`.

## Security reports

Do not publish exploitable vulnerability details in a public issue. Use the repository's private security reporting mechanism where enabled.
