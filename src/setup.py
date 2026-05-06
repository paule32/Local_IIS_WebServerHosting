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
import tempfile
import base64

import traceback
import threading

import ctypes
from   ctypes import wintypes
from   copy   import deepcopy

# -----------------------------------------------------------------------
# Qt Backend Factory + Property Mapping
# -----------------------------------------------------------------------
from PyQt5.QtCore    import (
    Qt, QDate, QThread, pyqtSignal
)
from PyQt5.QtGui     import (
    QPalette, QFont, QFontMetrics
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMdiArea, QMdiSubWindow, QGroupBox, QDateEdit,
    QWidget, QVBoxLayout, QLabel, QAction, QFileDialog, QRadioButton,
    QMessageBox, QDockWidget, QToolBar, QTextEdit, QComboBox, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QInputDialog, QCheckBox, QDialog,
    QScrollArea, QSizePolicy, QPlainTextEdit, QSplitter, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QProgressDialog, QDialogButtonBox, QInputDialog,
)

# -----------------------------------------------------------------------
# resources suff like icons, ...
# -----------------------------------------------------------------------
import resources_rc

from theme import *

from InlineSpinEdit         import InlineSpinEdit
from user_management_dialog import UserManagementWindow

APP_NAME  = "IIS Setup v.0.0.1 (c) 2026 Jens Kallup - paule32"
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


def is_user_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def restart_as_admin():
    params = " ".join([f'"{arg}"' for arg in sys.argv])
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        params,
        None,
        1
    )
    sys.exit(0)


class ExceptionDialog(QDialog):
    def __init__(self, title, message, details, parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.resize(900, 520)

        layout = QVBoxLayout(self)

        label = QLabel(message, self)
        label.setWordWrap(True)
        layout.addWidget(label)

        self.details = QTextEdit(self)
        self.details.setReadOnly(True)
        self.details.setPlainText(details)
        layout.addWidget(self.details, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)

        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)

        buttons.addWidget(close_button)
        layout.addLayout(buttons)


class PowerShellWorker(QThread):
    output = pyqtSignal(str)
    finished_ok = pyqtSignal()
    finished_error = pyqtSignal(int)

    def __init__(self, ps_script, parent=None):
        super().__init__(parent)
        self.ps_script = ps_script
        self.process = None

    def run(self):
        try:
            script = (
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
                + self.ps_script
            )

            encoded = base64.b64encode(
                script.encode("utf-16le")
            ).decode("ascii")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".ps1", mode="w", encoding="utf-8") as f:
                f.write(self.ps_script)
                script_path = f.name
            
            self.process = subprocess.Popen(
                [   "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy", "RemoteSigned",
                    "-File", script_path
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            for line in self.process.stdout:
                self.output.emit(line.rstrip())

            return_code = self.process.wait()

            if return_code == 0:
                self.finished_ok.emit()
            else:
                self.finished_error.emit(return_code)

        except Exception as e:
            self.output.emit("[ERROR] " + str(e))
            self.finished_error.emit(-1)

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()


class PowerShellOutputDialog(QDialog):
    def __init__(self, ps_script, parent=None):
        super().__init__(parent)

        self.setWindowTitle("PowerShell Output")
        self.resize(640, 480)

        layout = QVBoxLayout(self)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))

        self.btn_close = QPushButton("Close")
        self.btn_close.setEnabled(False)
        self.btn_close.clicked.connect(self.close)

        layout.addWidget(self.output)
        layout.addWidget(self.btn_close)

        self.worker = PowerShellWorker(ps_script, self)
        self.worker.output.connect(self.append_stdout)
        #self.worker.error.connect(self.append_stderr)
        self.worker.finished_ok.connect(self.on_finished_ok)
        self.worker.finished_error.connect(self.on_finished_error)

        self.worker.start()

    def append_stdout(self, text):
        self.output.appendPlainText(text)

    def append_stderr(self, text):
        self.output.appendPlainText("[ERROR] " + text)

    def on_finished_ok(self):
        self.output.appendPlainText("")
        self.output.appendPlainText("PowerShell-Skript erfolgreich ausgeführt.")
        self.btn_close.setEnabled(True)

    def on_finished_error(self, code):
        self.output.appendPlainText("")
        self.output.appendPlainText(f"PowerShell wurde mit Fehlercode {code} beendet.")
        self.btn_close.setEnabled(True)

        QMessageBox.critical(
            self,
            "PowerShell Fehler",
            f"Das PowerShell-Skript wurde mit Fehlercode {code} beendet."
        )

    def closeEvent(self, event):
        if self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)

        super().closeEvent(event)


class CertificateSyncDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)

        self.main_window = main_window
        self.setWindowTitle("Certificate Store Synchronizing")
        self.resize(920, 560)

        layout = QVBoxLayout(self)

        self.info_label   = QLabel("Compare Windows certificate stores with the project JSON snapshot.")
        self.info_changes = False
        
        layout.addWidget(self.info_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["State", "Scope", "Store", "Certificate", "Thumbprint", "Not After"])
        layout.addWidget(self.tree)

        button_layout = QHBoxLayout()

        self.btn_refresh  = QPushButton("Refresh Diff")
        self.btn_snapshot = QPushButton("Store Snapshot to JSON")
        
        self.btn_apply    = QPushButton("Apply")
        self.btn_cancel   = QPushButton("Cancel")

        button_layout.addWidget(self.btn_refresh)
        button_layout.addWidget(self.btn_snapshot)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_apply)
        button_layout.addWidget(self.btn_cancel)

        layout.addLayout(button_layout)

        self.btn_refresh .clicked.connect(self.refresh_diff)
        self.btn_snapshot.clicked.connect(self.store_snapshot_to_json)
        self.btn_apply   .clicked.connect(self.on_apply_clicked)
        self.btn_cancel  .clicked.connect(self.on_cancel_clicked)

        self.store_certs = []
        self.refresh_diff()

    def on_apply_clicked(self):
        self.has_changes = True
        self.store_snapshot_to_json()

        sub = self.parentWidget()
        while sub is not None and not isinstance(sub, QMdiSubWindow):
            sub = sub.parentWidget()

        if sub is not None:
            self.accept()
            sub .close()
            return

        self.close()

    def on_cancel_clicked(self):
        self.has_changes = False

        sub = self.parentWidget()
        while sub is not None and not isinstance(sub, QMdiSubWindow):
            sub = sub.parentWidget()

        if sub is not None:
            sub.close()
            return

        self.close()
    
    def refresh_diff(self):
        self.store_certs = self.read_windows_certificate_stores()
        json_certs = self.main_window.current_project_data.get("certificate_snapshot", [])

        self.tree.clear()

        store_map = self.make_cert_map(self.store_certs)
        json_map  = self.make_cert_map(json_certs)

        all_keys = sorted(set(store_map.keys()) | set(json_map.keys()))

        for key in all_keys:
            store_cert = store_map.get(key)
            json_cert  = json_map.get(key)

            if store_cert and json_cert:
                if self.cert_metadata_equal(store_cert, json_cert):
                    state = "OK"
                else:
                    state = "CHANGED"
                cert = store_cert
            elif store_cert:
                state = "STORE ONLY"
                cert = store_cert
            else:
                state = "JSON ONLY"
                cert = json_cert

            item = QTreeWidgetItem()
            item.setText(0, state)
            item.setText(1, cert.get("Scope", ""))
            item.setText(2, cert.get("Store", ""))
            item.setText(3, self.extract_cn(cert.get("Subject", "")))
            item.setText(4, cert.get("Thumbprint", ""))
            item.setText(5, cert.get("NotAfter", ""))
            item.setData(0, Qt.UserRole, cert)

            self.tree.addTopLevelItem(item)

        for column in range(self.tree.columnCount()):
            self.tree.resizeColumnToContents(column)

        self.info_label.setText(
            f"Store: {len(self.store_certs)} certificate(s), "
            f"JSON: {len(json_certs)} certificate(s), "
            f"Diff: {len(all_keys)} row(s)"
        )

    def store_snapshot_to_json(self):
        if not self.main_window.current_project_data:
            QMessageBox.warning(self, "Certificate Sync", "No active project available.")
            return

        self.main_window.current_project_data["certificate_snapshot"] = self.store_certs

        if hasattr(self.main_window, "set_project_dirty"):
            self.main_window.set_project_dirty(True)

        result = QMessageBox.question(
            self,
            "Certificate Sync",
            "Certificate snapshot was copied to project data.\n\nSave project file now?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )

        if result == QMessageBox.Cancel:
            return

        if result == QMessageBox.Yes:
            self.main_window.on_save()

        self.refresh_diff()

    def read_windows_certificate_stores(self):
        ps_script = """
$ErrorActionPreference = "Continue"
$items = @()
$scopes = @("CurrentUser", "LocalMachine")
$stores = @("Root", "CA", "My")

foreach ($scope in $scopes) {
    foreach ($store in $stores) {
        $path = "Cert:\\$scope\\$store"

        try {
            Get-ChildItem $path | ForEach-Object {
                $items += [PSCustomObject]@{
                    Scope      = $scope
                    Store      = $store
                    Subject    = $_.Subject
                    Issuer     = $_.Issuer
                    Thumbprint = $_.Thumbprint
                    NotBefore  = $_.NotBefore.ToString("yyyy-MM-dd")
                    NotAfter   = $_.NotAfter.ToString("yyyy-MM-dd")
                    HasPrivateKey = $_.HasPrivateKey
                }
            }
        }
        catch {
            # Store could not be read. This is intentionally ignored here.
        }
    }
}

$items | ConvertTo-Json -Depth 5
"""

        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy", "RemoteSigned",
                    "-Command", ps_script
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            if result.returncode != 0:
                QMessageBox.warning(self, "Certificate Sync", result.stderr)
                return []

            text = result.stdout.strip()

            if not text:
                return []

            data = json.loads(text)

            if isinstance(data, dict):
                data = [data]

            return data

        except Exception as e:
            QMessageBox.critical(self, "Certificate Sync", str(e))
            return []

    def make_cert_map(self, certs):
        result = {}

        for cert in certs:
            thumbprint = cert.get("Thumbprint", "")
            scope = cert.get("Scope", "")
            store = cert.get("Store", "")

            if not thumbprint:
                continue

            key = (
                scope.lower(),
                store.lower(),
                thumbprint.upper()
            )
            result[key] = cert

        return result

    def cert_metadata_equal(self, left, right):
        fields = [
            "Subject",
            "Issuer",
            "NotBefore",
            "NotAfter",
            "HasPrivateKey"
        ]

        for field in fields:
            if str(left.get(field, "")) != str(right.get(field, "")):
                return False

        return True

    def extract_cn(self, subject):
        parts = subject.split(",")

        for part in parts:
            part = part.strip()
            if part.startswith("CN="):
                return part[3:]

        return subject


class ProjectMdiSubWindow(QMdiSubWindow):
    def closeEvent(self, event):
        widget = self.widget()

        if widget is not None and hasattr(widget, "request_close"):
            if not widget.request_close():
                event.ignore()
                return

        super().closeEvent(event)


class ProjectButton(QPushButton):
    def __init__(self, main_window, project_file, project_data, parent=None):
        super().__init__(parent)

        self.main_window = main_window
        self.project_file = project_file
        self.project_data = project_data
        self.project_name = project_data.get("project", {}).get("name", "New Project")

        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.update_project_text()
        self.clicked.connect(self.on_clicked)

    def update_project_text(self):
        metrics = QFontMetrics(self.font())
        display_text = metrics.elidedText(self.project_name, Qt.ElideRight, 110)

        self.setText(display_text)
        self.setProperty("project_name", self.project_name)
        self.setToolTip(self.project_name)

    def enterEvent(self, event):
        metrics = QFontMetrics(self.main_window.statusBar().font())
        status_text = metrics.elidedText(self.project_name, Qt.ElideRight, 200)
        self.main_window.statusBar().showMessage(status_text)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.main_window.statusBar().showMessage("Bereit")
        super().leaveEvent(event)

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

        self.project_name = new_name
        self.project_data["project"]["name"] = new_name
        self.update_project_text()
        self.main_window.save_project_file(self.project_file, self.project_data)

    def on_clicked(self):
        self.main_window.current_project_file = self.project_file
        self.main_window.current_project_data = self.project_data
        self.main_window.open_client_authority_dialog_for_project(
            self.project_file,
            self.project_data
        )


class CertificateStoreTabs(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        progress = QProgressDialog(
            "Searching Certificate...",
            None,
            0,
            6,
            self
        )
        progress.setWindowTitle("Please wait")
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.setStyleSheet("color:yellow;")
        progress.resize(280,74)
        progress.show()

        step = 0

        self.create_store_tab("Root Store", "Root", progress, step)
        step += 2

        self.create_store_tab("CA Store", "CA", progress, step)
        step += 2

        self.create_store_tab("Personal", "My", progress, step)
        step += 2

        progress.setValue(6)

        #self.create_store_tab("Root Store", "Root")
        #self.create_store_tab("CA Store", "CA")
        #self.create_store_tab("Personal", "My")

    def create_store_tab(self, title, store_name, progress=None, step=0):
        tab = QWidget()
        tab.setMinimumWidth(340)

        tab_layout = QVBoxLayout(tab)

        splitter = QSplitter(Qt.Vertical)

        current_user_widget = self.create_cert_tree_panel(
            "CurrentUser",
            store_name,
            progress,
            step + 1
        )

        local_machine_widget = self.create_cert_tree_panel(
            "LocalMachine",
            store_name,
            progress,
            step + 2
        )

        splitter.addWidget(current_user_widget)
        splitter.addWidget(local_machine_widget)
        splitter.setSizes([300, 300])

        tab_layout.addWidget(splitter)

        self.tabs.addTab(tab, title)

    def create_cert_tree_panel(self, scope, store_name, progress=None, step=0):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel(scope))

        tree = QTreeWidget()
        tree.setHeaderLabels(["Certificate", "Thumbprint", "Not After"])
        layout.addWidget(tree)

        button_layout = QHBoxLayout()

        btn_show      = QPushButton("Show")
        btn_delete    = QPushButton("Delete")

        button_layout.addWidget(btn_show)
        button_layout.addWidget(btn_delete)

        layout.addLayout(button_layout)

        btn_show  .clicked.connect(lambda: self.show_selected_certificate(tree))
        btn_delete.clicked.connect(lambda: self.delete_selected_certificate(tree, scope, store_name))

        if progress:
            progress.setLabelText(f"Load {scope}\\{store_name} ...")
            progress.setValue(step - 1)
            QApplication.processEvents()

        self.load_certificates(tree, scope, store_name)

        if progress:
            progress.setValue(step)
            QApplication.processEvents()

        return widget
    
    def show_selected_certificate(self, tree):
        item = tree.currentItem()

        if not item:
            QMessageBox.information(self, "Certificate", "Kein Zertifikat ausgewählt.")
            return

        cert = item.data(0, Qt.UserRole)

        if not cert:
            QMessageBox.warning(self, "Certificate", "Keine Zertifikatsdaten vorhanden.")
            return

        text = ""

        for key, value in cert.items():
            text += f"{key}: {value}\n"

        QMessageBox.information(self, "Certificate Properties", text)
    
    def delete_selected_certificate(self, tree, scope, store_name):
        item = tree.currentItem()

        if not item:
            QMessageBox.information(self, "Certificate", "Kein Zertifikat ausgewählt.")
            return

        cert = item.data(0, Qt.UserRole)

        if not cert:
            QMessageBox.warning(self, "Certificate", "Keine Zertifikatsdaten vorhanden.")
            return

        thumbprint = cert.get("Thumbprint", "")

        if not thumbprint:
            QMessageBox.warning(self, "Certificate", "Thumbprint fehlt.")
            return

        result = QMessageBox.warning(
            self,
            "Zertifikat löschen",
            f"Soll dieses Zertifikat wirklich gelöscht werden?\n\n"
            f"{cert.get('Subject', '')}\n\n"
            f"Thumbprint:\n{thumbprint}",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Cancel
        )

        if result != QMessageBox.Yes:
            return

        ps_script = f"""
$ErrorActionPreference = "Stop"

$thumbprint = "{thumbprint}"
$path = "Cert:\\{scope}\\{store_name}\\$thumbprint"

if (-not (Test-Path $path)) {{
    throw "Zertifikat wurde nicht gefunden: $path"
}}

Remove-Item -Path $path -Force
Write-Host "Zertifikat gelöscht: $thumbprint"
"""

        run = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        if run.returncode != 0:
            QMessageBox.critical(self, "Delete Certificate", run.stderr)
            return

        QMessageBox.information(self, "Delete Certificate", "Zertifikat wurde gelöscht.")

        self.load_certificates(tree, scope, store_name)
    
    def load_certificates(self, tree, scope, store_name):
        certs = self.get_certificates(scope, store_name)

        tree.clear()

        if not certs:
            return

        by_subject = {}

        for cert in certs:
            subject = cert.get("Subject", "")
            issuer = cert.get("Issuer", "")

            item = QTreeWidgetItem()
            item.setText(0, self.extract_cn(subject))
            item.setText(1, cert.get("Thumbprint", ""))
            item.setText(2, cert.get("NotAfter", ""))

            item.setData(0, Qt.UserRole, cert)
            by_subject[subject] = item

        added = set()

        for cert in certs:
            subject = cert.get("Subject", "")
            issuer = cert.get("Issuer", "")

            item = by_subject.get(subject)

            if not item:
                continue

            if issuer != subject and issuer in by_subject:
                parent_item = by_subject[issuer]
                parent_item.addChild(item)
                added.add(subject)
            else:
                tree.addTopLevelItem(item)
                added.add(subject)

        for cert in certs:
            subject = cert.get("Subject", "")

            if subject not in added:
                item = by_subject.get(subject)
                if item:
                    tree.addTopLevelItem(item)

        tree.expandAll()
        tree.resizeColumnToContents(0)

    def get_certificates(self, scope, store_name):
        ps_script = f"""
$ErrorActionPreference = "Stop"

$certs = Get-ChildItem Cert:\\{scope}\\{store_name} | ForEach-Object {{
    [PSCustomObject]@{{
        Subject    = $_.Subject
        Issuer     = $_.Issuer
        Thumbprint = $_.Thumbprint
        NotBefore  = $_.NotBefore.ToString("yyyy-MM-dd")
        NotAfter   = $_.NotAfter.ToString("yyyy-MM-dd")
    }}
}}

$certs | ConvertTo-Json -Depth 5
"""

        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy", "RemoteSigned",
                    "-Command", ps_script
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            if result.returncode != 0:
                QMessageBox.warning(
                    self,
                    "Certificate Store",
                    result.stderr
                )
                return []

            text = result.stdout.strip()

            if not text:
                return []

            data = json.loads(text)

            if isinstance(data, dict):
                data = [data]

            return data

        except Exception as e:
            QMessageBox.critical(
                self,
                "Certificate Store",
                str(e)
            )
            return []

    def extract_cn(self, subject):
        parts = subject.split(",")

        for part in parts:
            part = part.strip()
            if part.startswith("CN="):
                return part[3:]

        return subject
        

class RightCAWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


        self.main_window  = parent.owner.main_window
        self.project_data = parent.owner.project_data
        
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.edit_common_name       = QLineEdit()
        self.edit_organisation      = QLineEdit()
        self.edit_organisation_unit = QLineEdit()
        self.edit_location          = QLineEdit()

        self.edit_common_name       .setPlaceholderText("My Test Root CA")
        self.edit_organisation      .setPlaceholderText("My Company Root CA")
        self.edit_organisation_unit .setPlaceholderText("IT Department")
        self.edit_location          .setPlaceholderText("London")
        
        self.combo_country = QComboBox()

        for code, name in get_windows_countries():
            self.combo_country.addItem(f"{code} - {name}", code)

        form_layout.addRow("Common Name:",       self.edit_common_name)
        form_layout.addRow("Organisation:",      self.edit_organisation)
        form_layout.addRow("Organisation Unit:", self.edit_organisation_unit)
        form_layout.addRow("Location:",          self.edit_location)
        form_layout.addRow("Country:",           self.combo_country)

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
        
        self.setup_change_tracking()
        self.set_changed(False)

    def setup_change_tracking(self):
        widgets = [
            self.edit_common_name,
            self.edit_organisation,
            self.edit_organisation_unit,
            self.edit_location
        ]

        for widget in widgets:
            widget.textChanged.connect(self.mark_changed)

        combos = [
            self.combo_country,
            self.combo_algorithm,
            self.combo_key_size
        ]

        for combo in combos:
            combo.currentIndexChanged.connect(self.mark_changed)

        dates = [
            self.date_not_before,
            self.date_not_after
        ]

        for date_edit in dates:
            date_edit.dateChanged.connect(self.mark_changed)

        checks = [
            self.check_basic_constraints,
            self.radio_trusted_ca,
            self.radio_server_cert,
            self.radio_iis,
            self.radio_root,
            self.radio_ca_store,
            self.radio_personal,
            self.radio_local_machine,
            self.radio_current_user
        ]

        for check in checks:
            check.toggled.connect(self.mark_changed)

    def mark_changed(self, *args):
        self.set_changed(True)

    def set_changed(self, state):
        self.setProperty("changed", bool(state))

    def is_changed(self):
        return bool(self.property("changed"))

    def request_close(self):
        if not self.is_changed():
            return True

        result = QMessageBox.question(
            self,
            "Änderungen speichern",
            "Es wurden Änderungen vorgenommen. Möchten Sie diese vor dem Schließen speichern?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Cancel
        )

        if result == QMessageBox.Yes:
            self.save_to_project()
            self.main_window.save_project_file(
                self.main_window.current_project_file,
                self.main_window.current_project_data
            )
            self.set_changed(False)
            return True

        if result == QMessageBox.No:
            return True

        return False

    def on_algorithm_changed(self, text):
        self.combo_key_size.setEnabled(text == "RSA")
    
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

    def run_powershell_script(self, ps_script):
        dlg = PowerShellOutputDialog(ps_script, self)
        dlg.exec_()
    
    def on_create_ca_button_clicked(self):
        self.store_scope = ""
        self.store_name  = ""
        
        if not self.edit_common_name.text().split():
            QMessageBox.warning(self,
            "Create CA",
            "Error: common name is empty")
            return
            
        if not self.edit_organisation.text().split():
            QMessageBox.warning(self,
            "Create CA",
            "Error: organisation name is empty")
            return
            
        if not self.edit_organisation_unit.text().split():
            QMessageBox.warning(self,
            "Create CA",
            "Error: organisation unit name is empty")
            return
            
        if not self.edit_location.text().split():
            QMessageBox.warning(self,
            "Create CA",
            "Error: location name is empty")
            return
            
        self.not_before = self.date_not_before.date()
        self.not_after  = self.date_not_after .date()
        
        if self.not_before >= self.not_after:
            QMessageBox.warning(self,
            "Create CA",
            "Error: Not Before must be lesser as Not After.")
            return
        
        if self.radio_current_user.isChecked():
            self.store_scope = "CurrentUser"
        else:
            self.store_scope = "LocalMachine"
            result = QMessageBox.question(
                self,
                "Admin Rights requiered",
                "For LocalMachine, you need administrative rights.\n\n"
                "Do you want restart the Application as admin?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if result == QMessageBox.Yes:
                restart_as_admin()
            else:
                return
        
        if self.radio_root.isChecked():
            self.store_name = "Root"
            if not is_user_admin():
                QMessageBox.warning(self,
                "ACL Error",
                "You have no permissions to create a Root CA")
                return
        elif self.radio_ca_store.isChecked():
            self.store_name = "CA"
            if not is_user_admin():
                QMessageBox.warning(self,
                "ACL Error",
                "You have no permissions to create a CA")
                return
        else:
            self.store_name = "My"
        
        if not self.store_scope:
            QMessageBox.warning(self,
            "Create CA",
            "Error: store scope is unknown.")
            return
        
        if not self.store_name:
            QMessageBox.warning(self,
            "Create CA",
            "Error: store name is unknown.")
            return
        
        pwsh_script = f"""
$CommonName       = "{self.edit_common_name      .text()}"
$Organisation     = "{self.edit_organisation     .text()}"
$OrganisationUnit = "{self.edit_organisation_unit.text()}"
$Location         = "{self.edit_location         .text()}"
$Country          = "{self.combo_country  .currentData()}"
$Algorithm        = "{self.combo_algorithm.currentText()}"
$KeySize          =  {self.combo_key_size .currentText()}

$NotBefore        = Get-Date "{self.date_not_before.date().toString("yyyy-MM-dd")}"
$NotAfter         = Get-Date "{self.date_not_after .date().toString("yyyy-MM-dd")}"

$StoreScope       = "{self.store_scope}"
$StoreName        = "{self.store_name}"
$CertStore        = "Cert:\\$StoreScope\\$StoreName"

$Subject = "CN=$CommonName,O=$Organisation,OU=$OrganisationUnit,L=$Location,C=$Country"

Write-Host "CommonName       = $CommonName"
Write-Host "Organisation     = $Organisation"
Write-Host "OrganisationUnit = $OrganisationUnit"
Write-Host "Location         = $Location"
Write-Host "Country          = $Country"
Write-Host "Algorithm        = $Algorithm"
Write-Host "KeySize          = $KeySize"
Write-Host ""
Write-Host "NotBefore        = $NotBefore"
Write-Host "NotAfter         = $NotAfter"

Write-Host ""
Write-Host "StoreScope       = $StoreScope"
Write-Host "StoreName        = $StoreName"
Write-Host "CertStore        = $CertStore"
Write-Host ""
Write-Host "Subject          = $Subject"
Write-Host ""

if ([string]::IsNullOrWhiteSpace($CommonName)) {{
    throw "Common Name must be filled."
}}

if ($NotBefore -ge $NotAfter) {{
    throw "Not Before must be lesser as Not After."
}}

$existing = Get-ChildItem $CertStore | Where-Object {{
    $_.Subject -like "*CN=$CommonName*"
}}

if ($existing) {{
    throw "Certificate with Common Name already exists im Store: $CertStore"
}}

try {{
    $cert = New-SelfSignedCertificate `
        -Type Custom `
        -Subject $Subject `
        -KeyAlgorithm $Algorithm `
        -KeyLength $KeySize `
        -KeyExportPolicy Exportable `
        -KeyUsage CertSign, CRLSign, DigitalSignature `
        -NotBefore $NotBefore `
        -NotAfter $NotAfter `
        -CertStoreLocation $CertStore `
        -TextExtension @(
            "2.5.29.19={{critical}}{{text}}CA=true"
        ) `
        -ErrorAction Stop

    if ($null -eq $cert) {{
        throw "New-SelfSignedCertificate return no Certificate Object."
    }}

    Write-Host "CA-Certificate successfully created."
    Write-Host "Thumbprint: $($cert.Thumbprint)"
    Write-Host "Store:      $CertStore"
}}
catch {{
    Write-Host "FEHLER:"
    Write-Host $_.Exception.Message
    exit 1
}}
"""
        dlg = PowerShellOutputDialog(pwsh_script, self)
        dlg.exec_()


# country_code = self.combo_country.currentData()
class CaAuthorityWindow(QWidget):
    def __init__(self, main_window, project_data, parent=None):
        super().__init__(parent)

        self.owner        = self
        self.main_window  = main_window
        self.project_data = project_data
        
        self.setFont(QFont("Arial", 10))
        self.setProperty("changed", False)

        main_layout  = QVBoxLayout(self)
        
        splitter     = QSplitter(Qt.Horizontal)

        self.left_widget  = CertificateStoreTabs(self)
        self.right_widget = RightCAWidget(self)

        splitter.addWidget(self.left_widget)
        splitter.addWidget(self.right_widget)

        splitter.setSizes([180, 520])

        main_layout.addWidget(splitter)

    def setup_change_tracking(self):
        if hasattr(self, "right_widget"):
            self.right_widget.setup_change_tracking()

    def mark_changed(self, *args):
        self.set_changed(True)

    def set_changed(self, state):
        self.setProperty("changed", bool(state))
        if hasattr(self, "right_widget"):
            self.right_widget.set_changed(state)

    def is_changed(self):
        if bool(self.property("changed")):
            return True
        if hasattr(self, "right_widget"):
            return self.right_widget.is_changed()
        return False

    def save_to_project(self):
        if hasattr(self, "right_widget"):
            self.right_widget.save_to_project()
            self.right_widget.set_changed(False)
        self.set_changed(False)

    def request_close(self):
        if not self.is_changed():
            return True

        result = QMessageBox.question(
            self,
            "Save Changes",
            "There are unsaved changes. Do you want to save them before closing?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Cancel
        )

        if result == QMessageBox.Yes:
            self.save_to_project()
            self.main_window.save_project_file(
                self.main_window.current_project_file,
                self.main_window.current_project_data
            )
            return True

        if result == QMessageBox.No:
            return True

        return False
        

class ClientCertsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Client Certificates"))
        layout.addWidget(QTextEdit())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        if not is_user_admin():
            result = QMessageBox.warning(self,
                "Need Admin Rights",
                "Many parts of this Application need administrative Rights.\n"
                "Do you want try to re-start with admin rights?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes)
                
            if  result == QMessageBox.Yes:
                restart_as_admin()
            sys.exit(1)

        self.setWindowTitle(APP_NAME)
        self.resize(1000, 700)
        self.setFont(QFont("Arial", 10))

        self.current_project_file = None
        self.current_project_data = None
        self.current_ca_window = None
        self.project_dirty = False
        
        self.mdi = QMdiArea()
        self.mdi.setFont(QFont("Arial", 10))
        self.mdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.setCentralWidget(self.mdi)

        self.create_sidebar()
        self.create_actions()
        self.create_menus()
        self.create_toolbar()
        self.create_statusbar()
        self.update_project_actions()

        self.mdi.subWindowActivated.connect(self.update_window_menu)

    def create_sidebar(self):
        self.sidebar = QDockWidget("Sidebar", self)
        self.sidebar.setAllowedAreas(Qt.LeftDockWidgetArea)
        self.sidebar.setMinimumWidth(120)
        self.sidebar.resize(156, self.sidebar.height())

        self.sidebar_widget = QWidget()
        self.sidebar_outer_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_outer_layout.setContentsMargins(4, 4, 4, 4)
        self.sidebar_outer_layout.setSpacing(4)

        self.sidebar_outer_layout.addWidget(QLabel("Projects"))

        self.sidebar_scroll_up = QPushButton("▲")
        self.sidebar_scroll_up.setFixedHeight(24)
        self.sidebar_scroll_up.clicked.connect(self.scroll_sidebar_up)
        self.sidebar_outer_layout.addWidget(self.sidebar_scroll_up)

        self.sidebar_scroll_area = QScrollArea()
        self.sidebar_scroll_area.setWidgetResizable(True)
        self.sidebar_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.sidebar_projects_widget = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar_projects_widget)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(4)
        self.sidebar_layout.addStretch()

        self.sidebar_scroll_area.setWidget(self.sidebar_projects_widget)
        self.sidebar_outer_layout.addWidget(self.sidebar_scroll_area)

        self.sidebar_scroll_down = QPushButton("▼")
        self.sidebar_scroll_down.setFixedHeight(24)
        self.sidebar_scroll_down.clicked.connect(self.scroll_sidebar_down)
        self.sidebar_outer_layout.addWidget(self.sidebar_scroll_down)

        self.sidebar.setWidget(self.sidebar_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.sidebar)
        self.resizeDocks([self.sidebar], [156], Qt.Horizontal)

    def create_actions(self):
        self.act_new_project = QAction("Project", self)
        self.act_new_project.triggered.connect(self.on_new_project)
        
        self.act_ca_authority = QAction("CA - Client Authority", self)
        self.act_ca_authority.triggered.connect(self.on_ca_authority)

        self.act_client_certs = QAction("Client Certs", self)
        self.act_client_certs.triggered.connect(self.on_client_certs)
        
        self.act_sync_certs = QAction("Synchronize Certificates ...", self)
        self.act_sync_certs.triggered.connect(self.on_sync_certificates)

        self.act_open = QAction("Open", self)
        self.act_open.triggered.connect(self.on_open_project)

        self.act_save = QAction("Save", self)
        self.act_save.triggered.connect(self.on_save)
        
        self.act_save_as = QAction("Save As ...", self)
        self.act_save_as.setEnabled(False)
        self.act_save_as.triggered.connect(self.on_save_as)

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
        
        self.menu_iis_server_groups_and_users = QAction("User / Groups")
        self.menu_iis_server_groups_and_users.triggered.connect(self.on_groups_and_users)

    def create_menus(self):
        menu_file = self.menuBar().addMenu("File")

        menu_font = QFont("Arial", 11)
        menu_font.setBold(True)
        self.menuBar().setFont(menu_font)
        self.menuBar().setStyleSheet(f"""
        QMenuBar {{
            color: #ffd866;
            font-family: Arial;
            font-size: 10pt;
            font-weight: bold;
        }}
        QMenuBar::item {{
            color: #ffd866;
        }}
        QMenuBar::item:selected {{
            background-color: #5a1020;
        }}
        QMenu {{
            color: #ffd866;
            font-family: Arial;
            font-size: 10pt;
            font-weight: bold;
        }}
        QMenu::item:selected {{
            background-color: #5a1020;
        }}
        """)
        
        menu_new = menu_file.addMenu("New")
        menu_new.addAction(self.act_new_project)
        menu_new.addSeparator()
        menu_new.addAction(self.act_ca_authority)
        menu_new.addAction(self.act_client_certs)
        menu_new.addSeparator()
        menu_new.addAction(self.act_sync_certs)
        
        menu_file.addAction(self.act_open)
        menu_file.addAction(self.act_save)
        menu_file.addAction(self.act_save_as)

        menu_file.addSeparator()
        menu_file.addAction(self.act_exit)

        menu_iis_server = self.menuBar().addMenu("IIS Server")
        menu_iis_server.addAction(self.menu_iis_server_groups_and_users)
        
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
        self.statusBar().showMessage("Ready")

    def scroll_sidebar_up(self):
        scrollbar = self.sidebar_scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() - 48)

    def scroll_sidebar_down(self):
        scrollbar = self.sidebar_scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + 48)

    def find_project_window(self, project_file, window_role):
        normalized = os.path.abspath(project_file)

        for sub in self.mdi.subWindowList():
            if getattr(sub, "project_file", None) == normalized and \
               getattr(sub, "window_role", None) == window_role:
                return sub

        return None
        
    def add_mdi_widget(self, widget, title, width=700, height=500):
        sub = ProjectMdiSubWindow()
        sub.setAttribute(Qt.WA_DeleteOnClose, True)
        sub.setWidget(widget)
        sub.setWindowTitle(title)
        sub.resize(width, height)

        self.mdi.addSubWindow(sub)

        sub.destroyed.connect(self.update_window_menu)
        sub.show()

        self.update_window_menu()
        return sub

    def open_user_management_dialog_for_project(self, project_file, project_data):
        existing = self.find_project_window(project_file, "user_management")

        if existing:
            self.activate_mdi_window(existing)
            return

        project_name = project_data.get("project", {}).get("name", "Project")

        widget = UserManagementWindow(self, project_data)

        sub = self.add_mdi_widget(
            widget,
            f"User Verwaltung [{project_name}]",
            840,
            480
        )

        sub.project_file = os.path.abspath(project_file)
        sub.window_role = "user_management"
        
    def on_ca_authority(self):
        #widget = CaAuthorityWindow()
        #self.add_mdi_widget(widget, "CA - Client Authority", 600, 350)
        #self.statusBar().showMessage("CA - Client Authority geöffnet")
        
        self.open_client_authority_dialog()
        self.statusBar().showMessage("CA - Client Authority geöffnet")

    def on_groups_and_users(self):
        if self.current_project_file is None:
            QMessageBox.warning(self,
            "Error",
            "No project is available")
            return
            
        if not is_user_admin():
            result = QMessageBox.warning(
                self,
                "No Admin rights",
                "Users and Groups can only be displayed, but not create or delete "
                "without administrative rights.\n"
                "Would you like restart the Application\n"
                "with admin rights?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No)
                
            if result == QMessageBox.Yes:
                restart_as_admin()
            else:
                return
            
        self.open_user_management_dialog_for_project(
        self.current_project_file,
        self.current_project_data)
        
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
        self.statusBar().showMessage("New clicked")

    def on_open_project(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project File",
            "",
            "JSON Project Files (*.json);;All Files (*.*)"
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
                        "Open Project",
                        "This Project is already open."
                    )
                    return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                project_data = json.load(f)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Project File could not be opened:\n\n{e}"
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
        self.set_project_dirty(False)
        self.update_project_actions()

        self.statusBar().showMessage(f"Project opened: {filename}")

    def update_project_actions(self):
        has_project = bool(self.current_project_file and self.current_project_data)
        if hasattr(self, "act_save_as"):
            self.act_save_as.setEnabled(has_project)

    def set_project_dirty(self, dirty=True):
        self.project_dirty = bool(dirty)
        if self.current_project_data is not None:
            self.current_project_data.setdefault("state", {})["dirty"] = self.project_dirty

    def clear_dirty_flags(self):
        for sub in self.mdi.subWindowList():
            widget = sub.widget()
            if widget is None:
                continue
            widget.setProperty("dirty", False)
            for child in widget.findChildren(QWidget):
                child.setProperty("dirty", False)

    def has_dirty_components(self):
        if self.project_dirty:
            return True

        for sub in self.mdi.subWindowList():
            widget = sub.widget()
            if widget is None:
                continue
            if widget.property("dirty"):
                return True
            for child in widget.findChildren(QWidget):
                if child.property("dirty"):
                    return True

        return False
        
    def on_save(self):
        if not self.current_project_file or not self.current_project_data:
            QMessageBox.information(self,
            "Save",
            "No active Project available.")
            return

        if self.current_ca_window is not None:
            self.current_ca_window.save_to_project()

        try:
            self.save_project_file(
                self.current_project_file,
                self.current_project_data
            )

            self.set_project_dirty(False)
            self.clear_dirty_flags()
            self.update_project_actions()

            self.statusBar().showMessage(
                f"Project saved: {self.current_project_file}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Could not save Project:\n\n{e}"
            )

    def on_save_as(self):
        if not self.current_project_file or not self.current_project_data:
            QMessageBox.information(self,
            "Save As ...",
            "No active Project available.")
            return

        if self.current_ca_window is not None:
            self.current_ca_window.save_to_project()

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project File...",
            self.current_project_file,
            "JSON Project Files (*.json);;All Files (*.*)"
        )

        if not filename:
            return

        if not filename.lower().endswith(".json"):
            filename += ".json"

        try:
            self.save_project_file(filename, self.current_project_data)
            self.current_project_file = filename
            self.set_project_dirty(False)
            self.clear_dirty_flags()
            self.update_project_actions()
            self.statusBar().showMessage(f"Project saved under:: {filename}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Project could not be saved:\n\n{e}"
            )

    def on_sync_certificates(self):
        if not self.current_project_file or not self.current_project_data:
            QMessageBox.information(self,
            "Certificate Sync",
            "No active Project available.")
            return
        
        widget = CertificateSyncDialog(self, self)
        self.add_mdi_widget(widget, "Client Certs", 700, 400)
        self.statusBar().showMessage("Client Certs geöffnet")

    def on_help_contents(self):
        if not os.path.exists(HELP_FILE):
            QMessageBox.warning(
                self,
                "Hilfe",
                f"The CHM-Help could not be found:\n\n{HELP_FILE}"
            )
            return

        try:
            subprocess.Popen(["hh.exe", HELP_FILE])
        except Exception as e:
            QMessageBox.critical(self,
            "Error",
            f"CHM-Help could not be open:\n\n{e}")

    def on_new_project(self):
        project_name, ok = QInputDialog.getText(
            self,
            "New Project",
            "Project Name:",
            text="New Project"
        )

        if not ok:
            return

        project_name = project_name.strip()

        if not project_name:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Create Project File",
            project_name + ".json",
            "JSON Project Files (*.json)"
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
        self.set_project_dirty(False)
        self.update_project_actions()

        self.statusBar().showMessage(f"Project successfully created: {filename}")


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
                "Project",
                "Firstly, you have to create a Project."
            )
            return

        self.open_client_authority_dialog_for_project(
            self.current_project_file,
            self.current_project_data
        )
    
    def check_certificate_snapshot_before_open(self, project_data):
        snapshots = project_data.get("certificate_snapshots", [])

        if not snapshots:
            return True

        missing = []

        for cert in snapshots:
            scope = cert.get("scope", "")
            store = cert.get("store", "")
            thumbprint = cert.get("thumbprint", "")

            if not scope or not store or not thumbprint:
                missing.append(cert)
                continue

            if not self.certificate_exists(scope, store, thumbprint):
                missing.append(cert)

        if not missing:
            return True

        dlg = CertificateSyncDialog(project_data, self)
        result = dlg.exec_()

        if result != QDialog.Accepted:
            return False

        if getattr(dlg, "has_changes", False):
            self.save_project_file(
                self.current_project_file,
                self.current_project_data
            )

            QMessageBox.information(
                self,
                "Certificate Snapshot",
                "Die Zertifikats-Snapshots wurden aktualisiert."
            )

        return True


    def certificate_exists(self, scope, store, thumbprint):
        ps_script = f"""
$path = "Cert:\\{scope}\\{store}\\{thumbprint}"

if (Test-Path $path) {{
    exit 0
}} else {{
    exit 1
}}
"""

        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        return result.returncode == 0
    
    def open_client_authority_dialog_for_project(self, project_file, project_data):
        self.current_project_file = project_file
        self.current_project_data = project_data

        if not self.check_certificate_snapshot_before_open(project_data):
            return
        
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
            820,
            580
        )

        sub.project_file = os.path.abspath(project_file)
        sub.window_role = "client_authority"

        sub.destroyed.connect(self.on_ca_window_destroyed)

    def on_ca_window_destroyed(self):
        self.current_ca_window = None

    def closeEvent(self, event):
        changed_widgets = []

        for sub in self.mdi.subWindowList():
            widget = sub.widget()

            if widget is not None and hasattr(widget, "is_changed"):
                if widget.is_changed():
                    changed_widgets.append(widget)

        if changed_widgets:
            result = QMessageBox.question(
                self,
                "Änderungen speichern",
                "Es wurden Änderungen vorgenommen. Möchten Sie diese vor dem Beenden speichern?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel
            )

            if result == QMessageBox.Yes:
                for widget in changed_widgets:
                    if hasattr(widget, "save_to_project"):
                        widget.save_to_project()

                if self.current_project_file and self.current_project_data:
                    self.save_project_file(
                        self.current_project_file,
                        self.current_project_data
                    )
                    self.set_project_dirty(False)
                    self.clear_dirty_flags()

                event.accept()
                return

            if result == QMessageBox.No:
                event.accept()
                return

            event.ignore()
            return

        result = QMessageBox.question(
            self,
            "Close Application",
            "Would you really close the Application?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
        
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


# ---------------------------------------------------------------------------
# \brief setup exception handler output to gui application for python throw
# ---------------------------------------------------------------------------
def show_exception_dialog(exc_type, exc_value, exc_traceback):
    # KeyboardInterrupt normal durchlassen
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    details = "".join(
        traceback.format_exception(exc_type, exc_value, exc_traceback)
    )

    with open("error.log", "a", encoding="utf-8") as f:
        f.write(details)
        f.write("\n" + "=" * 80 + "\n")

    print(details)

    app = QApplication.instance()
    if app is None:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    dlg = ExceptionDialog(
        "Unhandled Exception",
        str(exc_value),
        details,
        None
    )
    dlg.exec_()
    sys.exit(1)


# ---------------------------------------------------------------------------
# \brief setup exception handler output to gui application for threaded throw
# ---------------------------------------------------------------------------
def show_thread_exception(args):
    show_exception_dialog(
        args.exc_type,
        args.exc_value,
        args.exc_traceback
    )


# ---------------------------------------------------------------------------
# \brief this is the main entry point definition to start the qt5 application
# ---------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    
    sys      .excepthook = show_exception_dialog
    threading.excepthook = show_thread_exception

    window = MainWindow() ; apply_theme_global(window)
    window.show()

    sys.exit(app.exec_())


# ---------------------------------------------------------------------------
# \brief for python 3.14, this is the point where application starts. when
#        the interpreter could not found __main__, the app will not start.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
