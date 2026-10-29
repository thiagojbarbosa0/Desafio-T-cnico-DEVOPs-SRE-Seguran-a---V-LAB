# Engineering continuation R2 — CourseSphere AppSec/SRE

**Executable base:** the genuine recovered CourseSphere V19.9 Work with V19.9-specific improvements. **Not a reconstructed CourseSphere, and not the user's V19.15 checkout.**

Source changes: `backend/shared_quota.py`, `scripts/npm_lock_integrity_vlab.py`, `scripts/npm_audit_triage_vlab.py`, `scripts/release_gate_work_v19_9.py`, `.github/workflows/ci.yml`. Added `scripts/verify_release_archive_vlab.py`, portable clock-skew regression tests and ZIP auditing tests. Preserved the original React and Flask handlers and Firebase emulator wiring. Do not run public deploy commands.

To run Python offline regressions: `python3 -m unittest discover -s tests -p 'test_*.py' -q`; to regenerate audit-bound evidence use `python3 -m scripts.record_offline_v16`, then `python3 -m scripts.release_gate_work_v19_9`.

`docs/COURSESPHERE_VLAB_CHECKPOINT_R2_2026_10_25.md` explains the root cause and evidence invalidation. The addon for V19.15 includes *new* files for selective copy and an isolated patch for review. The patch must not be blindly applied without comparing V19.15 source.
