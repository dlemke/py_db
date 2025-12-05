## Simple Desktop Password Manager (SQLite + Encryption)

This is a small, modern desktop password manager written in Python.  
It uses **SQLite** to store accounts and **strong symmetric encryption** (via the `cryptography` package) to protect passwords at rest.

### Features

- **Desktop UI** built with `PyQt6`
- **SQLite** database stored locally in `passwords.db`
- **Master password–based encryption** for all stored passwords
- Create, search, edit, and delete accounts
- Copy decrypted passwords to the clipboard with one click

### Installation

1. Ensure you have **Python 3.10+** installed.
2. Install dependencies (preferably in a virtual environment):

```bash
pip install -r requirements.txt
pip install pyinstaller
```

(Optional) If you prefer, you can skip the separate `pip install pyinstaller` and let the batch script do it.

### Running the app

From the project directory:

```bash
python main.py
```

On first run you will be asked to **create a master password**.  
This password is used to derive the encryption key, and **cannot be recovered** if forgotten.

### How encryption works (high level)

- A random **salt** is generated once and stored in the `settings` table.
- On startup, you enter your **master password**.
- A key is derived from the master password + salt using **PBKDF2-HMAC-SHA256**.
- This key is turned into a `Fernet` key and used to **encrypt/decrypt** all account passwords.

If you change the master password outside of the app, existing data will become unreadable.  
To change master password safely you would need a small migration that decrypts all passwords with the old key and re‑encrypts them with the new one (not implemented in this minimal example).

### Notes and limitations

- This is a **simple example**, not a full-featured enterprise password manager.
- The database file is stored unhidden as `passwords.db` in the project folder.
- Clipboard contents are **not cleared automatically**; they stay there until you copy something else.
- Always keep your master password safe and **do not share it**.

### Build the .exe

You now have two options:

- Option 1 – Use the batch script (simplest)
  From the project root in Command Prompt or PowerShell:
  `build_windows.bat`

This will:
Ensure pyinstaller is installed
Run PyInstaller with:
--onefile (single .exe)
--windowed (no console window)
Output SimplePasswordManager.exe into the dist folder.

- Option 2 – Run PyInstaller manually
  From the project root:
  `py -m PyInstaller --name "SimplePasswordManager" --onefile --windowed main.py`

The resulting dist\SimplePasswordManager.exe should run on Windows 10 and 11 machines that match your architecture (e.g., 64‑bit → 64‑bit). You can copy that single .exe to other PCs; the SQLite DB (passwords.db) will be created alongside the EXE on first run.
