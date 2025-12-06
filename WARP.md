# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.
``

## Quick commands

Setup

- Create venv (optional) and install deps: `python -m pip install -r requirements.txt`

Run the desktop app (macOS/Linux/Windows with Python):

- `python main.py`

Build a packaged app

- Windows (uses provided script): `build_windows.bat`
- Manual (any OS with Python + PyInstaller installed):
  - Install PyInstaller: `python -m pip install pyinstaller`
  - Build one-file windowed app: `python -m PyInstaller --name "SimplePasswordManager" --onefile --windowed main.py`
  - Output appears in `dist/`

Linting and tests

- No linter or test suite is configured in this repo as of this version.

## High-level architecture

Purpose

- Simple desktop password manager with a PyQt6 UI, local SQLite storage, and symmetric encryption of stored passwords using `cryptography.Fernet` with a PBKDF2-derived key.

Key modules

- `main.py`: Application entry point and UI.
  - Starts Qt app, initializes DB, performs master-password unlock flow, and launches `MainWindow`.
  - `MasterPasswordDialog` collects the master password on startup (first-run vs. unlock).
  - `MainWindow` provides search, add/edit/delete accounts, and “Copy Password” to clipboard.
- `db.py`: Thin data layer over SQLite.
  - Ensures schema on startup (`init_db()`), including forward-compatible ALTERs for older DBs.
  - CRUD helpers: `list_accounts`, `add_account`, `update_account`, `delete_account`.
  - Settings helpers for salt and verifier: `get_settings`, `set_settings`, `get_verifier`.
- `crypto_utils.py`: Key derivation and encryption utilities.
  - PBKDF2-HMAC-SHA256 with 390,000 iterations and 16-byte random salt.
  - Fernet key is base64-url-encoded from the derived 32-byte key.

Data model (SQLite, file `passwords.db` in repo root)

- `settings (id=1, salt BLOB NOT NULL, verifier BLOB NULL)`
  - `salt`: random 16 bytes generated on first run and persisted.
  - `verifier`: encrypted marker (“master-password-verifier”) used to validate the master password without storing it.
- `accounts (id, service TEXT, username TEXT, password BLOB, notes TEXT, created_at TEXT, updated_at TEXT)`
  - `password` is the Fernet-encrypted bytes of the plaintext password.
  - Timestamps default to `datetime('now')`; `updated_at` refreshed on update.

Startup and unlock flow

1) `db.init_db()` creates or migrates tables.
2) App reads `(salt, verifier)` via `db.get_settings()`.
3) First run (no salt):
   - Generate salt (`generate_salt()`), derive key (`build_fernet()`), encrypt fixed marker, store `(salt, verifier)`.
4) Existing vault: derive candidate key from user input and stored salt; decrypt `verifier` and compare to marker to validate.
5) On success, `MainWindow` is shown with a live Fernet instance retained for the session.

UI and encryption boundaries

- Add/Edit: plaintext password from dialog is immediately encrypted (`encrypt_password`) before persisting via `db.add_account`/`db.update_account`.
- Copy Password: fetch row, decrypt in-memory (`decrypt_password`), copy to system clipboard. Clipboard contents are not auto-cleared.

Notable implementation details

- DB path is fixed (`passwords.db`) alongside the app; moving the DB between machines preserves data, provided the same master password is used.
- Changing the master password is not implemented; doing so externally will render existing data unreadable unless a re-encryption migration is performed.
- The schema migration attempts (`ALTER TABLE ... ADD COLUMN`) are guarded and safe to re-run.

## Files of interest

- `README.md`: Practical setup/run steps and a concise overview of encryption and build options; keep it in sync with this file.
- `build_windows.bat`: One-file windowed build for Windows via PyInstaller.
- `.gitignore`: Ignores local DBs, build artifacts, and Python caches.

## Agent usage tips specific to this repo

- When modifying DB or crypto flows, ensure consistency between `db.py` and `crypto_utils.py` and the unlock logic in `main.py` (marker string, salt handling, and Fernet construction must align).
- UI changes typically require coordinated updates in `AccountDialog`, `MainWindow._build_ui`, and the corresponding CRUD paths.
- If adding tests in the future, prefer isolating crypto (pure functions) and DB (temporary DB path) for deterministic testing.
