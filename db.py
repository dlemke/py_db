import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional


DB_PATH = Path("passwords.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            salt BLOB NOT NULL,
            verifier BLOB
        );
        """
    )

    # For existing databases created before verifier was added, try to add column.
    try:
        cur.execute("ALTER TABLE settings ADD COLUMN verifier BLOB;")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            username TEXT NOT NULL,
            password BLOB NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )

    # For existing databases created before timestamps were added, try to add columns.
    try:
        cur.execute(
            "ALTER TABLE accounts ADD COLUMN created_at TEXT NOT NULL DEFAULT (datetime('now'));"
        )
    except sqlite3.OperationalError:
        # Column already exists
        pass

    try:
        cur.execute(
            "ALTER TABLE accounts ADD COLUMN updated_at TEXT NOT NULL DEFAULT (datetime('now'));"
        )
    except sqlite3.OperationalError:
        # Column already exists
        pass

    conn.commit()
    conn.close()


def get_salt() -> Optional[bytes]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT salt FROM settings WHERE id = 1;")
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0]
    return None


def set_salt(salt: bytes) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM settings;")
    cur.execute("INSERT INTO settings (id, salt) VALUES (1, ?);", (salt,))
    conn.commit()
    conn.close()


def get_settings() -> Tuple[Optional[bytes], Optional[bytes]]:
    """
    Returns (salt, verifier).

    verifier is an encrypted marker used to validate the master password.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT salt, verifier FROM settings WHERE id = 1;")
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    return None, None


def set_settings(salt: bytes, verifier: bytes) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM settings;")
    cur.execute(
        "INSERT INTO settings (id, salt, verifier) VALUES (1, ?, ?);",
        (salt, verifier),
    )
    conn.commit()
    conn.close()


def get_verifier() -> Optional[bytes]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT verifier FROM settings WHERE id = 1;")
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0]
    return None


def list_accounts(
    search: str = "",
) -> List[Tuple[int, str, str, bytes, Optional[str], str, str]]:
    conn = get_connection()
    cur = conn.cursor()
    if search:
        pattern = f"%{search}%"
        cur.execute(
            """
            SELECT id, service, username, password, notes, created_at, updated_at
            FROM accounts
            WHERE service LIKE ? OR username LIKE ?
            ORDER BY service COLLATE NOCASE;
            """,
            (pattern, pattern),
        )
    else:
        cur.execute(
            """
            SELECT id, service, username, password, notes, created_at, updated_at
            FROM accounts
            ORDER BY service COLLATE NOCASE;
            """
        )
    rows = cur.fetchall()
    conn.close()
    return rows


def add_account(service: str, username: str, password: bytes, notes: str = "") -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO accounts (service, username, password, notes)
        VALUES (?, ?, ?, ?);
        """,
        (service, username, password, notes),
    )
    conn.commit()
    conn.close()


def update_account(
    account_id: int,
    service: str,
    username: str,
    password: bytes,
    notes: str = "",
) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE accounts
        SET service = ?, username = ?, password = ?, notes = ?, updated_at = datetime('now')
        WHERE id = ?;
        """,
        (service, username, password, notes, account_id),
    )
    conn.commit()
    conn.close()


def delete_account(account_id: int) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM accounts WHERE id = ?;", (account_id,))
    conn.commit()
    conn.close()


