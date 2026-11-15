import sqlite3
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QDialog, QDialogButtonBox, QFormLayout,
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

        self.inputs = []
        form = QFormLayout()
        for i, name in enumerate(COLUMNS):
            line = QLineEdit()
            if values:
                line.setText(values[i])
            form.addRow(name + ":", line)
            self.inputs.append(line)

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

    def validate(self):
        if any(not line.text().strip() for line in self.inputs):
            self.error_label.setText("Заполните все поля")
            return
        self.accept()

    def get_values(self):
        return [line.text().strip() for line in self.inputs]


class MainWindow(QWidget):
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
        buttons.addStretch()
        layout.addLayout(buttons)

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
        self.login_window = LoginWindow()
        self.login_window.logged_in.connect(self.open_main_window)
        self.main_window = None

    def open_main_window(self, login, role):
        self.main_window = MainWindow(login, role)
        self.main_window.show()
        self.login_window.close()

    def start(self):
        self.login_window.show()


if __name__ == "__main__":
    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(STYLE)
    app = App()
    app.start()
    sys.exit(qt_app.exec())