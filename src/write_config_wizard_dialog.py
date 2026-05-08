# ---------------------------------------------------------------------------------------
# file: write_config_wizard_dialog.py
# author: (c) 2026 Jens Kallup - paule32
# all rights reserved.
# ---------------------------------------------------------------------------------------
from __future__    import annotations
import os

from copy import deepcopy

from PyQt5.QtCore    import Qt
from PyQt5.QtGui     import QFont
from PyQt5.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QTextEdit,
    QCheckBox, QMessageBox,
)

class WebsiteWizard(QWizard):
    PAGE_WELCOME = 0
    PAGE_WEBSITE = 1
    PAGE_CONTENT = 2
    PAGE_FINISH = 3

    def __init__(self, main_window, project_file, project_data, parent=None):
        super().__init__(parent)

        self.main_window = main_window
        self.project_file = project_file
        self.project_data = project_data

        self.setWindowTitle("Website Wizard")
        self.resize(720, 520)

        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.HaveHelpButton, False)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.NoBackButtonOnLastPage, False)

        self.addPage(WelcomePage(self))
        self.addPage(WebsitePage(self))
        self.addPage(ContentPage(self))
        self.addPage(FinishPage(self))

        self.currentIdChanged.connect(self.on_page_changed)
        self.finished.connect(self.on_finished)

    def on_page_changed(self, page_id):
        pass

    def collect_data(self):
        return {
            "host_name": self.field("host_name"),
            "port": self.field("port"),
            "use_ssl": self.field("use_ssl"),
            "title": self.field("site_title"),
            "description": self.field("site_description"),
        }

    def save_to_project(self):
        data = self.collect_data()

        wizard_data = self.project_data.setdefault("website_wizard", {})
        wizard_data.update(data)

        if hasattr(self.main_window, "save_project_file") and self.project_file:
            self.main_window.save_project_file(self.project_file, self.project_data)

    def on_finished(self, result):
        if result == QWizard.Accepted:
            self.save_to_project()


class WelcomePage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Willkommen")
        self.setSubTitle("Dieser Assistent richtet eine Client-Website ein.")

        layout = QVBoxLayout(self)

        label = QLabel(
            "Der Wizard führt dich Schritt für Schritt durch die Einrichtung."
        )
        label.setWordWrap(True)

        layout.addWidget(label)
        layout.addStretch(1)


class WebsitePage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Website")
        self.setSubTitle("Hostname, Port und SSL einstellen.")

        layout = QVBoxLayout(self)

        host_row = QHBoxLayout()
        host_row.addWidget(QLabel("Hostname:"))

        self.host_edit = QLineEdit(self)
        self.host_edit.setPlaceholderText("z. B. client1.servera")
        self.host_edit.setMaxLength(64)

        host_row.addWidget(self.host_edit, 1)
        layout.addLayout(host_row)

        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Port:"))

        self.port_edit = QLineEdit(self)
        self.port_edit.setText("80")
        self.port_edit.setMaxLength(5)

        port_row.addWidget(self.port_edit)
        port_row.addStretch(1)
        layout.addLayout(port_row)

        self.ssl_check = QCheckBox("Use SSL", self)
        layout.addWidget(self.ssl_check)

        layout.addStretch(1)

        self.registerField("host_name*", self.host_edit)
        self.registerField("port", self.port_edit)
        self.registerField("use_ssl", self.ssl_check)

    def validatePage(self):
        port_text = self.port_edit.text().strip()

        try:
            port = int(port_text)
        except ValueError:
            QMessageBox.warning(
                self,
                "Port",
                "Bitte einen gültigen Port von 0 bis 65535 eingeben."
            )
            return False

        if port < 0 or port > 65535:
            QMessageBox.warning(
                self,
                "Port",
                "Der Port muss zwischen 0 und 65535 liegen."
            )
            return False

        return True


class ContentPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Inhalt")
        self.setSubTitle("Titel und Beschreibung der Website festlegen.")

        layout = QVBoxLayout(self)

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Titel:"))

        self.title_edit = QLineEdit(self)
        self.title_edit.setPlaceholderText("Website-Titel")

        title_row.addWidget(self.title_edit, 1)
        layout.addLayout(title_row)

        layout.addWidget(QLabel("Beschreibung:"))

        self.description_edit = QTextEdit(self)
        self.description_edit.setFont(QFont("Consolas", 10))

        layout.addWidget(self.description_edit, 1)

        self.registerField("site_title", self.title_edit)
        self.registerField("site_description", self.description_edit, "plainText")


class FinishPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Fertigstellen")
        self.setSubTitle("Die Einstellungen können jetzt übernommen werden.")

        layout = QVBoxLayout(self)

        self.summary = QLabel(self)
        self.summary.setWordWrap(True)

        layout.addWidget(self.summary)
        layout.addStretch(1)

    def initializePage(self):
        wizard = self.wizard()

        host = wizard.field("host_name")
        port = wizard.field("port")
        ssl = wizard.field("use_ssl")
        title = wizard.field("site_title")

        self.summary.setText(
            f"Hostname: {host}\n"
            f"Port: {port}\n"
            f"Use SSL: {'YES' if ssl else 'NO'}\n"
            f"Titel: {title}"
        )


def open_website_wizard(main_window, project_file, project_data):
    wizard = WebsiteWizard(main_window, project_file, project_data)

    if hasattr(main_window, "add_mdi_widget"):
        sub = main_window.add_mdi_widget(
            wizard,
            "Website Wizard",
            760,
            560,
        )
        sub.project_file = os.path.abspath(project_file) if project_file else ""
        sub.window_role = "website_wizard"
        return sub

    wizard.show()
    return wizard
