# ---------------------------------------------------------------------------------------
# file: user_management_dialog.py
# author: (c) 2026 Jens Kallup - paule32
# all rights reserved.
# ---------------------------------------------------------------------------------------
# User management dialog for the application.
#
# Schema:
# - Gruppen:  IISGRP_<id>, z.B. IISGRP_0001
# - Benutzer: IISUSR_<id>, z.B. IISUSR_0001
# - AppPools: IIS_APP_<id>, z.B. IIS_APP_0001
#
# Benutzer-Tree:
# IISUSR_0001
#     AppPool      | <editierbarer Wert, max. 20 Zeichen>
#     HTML Pfad    | <editierbarer Wert, max. 20 Zeichen, Doppelklick = Ordnerdialog>
#     Hostname     | <editierbarer Wert, max. 20 Zeichen>
#     Port         | <InlineSpinEdit 0..65535, Default 80>
#     Use SSL      | <QCheckBox>
#     Certificate  | <QComboBox aus LocalMachine/CurrentUser Zertifikaten>
#
# Die linke Eigenschaftsspalte ist nicht editierbar. Nur die rechte
# Wert-Spalte ist editierbar.
# ---------------------------------------------------------------------------------------
import ctypes
import json
import os
import re
import subprocess
from copy import deepcopy

from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal
)
from PyQt5.QtGui import QFont, QBrush, QColor
from PyQt5.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSplitter,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QInputDialog, QLineEdit, QDialogButtonBox,
    QGroupBox, QPlainTextEdit, QFileDialog, QStyledItemDelegate, QSpinBox, QCheckBox,
    QComboBox,
)
from InlineSpinEdit import InlineSpinEdit

GROUP_PREFIX     = "IISGRP_"
USER_PREFIX      = "IISUSR_"
APP_POOL_PREFIX  = "IIS_APP_"

DEFAULT_PASSWORD          = "ChangeMe-123!"
MAX_VALUE_TEXT_LEN        = 20
MAX_HTML_PATH_LEN         = 512
MAX_LOCAL_DESCRIPTION_LEN = 48

ROLE_USER          = "user"
ROLE_GROUP         = "group"

ROLE_APP_POOL      = "app_pool"
ROLE_HTML_PATH     = "html_path"

ROLE_HOST_NAME     = "host_name"
ROLE_PORT          = "port"

ROLE_USE_SSL       = "use_ssl"

ROLE_CERTIFICATE   = "certificate"
ROLE_CERT_THUMB    = "cert_thumb"
ROLE_CERT_UNTIL    = "cert_until"
ROLE_CERT_COUNTRY  = "cert_country"
ROLE_CERT_LOCATION = "cert_location"
ROLE_CERT_OU       = "cert_ou"
ROLE_CERT_ORG      = "cert_org"

FONT_FAMILY = "Arial"
FONT_POINT_SIZE = 10

CERT_HEADER_BG = "#7A0026"
CERT_HEADER_FG = "#FFD866"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def ps_quote(value):
    text = str(value or "").replace("'", "''")
    return "'" + text + "'"


def safe_text20(value):
    return str(value or "").strip()[:MAX_VALUE_TEXT_LEN]


def normalize_bool(value):
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in ("1", "true", "yes", "ja", "enabled", "on")


def only_numeric_suffix(name, prefix):
    match = re.match(r"^" + re.escape(prefix) + r"(\d+)$", str(name or ""), re.I)
    if not match:
        return None
    return int(match.group(1))


def normalize_id(value):
    return f"{int(value):04d}"


def group_name_from_id(idx):
    return f"{GROUP_PREFIX}{normalize_id(idx)}"


def user_name_from_id(idx):
    return f"{USER_PREFIX}{normalize_id(idx)}"


def app_pool_from_user_name(user_name):
    idx = only_numeric_suffix(user_name, USER_PREFIX)
    if idx is None:
        return safe_text20(APP_POOL_PREFIX + re.sub(r"[^A-Za-z0-9_-]", "_", str(user_name or "0001")))
    return safe_text20(f"{APP_POOL_PREFIX}{normalize_id(idx)}")


def make_description(name):
    return f"IIS Setup: {name}"[:MAX_LOCAL_DESCRIPTION_LEN]


def website_settings(user):
    settings = user.setdefault("settings", {})
    return settings.setdefault("website", {})


def get_user_app_pool(user):
    return safe_text20(user.get("app_pool") or website_settings(user).get("app_pool") or app_pool_from_user_name(user.get("system_name", "")))


def get_user_html_path(user):
    return str(user.get("html_path") or website_settings(user).get("html_path") or "").strip()[:MAX_HTML_PATH_LEN]


def get_user_host_name(user):
    return safe_text20(user.get("host_name") or website_settings(user).get("host_name") or "")


def get_user_port(user):
    try:
        port = int(user.get("port", website_settings(user).get("port", 80)))
    except Exception:
        port = 80
    return max(0, min(65535, port))


def get_user_use_ssl(user):
    return normalize_bool(user.get("use_ssl", website_settings(user).get("use_ssl", False)))


def get_user_certificate(user):
    value = user.get("certificate")
    if value is None:
        value = website_settings(user).get("certificate", "")
    if isinstance(value, dict):
        return value
    return str(value or "")


def set_website_value(user, key, value):
    ws = website_settings(user)
    if key in ("app_pool", "host_name"):
        value = safe_text20(value)
    elif key == "html_path":
        value = str(value or "").strip()[:MAX_HTML_PATH_LEN]
    elif key == "port":
        try:
            value = int(value)
        except Exception:
            value = 80
        value = max(0, min(65535, value))
    elif key == "use_ssl":
        value = bool(value)
    elif key == "certificate" and isinstance(value, dict):
        value = deepcopy(value)
    else:
        value = str(value or "")

    user[key] = value
    ws[key] = value
    return value


def next_id(snapshot, key, prefix):
    snapshot = normalize_snapshot(snapshot)
    used = set()
    for item in snapshot.get(key, []):
        name = item.get("name") or item.get("system_name") or ""
        idx = only_numeric_suffix(name, prefix)
        if idx is not None:
            used.add(idx)
    idx = 1
    while idx in used:
        idx += 1
    return idx


def normalize_snapshot(snapshot):
    snapshot = snapshot or {}
    groups = []
    users = []
    app_pools = []

    for group in snapshot.get("groups", []):
        name = str(group.get("name", "") or "")
        if not name.startswith(GROUP_PREFIX):
            continue
        members = []
        for member in group.get("users", []):
            member_name = str(member or "")
            if member_name.startswith(USER_PREFIX):
                members.append(member_name)
        groups.append({
            "name": name,
            "description": str(group.get("description", "") or ""),
            "users": sorted(set(members), key=str.lower),
        })

    for user in snapshot.get("users", []):
        system_name = str(user.get("system_name") or user.get("name") or "")
        if not system_name.startswith(USER_PREFIX):
            continue
        normalized = {
            "system_name": system_name,
            "name": system_name,
            "display_name": str(user.get("display_name") or system_name),
            "full_name": str(user.get("full_name") or user.get("display_name") or system_name),
            "description": str(user.get("description", "") or ""),
            "enabled": normalize_bool(user.get("enabled", True)),
            "settings": deepcopy(user.get("settings", {})),
        }
        set_website_value(normalized, "app_pool", user.get("app_pool") or website_settings(normalized).get("app_pool") or app_pool_from_user_name(system_name))
        set_website_value(normalized, "html_path", user.get("html_path") or website_settings(normalized).get("html_path") or "")
        set_website_value(normalized, "host_name", user.get("host_name") or website_settings(normalized).get("host_name") or "")
        set_website_value(normalized, "port", user.get("port", website_settings(normalized).get("port", 80)))
        set_website_value(normalized, "use_ssl", user.get("use_ssl", website_settings(normalized).get("use_ssl", False)))
        set_website_value(normalized, "certificate", user.get("certificate") or website_settings(normalized).get("certificate") or "")
        users.append(normalized)
        app_pools.append({"name": get_user_app_pool(normalized)})

    for pool in snapshot.get("app_pools", []):
        name = str(pool.get("name", "") or "")
        if name.startswith(APP_POOL_PREFIX):
            app_pools.append({"name": safe_text20(name)})

    groups.sort(key=lambda item: item["name"].lower())
    users.sort(key=lambda item: item["system_name"].lower())

    seen = set()
    unique_pools = []
    for pool in sorted(app_pools, key=lambda item: item["name"].lower()):
        name = pool["name"]
        if name in seen:
            continue
        seen.add(name)
        unique_pools.append({"name": name})

    return {
        "group_prefix": GROUP_PREFIX,
        "user_prefix": USER_PREFIX,
        "app_pool_prefix": APP_POOL_PREFIX,
        "groups": groups,
        "users": users,
        "app_pools": unique_pools,
    }


def merge_snapshots(project_snapshot, system_snapshot):
    project_snapshot = normalize_snapshot(project_snapshot)
    system_snapshot = normalize_snapshot(system_snapshot)
    groups = {g["name"]: deepcopy(g) for g in project_snapshot["groups"]}
    users = {u["system_name"]: deepcopy(u) for u in project_snapshot["users"]}
    app_pools = {p["name"]: deepcopy(p) for p in project_snapshot["app_pools"]}

    for group in system_snapshot["groups"]:
        name = group["name"]
        if name not in groups:
            groups[name] = deepcopy(group)
        else:
            merged_users = set(groups[name].get("users", []))
            merged_users.update(group.get("users", []))
            groups[name]["users"] = sorted(merged_users, key=str.lower)
            groups[name]["description"] = group.get("description", groups[name].get("description", ""))

    for user in system_snapshot["users"]:
        key = user["system_name"]
        if key not in users:
            users[key] = deepcopy(user)
        else:
            users[key]["enabled"] = user.get("enabled", users[key].get("enabled", True))
            users[key]["description"] = user.get("description", users[key].get("description", ""))

    for pool in system_snapshot["app_pools"]:
        app_pools[pool["name"]] = deepcopy(pool)

    return normalize_snapshot({"groups": list(groups.values()), "users": list(users.values()), "app_pools": list(app_pools.values())})


def snapshots_are_different(a, b):
    return normalize_snapshot(a) != normalize_snapshot(b)


class ValueDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setFont(QFont(FONT_FAMILY, FONT_POINT_SIZE))
            editor.setTextMargins(0, 0, 0, 0)
            editor.setMaxLength(MAX_VALUE_TEXT_LEN)
            editor.setStyleSheet("QLineEdit { margin: 0px; padding: 0px; }")

        return editor


class ManagedUserTreeWidget(QTreeWidget):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F2:
            item = self.currentItem()
            if item and self.currentColumn() == 1 and item.data(0, Qt.UserRole) in (ROLE_APP_POOL, ROLE_HTML_PATH, ROLE_HOST_NAME):
                self.editItem(item, 1)
            return
        super().keyPressEvent(event)


class LocalUserGroupBackend:
    def run_json(self, ps_script):
        result = subprocess.run([
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " + ps_script,
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        text = result.stdout.strip()
        return json.loads(text) if text else {}

    def run_plain(self, ps_script):
        result = subprocess.run([
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " + ps_script,
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()

    def get_snapshot(self):
        ps_script = r'''
$groupPrefix = 'IISGRP_'
$userPrefix  = 'IISUSR_'
$appPrefix   = 'IIS_APP_'

$groups = Get-LocalGroup |
    Where-Object { $_.Name -like "$groupPrefix*" } |
    Sort-Object Name |
    ForEach-Object {
        $members = @()
        try {
            $members = Get-LocalGroupMember -Group $_.Name -ErrorAction Stop |
                Where-Object { $_.ObjectClass -eq "User" } |
                ForEach-Object {
                    $name = $_.Name
                    if ($name.Contains('\')) { $name = $name.Substring($name.LastIndexOf('\') + 1) }
                    $name
                } |
                Where-Object { $_ -like "$userPrefix*" }
        } catch { $members = @() }
        [PSCustomObject]@{ name = $_.Name; description = $_.Description; users = @($members | Sort-Object -Unique) }
    }

$users = Get-LocalUser |
    Where-Object { $_.Name -like "$userPrefix*" } |
    Sort-Object Name |
    ForEach-Object {
        $id = $_.Name.Substring($userPrefix.Length)
        $appPool = $appPrefix + $id
        [PSCustomObject]@{
            system_name  = $_.Name
            name         = $_.Name
            display_name = $_.Name
            full_name    = $_.FullName
            description  = $_.Description
            enabled      = [bool]$_.Enabled
            app_pool     = $appPool
            settings     = @{ website = @{ app_pool = $appPool; html_path = ''; host_name = ''; port = 80; use_ssl = $false; certificate = '' } }
        }
    }

$appPools = @()
try {
    Import-Module WebAdministration -ErrorAction Stop
    $appPools = Get-ChildItem "IIS:\AppPools" |
        Where-Object { $_.Name -like "$appPrefix*" } |
        Sort-Object Name |
        ForEach-Object { [PSCustomObject]@{ name = $_.Name } }
} catch { $appPools = @() }

[PSCustomObject]@{ groups = @($groups); users = @($users); app_pools = @($appPools) } | ConvertTo-Json -Depth 10
'''
        return normalize_snapshot(self.run_json(ps_script))

    def get_certificates(self):
        ps_script = r'''
$items = @()
foreach ($scope in @('LocalMachine', 'CurrentUser')) {
    foreach ($store in @('My', 'WebHosting')) {
        $path = "Cert:\$scope\$store"
        if (Test-Path $path) {
            Get-ChildItem $path | ForEach-Object {
                $subject = $_.Subject
                if ([string]::IsNullOrWhiteSpace($subject)) { $subject = $_.DnsNameList.Unicode -join ',' }
                [PSCustomObject]@{
                    text       = "$scope/$store - $subject - $($_.Thumbprint)"
                    value      = "$scope|$store|$($_.Thumbprint)"
                    scope      = $scope
                    store      = $store
                    thumbprint = $_.Thumbprint
                    subject    = $subject
                }
            }
        }
    }
}
$items | ConvertTo-Json -Depth 6
'''
        try:
            data = self.run_json(ps_script)
            if isinstance(data, dict):
                return [data]
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def add_group(self, name):
        ps_script = f"""
$name = {ps_quote(name)}
$description = {ps_quote(make_description(name))}
if (-not (Get-LocalGroup -Name $name -ErrorAction SilentlyContinue)) {{
    New-LocalGroup -Name $name -Description $description | Out-Null
}} else {{
    Set-LocalGroup -Name $name -Description $description
}}
"""
        self.run_plain(ps_script)

    def delete_group(self, name):
        ps_script = f"""
$name = {ps_quote(name)}
if (Get-LocalGroup -Name $name -ErrorAction SilentlyContinue) {{ Remove-LocalGroup -Name $name }}
"""
        self.run_plain(ps_script)

    def add_user(self, system_name, password, group_name=None, app_pool=None):
        app_pool = app_pool or app_pool_from_user_name(system_name)
        ps_script = f"""
$name = {ps_quote(system_name)}
$description = {ps_quote(make_description(system_name))}
$passwordText = {ps_quote(password)}
$securePassword = ConvertTo-SecureString $passwordText -AsPlainText -Force
if (-not (Get-LocalUser -Name $name -ErrorAction SilentlyContinue)) {{
    New-LocalUser -Name $name -FullName $name -Description $description -Password $securePassword -PasswordNeverExpires | Out-Null
}} else {{
    Set-LocalUser -Name $name -FullName $name -Description $description
}}
"""
        if group_name:
            ps_script += f"""
$groupName = {ps_quote(group_name)}
try {{ Add-LocalGroupMember -Group $groupName -Member $name -ErrorAction Stop }} catch {{ }}
"""
        self.run_plain(ps_script)
        self.create_or_update_app_pool(app_pool)

    def delete_user(self, system_name, app_pool=None):
        ps_script = f"""
$name = {ps_quote(system_name)}
if (Get-LocalUser -Name $name -ErrorAction SilentlyContinue) {{ Remove-LocalUser -Name $name }}
"""
        self.run_plain(ps_script)
        if app_pool:
            self.delete_app_pool(app_pool)

    def create_or_update_app_pool(self, app_pool):
        app_pool = safe_text20(app_pool)
        ps_script = f"""
$appPool = {ps_quote(app_pool)}
Import-Module WebAdministration -ErrorAction Stop
$path = "IIS:\\AppPools\\$appPool"
if (-not (Test-Path $path)) {{ New-WebAppPool -Name $appPool | Out-Null }}
Set-ItemProperty $path -Name processModel.identityType -Value ApplicationPoolIdentity
"""
        self.run_plain(ps_script)

    def delete_app_pool(self, app_pool):
        ps_script = f"""
$appPool = {ps_quote(app_pool)}
Import-Module WebAdministration -ErrorAction Stop
$path = "IIS:\\AppPools\\$appPool"
if (Test-Path $path) {{ Remove-WebAppPool -Name $appPool }}
"""
        self.run_plain(ps_script)

    def get_personal_certificates(self):
        ps_script = r"""
function Get-CertItems($scopeName, $path) {
    try {
        Get-ChildItem $path -ErrorAction Stop |
            Where-Object { $_.HasPrivateKey -or $_.Subject -or $_.DnsNameList } |
            Sort-Object Subject, NotAfter |
            ForEach-Object {
                $dns = ""
                try {
                    if ($_.DnsNameList) {
                        $dns = ($_.DnsNameList | ForEach-Object { $_.Unicode }) -join ", "
                    }
                } catch {
                    $dns = ""
                }

                $label = $_.Subject

                if ([string]::IsNullOrWhiteSpace($label)) {
                    $label = $_.FriendlyName
                }

                if ([string]::IsNullOrWhiteSpace($label)) {
                    $label = $_.Thumbprint
                }

                [PSCustomObject]@{
                    scope       = $scopeName
                    store       = "My"
                    label       = $label
                    subject     = $_.Subject
                    friendly    = $_.FriendlyName
                    dns         = $dns
                    thumbprint  = $_.Thumbprint
                    not_after   = $_.NotAfter.ToString("yyyy-MM-dd HH:mm:ss")
                    has_private = [bool]$_.HasPrivateKey
                }
            }
    } catch {
        @()
    }
}

[PSCustomObject]@{
    CurrentUser  = @(Get-CertItems "CurrentUser"  "Cert:\CurrentUser\My")
    LocalMachine = @(Get-CertItems "LocalMachine" "Cert:\LocalMachine\My")
} | ConvertTo-Json -Depth 8
"""
        data = self.run_json(ps_script)

        if not isinstance(data, dict):
            return {"CurrentUser": [], "LocalMachine": []}

        return {
            "CurrentUser": data.get("CurrentUser") or [],
            "LocalMachine": data.get("LocalMachine") or [],
        }


class PingThread(QThread):
    finished_ping = pyqtSignal(str, bool, str)

    def __init__(self, host, timeout_ms=1000, parent=None):
        super().__init__(parent)
        self.host = host
        self.timeout_ms = timeout_ms

    def run(self):
        try:
            result = subprocess.run(
                [
                    "ping",
                    "-n", "1",
                    "-w", str(self.timeout_ms),
                    self.host
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=(self.timeout_ms / 1000.0) + 1
            )

            ok = result.returncode == 0
            error = ""

        except subprocess.TimeoutExpired:
            ok = False
            error = "Timeout"

        except Exception as exc:
            ok = False
            error = str(exc)

        self.finished_ping.emit(self.host, ok, error)


class UserDiffDialog(QDialog):
    def __init__(self, project_snapshot, system_snapshot, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User/Group Sync")
        self.resize(1000, 500)
        self.project_snapshot = normalize_snapshot(project_snapshot)
        self.system_snapshot = normalize_snapshot(system_snapshot)
        self.selected_actions = []

        layout = QVBoxLayout(self)
        info = QLabel("Es wurden Unterschiede zwischen Projekt-JSON und System gefunden.")
        info.setWordWrap(True)
        layout.addWidget(info)
        self.tree = QTreeWidget(self)
        self.tree.setFont(QFont(FONT_FAMILY, FONT_POINT_SIZE))
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Übernehmen", "Aktion", "Name"])
        layout.addWidget(self.tree, 1)
        box = QGroupBox("Details", self)
        box_layout = QVBoxLayout(box)
        self.preview = QPlainTextEdit(self)
        self.preview.setReadOnly(True)
        box_layout.addWidget(self.preview)
        layout.addWidget(box)
        buttons = QDialogButtonBox(self)
        buttons.addButton("Apply", QDialogButtonBox.AcceptRole)
        buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)
        self.tree.itemChanged.connect(self.update_preview)
        self.populate()
        self.update_preview()

    def populate(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        project_groups = {g["name"]: g for g in self.project_snapshot["groups"]}
        system_groups = {g["name"]: g for g in self.system_snapshot["groups"]}
        project_users = {u["system_name"]: u for u in self.project_snapshot["users"]}
        system_users = {u["system_name"]: u for u in self.system_snapshot["users"]}
        root_system = QTreeWidgetItem(["", "Vom System ins Projekt übernehmen", ""])
        root_project = QTreeWidgetItem(["", "Vom Projekt ins System übernehmen", ""])
        self.tree.addTopLevelItem(root_system)
        self.tree.addTopLevelItem(root_project)
        for name in sorted(set(system_groups) - set(project_groups), key=str.lower):
            self.add_action_item(root_system, "import_group", name, f"Gruppe: {name}")
        for key in sorted(set(system_users) - set(project_users), key=str.lower):
            self.add_action_item(root_system, "import_user", key, f"Benutzer: {key}")
        for name in sorted(set(project_groups) - set(system_groups), key=str.lower):
            self.add_action_item(root_project, "create_group", name, f"Gruppe: {name}")
        for key in sorted(set(project_users) - set(system_users), key=str.lower):
            self.add_action_item(root_project, "create_user", key, f"Benutzer: {key}")
        root_system.setExpanded(True)
        root_project.setExpanded(True)
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)
        self.tree.blockSignals(False)

    def add_action_item(self, parent, action, key, text):
        item = QTreeWidgetItem(["", action, text])
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Unchecked)
        item.setData(0, Qt.UserRole, {"action": action, "key": key})
        parent.addChild(item)

    def iter_action_items(self):
        for i in range(self.tree.topLevelItemCount()):
            root = self.tree.topLevelItem(i)
            for j in range(root.childCount()):
                yield root.child(j)

    def update_preview(self):
        lines = []
        for item in self.iter_action_items():
            if item.checkState(0) == Qt.Checked:
                data = item.data(0, Qt.UserRole)
                if data:
                    lines.append(f"{data['action']}: {data['key']}")
        self.preview.setPlainText("\n".join(lines) if lines else "Keine Aktion ausgewählt.")

    def apply(self):
        self.selected_actions = []
        for item in self.iter_action_items():
            if item.checkState(0) == Qt.Checked:
                data = item.data(0, Qt.UserRole)
                if data:
                    self.selected_actions.append(data)
        self.accept()


class UserManagementWindow(QWidget):
    def __init__(self, main_window, project_data, project_file=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.project_data = project_data
        self.project_file = project_file
        self.backend = LocalUserGroupBackend()
        self.snapshot = normalize_snapshot(project_data.get("user_management", {}))
        self.certificates = []
        self._loading = False
        self._dirty = False
        self._initial_snapshot = normalize_snapshot(self.snapshot)
        self._saved_snapshot = deepcopy(self._initial_snapshot)
        self._closing_without_save = False
        self.setObjectName("UserManagementWindow")
        self.build_ui()
        self.reload_from_system()

    def load_certificates(self):
        try:
            return self.backend.get_personal_certificates()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Certificate",
                "Die Zertifikate konnten nicht gelesen werden:\n\n" + str(exc)
            )
            return {"CurrentUser": [], "LocalMachine": []}

    def parse_subject_parts(self, subject):
        parts = {
            "CN": "",
            "O": "",
            "OU": "",
            "L": "",
            "C": "",
        }

        text = str(subject or "")

        for key in parts:
            match = re.search(r"(?:^|,)\s*" + re.escape(key) + r"\s*=\s*([^,]+)", text)
            if match:
                parts[key] = match.group(1).strip()

        return parts

    def certificate_cn_text(self, cert):
        subject = cert.get("subject") or cert.get("label") or ""
        parts = self.parse_subject_parts(subject)
        cn = parts.get("CN") or cert.get("label") or cert.get("friendly") or cert.get("thumbprint") or ""
        if cn.startswith("CN="):
            return cn
        return "CN=" + cn if cn else ""

    def certificate_detail_values(self, cert):
        subject = cert.get("subject") or cert.get("label") or ""
        parts = self.parse_subject_parts(subject)

        return {
            "org": "O=" + parts["O"] if parts["O"] else "",
            "ou": "OU=" + parts["OU"] if parts["OU"] else "",
            "location": "L=" + parts["L"] if parts["L"] else "",
            "country": "C=" + parts["C"] if parts["C"] else "",
            "until": "until " + str(cert.get("not_after", "")) if cert.get("not_after") else "",
            "thumb": cert.get("thumbprint", "") or "",
        }

    def certificate_display_text(self, cert):
        return self.certificate_cn_text(cert)

    def certificate_value(self, cert):
        return {
            "scope": cert.get("scope", ""),
            "store": cert.get("store", "My"),
            "thumbprint": cert.get("thumbprint", ""),
            "subject": cert.get("subject", ""),
            "label": cert.get("label", ""),
            "not_after": cert.get("not_after", ""),
        }

    def add_certificate_header(self, combo, title):
        combo.addItem(title, None)
        index = combo.count() - 1
        combo.setItemData(index, 0, Qt.UserRole - 1)
        combo.setItemData(index, QBrush(QColor(CERT_HEADER_BG)), Qt.BackgroundRole)
        combo.setItemData(index, QBrush(QColor(CERT_HEADER_FG)), Qt.ForegroundRole)

    def selected_certificate_from_combo(self, combo):
        value = combo.currentData()
        if isinstance(value, dict):
            return value
        return None

    def update_certificate_detail_items(self, system_name, cert):
        if not hasattr(self, "_certificate_detail_items"):
            return

        items = self._certificate_detail_items.get(system_name)
        if not items:
            return

        details = self.certificate_detail_values(cert or {})

        self._loading = True
        items.get("org").setText(1, details["org"])
        items.get("ou").setText(1, details["ou"])
        items.get("location").setText(1, details["location"])
        items.get("country").setText(1, details["country"])
        items.get("until").setText(1, details["until"])
        items.get("thumb").setText(1, details["thumb"])
        self._loading = False

    def fill_certificate_combo(self, combo, selected_value):
        combo.blockSignals(True)
        combo.clear()

        combo.addItem("", "")
        certificates = self.load_certificates()

        selected_thumbprint = ""
        selected_scope = ""

        if isinstance(selected_value, dict):
            selected_thumbprint = selected_value.get("thumbprint", "")
            selected_scope = selected_value.get("scope", "")
            selected_store = selected_value.get("store", "")
        else:
            selected_thumbprint = str(selected_value or "")
            selected_store = ""

        for title, key in (("CurrentUser", "CurrentUser"), ("LocalMaschine", "LocalMachine")):
            self.add_certificate_header(combo, title)

            certs = certificates.get(key) or []

            if not certs:
                combo.addItem("  <keine Zertifikate gefunden>", None)
                idx = combo.count() - 1
                combo.setItemData(idx, 0, Qt.UserRole - 1)
                continue

            for cert in certs:
                combo.addItem("  " + self.certificate_display_text(cert), self.certificate_value(cert))
                idx = combo.count() - 1

                if (
                    cert.get("thumbprint", "") == selected_thumbprint
                    and (not selected_scope or cert.get("scope", "") == selected_scope)
                    and (not selected_store or cert.get("store", "My") == selected_store)
                ):
                    combo.setCurrentIndex(idx)

        combo.blockSignals(False)

    def build_ui(self):
        layout = QVBoxLayout(self)
        self.splitter = QSplitter(Qt.Horizontal, self)
        layout.addWidget(self.splitter, 1)
        font = QFont(FONT_FAMILY, FONT_POINT_SIZE)

        left = QWidget(self)
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Benutzer", left))
        
        self.user_tree = ManagedUserTreeWidget(left)
        self.user_tree.setFont(font)
        self.user_tree.setItemDelegate(ValueDelegate(self.user_tree))
        self.user_tree.setColumnCount(3)
        self.user_tree.setHeaderLabels(["Property", "Value", "Active"])
        self.user_tree.setEditTriggers(QTreeWidget.DoubleClicked | QTreeWidget.EditKeyPressed | QTreeWidget.SelectedClicked)
        self.user_tree.setColumnWidth(1, 250)
        
        left_layout.addWidget(self.user_tree, 1)
        user_buttons = QHBoxLayout()
        self.add_user_button = QPushButton("Add", left)
        self.delete_user_button = QPushButton("Delete", left)
        user_buttons.addWidget(self.add_user_button)
        user_buttons.addWidget(self.delete_user_button)
        user_buttons.addStretch(1)
        left_layout.addLayout(user_buttons)

        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Gruppen", right))
        self.group_tree = QTreeWidget(right)
        self.group_tree.setFont(font)
        self.group_tree.setColumnCount(2)
        self.group_tree.setHeaderLabels(["Gruppe", "Beschreibung"])
        right_layout.addWidget(self.group_tree, 1)
        group_buttons = QHBoxLayout()
        self.add_group_button = QPushButton("Add", right)
        self.delete_group_button = QPushButton("Delete", right)
        group_buttons.addWidget(self.add_group_button)
        group_buttons.addWidget(self.delete_group_button)
        group_buttons.addStretch(1)
        right_layout.addLayout(group_buttons)

        self.splitter.addWidget(left)
        self.splitter.addWidget(right)
        self.splitter.setSizes([832, 360])
        
        self.group_tree.itemSelectionChanged.connect(self.on_group_selection_changed)
        self.user_tree.itemChanged.connect(self.on_user_item_changed)
        self.user_tree.itemDoubleClicked.connect(self.on_user_item_double_clicked)
        self.add_group_button.clicked.connect(self.add_group)
        self.delete_group_button.clicked.connect(self.delete_group)
        self.add_user_button.clicked.connect(self.add_user)
        self.delete_user_button.clicked.connect(self.delete_user)

    def mark_dirty(self):
        if self._loading:
            return
        self._dirty = snapshots_are_different(self.snapshot, self._saved_snapshot)

    def has_unsaved_changes(self):
        return self._dirty or snapshots_are_different(self.snapshot, self._saved_snapshot)

    def save_changes(self):
        self.project_data["user_management"] = normalize_snapshot(self.snapshot)
        self.save_project()
        self._saved_snapshot = normalize_snapshot(self.snapshot)
        self._dirty = False

    def closeEvent(self, event):
        if self._closing_without_save:
            event.accept()
            return

        if not self.has_unsaved_changes():
            event.accept()
            return

        result = QMessageBox.question(
            self,
            "User Management",
            "Es wurden Änderungen vorgenommen.\n\nSollen die Daten in der Projektdatei gespeichert werden?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )

        if result == QMessageBox.Yes:
            self.save_changes()
            event.accept()
            return

        if result == QMessageBox.No:
            self._closing_without_save = True
            event.accept()
            return

        event.ignore()
        self.setFocus(Qt.OtherFocusReason)
        self.activateWindow()

    def set_html_acl(self, item):
        self.user_tree.closePersistentEditor(item, 1)
        self.user_tree.clearFocus()
        
        self.setFocus(Qt.OtherFocusReason)
        path_name = item.text(1).strip()
        
        if not path_name:
            QMessageBox.information(self,
                "Set Path ACL...",
                "No path name to set ACL (path name is empty).")
            return
        
        data = item.data(0, Qt.UserRole) or {}
        
        if isinstance(data, dict):
            system_name = data.get("system_name", "")
        else:
            system_name = str(data or "")
            
        user = self.find_user(system_name)
        
        if user:
            set_user_host_name(user, host_name)
            self.project_data["user_management"] = normalize_snapshot(self.snapshot)
            self.mark_dirty()
        
        self.set_html_path_acl(path_name)
    
    def set_html_path_acl(self, path_name):
        QMessageBox.information(self,
        "TODO",
        "ToDo: set path acl")
        return
        
    def check_host_silent(self, host):
        self.ping_thread = PingThread(host, timeout_ms=1000, parent=self)
        self.ping_thread.finished_ping.connect(self.on_ping_finished)
        self.ping_thread.start()
        
    def check_hostname_item(self, item):
        self.user_tree.closePersistentEditor(item, 1)
        self.user_tree.clearFocus()
        
        self.setFocus(Qt.OtherFocusReason)
        host_name = item.text(1).strip()
        
        if not host_name:
            QMessageBox.information(self,
                "Check Hostname...",
                "No hostname to check (hostname is empty).")
            return
        
        data = item.data(0, Qt.UserRole) or {}
        
        if isinstance(data, dict):
            system_name = data.get("system_name", "")
        else:
            system_name = str(data or "")
            
        user = self.find_user(system_name)
        
        if user:
            set_user_host_name(user, host_name)
            self.project_data["user_management"] = normalize_snapshot(self.snapshot)
            self.mark_dirty()
        
        self.check_host_silent(host_name)
        
    def on_ping_finished(self, host, ok, error):
        if ok:
            QMessageBox.information(self,
            "Host Ping...",
            f"The host: {host}\nis reachable.")
            return
        else:
            QMessageBox.warning(self,
            "Host Ping...",
            f"The host: {host}\nis not reachable.")
            return
        
    def selected_certificate_key(self, value):
        if isinstance(value, dict):
            return (
                str(value.get("scope", "")),
                str(value.get("store", "")),
                str(value.get("thumbprint", "")),
            )
        return ("", "", str(value or ""))

    def current_user_has_unsaved_changes(self, system_name):
        saved_users = {
            user.get("system_name", ""): user
            for user in self._saved_snapshot.get("users", [])
        }
        current_user = self.find_user(system_name)
        saved_user = saved_users.get(system_name)
        if not current_user or not saved_user:
            return False
        return normalize_snapshot({"users": [current_user]}) != normalize_snapshot({"users": [saved_user]})

    def ask_save_current_user_changes(self):
        system_name = getattr(self, "_current_user_system_name", "")
        if not system_name or not self.current_user_has_unsaved_changes(system_name):
            return True
        result = QMessageBox.question(
            self,
            "User Management",
            f"Für den Benutzer '{system_name}' wurden Änderungen vorgenommen.\n\nSollen die Daten gespeichert werden?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if result == QMessageBox.Cancel:
            self.setFocus(Qt.OtherFocusReason)
            self.activateWindow()
            return False
        if result == QMessageBox.Yes:
            self.save_changes()
            return True
        if result == QMessageBox.No:
            self.restore_user_from_saved_snapshot(system_name)
            self._dirty = snapshots_are_different(self.snapshot, self._saved_snapshot)
            return True
        return False

    def restore_user_from_saved_snapshot(self, system_name):
        saved_users = {
            user.get("system_name", ""): deepcopy(user)
            for user in self._saved_snapshot.get("users", [])
        }
        saved_user = saved_users.get(system_name)
        if not saved_user:
            return
        for idx, user in enumerate(self.snapshot.get("users", [])):
            if user.get("system_name") == system_name:
                self.snapshot["users"][idx] = saved_user
                break
        self.project_data["user_management"] = normalize_snapshot(self.snapshot)

    def on_group_selection_changed(self):
        if self._loading:
            return
        if not self.ask_save_current_user_changes():
            return
        self.refresh_user_tree()

    def reload_from_system(self):
        try:
            self.certificates = self.backend.get_certificates()
        except Exception:
            self.certificates = []
        try:
            system_snapshot = self.backend.get_snapshot()
            project_snapshot = normalize_snapshot(self.project_data.get("user_management", {}))
            self.snapshot = merge_snapshots(project_snapshot, system_snapshot)
        except Exception as exc:
            QMessageBox.warning(self, "User Management", "Systemdaten konnten nicht gelesen werden. Projekt-Snapshot wird verwendet.\n\n" + str(exc))
            self.snapshot = normalize_snapshot(self.project_data.get("user_management", {}))
        self.project_data["user_management"] = deepcopy(self.snapshot)
        self._saved_snapshot = normalize_snapshot(self.snapshot)
        self._dirty = False
        self.refresh_group_tree()

    def refresh_group_tree(self):
        current = self.selected_group_name()
        self._loading = True
        self.group_tree.clear()
        for group in self.snapshot.get("groups", []):
            item = QTreeWidgetItem([group.get("name", ""), group.get("description", "")])
            item.setData(0, Qt.UserRole, ROLE_GROUP)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.group_tree.addTopLevelItem(item)
            if current and group.get("name") == current:
                item.setSelected(True)
        if self.group_tree.topLevelItemCount() and not self.group_tree.selectedItems():
            self.group_tree.topLevelItem(0).setSelected(True)
        self.group_tree.resizeColumnToContents(0)
        self._loading = False
        self.refresh_user_tree()

    def make_property_item(self, root, label, role, value, system_name, editable=True):
        item = QTreeWidgetItem([label, str(value), ""])
        item.setData(0, Qt.UserRole, role)
        item.setData(1, Qt.UserRole, system_name)
        flags = item.flags() & ~Qt.ItemIsEditable
        if editable:
            flags |= Qt.ItemIsEditable
        item.setFlags(flags)
        root.addChild(item)
        return item

    def refresh_user_tree(self):
        if self._loading:
            return
        self._loading = True
        self.user_tree.blockSignals(True)
        self.user_tree.clear()
        group_name = self.selected_group_name()
        if not group_name:
            self.user_tree.blockSignals(False)
            self._loading = False
            return
        group = self.find_group(group_name)
        group_users = set(group.get("users", [])) if group else set()
        all_users = {u.get("system_name", ""): u for u in self.snapshot.get("users", [])}
        for system_name in sorted(group_users, key=str.lower):
            user = all_users.get(system_name)
            if not user:
                continue
            root = QTreeWidgetItem([system_name, user.get("full_name", system_name), "Ja" if user.get("enabled") else "Nein"])
            root.setData(0, Qt.UserRole, ROLE_USER)
            root.setData(1, Qt.UserRole, system_name)
            root.setFlags(root.flags() & ~Qt.ItemIsEditable)
            self.user_tree.addTopLevelItem(root)
            self.make_property_item(root, "AppPool", ROLE_APP_POOL, get_user_app_pool(user), system_name)
            
            html_item = self.make_property_item(
                root,
                "HTML Path",
                ROLE_HTML_PATH,
                get_user_html_path(user),
                system_name
            )
            html_item.setToolTip(1, "Double click, to open path Dialog.")
            html_button = QPushButton("Set ACL", self.user_tree)
            html_button.setFont(QFont(FONT_FAMILY, FONT_POINT_SIZE))
            html_button.clicked.connect(
                lambda _checked=False, item=html_item: self.set_html_acl(item)
            )
            self.user_tree.setItemWidget(html_item, 2, html_button)

            check_item = self.make_property_item(
                root,
                "Hostname",
                ROLE_HOST_NAME,
                get_user_host_name(user),
                system_name
            )
            check_button = QPushButton("Check", self.user_tree)
            check_button.setFont(QFont(FONT_FAMILY, FONT_POINT_SIZE))
            check_button.clicked.connect(
                lambda _checked=False, item=check_item: self.check_hostname_item(item)
            )
            self.user_tree.setItemWidget(check_item, 2, check_button)
            
            self._current_user_system_name = system_name
            
            port_item = self.make_property_item(root, "Port", ROLE_PORT, "", system_name, editable=False)
            spin = InlineSpinEdit(
                self.user_tree,
                icon_up   = ":/icons/arrow_up.png",
                icon_down = ":/icons/arrow_down.png"
            )
            spin.spin.setRange(0, 65535)
            spin.spin.setValue(get_user_port(user))
            spin.spin.setFont(QFont(FONT_FAMILY, FONT_POINT_SIZE))
            spin.spin.valueChanged.connect(lambda value, sn=system_name: self.set_user_setting(sn, "port", value))
            self.user_tree.setItemWidget(port_item, 1, spin)
            
            ssl_item = self.make_property_item(root, "Use SSL", ROLE_USE_SSL, "", system_name, editable=False)
            chk = QCheckBox(self.user_tree)
            chk.setFont(QFont(FONT_FAMILY, FONT_POINT_SIZE))
            chk.setChecked(get_user_use_ssl(user))
            chk.setText("set" if chk.isChecked() else "not set")
            chk.stateChanged.connect(
                lambda state, cb=chk, sn=system_name: self.on_use_ssl_changed(sn, cb, state)
            )
            self.user_tree.setItemWidget(ssl_item, 1, chk)

            cert_item = self.make_property_item(root, "Certificate", ROLE_CERTIFICATE, "", system_name, editable=False)
            combo = QComboBox(self.user_tree)
            combo.setFont(QFont(FONT_FAMILY, FONT_POINT_SIZE))
            self.fill_certificate_combo(combo, get_user_certificate(user))
            combo.currentIndexChanged.connect(lambda _idx, cb=combo, sn=system_name: self.on_certificate_changed(sn, cb))
            self.user_tree.setItemWidget(cert_item, 1, combo)
            
            cert_button = QPushButton("Create Cert", self.user_tree)
            cert_button.setFont(QFont(FONT_FAMILY, FONT_POINT_SIZE))
            cert_button.clicked.connect(lambda _checked=False, sn=system_name: self.open_ca_authority_dialog(sn))
            self.user_tree.setItemWidget(cert_item, 2, cert_button)

            selected_cert = self.selected_certificate_from_combo(combo)
            cert_details = self.certificate_detail_values(selected_cert or {})

            org_item = self.make_property_item(cert_item, "Organization", ROLE_CERT_ORG, cert_details["org"], system_name, editable=False)
            ou_item = self.make_property_item(cert_item, "Organization Unit", ROLE_CERT_OU, cert_details["ou"], system_name, editable=False)
            location_item = self.make_property_item(cert_item, "Location", ROLE_CERT_LOCATION, cert_details["location"], system_name, editable=False)
            country_item = self.make_property_item(cert_item, "Country", ROLE_CERT_COUNTRY, cert_details["country"], system_name, editable=False)
            until_item = self.make_property_item(cert_item, "Valid", ROLE_CERT_UNTIL, cert_details["until"], system_name, editable=False)
            thumb_item = self.make_property_item(cert_item, "Thumb", ROLE_CERT_THUMB, cert_details["thumb"], system_name, editable=False)

            if not hasattr(self, "_certificate_detail_items"):
                self._certificate_detail_items = {}

            self._certificate_detail_items[system_name] = {
                "org": org_item,
                "ou": ou_item,
                "location": location_item,
                "country": country_item,
                "until": until_item,
                "thumb": thumb_item,
            }

            cert_item.setExpanded(True)
            root.setExpanded(True)
        self.user_tree.resizeColumnToContents(0)
        self.user_tree.setColumnWidth(1, 320)
        self.user_tree.blockSignals(False)
        self._loading = False

    def selected_group_name(self):
        items = self.group_tree.selectedItems()
        return items[0].text(0) if items else None

    def selected_user_item(self):
        items = self.user_tree.selectedItems()
        if not items:
            return None
        item = items[0]
        while item.parent() is not None:
            item = item.parent()
        return item

    def selected_user_system_name(self):
        item = self.selected_user_item()
        return item.data(1, Qt.UserRole) if item else None

    def find_group(self, group_name):
        for group in self.snapshot.get("groups", []):
            if group.get("name") == group_name:
                return group
        return None

    def find_user(self, system_name):
        for user in self.snapshot.get("users", []):
            if user.get("system_name") == system_name:
                return user
        return None

    def add_group(self):
        name = group_name_from_id(next_id(self.snapshot, "groups", GROUP_PREFIX))
        try:
            self.backend.add_group(name)
            self.snapshot.setdefault("groups", []).append({"name": name, "description": make_description(name), "users": []})
            self.project_data["user_management"] = normalize_snapshot(self.snapshot)
            self.mark_dirty()
            self.refresh_group_tree()
        except Exception as exc:
            QMessageBox.critical(self, "Gruppe hinzufügen", str(exc))

    def delete_group(self):
        group_name = self.selected_group_name()
        if not group_name:
            return
        result = QMessageBox.question(self, "Gruppe löschen", f"Soll die Gruppe '{group_name}' wirklich gelöscht werden?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if result != QMessageBox.Yes:
            return
        try:
            self.backend.delete_group(group_name)
            self.snapshot["groups"] = [g for g in self.snapshot.get("groups", []) if g.get("name") != group_name]
            self.project_data["user_management"] = normalize_snapshot(self.snapshot)
            self.mark_dirty()
            self.refresh_group_tree()
        except Exception as exc:
            QMessageBox.critical(self, "Gruppe löschen", str(exc))

    def add_user(self):
        group_name = self.selected_group_name()
        if not group_name:
            QMessageBox.information(self, "Benutzer hinzufügen", "Bitte zuerst eine Gruppe auswählen.")
            return
        system_name = user_name_from_id(next_id(self.snapshot, "users", USER_PREFIX))
        app_pool = app_pool_from_user_name(system_name)
        password, ok = QInputDialog.getText(self, "Benutzer hinzufügen", f"Kennwort für {system_name}:", QLineEdit.Password, DEFAULT_PASSWORD)
        if not ok:
            return
        try:
            self.backend.add_user(system_name, password, group_name, app_pool)
            group = self.find_group(group_name)
            if group is not None:
                group.setdefault("users", [])
                if system_name not in group["users"]:
                    group["users"].append(system_name)
            user = {
                "system_name": system_name,
                "name": system_name,
                "display_name": system_name,
                "full_name": system_name,
                "description": make_description(system_name),
                "enabled": True,
                "settings": {"website": {"app_pool": app_pool, "html_path": "", "host_name": "", "port": 80, "use_ssl": False, "certificate": ""}},
            }
            self.snapshot.setdefault("users", []).append(user)
            self.snapshot.setdefault("app_pools", []).append({"name": app_pool})
            self.project_data["user_management"] = normalize_snapshot(self.snapshot)
            self.mark_dirty()
            self.refresh_group_tree()
        except Exception as exc:
            QMessageBox.critical(self, "Benutzer hinzufügen", str(exc))

    def delete_user(self):
        system_name = self.selected_user_system_name()
        if not system_name:
            return
        user = self.find_user(system_name)
        app_pool = get_user_app_pool(user) if user else app_pool_from_user_name(system_name)
        result = QMessageBox.question(self, "Benutzer löschen", f"Soll der Benutzer '{system_name}' wirklich gelöscht werden?\n\nAppPool: {app_pool}", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if result != QMessageBox.Yes:
            return
        try:
            self.backend.delete_user(system_name, app_pool)
            self.snapshot["users"] = [u for u in self.snapshot.get("users", []) if u.get("system_name") != system_name]
            for group in self.snapshot.get("groups", []):
                group["users"] = [u for u in group.get("users", []) if u != system_name]
            self.snapshot["app_pools"] = [p for p in self.snapshot.get("app_pools", []) if p.get("name") != app_pool]
            self.project_data["user_management"] = normalize_snapshot(self.snapshot)
            self.mark_dirty()
            self.refresh_group_tree()
        except Exception as exc:
            QMessageBox.critical(self, "Benutzer löschen", str(exc))

    def on_certificate_changed(self, system_name, combo):
        value = combo.currentData()

        if value is None:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
            self.update_certificate_detail_items(system_name, {})
            return

        self.set_user_setting(system_name, "certificate", value)
        self.update_certificate_detail_items(system_name, value)

    def on_use_ssl_changed(self, system_name, checkbox, state):
        checked = state == Qt.Checked
        checkbox.setText("set" if checked else "not set")
        self.set_user_setting(system_name, "use_ssl", checked)
    
    def open_ca_authority_dialog(self, system_name):
        user = self.find_user(system_name)

        if user is None:
            QMessageBox.warning(
                self,
                "Create Cert",
                "Der ausgewählte Benutzer wurde nicht gefunden."
            )
            return

        project_file = self.project_file or getattr(self.main_window, "current_project_file", None)

        if hasattr(self.main_window, "open_client_authority_dialog_for_project"):
            self.main_window.open_client_authority_dialog_for_project(
                project_file,
                self.project_data
            )
            return

        if hasattr(self.main_window, "open_ca_authority_dialog_for_project"):
            self.main_window.open_ca_authority_dialog_for_project(
                project_file,
                self.project_data
            )
            return

        if hasattr(self.main_window, "open_client_authority_dialog"):
            self.main_window.open_client_authority_dialog()
            return

        QMessageBox.information(
            self,
            "Create Cert",
            "Der CA Authority Dialog konnte nicht automatisch geöffnet werden. "
            "Bitte verbinde den Button mit open_client_authority_dialog_for_project()."
        )

    def on_user_item_double_clicked(self, item, column):
        if column != 1:
            return
        role = item.data(0, Qt.UserRole)
        if role != ROLE_HTML_PATH:
            return
        user = self.find_user(item.data(1, Qt.UserRole))
        if not user:
            return
        start_dir = get_user_html_path(user)
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = os.path.expanduser("~")
        directory = QFileDialog.getExistingDirectory(self, "HTML-Verzeichnis auswählen", start_dir)
        if not directory:
            return
        directory = str(directory or "").strip()[:MAX_HTML_PATH_LEN]
        self._loading = True
        item.setText(1, directory)
        self._loading = False
        self.set_user_setting(user["system_name"], "html_path", directory)

    def on_user_item_changed(self, item, column):
        if self._loading or column != 1:
            return
        role = item.data(0, Qt.UserRole)
        if role not in (ROLE_APP_POOL, ROLE_HTML_PATH, ROLE_HOST_NAME):
            return
        system_name = item.data(1, Qt.UserRole)
        key_map = {ROLE_APP_POOL: "app_pool", ROLE_HTML_PATH: "html_path", ROLE_HOST_NAME: "host_name"}
        value = safe_text20(item.text(1))
        if item.text(1) != value:
            self._loading = True
            item.setText(1, value)
            self._loading = False
        self.set_user_setting(system_name, key_map[role], value)
        if role == ROLE_APP_POOL:
            try:
                self.backend.create_or_update_app_pool(value)
            except Exception as exc:
                QMessageBox.warning(self, "AppPool", str(exc))

    def set_user_setting(self, system_name, key, value):
        if self._loading:
            return
        user = self.find_user(system_name)
        if not user:
            return
        set_website_value(user, key, value)
        self.project_data["user_management"] = normalize_snapshot(self.snapshot)
        self.mark_dirty()

    def save_project(self):
        if hasattr(self.main_window, "save_project_file"):
            if self.project_file:
                self.main_window.save_project_file(self.project_file, self.project_data)
            elif hasattr(self.main_window, "current_project_file"):
                self.main_window.save_project_file(self.main_window.current_project_file, self.project_data)


def apply_diff_actions(project_data, system_snapshot, actions, backend):
    snapshot = normalize_snapshot(project_data.get("user_management", {}))
    system_snapshot = normalize_snapshot(system_snapshot)
    groups = {g["name"]: g for g in snapshot["groups"]}
    users = {u["system_name"]: u for u in snapshot["users"]}
    system_groups = {g["name"]: g for g in system_snapshot["groups"]}
    system_users = {u["system_name"]: u for u in system_snapshot["users"]}
    for action in actions:
        key = action["key"]
        kind = action["action"]
        if kind == "import_group" and key in system_groups:
            groups[key] = deepcopy(system_groups[key])
        elif kind == "import_user" and key in system_users:
            users[key] = deepcopy(system_users[key])
        elif kind == "create_group" and key in groups:
            backend.add_group(key)
        elif kind == "create_user" and key in users:
            user = users[key]
            backend.add_user(user["system_name"], DEFAULT_PASSWORD, None, get_user_app_pool(user))
    project_data["user_management"] = normalize_snapshot({"groups": list(groups.values()), "users": list(users.values())})


def open_user_management_for_project(main_window, project_file, project_data):
    backend = LocalUserGroupBackend()
    try:
        system_snapshot = backend.get_snapshot()
    except Exception as exc:
        QMessageBox.warning(main_window, "User Management", str(exc))
        system_snapshot = normalize_snapshot(project_data.get("user_management", {}))
    project_snapshot = project_data.get("user_management", {})
    if snapshots_are_different(project_snapshot, system_snapshot):
        dlg = UserDiffDialog(project_snapshot, system_snapshot, main_window)
        dlg.resize(1000, 560)
        if dlg.exec_() != QDialog.Accepted:
            return None
        apply_diff_actions(project_data, system_snapshot, dlg.selected_actions, backend)
        if hasattr(main_window, "save_project_file"):
            main_window.save_project_file(project_file, project_data)
    widget = UserManagementWindow(main_window, project_data, project_file)
    widget.resize(1000,560)
    project_name = project_data.get("project", {}).get("name", "Project")
    if hasattr(main_window, "add_mdi_widget"):
        sub = main_window.add_mdi_widget(widget, f"User Management [{project_name}]", 980, 660)
        sub.project_file = os.path.abspath(project_file)
        sub.window_role = "user_management"
        return sub
    widget.show()
    return widget


# ---------------------------------------------------------------------------------------
# Add-on patch: Active ComboBox persistence without changing existing implementation.
# ---------------------------------------------------------------------------------------

ACTIVE_STATES = ("YES", "NO", "BLOCKED")


def normalize_active_state(value):
    text = str(value or "").strip().upper()

    if text in ACTIVE_STATES:
        return text

    if text in ("1", "TRUE", "YES", "JA", "ENABLED", "ON"):
        return "YES"

    if text in ("BLOCK", "BLOCKED", "LOCKED"):
        return "BLOCKED"

    return "NO"


def get_user_active_state(user):
    value = user.get("active_state")

    if value is None:
        value = website_settings(user).get("active_state")

    if value is None:
        value = "YES" if normalize_bool(user.get("enabled", True)) else "NO"

    return normalize_active_state(value)


def set_user_active_state_value(user, value):
    value = normalize_active_state(value)

    user["active_state"] = value
    user["enabled"] = value == "YES"

    ws = website_settings(user)
    ws["active_state"] = value

    return value


_original_normalize_snapshot = normalize_snapshot


def normalize_snapshot(snapshot):
    result = _original_normalize_snapshot(snapshot)

    source_users = {}

    for user in (snapshot or {}).get("users", []):
        system_name = str(user.get("system_name") or user.get("name") or "")

        if system_name:
            source_users[system_name] = user

    for user in result.get("users", []):
        system_name = user.get("system_name", "")
        source_user = source_users.get(system_name, {})
        active_state = get_user_active_state(source_user) if source_user else ("YES" if user.get("enabled", True) else "NO")
        set_user_active_state_value(user, active_state)

    return result


_original_reload_from_system = UserManagementWindow.reload_from_system


def _patched_reload_from_system(self):
    _original_reload_from_system(self)

    self.snapshot = normalize_snapshot(self.snapshot)
    self.project_data["user_management"] = deepcopy(self.snapshot)
    self._saved_snapshot = normalize_snapshot(self.snapshot)
    self._dirty = False
    self.refresh_group_tree()


UserManagementWindow.reload_from_system = _patched_reload_from_system


def _active_combo_selected_text(combo):
    data = combo.currentData()

    if data:
        return normalize_active_state(data)

    return normalize_active_state(combo.currentText())


def _set_active_state_from_combo(self, system_name, combo):
    if getattr(self, "_loading", False):
        return

    user = self.find_user(system_name)

    if not user:
        return

    value = _active_combo_selected_text(combo)
    set_user_active_state_value(user, value)

    self.project_data["user_management"] = normalize_snapshot(self.snapshot)
    self.mark_dirty()


def _make_active_combo(self, system_name, value):
    combo = QComboBox(self.user_tree)
    combo.setFont(QFont(FONT_FAMILY, FONT_POINT_SIZE))

    for state in ACTIVE_STATES:
        combo.addItem(state, state)

    idx = combo.findData(normalize_active_state(value))

    if idx < 0:
        idx = 0

    combo.setCurrentIndex(idx)
    combo.currentIndexChanged.connect(
        lambda _idx, cb=combo, sn=system_name: _set_active_state_from_combo(self, sn, cb)
    )

    return combo


_original_refresh_user_tree = UserManagementWindow.refresh_user_tree


def _patched_refresh_user_tree(self):
    _original_refresh_user_tree(self)

    if getattr(self, "_loading", False):
        return

    self._loading = True

    try:
        for i in range(self.user_tree.topLevelItemCount()):
            root = self.user_tree.topLevelItem(i)
            system_name = root.data(1, Qt.UserRole) or root.text(0)
            user = self.find_user(system_name)

            if not user:
                continue

            root.setText(2, "")
            combo = _make_active_combo(self, system_name, get_user_active_state(user))
            self.user_tree.setItemWidget(root, 2, combo)

    finally:
        self._loading = False


UserManagementWindow.refresh_user_tree = _patched_refresh_user_tree


_original_add_user = UserManagementWindow.add_user


def _patched_add_user(self):
    _original_add_user(self)

    system_name = self.selected_user_system_name()

    if not system_name:
        return

    user = self.find_user(system_name)

    if user:
        set_user_active_state_value(user, get_user_active_state(user))
        self.project_data["user_management"] = normalize_snapshot(self.snapshot)
        self.mark_dirty()


UserManagementWindow.add_user = _patched_add_user

