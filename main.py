from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import db
from crypto_utils import build_fernet, encrypt_password, decrypt_password, generate_salt


class MasterPasswordDialog(QDialog):
    def __init__(self, has_existing_salt: bool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Unlock Vault")
        self.setModal(True)
        self.password: Optional[str] = None

        self._build_ui(has_existing_salt)

    def _build_ui(self, has_existing_salt: bool) -> None:
        layout = QVBoxLayout(self)

        label_text = (
            "Enter your master password to unlock the vault."
            if has_existing_salt
            else (
                "Create a new master password.\n\n"
                "You must remember this password – it cannot be recovered."
            )
        )
        label = QLabel(label_text)
        label.setWordWrap(True)
        layout.addWidget(label)

        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.returnPressed.connect(self.accept)
        layout.addWidget(self.edit)

        button_row = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addStretch(1)
        button_row.addWidget(ok_btn)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self.resize(380, 150)

    def accept(self) -> None:
        text = self.edit.text().strip()
        if not text:
            QMessageBox.warning(self, "Missing password", "Please enter a master password.")
            return
        self.password = text
        super().accept()


class AccountDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        service: str = "",
        username: str = "",
        password: str = "",
        notes: str = "",
        require_confirm: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Account")
        self.service = service
        self.username = username
        self.password = password
        self.notes = notes
        self.require_confirm = require_confirm

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QGridLayout(self)

        row = 0
        layout.addWidget(QLabel("Service"), row, 0)
        self.service_edit = QLineEdit(self.service)
        layout.addWidget(self.service_edit, row, 1)

        row += 1
        layout.addWidget(QLabel("Username"), row, 0)
        self.username_edit = QLineEdit(self.username)
        layout.addWidget(self.username_edit, row, 1)

        row += 1
        layout.addWidget(QLabel("Password"), row, 0)
        self.password_edit = QLineEdit(self.password)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_edit, row, 1)

        if self.require_confirm:
            row += 1
            layout.addWidget(QLabel("Confirm password"), row, 0)
            self.password_confirm_edit = QLineEdit()
            self.password_confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(self.password_confirm_edit, row, 1)
        else:
            self.password_confirm_edit = None

        row += 1
        layout.addWidget(QLabel("Notes"), row, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        self.notes_edit = QTextEdit(self.notes)
        layout.addWidget(self.notes_edit, row, 1)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)

        row += 1
        layout.addLayout(buttons, row, 0, 1, 2)
        self.resize(420, 260)

    def _on_save(self) -> None:
        service = self.service_edit.text().strip()
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        notes = self.notes_edit.toPlainText().strip()

        if not service or not username or not password:
            QMessageBox.warning(self, "Missing data", "Service, username and password are required.")
            return

        if self.require_confirm and self.password_confirm_edit is not None:
            confirm_pw = self.password_confirm_edit.text()
            if password != confirm_pw:
                QMessageBox.warning(self, "Password mismatch", "Passwords do not match.")
                return

        self.service = service
        self.username = username
        self.password = password
        self.notes = notes
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, fernet, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.fernet = fernet
        self.setWindowTitle("Simple Password Manager")
        self.resize(720, 420)

        self._build_ui()
        self.refresh_table()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        # Top search & actions
        top_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by service or username…")
        self.search_edit.textChanged.connect(self.refresh_table)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_account)
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self.edit_selected)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_selected)
        copy_btn = QPushButton("Copy Password")
        copy_btn.clicked.connect(self.copy_password)

        top_row.addWidget(self.search_edit, 4)
        top_row.addWidget(add_btn)
        top_row.addWidget(edit_btn)
        top_row.addWidget(delete_btn)
        top_row.addWidget(copy_btn)
        layout.addLayout(top_row)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Service", "Username", "Notes", "Last Modified"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.setCentralWidget(central)

        # Light modern style tweaks
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                font-size: 11pt;
            }
            QLineEdit, QTextEdit {
                padding: 6px;
                border-radius: 4px;
                border: 1px solid #cccccc;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #4a90e2;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                background-color: #4a90e2;
                color: white;
            }
            QPushButton:hover {
                background-color: #3a7bc4;
            }
            QPushButton:disabled {
                background-color: #bbbbbb;
            }
            QTableWidget {
                gridline-color: #e0e0e0;
            }
            """
        )

    # Data helpers
    def _current_account_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        return int(item.data(QtCore.Qt.ItemDataRole.UserRole))

    def refresh_table(self) -> None:
        search = self.search_edit.text().strip()
        accounts = db.list_accounts(search)

        self.table.setRowCount(0)
        for row_index, (acc_id, service, username, _pw, notes, _created_at, updated_at) in enumerate(accounts):
            self.table.insertRow(row_index)
            service_item = QTableWidgetItem(service)
            # store id in user data
            service_item.setData(QtCore.Qt.ItemDataRole.UserRole, acc_id)
            username_item = QTableWidgetItem(username)
            notes_item = QTableWidgetItem(notes or "")
            self.table.setItem(row_index, 0, service_item)
            self.table.setItem(row_index, 1, username_item)
            self.table.setItem(row_index, 2, notes_item)
            updated_item = QTableWidgetItem(updated_at)
            self.table.setItem(row_index, 3, updated_item)

        self.table.resizeColumnsToContents()

    # CRUD + actions
    def add_account(self) -> None:
        dlg = AccountDialog(self, require_confirm=True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            enc_pw = encrypt_password(self.fernet, dlg.password)
            db.add_account(dlg.service, dlg.username, enc_pw, dlg.notes)
            self.refresh_table()

    def edit_selected(self) -> None:
        acc_id = self._current_account_id()
        if acc_id is None:
            QMessageBox.information(self, "No selection", "Select an account to edit.")
            return

        # Load account row from db
        accounts = db.list_accounts()
        current = next((a for a in accounts if a[0] == acc_id), None)
        if not current:
            QMessageBox.warning(self, "Not found", "Account not found.")
            return

        _, service, username, enc_pw, notes, _created_at, _updated_at = current
        try:
            password = decrypt_password(self.fernet, enc_pw)
        except Exception:
            QMessageBox.critical(
                self,
                "Decryption error",
                "Could not decrypt password. Is the master password correct?",
            )
            return

        dlg = AccountDialog(
            self,
            service=service,
            username=username,
            password=password,
            notes=notes or "",
            require_confirm=False,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_enc_pw = encrypt_password(self.fernet, dlg.password)
            db.update_account(acc_id, dlg.service, dlg.username, new_enc_pw, dlg.notes)
            self.refresh_table()

    def delete_selected(self) -> None:
        acc_id = self._current_account_id()
        if acc_id is None:
            QMessageBox.information(self, "No selection", "Select an account to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete account",
            "Are you sure you want to delete this account?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            db.delete_account(acc_id)
            self.refresh_table()

    def copy_password(self) -> None:
        acc_id = self._current_account_id()
        if acc_id is None:
            QMessageBox.information(self, "No selection", "Select an account first.")
            return

        accounts = db.list_accounts()
        current = next((a for a in accounts if a[0] == acc_id), None)
        if not current:
            QMessageBox.warning(self, "Not found", "Account not found.")
            return

        _, _service, _username, enc_pw, _notes, _created_at, _updated_at = current
        try:
            pw = decrypt_password(self.fernet, enc_pw)
        except Exception:
            QMessageBox.critical(
                self,
                "Decryption error",
                "Could not decrypt password. Is the master password correct?",
            )
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(pw)
        QMessageBox.information(
            self,
            "Copied",
            "Password copied to clipboard.\nIt will remain there until you copy something else.",
        )


def create_app() -> QApplication:
    import sys

    app = QApplication(sys.argv)
    app.setApplicationName("Simple Password Manager")
    app.setWindowIcon(QtGui.QIcon())  # placeholder, no icon file
    return app


def main() -> None:
    import sys

    app = create_app()

    db.init_db()

    salt, verifier = db.get_settings()
    has_existing_salt = salt is not None

    fernet = None

    while True:
        dlg = MasterPasswordDialog(has_existing_salt)
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.password is None:
            sys.exit(0)

        master_password = dlg.password

        if not has_existing_salt:
            # First-time setup: generate salt and verifier using this master password.
            salt = generate_salt()
            fernet = build_fernet(master_password, salt)
            verifier_token = encrypt_password(fernet, "master-password-verifier")
            db.set_settings(salt, verifier_token)
            has_existing_salt = True
            break

        # Existing vault: validate master password by decrypting stored verifier.
        assert salt is not None
        fernet_candidate = build_fernet(master_password, salt)
        stored_verifier = db.get_verifier()
        if stored_verifier is None:
            # Fallback: no verifier yet (older DB). Initialize it now and accept password.
            verifier_token = encrypt_password(fernet_candidate, "master-password-verifier")
            db.set_settings(salt, verifier_token)
            fernet = fernet_candidate
            break

        try:
            marker = decrypt_password(fernet_candidate, stored_verifier)
        except Exception:
            marker = None

        if marker == "master-password-verifier":
            fernet = fernet_candidate
            break

        QMessageBox.critical(
            None,
            "Invalid master password",
            "The master password is incorrect. Please try again.",
        )

    assert fernet is not None

    window = MainWindow(fernet)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()


