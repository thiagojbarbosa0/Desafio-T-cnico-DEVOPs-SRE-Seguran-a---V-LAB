# R7 — Security design and validation

## Bounded demo bearer credentials

Local-only HMAC tokens are parsed only after bounded size/shape checks. Signature comparison precedes JSON parsing. Duplicate keys and noncanonical Base64 are invalid; issued sessions are limited to 24h. This is *not* Firebase authentication.

## SQLite abuse-control invariant

For fixed bucket B, with C the count of **accepted** requests and limit L:

- 0 <= C <= L; denial does not increment C.
- Clock rollback `now < window_started` blocks rather than resetting.
- Corrupt counters/window cannot be silently healed by reopening quota.
- Concurrent requests from multiple API instances share one SQLite file; `BEGIN IMMEDIATE` serializes check/update.

This is per source network address in the synthetic login endpoint; it is not a distributed rate limiter against a botnet or a substitute for Firebase RTDB's authenticated-user quota in the original app.

## JSON and transport boundaries

Duplicate object keys are forbidden on the synthetic demo API because different downstream parsers may disagree about which claim wins. `NaN` and `Infinity` are not valid JSON. HTTP transfer encodings and duplicate `Content-Length` are rejected as unsupported. Logging records request template/status only, never raw exceptions.

## Evidence limitations

R7 proofs: local Python `http.server` + SQLite and offline regression. No V19.15 integration, no active Firebase Admin SDK, and no Docker. Do not increment weighted acceptance for unproven upstream security repairs. Do not publish the lab on external interfaces.
