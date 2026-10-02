# Email action codes v1

Active contract for account email verification and password recovery; supplements the existing account/session authority without changing MFA.

- New emails use a CSPRNG-generated **eight ASCII digits**, including leading zeros; codes are ordinary selectable text in both HTML and plaintext. No remote image, tracking pixel, credential-bearing link or JavaScript copy button.
- Presentation follows SENTINEL calm precision: text wordmark, restrained teal accent, readable card, RU/EN chosen from explicit request language; system dark styling where supported by the mail client. System font fallbacks avoid external font loads.
- Code TTL is **15 minutes**, single-use, bound to normalized account email **and action purpose**. Numeric confirmation must include the email. Older opaque codes retain their existing expiry/single-use contract until replaced or expired.
- Store only salted scrypt digests behind unrelated high-entropy row selectors. No plaintext code, bare short-code SHA lookup, subject/preheader code, API response code or body in object repr.
- Five invalid attempts consume the challenge, without locking the account. Maximum three issued codes per account/purpose in a rolling hour; replacements invalidate earlier challenges. Existing public request responses remain non-enumerating. Existing endpoint/IP limits remain enforced.
- PostgreSQL account-row locking serializes issuance, budget checks and consumption across processes. Consuming a valid reset, updating password and revoking sessions are one transaction. MFA is preserved. Forced RLS/default-deny remains unchanged.
- Additive migration `015_email_action_codes.sql` adds digest and attempt columns to existing auth action rows. Retention preserves short-code issuance history for the rolling hour even after expiry. No reset or legacy migration edits.
- Android/Web accept a whole numeric code pasted with whitespace, preserve leading zeros, request numeric keyboards and keep earlier opaque email input valid. Password recovery asks for the email in direct-confirm mode as well.

Acceptance requires exact-source Core/PostgreSQL, Web/browser and Android CI. Browser HTML preview is layout evidence, not Gmail/inbox delivery or physical acceptance. Owner's previous APK test remains evidence only for its original generation.
