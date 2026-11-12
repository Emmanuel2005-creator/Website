# Application improvement verification

Verified on November 12, 2026, on Windows with Python 3.13 and headless Microsoft Edge (Chromium).

## Results

| Check | Actual result |
| --- | --- |
| `python -m pytest -q` | **65 passed**, 43 upstream deprecation warnings, 13.46 seconds |
| `BROWSER_CHANNEL=msedge python tests/browser_check.py` | **Passed** |
| `python -m pip check` | **No broken requirements found** |
| Final `git diff --check main` | **Passed** |
| Original SQLite file | Byte-for-byte unchanged; checksum below |

Backend tests cover startup, environment configuration, required secrets, health JSON, existing routes, signup/login/logout, remember cookies, invalid/duplicate registrations, all original password formats, unusual legacy credentials, CSRF across every state-changing route, anonymous access, note ownership, validation, escaping, refresh safety, malformed deletion, database rollback, oversized requests, and original-schema compatibility.

Browser checks cover:
- Login and registration layouts at 320, 390, 768, 900, and 1440 pixels wide.
- Dashboard layouts additionally at 700 and 1024 pixels wide.
- Signup, empty state, note entry, live character count, saving, viewing, login, and logout.
- Successful deletion, cancellation, Escape, initial dialog focus, returned focus, and failed-delete feedback without removing the note.
- Whitespace rejection, long unbroken content, horizontal overflow, loaded imagery, JavaScript errors, and CSP violations.
- Six saved screenshots, reviewed visually: desktop/mobile login, desktop registration, desktop/mobile dashboard, and empty dashboard.

A mobile illustration overflow and overlap found during verification were corrected before the final passing run. The browser suite uses only a temporary database and synthetic account, automatically shut down and discarded afterward.

## Preservation and scope

- The original tracked database contains zero users and zero notes. It was read only for inspection and preserved locally, with an ignored backup in `.artifacts/original-database.db`.
- Original and final database SHA-256: `90b7b31ac9ab91c32f16b431119499f831b77982d1b91c1770d1270f8ebe1ea5`.
- No changes to `website/models.py`, existing tables, stored notes, or existing password hashes.
- The database and compiled Python files are removed from the Git index, not the local working copy. Back up any other existing installation's data outside its checkout before changing branches.
- Existing route URLs remain. GET `/logout` now asks for confirmation; CSRF-protected POST performs logout. The dashboard logout button submits that POST directly.
- The new secret key invalidates prior sessions; users log in again with the same account credentials.
- No changes to QuizCloud. No Docker, Terraform, GitHub Actions, or AWS resources. No merge into main.

## Remaining limitations

- Flask-Login 0.6.3 emits 43 `datetime.utcnow()` deprecation warnings under Python 3.13 in this suite. Warnings are visible and do not fail tests.
- Browser checks used Chromium-based Edge; Firefox, Safari, and physical devices were not tested. A full accessibility audit has not been performed.
- Older salted SHA-256 hashes remain compatible and unchanged. New accounts use scrypt.
- `/health` reports process liveness, not database readiness.
- Flask's local server, SQLite storage, authentication rate limiting, account recovery, production HTTPS, and backups remain future-phase considerations described in the README.
- Removing tracked data and the secret from current code does not erase historical Git objects.

## Complete changed-file list

Compared with the original `main` commit. “Removed” means removed from the branch's tracked files. Local SQLite/cache copies are preserved.

| Status | File |
| --- | --- |
| Added | `.env.example` |
| Added | `.gitignore` |
| Modified | `README.md` |
| Added | `docs/screenshots/dashboard-desktop.png` |
| Added | `docs/screenshots/dashboard-empty.png` |
| Added | `docs/screenshots/dashboard-mobile.png` |
| Added | `docs/screenshots/login-desktop.png` |
| Added | `docs/screenshots/login-mobile.png` |
| Added | `docs/screenshots/registration-desktop.png` |
| Added | `docs/verification.md` |
| Removed | `instance/database.db` |
| Modified | `main.py` |
| Added | `pytest.ini` |
| Added | `requirements-dev.txt` |
| Added | `requirements.txt` |
| Added | `tests/browser_check.py` |
| Added | `tests/conftest.py` |
| Added | `tests/test_app.py` |
| Removed | `website/README.md` |
| Modified | `website/__init__.py` |
| Removed | `website/__pycache__/__init__.cpython-313.pyc` |
| Removed | `website/__pycache__/__init__.cpython-39.pyc` |
| Removed | `website/__pycache__/auth.cpython-313.pyc` |
| Removed | `website/__pycache__/models.cpython-313.pyc` |
| Removed | `website/__pycache__/views.cpython-313.pyc` |
| Modified | `website/auth.py` |
| Added | `website/security.py` |
| Added | `website/static/favicon.svg` |
| Modified | `website/static/index.js` |
| Added | `website/static/notebook.svg` |
| Added | `website/static/styles.css` |
| Added | `website/templates/auth_layout.html` |
| Modified | `website/templates/base.html` |
| Added | `website/templates/error.html` |
| Modified | `website/templates/home.html` |
| Added | `website/templates/icons.html` |
| Modified | `website/templates/login.html` |
| Added | `website/templates/logout.html` |
| Modified | `website/templates/sign_up.html` |
| Modified | `website/views.py` |
