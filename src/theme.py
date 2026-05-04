# ---------------------------------------------------------------------------
# File:   theme.py
# Author: (c) 2024, 2025, 2026 Jens Kallup - paule32
# All rights reserved
# ---------------------------------------------------------------------------
from __future__    import annotations

from PyQt5.QtCore    import Qt
from PyQt5.QtGui     import (
    QPalette, QColor
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMdiArea, QMdiSubWindow,
    QWidget, QVBoxLayout, QLabel, QAction, QFileDialog,
    QMessageBox, QDockWidget, QToolBar, QTextEdit, QComboBox,
    QLineEdit, QPushButton, QFormLayout, QLineEdit, QPushButton
)

def apply_theme_global(w: QWidget):
    app = QApplication.instance()
    pal = QPalette()

    pal.setColor(QPalette.Window, QColor(40, 40, 40))
    pal.setColor(QPalette.WindowText, Qt.black)
    pal.setColor(QPalette.Base, QColor(34, 34, 34))
    pal.setColor(QPalette.AlternateBase, QColor(35, 35, 35))
    pal.setColor(QPalette.Text, Qt.white)
    pal.setColor(QPalette.Button, QColor(45, 45, 45))
    pal.setColor(QPalette.ButtonText, Qt.white)
    pal.setColor(QPalette.Highlight, QColor(80, 120, 200))
    pal.setColor(QPalette.HighlightedText, Qt.white)
    
    app.setPalette(pal)
    
    header_bg               = "#222222"
    header_fg               = "#ffd866"
    tree_bg                 = "#181818"
    tree_fg                 = "#ffffff"
    sel_bg                  = "#2b4c7e"
    sel_fg                  = "#ffffff"
    border                  = "#333333"
    
    tab_bg                  = "#1c1c1c"
    tab_bar_bg              = "#161616"
    tab_fg                  = "#ffffff"
    tab_fg_active           = "#ffd866"
    tab_sel_bg              = "#242424"
    tab_hover_bg            = "#202020"
    
    toolbar_bg              = "#1a1a1a"
    toolbtn_bg              = "#222222"
    toolbtn_fg              = "#ffd866"
    toolbtn_hover           = "#2a2a2a"
    toolbtn_pressed         = "#303030"
    
    title_bg                = "#121212"  # Hintergrund Titelleiste
    title_fg                = "#1fd816"  # Text/Farbe Buttons (oder "#ffffff")
    title_btn_bg            = "#1f1f1f"  # Buttons normal
    title_btn_hover         = "#2a2a2a"  # Buttons hover
    title_btn_close_hover   = "#8a1f1f"  # Close hover
    
    status_bg               = "#121212"
    status_fg               = "#ffd866"  # oder "#ffffff"
    status_border           = "#333333"
    
    # Scrollbar dark-blue
    sb_face  = "#001f4d"   # navy
    sb_track = "#001a40"
    sb_thumb = "#002b66"
    sb_hi    = "#2d5aa0"
    sb_mid   = "#000b1a"
    sb_dark  = "#000000"
    arrow    = "#FFD400"

    window_bg=        "#0f1116"
    panel_bg=         "#141824"
    input_bg=         "#101521"

    text_fg=          "#e6e6e6"
    text_hover_fg=    "#ffffff"
    text_disabled_fg= "#7a808a"

    title_fg=         "#ffd866"

    border=           "#3a2f3a"
    border_hover=     "#3a4150"
    border_disabled=  "#242935"

    accent=           "#2b4c7e"
    accent_hover =     "#3b68ad"
    accent_disabled=  "#223a5e"

    disabled_bg=      "#0c0f14"
    
    size = 21  # Win95 vibe
    w.setStyleSheet(f"""
/* ========================= 
   QCheckBox (Dark)
   ========================= */
QCheckBox {{
    color: {text_fg};
    spacing: 8px;
}}

QCheckBox:hover {{
    color: {text_hover_fg};
}}

QCheckBox:disabled {{
    color: {text_disabled_fg};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {border};
    background: {input_bg};
}}

QCheckBox::indicator:hover {{
    border: 1px solid {accent};
}}

QCheckBox::indicator:focus {{
    border: 1px solid {accent};
}}

QCheckBox::indicator:checked {{
    background: {accent};
    border: 1px solid {accent};
}}

QCheckBox::indicator:checked:hover {{
    background: {accent_hover};
    border: 1px solid {accent_hover};
}}

QCheckBox::indicator:unchecked {{
    background: {input_bg};
}}

QCheckBox::indicator:indeterminate {{
    background: {accent};
    border: 1px solid {accent};
}}

QCheckBox::indicator:disabled {{
    background: {disabled_bg};
    border: 1px solid {border_disabled};
}}

QCheckBox::indicator:checked:disabled {{
    background: {accent_disabled};
    border: 1px solid {border_disabled};
}}


/* =========================
   QGroupBox (Dark)
   ========================= */
QGroupBox {{
    color: {text_fg};
    border: 1px solid {border};
    border-radius: 10px;
    margin-top: 14px;     /* Platz für Titel */
    padding: 10px;
    background: {panel_bg};
}}

QGroupBox:hover {{
    border: 1px solid {border_hover};
}}

QGroupBox:disabled {{
    color: {text_disabled_fg};
    border: 1px solid {border_disabled};
    background: {disabled_bg};
}}

/* Titel-Label */
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 10px;
    top: 2px;

    color: {title_fg};
    background: {window_bg}; /* damit der Titel die Border "überdeckt" */
}}

/* Optional: wenn du GroupBoxen checkable nutzt */
QGroupBox::indicator {{
    width: 16px;
    height: 16px;
    margin-left: 6px;
}}

QGroupBox::indicator:unchecked {{
    border: 1px solid {border};
    border-radius: 4px;
    background: {input_bg};
}}

QGroupBox::indicator:checked {{
    border: 1px solid {accent};
    background: {accent};
}}

QMenuBar {{ background: #1a1a1a; color: #ffd866; }}
QMenuBar::item {{ background: transparent; padding: 6px 10px; }}
QMenuBar::item:selected {{ background: #2a2a2a; }}
QMenu {{ background: #141414; color: #ffffff; border: 1px solid #333333; }}
QMenu::separator {{
    height: 2px;
    margin: 6px 10px;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #2a2a2a,
        stop:1 #555555
    );
}}
QMenu::item:selected {{ background: #2b4c7e; color: #ffffff; }}
QMdiArea {{
    background: #1e1e1e;           /* noch dunkler */
    border: 2px solid #333333;
}}
QMdiArea::viewport {{
    background: #1b1b0b;
}}
/* optional: Subwindows im Dark Mode passend */
QMdiSubWindow {{
    background: #343434;
    border: 2px solid #333333;
}}
QMdiSubWindow:title {{
    background: 0;
    color: #ffffff;
}}
QComboBox {{
    background: #2a2a2a;          /* Feld grau */
    color: #ffffff;
    border: 1px solid #333333;
    padding: 6px 10px;
    padding-right: 28px;          /* Platz für den Pfeil */
}}

QComboBox:hover {{
    background: #303030;
}}

QComboBox:disabled {{
    background: #202020;
    color: #777777;
}}

/* Drop-down Button rechts */
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #333333;
    background: #222222;
}}

QComboBox::drop-down:hover {{
    background: #2a2a2a;
}}

/* Pfeil */
QComboBox::down-arrow {{
    width: 12px;
    height: 12px;
    image: url(:/icons/arrow_down.png);
}}

/* Popup-Liste */
QComboBox QAbstractItemView {{
    background: #1c1c1c;
    color: #ffffff;
    border: 1px solid #333333;
    selection-background-color: #2b4c7e;
    selection-color: #ffffff;
    outline: 1px;
}}
QTableView, QTableWidget {{
    background: #0b0b0b;
    color: #ffffff;
    gridline-color: #333333;
    border: 1px solid #333333;
    selection-background-color: #2b4c7e;
    selection-color: #ffffff;
}}

/* WICHTIG: leere Fläche kommt oft vom viewport */
QTableView::viewport, QTableWidget::viewport {{
    background-color: #0b0b0b;
}}

/* Header oben/links */
QHeaderView::section {{
    background-color: #000000;
    color: #e6e6e6;
    padding: 6px;
    border: none;
    border-right: 1px solid #333333;
    border-bottom: 1px solid #333333;
}}

/* Der “Eck-Button” oben links (häufig DER weiße Fleck) */
QTableCornerButton::section {{
    background-color: #000000;
    border-right: 1px solid #333333;
    border-bottom: 1px solid #333333;
}}

QMessageBox {{
    background-color: #2b2b2b;
    color: #e8e8e8;
    font-size: 10pt;
}}
QMessageBox QLabel {{
    color: #e8e8e8;
}}
QMessageBox QLabel#qt_msgbox_label {{
    color: #e8e8e8;
}}
QMessageBox QLabel#qt_msgboxex_icon_label {{
    /* Icon-Label */
    padding-right: 10px;
}}
QMessageBox QTextEdit {{
    background-color: #232323;
    color: #e8e8e8;
    border: 1px solid #3a3a3a;
    border-radius: 8px;
}}
QMessageBox QMessageBox QPushButton {{
    background-color: #3a3a3a;
    color: #a0a0f0;
    border: 1px solid #555;
    border-radius: 8px;
    padding: 6px 12px;
    min-width: 90px;
}}
QMessageBox QPushButton:hover {{
    background-color: #444;
    border-color: #777;
}}
QMessageBox QPushButton:pressed {{
    background-color: #2f2f2f;
}}
QMessageBox QPushButton:default {{
    border: 1px solid #a33;   /* dezenter roter Akzent */
}}
QMessageBox QPushButton:focus {{
    outline: none;
    border: 1px solid #888;
}}
QAbstractItemView, QAbstractButton {{
    background-color: #000000;
    border-right: 1px solid #333333;
    border-bottom: 1px solid #333333;
}}
/* Optional: falls Qt dort eine Ecke der ScrollArea malt */
QAbstractScrollArea::corner {{
    background-color: #000000;
    border: 1px solid #222222;
}}
QToolBar {{spacing: 8px;background: {toolbar_bg};border: none;}}
QToolBar::separator {{background: {border};width: 1px;margin: 6px 8px;}}
QLineEdit {{padding: 6px 10px;border: 1px solid {border};background: {tab_bg};color: {tab_fg};}}
QLabel {{color: {tab_fg};}}
QToolButton {{background: {toolbtn_bg};color: {toolbtn_fg};border: 1px solid {border};padding: 6px 10px;}}
QToolButton:hover {{background: {toolbtn_hover};}}
QToolButton:pressed {{background: {toolbtn_pressed};}}
QTabWidget::pane {{border: 1px solid {border};top: -1px;background: {tab_bg};}}
QTabBar {{background: {tab_bar_bg};}}
QTabBar::tab {{background: {tab_bar_bg};color: {tab_fg};border: 1px solid {border};border-bottom: none;padding: 7px 14px;margin-right: 6px;min-width: 90px;}}
QTabBar::tab:hover {{background: {tab_hover_bg};}}
QTabBar::tab:selected {{background: {tab_sel_bg};color: {tab_fg_active};}}
QTreeView {{border: none;background: {tree_bg};color: {tree_fg};}}
QTreeView::item:selected {{background: {sel_bg};color: {sel_fg};}}
QHeaderView::section {{background: {header_bg};color: {header_fg};padding: 6px;border: none;border-bottom: 1px solid {border};}}
QPushButton {{background: {toolbtn_bg};color: {toolbtn_fg};border: 2px solid {border};border-radius: 10px;padding: 7px 12px;}}
QPushButton:hover {{background: {toolbtn_hover};}}
QPushButton:pressed {{background: {toolbtn_pressed};}}
TopContainer {{ background: transparent; }}
TitleBar {{background: {title_bg};}}
TitleLabel {{color: {title_fg};font-weight: 600;}}
TitleSeparator {{background: {border};}}
QPushButton#TitleBtnMin,QPushButton#TitleBtnMax,QPushButton#TitleBtnClose {{background: {title_btn_bg};color: {title_fg};border: 1px solid {border};border-radius: 10px;}}
QPushButton#TitleBtnMin:hover,QPushButton#TitleBtnMax:hover {{background: {title_btn_hover};}}
QPushButton#TitleBtnClose:hover {{background: {title_btn_close_hover};}}
QStatusBar {{background: {status_bg};color: {status_fg};border-top: 1px solid {status_border};}}
QStatusBar QLabel {{color: {status_fg};}}
QTabBar::scroller {{width: 22px;height: 22px;background: {tab_bar_bg};border: 1px solid {border};border-radius: 10px;margin: 2px;}}
QTabBar::scroller:hover {{background: {tab_hover_bg};}}
QTabBar QToolButton {{background: {tab_bar_bg};border: 1px solid {border};border-radius: 10px;padding: 2px;color: {tab_fg_active};}}
QTabBar QToolButton:hover {{background: {tab_hover_bg};}}
QTabBar QToolButton:pressed {{background: {tab_sel_bg};}}
QSplitter {{background: {tree_bg};}}
QSplitter::handle {{background: {border};}}
QWebEngineView {{background: {tree_bg};}}
QScrollBar:vertical {{background: {sb_face};width: {size}px;margin: 0px;border: 1px solid {sb_dark};}}
QScrollBar:horizontal {{background: {sb_face};height: {size}px;margin: 0px;border: 1px solid {sb_dark};}}
QScrollBar::track:vertical, QScrollBar::track:horizontal {{background: {sb_track};}}
/*QScrollBar::handle:vertical {{background: {sb_thumb};min-height: 28px;border-top: 1px solid {sb_hi};border-left: 1px solid {sb_hi};border-right: 1px solid {sb_mid};border-bottom: 1px solid {sb_mid};}}*/
/*QScrollBar::handle:horizontal {{background: {sb_thumb};min-width: 28px;border-top: 1px solid {sb_hi};border-left: 1px solid {sb_hi};border-right: 1px solid {sb_mid};border-bottom: 1px solid {sb_mid};}}*/

/* Ecke unten rechts bei ScrollAreas */
QAbstractScrollArea::corner {{
    background: #000a8a;
}}

/* Vertikale ScrollBars */
QPlainTextEdit QScrollBar:vertical,
QTextEdit QScrollBar:vertical,
QListWidget QScrollBar:vertical,
QListView QScrollBar:vertical,
QTreeView QScrollBar:vertical {{
    background: #000a8a;
    width: 16px;
    margin: 16px 0 16px 0;
    border: 1px solid #0f2d5c;
}}

/* Horizontale ScrollBars */
QPlainTextEdit QScrollBar:horizontal,
QTextEdit QScrollBar:horizontal,
QListWidget QScrollBar:horizontal,
QListView QScrollBar:horizontal,
QTreeView QScrollBar:horizontal {{
    background: #000a8a;
    height: 16px;
    margin: 0 16px 0 16px;
    border: 1px solid #0f2d5c;
}}

/* Die leeren Track-Bereiche oberhalb/unterhalb oder links/rechts vom Thumb */
QPlainTextEdit QScrollBar::add-page:vertical,
QPlainTextEdit QScrollBar::sub-page:vertical,
QTextEdit QScrollBar::add-page:vertical,
QTextEdit QScrollBar::sub-page:vertical,
QListWidget QScrollBar::add-page:vertical,
QListWidget QScrollBar::sub-page:vertical,
QListView QScrollBar::add-page:vertical,
QListView QScrollBar::sub-page:vertical,
QTreeView QScrollBar::add-page:vertical,
QTreeView QScrollBar::sub-page:vertical,

QPlainTextEdit QScrollBar::add-page:horizontal,
QPlainTextEdit QScrollBar::sub-page:horizontal,
QTextEdit QScrollBar::add-page:horizontal,
QTextEdit QScrollBar::sub-page:horizontal,
QListWidget QScrollBar::add-page:horizontal,
QListWidget QScrollBar::sub-page:horizontal,
QListView QScrollBar::add-page:horizontal,
QListView QScrollBar::sub-page:horizontal,
QTreeView QScrollBar::add-page:horizontal,
QTreeView QScrollBar::sub-page:horizontal {{
    background: #000aaa;
}}

/* Thumb */
QPlainTextEdit QScrollBar::handle:vertical,
QTextEdit QScrollBar::handle:vertical,
QListWidget QScrollBar::handle:vertical,
QListView QScrollBar::handle:vertical,
QTreeView QScrollBar::handle:vertical {{
    background: #003afa;
    min-height: 24px;
    border: 1px solid #08162f;
    border-radius: 3px;
}}

QPlainTextEdit QScrollBar::handle:horizontal,
QTextEdit QScrollBar::handle:horizontal,
QListWidget QScrollBar::handle:horizontal,
QListView QScrollBar::handle:horizontal,
QTreeView QScrollBar::handle:horizontal {{
    background: #003afa;
    min-width: 24px;
    border: 1px solid #08162f;
    border-radius: 3px;
}}

/* Buttons an den Enden */
QPlainTextEdit QScrollBar::add-line:vertical,
QPlainTextEdit QScrollBar::sub-line:vertical,
QTextEdit QScrollBar::add-line:vertical,
QTextEdit QScrollBar::sub-line:vertical,
QListWidget QScrollBar::add-line:vertical,
QListWidget QScrollBar::sub-line:vertical,
QListView QScrollBar::add-line:vertical,
QListView QScrollBar::sub-line:vertical,
QTreeView QScrollBar::add-line:vertical,
QTreeView QScrollBar::sub-line:vertical {{
    background: #000a8a;
    height: 16px;
    border: 1px solid #0f2d5c;
}}

QPlainTextEdit QScrollBar::add-line:horizontal,
QPlainTextEdit QScrollBar::sub-line:horizontal,
QTextEdit QScrollBar::add-line:horizontal,
QTextEdit QScrollBar::sub-line:horizontal,
QListWidget QScrollBar::add-line:horizontal,
QListWidget QScrollBar::sub-line:horizontal,
QListView QScrollBar::add-line:horizontal,
QListView QScrollBar::sub-line:horizontal,
QTreeView QScrollBar::add-line:horizontal,
QTreeView QScrollBar::sub-line:horizontal {{
    background: #000a8a;
    width: 16px;
    border: 1px solid #0f2d5c;
}}

/* Pfeile unsichtbar */
QScrollBar::up-arrow,
QScrollBar::down-arrow,
QScrollBar::left-arrow,
QScrollBar::right-arrow {{
    width: 0px;
    height: 0px;
    background: transparent;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{background: transparent;}}
QScrollBar::sub-line:vertical {{background: {sb_face};height: {size}px;border-top: 1px solid {sb_hi};border-left: 1px solid {sb_hi};border-right: 1px solid {sb_mid};border-bottom: 1px solid {sb_mid};}}
QScrollBar::add-line:vertical {{background: {sb_face};height: {size}px;border-top: 1px solid {sb_hi};border-left: 1px solid {sb_hi};border-right: 1px solid {sb_mid};border-bottom: 1px solid {sb_mid};}}
QScrollBar::sub-line:horizontal {{background: {sb_face};width: {size}px;border-top: 1px solid {sb_hi};border-left: 1px solid {sb_hi};border-right: 1px solid {sb_mid};border-bottom: 1px solid {sb_mid};}}
QScrollBar::add-line:horizontal {{background: {sb_face};width: {size}px;border-top: 1px solid {sb_hi};border-left: 1px solid {sb_hi};border-right: 1px solid {sb_mid};border-bottom: 1px solid {sb_mid};}}
QScrollBar::sub-line:vertical:pressed, QScrollBar::add-line:vertical:pressed,
QScrollBar::sub-line:horizontal:pressed, QScrollBar::add-line:horizontal:pressed {{border-top: 1px solid {sb_mid};border-left: 1px solid {sb_mid};border-right: 1px solid {sb_hi};border-bottom: 1px solid {sb_hi};}}
QScrollBar::up-arrow:vertical {{
    width: 12px;
    height: 12px;
    image: url(:/icons/arrow_up.png);
}}
QScrollBar::down-arrow:vertical {{
    width: 12px;
    height: 12px;
    image: url(:/icons/arrow_down.png);
}}
QScrollBar::left-arrow:horizontal {{
    width: 12px;
    height: 12px;
    image: url(:/icons/arrow_left.png);
}}
QScrollBar::right-arrow:horizontal {{
    width: 12px;
    height: 12px;
    image: url(:/icons/arrow_right.png);
}}

QScrollBar::sub-line:vertical {{ subcontrol-position: top;    subcontrol-origin: margin; }}
QScrollBar::add-line:vertical {{ subcontrol-position: bottom; subcontrol-origin: margin; }}
QScrollBar::sub-line:horizontal {{ subcontrol-position: left;  subcontrol-origin: margin; }}
QScrollBar::add-line:horizontal {{ subcontrol-position: right; subcontrol-origin: margin; }}

QScrollBar:vertical[dir="down"]::handle {{ image: url(:/icons/arrow_down.png); }}
QScrollBar:vertical[dir="up"]::handle   {{ image: url(:/icons/arrow_up.png); }}

/* ===== FORCE: Table Header + Corner wirklich schwarz ===== */

/* Header (oben + links) */
QTableView QHeaderView::section,
QTableWidget QHeaderView::section {{
    background-color: #000000;
    border-right: 1px solid #333333;
    border-bottom: 1px solid #333333;
}}

/* obere linke Ecke (zwischen Headern) */
QTableView QTableCornerButton::section,
QTableWidget QTableCornerButton::section {{
    background-color: #000000;
    border-right: 1px solid #333333;
    border-bottom: 1px solid #333333;
}}

/* falls Qt statt CornerButton die ScrollArea-Ecke malt (wenn beide Scrollbars da sind) */
QTableView QAbstractScrollArea::corner,
QTableWidget QAbstractScrollArea::corner {{
    background-color: #000000;
    border: 1px solid #333333;
}}
QDockWidget::title {{
    color: #ffd866;              /* gelb */
    padding-left: 8px;
    padding-top: 2px;
    padding-bottom: 2px;
}}
QDockWidget::close-button, QDockWidget::float-button {{
    background: transparent;
    border: none;
    color: #ffffff;              /* wirkt bei font-basierten Icons */
    icon-size: 14px;
}}
QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
    background: rgba(255,255,255,0.08);
    border-radius: 3px;
}}
DockTitleBar {{
    background: #1e1e1e;
}}
QLabel {{
    color: #ffd866;           /* GELB */
    font-weight: 600;
}}
QToolButton {{
    color: #ffffff;           /* WEISS (falls Text/Icon-Font) */
    background: transparent;
    border: none;
    padding: 2px;
}}
QToolButton:hover {{
    background: rgba(255,255,255,0.10);
    border-radius: 3px;
}}
QWebEngineView {{background: {tree_bg};}}

QSpinBox, QDoubleSpinBox {{
    background-color: #1e1e1e;
    color: #ffffff;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 2px 20px 2px 6px;
    font-family: Arial;
    font-size: 10pt;
    selection-background-color: #3d6ea8;
    selection-color: #ffffff;
}}

QSpinBox:hover, QDoubleSpinBox:hover {{
    border: 1px solid #666666;
    background-color: #252525;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid #d7b300;
    background-color: #202020;
}}

QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: #2a2a2a;
    color: #777777;
    border: 1px solid #3a3a3a;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #444444;
    border-bottom: 1px solid #444444;
    background-color: #2b2b2b;
    border-top-right-radius: 4px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid #444444;
    background-color: #2b2b2b;
    border-bottom-right-radius: 4px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: #3a3a3a;
}}

QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
    background-color: #505050;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none;
    width: 0px;
    height: 0px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
}}

/* --------------------------------------*/

QComboBox,
QDateEdit {{
    background-color: #1f1f1f;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 6px;
    padding: 4px 28px 4px 8px;
    selection-background-color: #5a1020;
    selection-color: #ffffff;
}}

QComboBox:hover,
QDateEdit:hover {{
    border: 1px solid #8b1e35;
}}

QComboBox:focus,
QDateEdit:focus {{
    border: 1px solid #b52b45;
}}

/*QComboBox::drop-down,*/
QDateEdit::drop-down {{
    image: url(:/icons/arrow_down.png);
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #555555;
    background-color: #2a2a2a;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}}

QComboBox::down-arrow,
QDateEdit::down-arrow {{
    width: 10px;
    height: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: #202020;
    color: #ffffff;
    border: 1px solid #8b1e35;
    selection-background-color: #5a1020;
    selection-color: #ffffff;
    outline: 0;
}}

QCalendarWidget {{
    background-color: #202020;
    color: #ffffff;
}}

QCalendarWidget QWidget {{
    alternate-background-color: #2a2a2a;
    background-color: #202020;
    color: #ffffff;
}}

QCalendarWidget QToolButton {{
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px;
}}

QCalendarWidget QToolButton:hover {{
    background-color: #5a1020;
    border: 1px solid #b52b45;
}}

QCalendarWidget QMenu {{
    background-color: #202020;
    color: #ffffff;
    border: 1px solid #8b1e35;
}}

QCalendarWidget QSpinBox {{
    background-color: #1f1f1f;
    color: #ffffff;
    border: 1px solid #555555;
}}

QCalendarWidget QAbstractItemView {{
    background-color: #202020;
    color: #ffffff;
    selection-background-color: #5a1020;
    selection-color: #ffffff;
}}

QRadioButton {{
    color: #ffffff;
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 8px;
    border: 2px solid #7a1f35;
    background-color: #1f1f1f;
}}

QRadioButton::indicator:hover {{
    border: 2px solid #b52b45;
}}

QRadioButton::indicator:checked {{
    border: 2px solid #d64562;
    background-color: #6e1026;
}}

QRadioButton::indicator:unchecked {{
    background-color: #1f1f1f;
}}

QRadioButton::indicator:disabled {{
    border: 2px solid #444444;
    background-color: #2a2a2a;
}}
""")