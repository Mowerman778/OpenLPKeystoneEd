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
Tests for the Library buttons under the menu
"""
import pytest
from PyQt5 import QtCore, QtGui, QtWidgets

from openlp.core.ui.librarybar import LibraryBar, LibraryToolBox


def _library(name):
    widget = QtWidgets.QWidget()
    widget.settings_section = name
    return widget


@pytest.fixture
def window(qapp):
    main_window = QtWidgets.QMainWindow()
    dock = QtWidgets.QDockWidget('Library', main_window)
    main_window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
    tool_box = LibraryToolBox(dock)
    dock.setWidget(tool_box)
    main_window.dock = dock
    main_window.tool_box = tool_box
    main_window.library_bar = LibraryBar(main_window, tool_box)
    main_window.addToolBar(main_window.library_bar)
    for name, title in (('songs', 'Songs'), ('bibles', 'Bibles'), ('images', 'Images'), ('other', 'Other')):
        tool_box.addItem(_library(name), QtGui.QIcon(), title)
    main_window.show()
    yield main_window
    main_window.close()


def test_one_button_per_library(window):
    """
    Test there is a button for each library, named and in order, with the name under the icon
    """
    actions = window.library_bar.actions()
    assert [action.text() for action in actions] == ['Songs', 'Bibles', 'Images', 'Other']
    assert window.library_bar.toolButtonStyle() == QtCore.Qt.ToolButtonTextUnderIcon
    assert not actions[0].icon().isNull(), 'Standard libraries get a modern icon'


def test_headers_hidden(window):
    """
    Test the old stacked library headers are hidden
    """
    headers = [button for button in window.tool_box.findChildren(QtWidgets.QAbstractButton)
               if button.metaObject().className() == 'QToolBoxButton']
    assert len(headers) == 4
    assert not any(header.isVisible() for header in headers)


def test_clicking_a_button_shows_only_that_library(window):
    """
    Test clicking a button shows that library and checks only that button
    """
    window.library_bar.actions()[2].trigger()
    assert window.tool_box.currentIndex() == 2
    assert window.tool_box.widget(2).isVisible()
    assert not window.tool_box.widget(0).isVisible()
    assert [action.isChecked() for action in window.library_bar.actions()] == [False, False, True, False]


def test_clicking_a_button_shows_hidden_library_panel(window):
    """
    Test a button brings the Library panel back if it was closed
    """
    window.dock.hide()
    window.library_bar.actions()[1].trigger()
    assert window.dock.isVisible()


def test_button_follows_library_changes(window):
    """
    Test the checked button follows the current library, and buttons follow libraries being removed
    """
    window.tool_box.setCurrentIndex(1)
    assert window.library_bar.actions()[1].isChecked()
    window.tool_box.removeItem(3)
    assert [action.text() for action in window.library_bar.actions()] == ['Songs', 'Bibles', 'Images']
