# Staging telemetry privacy delta — 2026-10-02

The custom Core HTTPS sink now sends `$geoip_disable=true` on both runtime and
Companion operational events. Live project property discovery showed GeoIP fields;
the server-location enrichment is unnecessary for source/release correlation.
This change suppresses enrichment for new events, not deletion of historical data.

Person profiling remains disabled, identity remains `sentinel-runtime`, region
endpoints and operational attribute allowlist remain fixed. No browser SDK, replay,
auth data, game frames or voice payload is added. Activation is staging-only;
changing a key cannot enable production telemetry.

Reference: [PostHog Python GeoIP behavior](https://posthog.com/docs/libraries/python#geoip-properties),
read through the connected provider documentation on 2026-10-02. Unlike the SDK,
the custom HTTPS transport must explicitly set the per-event suppression property.
Deterministic capture and actual lifespan tests verify the exact outbound property
set. Provider ingestion and absence of location enrichment require a new source-bound
event after deployment; project settings alone are not that evidence.
