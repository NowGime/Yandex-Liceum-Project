import sqlite3
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget,
)

DB_NAME = "hospital.db"

DEFAULT_USERS = [
    ("admin", "admin123", "admin"),
    ("doctor", "doctor123", "doctor"),
    ("nurse", "nurse123", "nurse"),
]


def init_users_table():
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   login TEXT UNIQUE NOT NULL,
                   password TEXT NOT NULL,
                   role TEXT NOT NULL
               )"""
        )
        if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO users (login, password, role) VALUES (?, ?, ?)",
                DEFAULT_USERS,
            )
        con.commit()


def authenticate(login, password):
    with sqlite3.connect(DB_NAME) as con:
        row = con.execute(
            "SELECT role FROM users WHERE login = ? AND password = ?",
            (login, password),
        ).fetchone()
    return row[0] if row else None


class LoginWindow(QWidget):
    logged_in = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Больница - вход")
        self.setFixedSize(340, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(10)

        title = QLabel("Авторизация")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #000000;")
        layout.addWidget(title)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Логин")
        layout.addWidget(self.login_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.try_login)
        layout.addWidget(self.password_input)

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("color: #b71c1c; font-weight: bold;")
        layout.addWidget(self.error_label)

        self.login_button = QPushButton("Войти")
        self.login_button.clicked.connect(self.try_login)
        layout.addWidget(self.login_button)

        self.setStyleSheet(
            """
            QWidget { background-color: #ffffff; color: #000000; font-size: 16px; }
            QLabel { color: #000000; }
            QLineEdit {
                padding: 10px; border: 2px solid #455a64;
                background-color: #ffffff; color: #000000;
                selection-background-color: #2e86de; selection-color: #ffffff;
            }
            QLineEdit:focus { border: 2px solid #1565c0; }
            QPushButton {
                padding: 11px; border: none;
                background-color: #1565c0; color: #ffffff; font-weight: bold;
            }
            QPushButton:hover { background-color: #0d47a1; }
            """
        )

    def try_login(self):
        login = self.login_input.text().strip()
        password = self.password_input.text()

        if not login or not password:
            self.error_label.setText("Введите логин и пароль")
            return

        role = authenticate(login, password)
        if role is None:
            self.error_label.setText("Неверный логин или пароль")
            self.password_input.clear()
            return

        self.error_label.setText("")
        self.logged_in.emit(login, role)


if __name__ == "__main__":
    init_users_table()
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
