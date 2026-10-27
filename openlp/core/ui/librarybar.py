# -*- coding: utf-8 -*-

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008-2024 OpenLP Developers                              #
# ---------------------------------------------------------------------- #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                        #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <https://www.gnu.org/licenses/>. #
##########################################################################
"""
The :mod:`~openlp.core.ui.librarybar` module holds the Library buttons shown under the menu (Songs, Bibles,
Presentations, ...). Clicking one shows just that library in the Library panel.
"""
import qtawesome as qta
from PyQt5 import QtCore, QtWidgets

# Modern icons for the standard libraries, by plugin name. Other plugins use their own icon.
LIBRARY_ICONS = {
    'songs': 'mdi6.music-note',
    'bibles': 'mdi6.book-cross',
    'presentations': 'mdi6.presentation-play',
    'images': 'mdi6.image-multiple',
    'media': 'mdi6.play-box-multiple',
    'custom': 'mdi6.card-text-outline',
}
ICON_COLOUR = '#2b5797'
ICON_COLOUR_CHECKED = '#ffffff'
LIBRARY_BAR_STYLE = """
QToolBar#library_bar { spacing: 4px; padding: 2px 6px; border-bottom: 1px solid #c8c8c8; }
QToolBar#library_bar QToolButton { padding: 4px 10px; border-radius: 6px; min-width: 64px; }
QToolBar#library_bar QToolButton:hover { background: #e3ecf7; }
QToolBar#library_bar QToolButton:checked { background: #2b5797; color: white; }
"""


class LibraryToolBox(QtWidgets.QToolBox):
    """
    The Library panel's contents. It works like a QToolBox, but without the stacked header buttons: only the current
    library is shown, and the Library bar is used to switch.
    """
    items_changed = QtCore.pyqtSignal()

    def itemInserted(self, index):
        self._hide_headers()
        self.items_changed.emit()

    def itemRemoved(self, index):
        self.items_changed.emit()

    def _hide_headers(self):
        for button in self.findChildren(QtWidgets.QAbstractButton):
            if button.metaObject().className() == 'QToolBoxButton':
                button.hide()


class LibraryBar(QtWidgets.QToolBar):
    """
    One button per library, with the name under a large icon
    """
    def __init__(self, parent, tool_box):
        super().__init__(parent)
        self.tool_box = tool_box
        self.setObjectName('library_bar')
        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QtCore.QSize(28, 28))
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.setStyleSheet(LIBRARY_BAR_STYLE)
        self.action_group = QtWidgets.QActionGroup(self)
        self.action_group.setExclusive(True)
        self.tool_box.items_changed.connect(self.rebuild)
        self.tool_box.currentChanged.connect(self.sync_checked)
        self.rebuild()

    def library_icon(self, index):
        widget = self.tool_box.widget(index)
        icon_name = LIBRARY_ICONS.get(getattr(widget, 'settings_section', None))
        if icon_name:
            return qta.icon(icon_name, color=ICON_COLOUR, color_on=ICON_COLOUR_CHECKED,
                            color_active=ICON_COLOUR, color_on_active=ICON_COLOUR_CHECKED)
        return self.tool_box.itemIcon(index)

    def rebuild(self):
        """
        Make one button per library, in the same order as the Library panel
        """
        self.clear()
        for action in self.action_group.actions():
            self.action_group.removeAction(action)
        for index in range(self.tool_box.count()):
            action = QtWidgets.QAction(self.library_icon(index), self.tool_box.itemText(index), self)
            action.setCheckable(True)
            action.setToolTip(self.tool_box.itemText(index))
            action.triggered.connect(lambda checked, widget=self.tool_box.widget(index): self.show_library(widget))
            self.action_group.addAction(action)
            self.addAction(action)
        self.sync_checked(self.tool_box.currentIndex())

    def show_library(self, widget):
        """
        Show just this library in the Library panel, making sure the panel is visible
        """
        index = self.tool_box.indexOf(widget)
        if index >= 0:
            self.tool_box.setCurrentIndex(index)
        dock = self.tool_box.parentWidget()
        while dock and not isinstance(dock, QtWidgets.QDockWidget):
            dock = dock.parentWidget()
        if dock and not dock.isVisible():
            dock.setVisible(True)

    def sync_checked(self, index):
        actions = self.action_group.actions()
        if 0 <= index < len(actions):
            actions[index].setChecked(True)
