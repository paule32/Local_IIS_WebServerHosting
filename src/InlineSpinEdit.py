# ---------------------------------------------------------------------------------------
# file: InlineSpinEdit.py
# author: (c) 2026 Jens Kallup - paule32
# all rights reserved.
# ---------------------------------------------------------------------------------------
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QToolButton, QSpinBox
from PyQt5.QtGui     import QIcon
from PyQt5.QtCore    import QSize


class InlineSpinEdit(QWidget):
    def __init__(self, parent=None, icon_up=None, icon_down=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        
        self.spin = QSpinBox(self)
        self.spin.setRange(0, 65535)
        self.spin.setButtonSymbols(QSpinBox.NoButtons)
        
        self.button_up   = QToolButton(self)
        self.button_down = QToolButton(self)
        
        self.button_up  .setText("+")
        self.button_down.setText("-")
        
        self.button_up  .setStyleSheet("color: yellow;")
        self.button_down.setStyleSheet("color: yellow;")
        
        if icon_up:
            self.button_up.setIcon(QIcon(icon_up))
        
        if icon_down:
            self.button_down.setIcon(QIcon(icon_down))
        
        self.button_up  .setIconSize(QSize(14, 14))
        self.button_down.setIconSize(QSize(14, 14))
        
        self.button_up  .clicked.connect(self.spin.stepUp)
        self.button_down.clicked.connect(self.spin.stepDown)
        
        layout.addWidget(self.spin, 1)
        layout.addWidget(self.button_down)
        layout.addWidget(self.button_up)
    
    def value(self):
        return self.spin.value()
    
    def setValue(self, value):
        self.spin.setValue(int(value))
