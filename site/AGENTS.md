# Public Website scoped agent instructions

Scope: site/.

- Follow root AGENTS.md.
- Public Website is isolated from authenticated Control Plane authority.
- Keep static export and no app/api trust boundary unless Owner explicitly changes product architecture.
- Do not publish download/availability claims before matching release evidence exists.
- Default validation: npm ci, npm run lint, npm run build.
- A green static build is only BUILD-VERIFIED. Owner acceptance requires a real browser-openable exact build/preview.
- Visual work must be responsive and cover accessibility, reduced motion, and forced-colors expectations.
