# Authenticated Web Control Plane scoped agent instructions

Scope: web/.

- Follow root AGENTS.md.
- This is the authenticated Control Plane, not the public marketing site.
- Preserve HttpOnly/session proxy boundaries and server-authoritative Core state.
- Runtime requires correct SENTINEL_CORE_URL and origin configuration; build success does not prove Web-to-Core connectivity.
- Node contract is 24.x and repository .node-version.
- Production/staging `npm start` binds Next explicitly to `0.0.0.0`; do not rely on platform hostname defaults.
- Default validation: npm ci, npm test, npm run test:coverage, npm run lint, npm run build.
- User-visible acceptance requires a real browser-openable exact build and end-to-end staging checks, not screenshots.
- After deploy validate load, Core reachability, disposable auth/session flow, account API, logout, and applicable failure/degraded states.
