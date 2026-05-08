# ---------------------------------------------------------------------------------------
# file: header_footer_dialog.py
# author: (c) 2026 Jens Kallup - paule32
# all rights reserved.
# ---------------------------------------------------------------------------------------
from __future__    import annotations
import os
from copy import deepcopy

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPlainTextEdit, QPushButton, QSplitter, QMessageBox
)


EDITOR_FONT = QFont("Consolas", 10)


def website_settings(user):
    settings = user.setdefault("settings", {})
    return settings.setdefault("website", {})


def collect_client_websites(project_data):
    items = []

    for user in project_data .get("user_management",    {}).get("users", []):
        system_name = user   .get("system_name") or    user.get("name")     or ""
        website     = user   .get("settings",           {}).get("website", {})
        host_name   = website.get("host_name")   or website.get("hostname") or ""

        if not system_name:
            continue

        if host_name:
            caption = f"{host_name}  [{system_name}]"
        else:
            caption = f"<kein Hostname>  [{system_name}]"

        items.append({
            "system_name": system_name,
            "host_name": host_name,
            "caption": caption,
        })

    items.sort(key=lambda item: item["caption"].lower())
    return items


def find_user(project_data, system_name):
    for user in project_data.get("user_management", {}).get("users", []):
        if user.get("system_name") == system_name or user.get("name") == system_name:
            return user
    return None


def get_header_footer(project_data, system_name):
    user = find_user(project_data, system_name)

    if not user:
        return {"header": "", "footer": ""}

    website = website_settings(user)

    return {
        "header": str(website.get("header", "")),
        "footer": str(website.get("footer", "")),
    }


def set_header_footer(project_data, system_name, header, footer):
    user = find_user(project_data, system_name)

    if not user:
        return False

    website = website_settings(user)
    website["header"] = str(header or "")
    website["footer"] = str(footer or "")
    return True


class WebsiteHeaderFooterWindow(QWidget):
    def __init__(self, main_window, project_data, project_file=None, system_name=None, parent=None):
        super().__init__(parent)

        self.main_window     = main_window
        self.project_file    = project_file
        self.project_data    = project_data
        self.system_name     = system_name
        
        self._dirty          = False
        self._loading        = False
        self._switching_site = False
        
        self._saved_data = {"header": "", "footer": ""}

        if not self.system_name:
            sites = collect_client_websites(self.project_data)
            if sites:
                self.system_name = sites[0]["system_name"]

        self.setObjectName("WebsiteHeaderFooterWindow")
        self.build_ui()
        self.load_current_site()

    def build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("Website:", self))

        self.website_combo = QComboBox(self)
        self.website_combo.setFont(QFont("Consolas", 10))
        self.website_combo.setMinimumWidth(360)
        top.addWidget(self.website_combo, 1)

        layout.addLayout(top)

        self.splitter = QSplitter(Qt.Vertical, self)

        header_page = QWidget(self)
        header_layout = QVBoxLayout(header_page)
        header_layout.setContentsMargins(0, 0, 0, 0)

        header_label = QLabel("Header:", header_page)
        self.header_edit = QPlainTextEdit(header_page)
        self.header_edit.setFont(EDITOR_FONT)
        self.header_edit.textChanged.connect(self.mark_dirty)

        header_layout.addWidget(header_label)
        header_layout.addWidget(self.header_edit, 1)

        footer_page = QWidget(self)
        footer_layout = QVBoxLayout(footer_page)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        footer_label = QLabel("Footer:", footer_page)
        self.footer_edit = QPlainTextEdit(footer_page)
        self.footer_edit.setFont(EDITOR_FONT)
        self.footer_edit.textChanged.connect(self.mark_dirty)

        footer_layout.addWidget(footer_label)
        footer_layout.addWidget(self.footer_edit, 1)

        self.splitter.addWidget(header_page)
        self.splitter.addWidget(footer_page)
        self.splitter.setSizes([280, 240])

        layout.addWidget(self.splitter, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)

        self.save_button = QPushButton("Save", self)
        self.apply_button = QPushButton("Apply", self)
        self.cancel_button = QPushButton("Cancel", self)

        buttons.addWidget(self.save_button)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.cancel_button)

        layout.addLayout(buttons)

        self.save_button.clicked.connect(self.save_and_close)
        self.apply_button.clicked.connect(self.apply_changes)
        self.cancel_button.clicked.connect(self.cancel_dialog)
        self.website_combo.currentIndexChanged.connect(self.on_website_changed)

        self.fill_website_combo()

    def fill_website_combo(self):
        self.website_combo.blockSignals(True)
        self.website_combo.clear()

        for item in collect_client_websites(self.project_data):
            self.website_combo.addItem(item["caption"], item["system_name"])

        if self.system_name:
            index = self.website_combo.findData(self.system_name)
            if index >= 0:
                self.website_combo.setCurrentIndex(index)

        self.website_combo.blockSignals(False)

    def mark_dirty(self):
        if self._loading:
            return
        self._dirty = True

    def current_data(self):
        return {
            "header": self.header_edit.toPlainText(),
            "footer": self.footer_edit.toPlainText(),
        }

    def load_current_site(self):
        self._loading = True
        data = get_header_footer(self.project_data, self.system_name)
        self._saved_data = deepcopy(data)
        self.header_edit.setPlainText(data.get("header", ""))
        self.footer_edit.setPlainText(data.get("footer", ""))
        self._dirty = False
        self._loading = False

    def save_changes(self, system_name=None):
        target_system_name = system_name or self.system_name
        data = self.current_data()

        ok = set_header_footer(
            self.project_data,
            target_system_name,
            data.get("header", ""),
            data.get("footer", ""),
        )

        if not ok:
            QMessageBox.warning(
                self,
                "Header/Footer",
                "Die ausgewählte Website konnte nicht gefunden werden."
            )
            return False

        if hasattr(self.main_window, "save_project_file") and self.project_file:
            self.main_window.save_project_file(self.project_file, self.project_data)

        if target_system_name == self.system_name:
            self._saved_data = deepcopy(data)
            self._dirty = False

        return True

    def ask_save_current_changes(self, target_system_name=None):
        if not self._dirty:
            return True

        result = QMessageBox.question(
            self,
            "Header/Footer speichern",
            "Es wurden Änderungen am Header oder Footer vorgenommen.\n\n"
            "Sollen die Daten gespeichert werden?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )

        if result == QMessageBox.Yes:
            return self.save_changes(target_system_name or self.system_name)

        if result == QMessageBox.No:
            self._loading = True
            self.header_edit.setPlainText(self._saved_data.get("header", ""))
            self.footer_edit.setPlainText(self._saved_data.get("footer", ""))
            self._loading = False
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

        if not self.ask_save_current_changes(old_system_name):
            self._switching_site = True
            old_index = self.website_combo.findData(old_system_name)
            if old_index >= 0:
                self.website_combo.setCurrentIndex(old_index)
            self._switching_site = False
            return

        self.system_name = new_system_name
        self.load_current_site()

    def apply_changes(self):
        self.save_changes(self.system_name)

    def save_and_close(self):
        if self.save_changes(self.system_name):
            self.close()

    def cancel_dialog(self):
        if self.ask_save_current_changes(self.system_name):
            self.close()

    def closeEvent(self, event):
        if self.ask_save_current_changes(self.system_name):
            event.accept()
            return
        event.ignore()


def open_website_header_footer_dialog(main_window, project_file, project_data, system_name=None):
    widget = WebsiteHeaderFooterWindow(main_window, project_file, project_data, system_name)
    title = "Website Header/Footer"

    if system_name:
        title += f" [{system_name}]"

    if hasattr(main_window, "add_mdi_widget"):
        sub = main_window.add_mdi_widget(widget, title, 800, 600)
        sub.project_file = os.path.abspath(project_file) if project_file else ""
        sub.window_role = "website_header_footer"
        return sub

    widget.resize(800, 600)
    widget.show()
    return widget
