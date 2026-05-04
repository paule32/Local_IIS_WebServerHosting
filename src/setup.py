# ---------------------------------------------------------------------------
# File:   setup.py
# Author: (c) 2024, 2025, 2026 Jens Kallup - paule32
# All rights reserved
# ---------------------------------------------------------------------------
from __future__   import annotations

import sys
import json
import os
import subprocess

import ctypes
from   ctypes import wintypes

# -----------------------------------------------------------------------
# Qt Backend Factory + Property Mapping
# -----------------------------------------------------------------------
from PyQt5.QtCore    import (
    Qt, QDate
)
from PyQt5.QtGui     import (
    QPalette, QFont
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMdiArea, QMdiSubWindow, QGroupBox, QDateEdit,
    QWidget, QVBoxLayout, QLabel, QAction, QFileDialog, QRadioButton,
    QMessageBox, QDockWidget, QToolBar, QTextEdit, QComboBox, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QInputDialog, QCheckBox
)

# -----------------------------------------------------------------------
# resources suff like icons, ...
# -----------------------------------------------------------------------
import resources_rc

from theme import *

APP_NAME = "IIS Setup v.0.0.1 (c) 2026 Jens Kallup - paule32"
HELP_FILE = os.path.join("data", "help", "help.chm")

def get_windows_countries():
    result = {}

    LOCALE_SISO3166CTRYNAME      = 0x0000005A
    LOCALE_SLOCALIZEDCOUNTRYNAME = 0x00000006
    
    LOCALE_ENUMPROCEX = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.LPARAM
    )
    
    GetLocaleInfoEx     = ctypes.windll.kernel32.GetLocaleInfoEx
    EnumSystemLocalesEx = ctypes.windll.kernel32.EnumSystemLocalesEx
    
    def get_locale_info(locale_name, info_type, size=128):
        buffer = ctypes.create_unicode_buffer(size)
        
        if GetLocaleInfoEx(locale_name, info_type, buffer, len(buffer)):
            return buffer.value.strip()
        
        return ""
    
    def callback(locale_name, flags, param):
        code = get_locale_info(locale_name, LOCALE_SISO3166CTRYNAME, 10)
        name = get_locale_info(locale_name, LOCALE_SLOCALIZEDCOUNTRYNAME, 128)
        
        if code and name:
            result[code] = name
        
        return True
    
    EnumSystemLocalesEx(LOCALE_ENUMPROCEX(callback), 0, 0, None)
    return sorted(result.items())


class ProjectButton(QPushButton):
    def __init__(self, main_window, project_file, project_data, parent=None):
        super().__init__(parent)

        self.main_window = main_window
        self.project_file = project_file
        self.project_data = project_data

        self.setText(project_data.get("project", {}).get("name", "New Project"))
        self.clicked.connect(self.on_clicked)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F2:
            self.rename_project()
            return

        super().keyPressEvent(event)

    def rename_project(self):
        old_name = self.text()

        new_name, ok = QInputDialog.getText(
            self,
            "Projekt umbenennen",
            "Projektname:",
            text=old_name
        )

        if not ok:
            return

        new_name = new_name.strip()

        if not new_name:
            return

        self.setText(new_name)
        self.project_data["project"]["name"] = new_name
        self.main_window.save_project_file(self.project_file, self.project_data)

    def on_clicked(self):
        self.main_window.current_project_file = self.project_file
        self.main_window.current_project_data = self.project_data
        self.main_window.open_client_authority_dialog_for_project(
            self.project_file,
            self.project_data
        )


# country_code = self.combo_country.currentData()
class CaAuthorityWindow(QWidget):
    def __init__(self, main_window, project_data, parent=None):
        super().__init__(parent)

        self.main_window = main_window
        self.project_data = project_data
        
        self.setFont(QFont("Arial", 10))

        main_layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.edit_common_name = QLineEdit()
        self.edit_organisation = QLineEdit()
        self.edit_organisation_unit = QLineEdit()
        self.edit_location = QLineEdit()

        self.combo_country = QComboBox()

        for code, name in get_windows_countries():
            self.combo_country.addItem(f"{code} - {name}", code)

        form_layout.addRow("Common Name:", self.edit_common_name)
        form_layout.addRow("Organisation:", self.edit_organisation)
        form_layout.addRow("Organisation Unit:", self.edit_organisation_unit)
        form_layout.addRow("Location:", self.edit_location)
        form_layout.addRow("Country:", self.combo_country)

        main_layout.addLayout(form_layout)
        crypto_layout = QHBoxLayout()

        crypto_layout.addWidget(QLabel("Algorithm:"))

        self.combo_algorithm = QComboBox()
        self.combo_algorithm.addItems(["RSA", "ECC"])
        crypto_layout.addWidget(self.combo_algorithm)

        crypto_layout.addWidget(QLabel("Key Size:"))

        self.combo_key_size = QComboBox()
        self.combo_key_size.addItems(["2048", "4096"])
        crypto_layout.addWidget(self.combo_key_size)

        crypto_layout.addStretch()

        main_layout.addLayout(crypto_layout)

        date_layout = QHBoxLayout()

        date_layout.addWidget(QLabel("Not Before:"))

        self.date_not_before = QDateEdit()
        self.date_not_before.setCalendarPopup(True)
        self.date_not_before.setDate(QDate.currentDate())
        date_layout.addWidget(self.date_not_before)

        date_layout.addWidget(QLabel("Not After:"))

        self.date_not_after = QDateEdit()
        self.date_not_after.setCalendarPopup(True)
        self.date_not_after.setDate(QDate.currentDate().addYears(10))
        date_layout.addWidget(self.date_not_after)

        date_layout.addStretch()

        main_layout.addLayout(date_layout)

        self.check_basic_constraints = QCheckBox("BasicConstraints:")
        self.check_basic_constraints.setChecked(True)

        main_layout.addWidget(self.check_basic_constraints)

        self.combo_algorithm.currentTextChanged.connect(self.on_algorithm_changed)
        self.on_algorithm_changed(self.combo_algorithm.currentText())

        groups_layout = QHBoxLayout()

        self.group_usage = QGroupBox("Usage")
        usage_layout = QVBoxLayout(self.group_usage)

        self.radio_trusted_ca = QRadioButton("Trusted CA")
        self.radio_server_cert = QRadioButton("Server Cert")
        self.radio_iis = QRadioButton("IIS")

        usage_layout.addWidget(self.radio_trusted_ca)
        usage_layout.addWidget(self.radio_server_cert)
        usage_layout.addWidget(self.radio_iis)

        self.group_store = QGroupBox("Certificate Store")
        store_layout = QVBoxLayout(self.group_store)

        self.radio_root = QRadioButton("Root Store")
        self.radio_ca_store = QRadioButton("CA Store")
        self.radio_personal = QRadioButton("Personal Store")

        store_layout.addWidget(self.radio_root)
        store_layout.addWidget(self.radio_ca_store)
        store_layout.addWidget(self.radio_personal)

        groups_layout.addWidget(self.group_usage)
        groups_layout.addWidget(self.group_store)

        main_layout.addLayout(groups_layout)

        self.group_scope = QGroupBox("Scope")
        scope_layout = QHBoxLayout(self.group_scope)

        self.radio_local_machine = QRadioButton("LocalMachine")
        self.radio_current_user = QRadioButton("CurrentUser")

        scope_layout.addWidget(self.radio_local_machine)
        scope_layout.addWidget(self.radio_current_user)
        scope_layout.addStretch()

        self.create_ca_button = QPushButton("Create CA")
        self.create_ca_button.clicked.connect(self.on_create_ca_button_clicked)

        main_layout.addWidget(self.group_scope)
        main_layout.addWidget(self.create_ca_button)

        self.radio_trusted_ca.setChecked(True)
        self.radio_root.setChecked(True)
        self.radio_current_user.setChecked(True)

        self.load_from_project()

    def on_algorithm_changed(self, text):
        self.combo_key_size.setEnabled(text == "RSA")
        
    def load_from_project(self):
        ca = self.project_data.get("client_authority", {})

        self.edit_common_name.setText(ca.get("common_name", ""))
        self.edit_organisation.setText(ca.get("organisation", ""))
        self.edit_organisation_unit.setText(ca.get("organisation_unit", ""))
        self.edit_location.setText(ca.get("location", ""))

        country = ca.get("country", "DE")
        index = self.combo_country.findData(country)

        if index >= 0:
            self.combo_country.setCurrentIndex(index)

        algorithm = ca.get("algorithm", "RSA")
        index = self.combo_algorithm.findText(algorithm)

        if index >= 0:
            self.combo_algorithm.setCurrentIndex(index)

        key_size = ca.get("key_size", "4096")
        index = self.combo_key_size.findText(str(key_size))

        if index >= 0:
            self.combo_key_size.setCurrentIndex(index)

        not_before = ca.get("not_before", QDate.currentDate().toString("yyyy-MM-dd"))
        self.date_not_before.setDate(QDate.fromString(not_before, "yyyy-MM-dd"))

        not_after = ca.get("not_after", QDate.currentDate().addYears(10).toString("yyyy-MM-dd"))
        self.date_not_after.setDate(QDate.fromString(not_after, "yyyy-MM-dd"))

        self.check_basic_constraints.setChecked(
            ca.get("basic_constraints", True)
        )

        usage = ca.get("usage", "trusted_ca")

        self.radio_trusted_ca.setChecked(usage == "trusted_ca")
        self.radio_server_cert.setChecked(usage == "server_cert")
        self.radio_iis.setChecked(usage == "iis")

        store = ca.get("store", "root")

        self.radio_root.setChecked(store == "root")
        self.radio_ca_store.setChecked(store == "ca_store")
        self.radio_personal.setChecked(store == "personal")

        scope = ca.get("scope", "current_user")

        self.radio_local_machine.setChecked(scope == "local_machine")
        self.radio_current_user.setChecked(scope == "current_user")

    def save_to_project(self):
        if self.radio_trusted_ca.isChecked():
            usage = "trusted_ca"
        elif self.radio_server_cert.isChecked():
            usage = "server_cert"
        else:
            usage = "iis"

        if self.radio_root.isChecked():
            store = "root"
        elif self.radio_ca_store.isChecked():
            store = "ca_store"
        else:
            store = "personal"

        if self.radio_local_machine.isChecked():
            scope = "local_machine"
        else:
            scope = "current_user"

        self.project_data["client_authority"] = {
            "common_name": self.edit_common_name.text(),
            "organisation": self.edit_organisation.text(),
            "organisation_unit": self.edit_organisation_unit.text(),
            "location": self.edit_location.text(),
            "country": self.combo_country.currentData(),
            "algorithm": self.combo_algorithm.currentText(),
            "key_size": self.combo_key_size.currentText(),
            "not_before": self.date_not_before.date().toString("yyyy-MM-dd"),
            "not_after": self.date_not_after.date().toString("yyyy-MM-dd"),
            "basic_constraints": self.check_basic_constraints.isChecked(),
            "usage": usage,
            "store": store,
            "scope": scope
        }

    def on_create_ca_button_clicked(self):
        print("create")

class ClientCertsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Client Certificates"))
        layout.addWidget(QTextEdit())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(APP_NAME)
        self.resize(800, 600)

        self.current_project_file = None
        self.current_project_data = None
        self.current_ca_window = None
        
        self.mdi = QMdiArea()
        self.mdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.setCentralWidget(self.mdi)

        self.create_sidebar()
        self.create_actions()
        self.create_menus()
        self.create_toolbar()
        self.create_statusbar()

        self.mdi.subWindowActivated.connect(self.update_window_menu)

    def create_sidebar(self):
        self.sidebar = QDockWidget("Sidebar", self)
        self.sidebar.setAllowedAreas(Qt.LeftDockWidgetArea)

        self.sidebar_widget = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)

        self.sidebar_layout.addWidget(QLabel("Projects"))
        self.sidebar_layout.addStretch()

        self.sidebar.setWidget(self.sidebar_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.sidebar)

    def create_actions(self):
        self.act_new_project = QAction("Project", self)
        self.act_new_project.triggered.connect(self.on_new_project)
        
        self.act_ca_authority = QAction("CA - Client Authority", self)
        self.act_ca_authority.triggered.connect(self.on_ca_authority)

        self.act_client_certs = QAction("Client Certs", self)
        self.act_client_certs.triggered.connect(self.on_client_certs)

        self.act_open = QAction("Open", self)
        self.act_open.triggered.connect(self.on_open_project)

        self.act_save = QAction("Save", self)
        self.act_save.triggered.connect(self.on_save)

        self.act_exit = QAction("Exit", self)
        self.act_exit.triggered.connect(self.close)

        self.act_help_contents = QAction("Contents", self)
        self.act_help_contents.setShortcut("F1")
        self.act_help_contents.triggered.connect(self.on_help_contents)

        self.act_about = QAction("About ...", self)
        self.act_about.triggered.connect(self.on_about)

        self.act_cascade = QAction("Cascade", self)
        self.act_cascade.triggered.connect(self.mdi.cascadeSubWindows)

        self.act_tile = QAction("Tile", self)
        self.act_tile.triggered.connect(self.mdi.tileSubWindows)

    def create_menus(self):
        menu_file = self.menuBar().addMenu("File")
        self.menuBar().setFont(QFont("Arial", 10))
        self.menuBar().font().setBold(True)
        
        menu_new = menu_file.addMenu("New")
        menu_new.addAction(self.act_new_project)
        menu_new.addSeparator()
        menu_new.addAction(self.act_ca_authority)
        menu_new.addAction(self.act_client_certs)
        
        
        menu_file.addAction(self.act_open)
        menu_file.addAction(self.act_save)

        menu_file.addSeparator()
        menu_file.addAction(self.act_exit)

        self.menu_windows = self.menuBar().addMenu("Windows")
        self.update_window_menu()

        menu_help = self.menuBar().addMenu("Help")
        menu_help.addAction(self.act_help_contents)
        menu_help.addSeparator()
        menu_help.addAction(self.act_about)

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)

        self.addToolBar(toolbar)

    def create_statusbar(self):
        self.statusBar().showMessage("Bereit")

    def find_project_window(self, project_file, window_role):
        normalized = os.path.abspath(project_file)

        for sub in self.mdi.subWindowList():
            if getattr(sub, "project_file", None) == normalized and \
               getattr(sub, "window_role", None) == window_role:
                return sub

        return None
        
    def add_mdi_widget(self, widget, title, width=700, height=500):
        sub = QMdiSubWindow()
        sub.setAttribute(Qt.WA_DeleteOnClose, True)
        sub.setWidget(widget)
        sub.setWindowTitle(title)
        sub.resize(width, height)

        self.mdi.addSubWindow(sub)

        sub.destroyed.connect(self.update_window_menu)
        sub.show()

        self.update_window_menu()
        return sub

    def on_ca_authority(self):
        #widget = CaAuthorityWindow()
        #self.add_mdi_widget(widget, "CA - Client Authority", 600, 350)
        #self.statusBar().showMessage("CA - Client Authority geöffnet")
        
        self.open_client_authority_dialog()
        self.statusBar().showMessage("CA - Client Authority geöffnet")

    def on_client_certs(self):
        widget = ClientCertsWindow()
        self.add_mdi_widget(widget, "Client Certs", 700, 500)
        self.statusBar().showMessage("Client Certs geöffnet")
    
    def update_window_menu(self):
        self.menu_windows.clear()

        windows = self.mdi.subWindowList()

        for index, window in enumerate(windows, start=1):
            title = window.windowTitle()
            action = QAction(f"{index}. {title}", self)
            action.triggered.connect(lambda checked=False, w=window: self.activate_mdi_window(w))
            self.menu_windows.addAction(action)

        if windows:
            self.menu_windows.addSeparator()

        self.menu_windows.addAction(self.act_cascade)
        self.menu_windows.addAction(self.act_tile)

    def activate_mdi_window(self, window):
        self.mdi.setActiveSubWindow(window)
        window.showNormal()
        window.raise_()
        window.activateWindow()
        window.widget().setFocus()

    def on_new(self):
        self.statusBar().showMessage("New geklickt")

    def on_open_project(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Projektdatei öffnen",
            "",
            "JSON Projektdateien (*.json);;Alle Dateien (*.*)"
        )

        if not filename:
            return

        normalized_filename = os.path.abspath(filename)

        for i in range(self.sidebar_layout.count()):
            item = self.sidebar_layout.itemAt(i)
            widget = item.widget()

            if isinstance(widget, ProjectButton):
                if os.path.abspath(widget.project_file) == normalized_filename:
                    QMessageBox.warning(
                        self,
                        "Projekt bereits geöffnet",
                        "Dieses Projekt ist bereits geöffnet."
                    )
                    return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                project_data = json.load(f)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Projektdatei konnte nicht geöffnet werden:\n\n{e}"
            )
            return

        if "header" not in project_data:
            project_data["header"] = {
                "version": "1.0",
                "app": "iis setup"
            }

        if "project" not in project_data:
            project_data["project"] = {
                "name": os.path.splitext(os.path.basename(filename))[0]
            }

        if "client_authority" not in project_data:
            project_data["client_authority"] = {
                "common_name": "",
                "organisation": "",
                "organisation_unit": "",
                "location": "",
                "country": "DE"
            }

        if "client_certs" not in project_data:
            project_data["client_certs"] = []

        self.current_project_file = filename
        self.current_project_data = project_data

        self.add_project_button(filename, project_data)

        self.statusBar().showMessage(f"Projekt geöffnet: {filename}")

    def on_save(self):
        if not self.current_project_file or not self.current_project_data:
            QMessageBox.information(self, "Save", "Kein aktives Projekt vorhanden.")
            return

        if self.current_ca_window is not None:
            self.current_ca_window.save_to_project()

        try:
            self.save_project_file(
                self.current_project_file,
                self.current_project_data
            )

            self.statusBar().showMessage(
                f"Projekt gespeichert: {self.current_project_file}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Projekt konnte nicht gespeichert werden:\n\n{e}"
            )

    def on_help_contents(self):
        if not os.path.exists(HELP_FILE):
            QMessageBox.warning(
                self,
                "Hilfe",
                f"Die CHM-Hilfe wurde nicht gefunden:\n\n{HELP_FILE}"
            )
            return

        try:
            subprocess.Popen(["hh.exe", HELP_FILE])
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"CHM-Hilfe konnte nicht geöffnet werden:\n\n{e}")

    def on_new_project(self):
        project_name, ok = QInputDialog.getText(
            self,
            "Neues Projekt",
            "Projektname:",
            text="New Project"
        )

        if not ok:
            return

        project_name = project_name.strip()

        if not project_name:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Projektdatei erstellen",
            project_name + ".json",
            "JSON Projektdateien (*.json)"
        )

        if not filename:
            return

        if not filename.lower().endswith(".json"):
            filename += ".json"

        project_data = {
            "header": {
                "version": "1.0",
                "app": "iis setup"
            },
            "project": {
                "name": project_name
            },
            "client_authority": {
                "common_name": "",
                "organisation": "",
                "organisation_unit": "",
                "location": "",
                "country": "DE"
            },
            "client_certs": []
        }

        self.save_project_file(filename, project_data)

        self.current_project_file = filename
        self.current_project_data = project_data

        self.add_project_button(filename, project_data)

        self.statusBar().showMessage(f"Projekt erstellt: {filename}")


    def add_project_button(self, project_file, project_data):
        button = ProjectButton(self, project_file, project_data)

        insert_index = max(0, self.sidebar_layout.count() - 1)
        self.sidebar_layout.insertWidget(insert_index, button)

        button.setFocus()


    def save_project_file(self, filename, data):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def open_client_authority_dialog(self):
        if not self.current_project_file or not self.current_project_data:
            QMessageBox.information(
                self,
                "Projekt",
                "Bitte zuerst ein Projekt erstellen oder öffnen."
            )
            return

        self.open_client_authority_dialog_for_project(
            self.current_project_file,
            self.current_project_data
        )
        
    def open_client_authority_dialog_for_project(self, project_file, project_data):
        existing = self.find_project_window(project_file, "client_authority")

        if existing:
            self.activate_mdi_window(existing)
            return

        project_name = project_data.get("project", {}).get("name", "Project")

        widget = CaAuthorityWindow(self, project_data)
        self.current_ca_window = widget

        title = f"CA - Client Authority [{project_name}]"

        sub = self.add_mdi_widget(
            widget,
            title,
            600,
            350
        )

        sub.project_file = os.path.abspath(project_file)
        sub.window_role = "client_authority"

        sub.destroyed.connect(self.on_ca_window_destroyed)

    def on_ca_window_destroyed(self):
        self.current_ca_window = None
        
    def on_about(self):
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"{APP_NAME}\n\n"
            "Qt5 MDI Application to setup a WebHosting\n"
            "Server, and Client management.\n\n"
            "(c) 2026 by Jens Kallup - paule32\n"
            "all rights reserved."
        )


def main():
    app = QApplication(sys.argv)

    window = MainWindow() ; apply_theme_global(window)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
