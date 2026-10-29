# CourseSphere — engineering checkpoint R2 (2026-10-25)

**Source of code:** recovered executable CourseSphere V19.9 Work, extended from the previous refined V19.9 checkpoint. **This is NOT the V19.15 checkout.** No upstream accounts, keys, publication or deployment were used. Original React/Vite + Flask + Firebase modules and the separate demonstration laboratory are preserved.

## Change 1 — real security improvement: shared quota clock rollback

`backend/shared_quota.py` uses a shared RTDB transaction, but its previous fixed-window algorithm reset a counter whenever the stored window did not equal the local server window. With two replicas near a window boundary, a slow clock could rewrite the shared counter to an *older* window, allowing subsequent calls to reset and extend the quota. A corrupted window value could also be treated as a new window.

The revised transaction accepts `None` as a first use, permits a strictly later window and rejects attempts to roll back to an earlier window; invalid windows fail closed and retain their state. Invalid count values, including booleans, do not reopen a quota. Old/invalid clock input is rejected. Counters remain per authenticated UID/action, keyed by SHA-256, inside RTDB. The existing transaction/authorization/error handling remains intact.

Proofs are deterministic, two-replica simulated RTDB tests (`tests/test_v17_shared_quota.py`, `tests/test_quota_clock_skew_vlab.py`). These **do not replace Firebase Emulator or Docker HTTP concurrency proofs**. A known limitation of fixed-window quotas remains boundary bursts when time legitimately moves forward; that requires separate policy and, if necessary, a sliding-window/token-bucket design.

**Evidence impact:** changing `backend/shared_quota.py` invalidates older Flask and Firebase Emulator source-bound proofs. Do not import credit from V19.9, V19.12 or V19.15 without executing the correct checkout and checking hash congruence.

## Change 2 — real dependency chain integrity

`npm_lock_integrity_vlab.py` now verifies that the `package.json` dependency groups and root package identity correspond exactly to the npm lockfile, that each directly declared package exists in the lock, and that SRI values decode to the full required byte count. URLs still require HTTPS and no credentials. It identifies packages with install scripts for manual review rather than treating their presence as proof of compromise.

`npm_audit_triage_vlab.py` now rejects tool/network `error` fields, totals inconsistent with their vulnerability list, and mismatched package severity between full/production reports. Optional CI flags require audit v2 metadata, production scope, and no high/critical packages in the production report. The report records hashes of the lockfile and audit input files, avoiding unverifiable counts. This is *not* an exploitability scan and does not replace dependency upgrade review.

The `.github/workflows/ci.yml` frontend job captures the full and `--omit=dev` audit JSON locally, runs fail-closed triage and uploads only the sanitized triage report. No `npm audit fix --force`, no mutation of production dependencies.

## Change 3 — release ZIP validation

`scripts/verify_release_archive_vlab.py` rejects path traversal, windows separators, casefold duplicates, symlink entries, private paths (`.local`, `.git`, virtualenvs), `.env` files, non-regular records, corrupt CRCs, encrypted entries and suspicious sizes/compression. It allows the original project's large Cornell dataset within a documented bounded archive limit. No extraction occurs during validation. **Filename/CRC safety is not secret scanning**, and a separate Git history/license audit is still required.

## Current release boundary

The only source we can edit in this environment is the recovered V19.9. The real V19.15 source ZIP remains unavailable for byte-level patching. The portable addon contains new standalone utilities/tests and a *review-only* patch for the quota algorithm, not a complete replacement of V19.15. The next integration must compare the exact `backend/shared_quota.py` of V19.15 before applying patches; **do not overwrite its Firebase adapter or Compose config**.

### Execution from the refined V19.9 checkout

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -q
python3 -m scripts.record_offline_v16
python3 scripts/npm_lock_integrity_vlab.py --output evidence/generated/NPM_LOCK_INTEGRITY_VLAB.json
python3 -m scripts.release_gate_work_v19_9
```

On a system with npm registry access, capture the complete and production audit reports at a consistent checkout before triage. Do not commit the raw audit reports or use `|| true` to claim a successful scan. The Docker/Firebase proof and original React browser test remain separate, and can only receive credit after actual execution on the same source version.

## OWASP findings / editorial integrity

Keep F03 (token in URL), F04 (upstream credential material), F05 (exception detail), F06 (input limits) and P-PROFILE (stale client session) under their original limitations. F01/F02 are dependent on expected business authorization; D01/D02 emerged in the derived code and must not be mislabeled upstream. The new clock guard is a derived hardening, not a sixth confirmed upstream vulnerability. Five findings + three root-cause remediations still need formal review, owner license permission and possible secret rotation.
