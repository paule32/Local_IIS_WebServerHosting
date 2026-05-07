# ---------------------------------------------------------------------------------------
# file: timewindow_dialog.py
# author: (c) 2026 Jens Kallup - paule32
# all rights reserved.
# ---------------------------------------------------------------------------------------
import os
from copy import deepcopy
from datetime import date

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit,
    QComboBox, QMessageBox
)


DAYS = [
    ("MO", "Montag"),
    ("TU", "Dienstag"),
    ("WE", "Mittwoch"),
    ("TH", "Donnerstag"),
    ("FR", "Freitag"),
    ("SA", "Samstag"),
    ("SU", "Sonntag"),
]

ACTIVE_BG   = QColor( 70, 120,  70)
ACTIVE_FG   = QColor(255, 255, 255)
INACTIVE_BG = QColor( 35,  35,  35)
INACTIVE_FG = QColor(210, 210, 210)


def slot_label(index):
    hour = index // 2
    return str(hour) if index % 2 == 0 else f"{hour}:30"


def slot_time(index):
    hour = index // 2
    minute = 30 if index % 2 else 0
    return f"{hour:02d}:{minute:02d}"


def normalize_slot(value):
    return 1 if str(value or "").lower() in ("1", "true", "yes", "allowed", "on") else 0


def empty_week_grid():
    return [[0 for _ in range(48)] for _ in range(7)]


def normalize_rules_data(data):
    data = data or {}
    selected_date = str(data.get("date") or date.today().isoformat())
    grid = deepcopy(data.get("grid") or empty_week_grid())

    if len(grid) != 7:
        grid = empty_week_grid()

    fixed_grid = []

    for row in grid[:7]:
        row_values = list(row or [])
        if len(row_values) < 48:
            row_values += [0] * (48 - len(row_values))
        fixed_grid.append([normalize_slot(value) for value in row_values[:48]])

    return {"date": selected_date, "grid": fixed_grid}


def time_text_to_slot(text):
    text = str(text or "00:00").strip()

    if ":" not in text:
        hour = int(text)
        minute = 0
    else:
        hour_text, minute_text = text.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)

    hour = max(0, min(23, hour))
    minute = 30 if minute >= 30 else 0
    return max(0, min(47, hour * 2 + (1 if minute else 0)))


def week_grid_to_ranges(grid):
    ranges = []

    for day_index, row in enumerate(grid):
        col = 0
        while col < 48:
            if not row[col]:
                col += 1
                continue

            start = col
            while col < 48 and row[col]:
                col += 1

            end = col
            ranges.append({
                "enabled": True,
                "mode": "allowed",
                "day": DAYS[day_index][0],
                "from": slot_time(start),
                "to": "24:00" if end >= 48 else slot_time(end),
            })

    return ranges


def ranges_to_week_grid(ranges):
    grid = empty_week_grid()
    day_map = {name: idx for idx, (name, _caption) in enumerate(DAYS)}

    for rule in ranges or []:
        if not rule.get("enabled", True):
            continue
        if rule.get("mode", "allowed") != "allowed":
            continue

        day = str(rule.get("day") or "").upper()
        row = day_map.get(day)

        if row is None:
            continue

        start = time_text_to_slot(rule.get("from", "00:00"))
        end_text = str(rule.get("to", "00:00"))
        end = 48 if end_text == "24:00" else time_text_to_slot(end_text)

        for col in range(max(0, start), min(48, end)):
            grid[row][col] = 1

    return grid


def get_project_rules_container(project_data, system_name=None):
    if system_name:
        for user in project_data.get("user_management", {}).get("users", []):
            if user.get("system_name") == system_name or user.get("name") == system_name:
                settings = user.setdefault("settings", {})
                return settings.setdefault("website", {})

    return project_data.setdefault("availability_rules", {})


def get_rules_data(project_data, system_name=None):
    container = get_project_rules_container(project_data, system_name)

    if "availability_grid" in container:
        return normalize_rules_data(container.get("availability_grid"))

    if "availability_rules" in container:
        return normalize_rules_data({
            "date": container.get("availability_date") or date.today().isoformat(),
            "grid": ranges_to_week_grid(container.get("availability_rules")),
        })

    return normalize_rules_data({})


def set_rules_data(project_data, rules_data, system_name=None):
    rules_data = normalize_rules_data(rules_data)
    container = get_project_rules_container(project_data, system_name)

    container["availability_grid"] = rules_data
    container["availability_rules"] = week_grid_to_ranges(rules_data["grid"])
    container["availability_date"] = rules_data["date"]


def website_display_name(user):
    system_name = user.get("system_name") or user.get("name") or ""
    website = user.get("settings", {}).get("website", {})
    host_name = website.get("host_name") or website.get("hostname") or ""

    if host_name:
        return f"{system_name} - {host_name}"

    return system_name or "<unknown>"


def collect_client_websites(project_data):
    items = []

    for user in project_data.get("user_management", {}).get("users", []):
        system_name = user.get("system_name") or user.get("name") or ""

        if not system_name:
            continue

        items.append({
            "system_name": system_name,
            "caption": website_display_name(user),
        })

    items.sort(key=lambda item: item["caption"].lower())
    return items



class AvailabilityGrid(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(7, 48, parent)

        self._dragging = False
        self._drag_value = 1

        self.setFont(QFont("Arial", 10))
        self.setSelectionMode(QTableWidget.NoSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setMouseTracking(True)

        self.setHorizontalHeaderLabels([slot_label(i) for i in range(48)])
        self.setVerticalHeaderLabels([caption for _key, caption in DAYS])

        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        for col in range(48):
            self.setColumnWidth(col, 42)

        for row in range(7):
            self.setRowHeight(row, 26)

        self.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.verticalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.build_items()

    def build_items(self):
        for row in range(7):
            for col in range(48):
                item = QTableWidgetItem("")
                item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, 0)
                self.setItem(row, col, item)
                self.apply_cell_style(item, 0)

    def apply_cell_style(self, item, value):
        value = normalize_slot(value)
        item.setData(Qt.UserRole, value)

        if value:
            item.setText("●")
            item.setBackground(QBrush(ACTIVE_BG))
            item.setForeground(QBrush(ACTIVE_FG))
        else:
            item.setText("")
            item.setBackground(QBrush(INACTIVE_BG))
            item.setForeground(QBrush(INACTIVE_FG))

    def set_cell_value(self, row, col, value):
        item = self.item(row, col)

        if item is None:
            return

        self.apply_cell_style(item, value)

        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "mark_dirty"):
                parent.mark_dirty()
                break
            parent = parent.parent()

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())

        if item is not None and event.button() == Qt.LeftButton:
            current = normalize_slot(item.data(Qt.UserRole))
            self._dragging = True
            self._drag_value = 0 if current else 1
            self.set_cell_value(item.row(), item.column(), self._drag_value)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            item = self.itemAt(event.pos())
            if item is not None:
                self.set_cell_value(item.row(), item.column(), self._drag_value)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        super().mouseReleaseEvent(event)

    def set_grid(self, grid):
        grid = normalize_rules_data({"grid": grid}).get("grid")

        for row in range(7):
            for col in range(48):
                item = self.item(row, col)
                if item:
                    self.apply_cell_style(item, grid[row][col])

    def grid(self):
        result = empty_week_grid()

        for row in range(7):
            for col in range(48):
                item = self.item(row, col)
                result[row][col] = normalize_slot(item.data(Qt.UserRole)) if item else 0

        return result


class TimeWindowRules(QWidget):
    def __init__(self, main_window, project_data, project_file=None, system_name=None, parent=None):
        super().__init__(parent)

        self.main_window = main_window
        self.project_file = project_file
        self.project_data = project_data
        self.system_name = system_name
        self._dirty = False
        self._switching_site = False

        if not self.system_name:
            sites = collect_client_websites(project_data)
            if sites:
                self.system_name = sites[0]["system_name"]

        self._saved_data = get_rules_data(project_data, self.system_name)

        self.setObjectName("TimeWindoRules")
        self.build_ui()
        self.load_data(self._saved_data)

    def build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("Startdatum:", self))

        self.date_edit = QDateEdit(self)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.dateChanged.connect(lambda _date: self.mark_dirty())
        top.addWidget(self.date_edit)

        top.addStretch(1)

        self.select_all_button = QPushButton("All", self)
        self.clear_button = QPushButton("Clear", self)
        self.invert_button = QPushButton("Invert", self)
        self.save_button = QPushButton("Save", self)

        top.addWidget(self.select_all_button)
        top.addWidget(self.clear_button)
        top.addWidget(self.invert_button)
        top.addWidget(self.save_button)

        layout.addLayout(top)

        self.grid_widget = AvailabilityGrid(self)
        layout.addWidget(self.grid_widget, 1)

        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("Client Website:", self))

        self.website_combo = QComboBox(self)
        self.website_combo.setFont(QFont("Consolas", 10))
        self.website_combo.setMinimumWidth(320)
        bottom.addWidget(self.website_combo, 1)

        layout.addLayout(bottom)

        hint = QLabel(
            "Maus: Zelle anklicken und ziehen, um 30-Minuten-Zeitfenster zu setzen oder zu entfernen.",
            self,
        )
        layout.addWidget(hint)

        self.select_all_button.clicked.connect(self.select_all)
        self.clear_button.clicked.connect(self.clear_all)
        self.invert_button.clicked.connect(self.invert_all)
        self.save_button.clicked.connect(self.save_changes)
        self.website_combo.currentIndexChanged.connect(self.on_website_changed)
        self.fill_website_combo()

    def fill_website_combo(self):
        self.website_combo.blockSignals(True)
        self.website_combo.clear()

        sites = collect_client_websites(self.project_data)

        for item in sites:
            self.website_combo.addItem(item["caption"], item["system_name"])

        if self.system_name:
            index = self.website_combo.findData(self.system_name)
            if index >= 0:
                self.website_combo.setCurrentIndex(index)

        self.website_combo.blockSignals(False)

    def ask_save_current_changes(self, target_system_name=None):
        if not self._dirty:
            return True

        result = QMessageBox.question(
            self,
            "Zeitfenster speichern",
            "Es wurden Änderungen an den Zeitfenstern vorgenommen.\n\n"
            "Sollen die Daten gespeichert werden?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )

        if result == QMessageBox.Yes:
            self.save_changes(target_system_name or self.system_name)
            return True

        if result == QMessageBox.No:
            self.load_data(self._saved_data)
            self._dirty = False
            return True

        self.setFocus(Qt.OtherFocusReason)
        self.activateWindow()
        return False

    def on_website_changed(self, index):
        if self._switching_site:
            return

        new_system_name = self.website_combo.itemData(index)

        if not new_system_name or new_system_name == self.system_name:
            return

        old_system_name = self.system_name

        # Wichtig:
        # Erst die Daten der bisherigen Website speichern/verwerfen,
        # danach erst zur neuen Website wechseln.
        if not self.ask_save_current_changes(old_system_name):
            self._switching_site = True
            old_index = self.website_combo.findData(old_system_name)

            if old_index >= 0:
                self.website_combo.setCurrentIndex(old_index)

            self._switching_site = False
            return

        self.system_name = new_system_name
        self._saved_data = get_rules_data(self.project_data, self.system_name)
        self.load_data(self._saved_data)

    def mark_dirty(self):
        self._dirty = True

    def load_data(self, data):
        data = normalize_rules_data(data)
        qdate = QDate.fromString(data["date"], "yyyy-MM-dd")

        if not qdate.isValid():
            qdate = QDate.currentDate()

        self.date_edit.blockSignals(True)
        self.date_edit.setDate(qdate)
        self.date_edit.blockSignals(False)

        self.grid_widget.set_grid(data["grid"])
        self._dirty = False

    def current_data(self):
        return normalize_rules_data({
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "grid": self.grid_widget.grid(),
        })

    def select_all(self):
        self.grid_widget.set_grid([[1 for _ in range(48)] for _ in range(7)])
        self.mark_dirty()

    def clear_all(self):
        self.grid_widget.set_grid(empty_week_grid())
        self.mark_dirty()

    def invert_all(self):
        grid = self.grid_widget.grid()

        for row in range(7):
            for col in range(48):
                grid[row][col] = 0 if grid[row][col] else 1

        self.grid_widget.set_grid(grid)
        self.mark_dirty()

    def save_changes(self, system_name=None):
        target_system_name = system_name or self.system_name

        data = self.current_data()
        set_rules_data(self.project_data, data, target_system_name)

        if hasattr(self.main_window, "save_project_file") and self.project_file:
            self.main_window.save_project_file(self.project_file, self.project_data)

        if target_system_name == self.system_name:
            self._saved_data = deepcopy(data)
            self._dirty = False

    def closeEvent(self, event):
        if self.ask_save_current_changes():
            event.accept()
            return

        event.ignore()


def open_availability_rules_dialog(main_window, project_data, project_file=None, system_name=None):
    widget = TimeWindowRules(main_window, project_data, project_file, system_name)
    title = "Availability Rules"

    if system_name:
        title += f" [{system_name}]"

    if hasattr(main_window, "add_mdi_widget"):
        sub = main_window.add_mdi_widget(widget, title, 800, 420)
        sub.project_file = os.path.abspath(project_file) if project_file else ""
        sub.window_role = "availability_rules"
        return sub

    widget.resize(800, 420)
    widget.show()
    return widget
