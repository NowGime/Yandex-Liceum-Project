import sqlite3
import sys

from PyQt6.QtCore import QDate, QRegularExpression, Qt, pyqtSignal
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDateEdit, QDialog,
    QDialogButtonBox, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from auth_window import DB_NAME, LoginWindow, init_users_table

ROLE_NAMES = {
    "admin": "Администратор",
    "doctor": "Врач",
    "nurse": "Медсестра",
}

PERMISSIONS = {
    "admin": {"add": True, "edit": True, "delete": True},
    "doctor": {"add": True, "edit": True, "delete": False},
    "nurse": {"add": False, "edit": False, "delete": False},
}

PROTECTED_USERS = ("admin", "doctor", "nurse")

DATE_FORMAT = "dd.MM.yyyy"

COLUMNS = ["ФИО", "Дата рождения", "Диагноз", "Палата", "Дата поступления"]

SAMPLE_PATIENTS = [
    ("Иванов Иван Иванович", "12.03.1985", "Гипертония", "101", "01.11.2026"),
    ("Петрова Анна Сергеевна", "25.07.1990", "Бронхит", "102", "03.11.2026"),
    ("Сидоров Пётр Алексеевич", "08.12.1972", "Перелом руки", "205", "05.11.2026"),
]

STYLE = """
    QWidget { background-color: #ffffff; color: #000000; font-size: 16px; }
    QLabel { color: #000000; }
    QLineEdit {
        padding: 8px; border: 2px solid #455a64;
        background-color: #ffffff; color: #000000;
        selection-background-color: #1565c0; selection-color: #ffffff;
    }
    QLineEdit:focus { border: 2px solid #1565c0; }
    QPushButton {
        padding: 9px 18px; border: none;
        background-color: #1565c0; color: #ffffff; font-weight: bold;
    }
    QPushButton:hover { background-color: #0d47a1; }
    QPushButton:disabled { background-color: #90a4ae; }
    QTableWidget {
        border: 2px solid #455a64; gridline-color: #b0bec5;
        background-color: #ffffff; color: #000000;
        selection-background-color: #1565c0; selection-color: #ffffff;
    }
    QTableWidget::item:selected {
        background-color: #1565c0; color: #ffffff;
    }
    QTableWidget::item:selected:!active {
        background-color: #1565c0; color: #ffffff;
    }
    QComboBox, QDateEdit {
        padding: 8px; border: 2px solid #455a64;
        background-color: #ffffff; color: #000000;
    }
    QCalendarWidget QWidget { background-color: #ffffff; color: #000000; }
    QCalendarWidget QToolButton {
        background-color: #263238; color: #ffffff; padding: 4px;
    }
    QCalendarWidget QAbstractItemView {
        background-color: #ffffff; color: #000000;
        selection-background-color: #1565c0; selection-color: #ffffff;
    }
    QComboBox QAbstractItemView {
        background-color: #ffffff; color: #000000;
        selection-background-color: #1565c0; selection-color: #ffffff;
    }
    QHeaderView::section {
        background-color: #263238; color: #ffffff;
        padding: 6px; border: none; font-weight: bold;
    }
"""


def init_patients_table():
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS patients (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   full_name TEXT NOT NULL,
                   birth_date TEXT NOT NULL,
                   diagnosis TEXT NOT NULL,
                   ward TEXT NOT NULL,
                   admission_date TEXT NOT NULL
               )"""
        )
        if cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 0:
            cur.executemany(
                """INSERT INTO patients
                   (full_name, birth_date, diagnosis, ward, admission_date)
                   VALUES (?, ?, ?, ?, ?)""",
                SAMPLE_PATIENTS,
            )
        con.commit()


class PatientDialog(QDialog):
    def __init__(self, parent=None, values=None):
        super().__init__(parent)
        self.setWindowTitle("Пациент")
        self.setMinimumWidth(420)

        self.name_input = QLineEdit()
        self.birth_input = self.make_date_edit()
        self.diagnosis_input = QLineEdit()
        self.ward_input = QLineEdit()
        self.ward_input.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d{0,4}"))
        )
        self.admission_input = self.make_date_edit()

        if values:
            self.name_input.setText(values[0])
            self.birth_input.setDate(QDate.fromString(values[1], DATE_FORMAT))
            self.diagnosis_input.setText(values[2])
            self.ward_input.setText(values[3])
            self.admission_input.setDate(QDate.fromString(values[4], DATE_FORMAT))
        else:
            self.birth_input.setDate(QDate(2000, 1, 1))
            self.admission_input.setDate(QDate.currentDate())

        self.inputs = [
            self.name_input, self.birth_input, self.diagnosis_input,
            self.ward_input, self.admission_input,
        ]
        form = QFormLayout()
        for name, widget in zip(COLUMNS, self.inputs):
            form.addRow(name + ":", widget)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b71c1c; font-weight: bold;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(buttons)

    def make_date_edit(self):
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat(DATE_FORMAT)
        date_edit.setMinimumDate(QDate(1900, 1, 1))
        date_edit.setMaximumDate(QDate.currentDate())
        return date_edit

    def validate(self):
        if (
            not self.name_input.text().strip()
            or not self.diagnosis_input.text().strip()
            or not self.ward_input.text().strip()
        ):
            self.error_label.setText("Заполните все поля")
            return
        if self.admission_input.date() < self.birth_input.date():
            self.error_label.setText("Дата поступления раньше даты рождения")
            return
        self.accept()

    def get_values(self):
        return [
            self.name_input.text().strip(),
            self.birth_input.date().toString(DATE_FORMAT),
            self.diagnosis_input.text().strip(),
            self.ward_input.text().strip(),
            self.admission_input.date().toString(DATE_FORMAT),
        ]


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Регистрация пользователя")
        self.setMinimumWidth(380)

        self.login_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.role_box = QComboBox()
        for role, name in ROLE_NAMES.items():
            self.role_box.addItem(name, role)

        form = QFormLayout()
        form.addRow("Логин:", self.login_input)
        form.addRow("Пароль:", self.password_input)
        form.addRow("Роль:", self.role_box)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b71c1c; font-weight: bold;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Создать")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.register)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(buttons)

    def register(self):
        login = self.login_input.text().strip()
        password = self.password_input.text()
        role = self.role_box.currentData()

        if not login or not password:
            self.error_label.setText("Заполните логин и пароль")
            return

        try:
            with sqlite3.connect(DB_NAME) as con:
                con.execute(
                    "INSERT INTO users (login, password, role) VALUES (?, ?, ?)",
                    (login, password, role),
                )
                con.commit()
        except sqlite3.IntegrityError:
            self.error_label.setText("Такой логин уже существует")
            return

        self.accept()


class DeleteUserDialog(QDialog):
    def __init__(self, parent, logins):
        super().__init__(parent)
        self.setWindowTitle("Удаление пользователя")
        self.setMinimumWidth(380)

        self.user_box = QComboBox()
        self.user_box.addItems(logins)

        form = QFormLayout()
        form.addRow("Пользователь:", self.user_box)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Удалить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def selected_login(self):
        return self.user_box.currentText()


class MainWindow(QWidget):
    logged_out = pyqtSignal()

    def __init__(self, login, role):
        super().__init__()
        self.login = login
        self.role = role
        self.rights = PERMISSIONS.get(role, PERMISSIONS["nurse"])
        self.setWindowTitle("Больница - пациенты")
        self.resize(900, 520)
        self.init_ui()
        self.load_patients()

    def init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel(f"Пользователь: {ROLE_NAMES.get(self.role, self.role)}")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        if self.rights["add"]:
            add_button = QPushButton("Добавить")
            add_button.clicked.connect(self.add_patient)
            buttons.addWidget(add_button)
        if self.rights["edit"]:
            edit_button = QPushButton("Изменить")
            edit_button.clicked.connect(self.edit_patient)
            buttons.addWidget(edit_button)
        if self.rights["delete"]:
            delete_button = QPushButton("Удалить")
            delete_button.clicked.connect(self.delete_patient)
            buttons.addWidget(delete_button)
        if self.role == "admin":
            register_button = QPushButton("Новый пользователь")
            register_button.clicked.connect(self.register_user)
            buttons.addWidget(register_button)
            delete_user_button = QPushButton("Удалить пользователя")
            delete_user_button.clicked.connect(self.delete_user)
            buttons.addWidget(delete_user_button)
        buttons.addStretch()
        logout_button = QPushButton("Выйти из аккаунта")
        logout_button.clicked.connect(self.logout)
        buttons.addWidget(logout_button)
        layout.addLayout(buttons)

    def register_user(self):
        dialog = RegisterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "Готово", "Пользователь создан")

    def delete_user(self):
        placeholders = ", ".join("?" for _ in PROTECTED_USERS)
        with sqlite3.connect(DB_NAME) as con:
            rows = con.execute(
                f"SELECT login FROM users WHERE login NOT IN ({placeholders}) "
                "AND login != ? ORDER BY login",
                PROTECTED_USERS + (self.login,),
            ).fetchall()

        logins = [row[0] for row in rows]
        if not logins:
            QMessageBox.information(
                self, "Удаление", "Нет созданных пользователей для удаления"
            )
            return

        dialog = DeleteUserDialog(self, logins)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        login = dialog.selected_login()
        answer = QMessageBox.question(
            self, "Удаление", f"Удалить пользователя {login}?"
        )
        if answer == QMessageBox.StandardButton.Yes:
            with sqlite3.connect(DB_NAME) as con:
                con.execute("DELETE FROM users WHERE login = ?", (login,))
                con.commit()
            QMessageBox.information(self, "Готово", "Пользователь удалён")

    def logout(self):
        self.logged_out.emit()
        self.close()

    def load_patients(self):
        with sqlite3.connect(DB_NAME) as con:
            rows = con.execute(
                """SELECT id, full_name, birth_date, diagnosis, ward,
                          admission_date FROM patients ORDER BY full_name"""
            ).fetchall()

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row[1:]):
                item = QTableWidgetItem(str(value))
                if c == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row[0])
                self.table.setItem(r, c, item)

    def selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите пациента в таблице")
            return None
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def add_patient(self):
        dialog = PatientDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            with sqlite3.connect(DB_NAME) as con:
                con.execute(
                    """INSERT INTO patients
                       (full_name, birth_date, diagnosis, ward, admission_date)
                       VALUES (?, ?, ?, ?, ?)""",
                    dialog.get_values(),
                )
                con.commit()
            self.load_patients()

    def edit_patient(self):
        patient_id = self.selected_id()
        if patient_id is None:
            return
        row = self.table.currentRow()
        values = [self.table.item(row, c).text() for c in range(len(COLUMNS))]
        dialog = PatientDialog(self, values)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            with sqlite3.connect(DB_NAME) as con:
                con.execute(
                    """UPDATE patients SET full_name = ?, birth_date = ?,
                       diagnosis = ?, ward = ?, admission_date = ?
                       WHERE id = ?""",
                    dialog.get_values() + [patient_id],
                )
                con.commit()
            self.load_patients()

    def delete_patient(self):
        patient_id = self.selected_id()
        if patient_id is None:
            return
        answer = QMessageBox.question(
            self, "Удаление", "Удалить выбранного пациента?"
        )
        if answer == QMessageBox.StandardButton.Yes:
            with sqlite3.connect(DB_NAME) as con:
                con.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
                con.commit()
            self.load_patients()


class App:
    def __init__(self):
        init_users_table()
        init_patients_table()
        self.login_window = None
        self.main_window = None

    def show_login(self):
        self.login_window = LoginWindow()
        self.login_window.logged_in.connect(self.open_main_window)
        self.login_window.show()

    def open_main_window(self, login, role):
        self.main_window = MainWindow(login, role)
        self.main_window.logged_out.connect(self.show_login)
        self.main_window.show()
        self.login_window.close()

    def start(self):
        self.show_login()


if __name__ == "__main__":
    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(STYLE)
    app = App()
    app.start()
    sys.exit(qt_app.exec())
