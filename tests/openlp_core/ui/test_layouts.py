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
Tests for the named screen layouts and Layout Setup Mode
"""
from unittest.mock import MagicMock, patch

import pytest
from PyQt5 import QtCore, QtWidgets

from openlp.core.common.registry import Registry
from openlp.core.ui import layouts
from openlp.core.ui.layouts import (ONE_MONITOR_DEFAULT, TWO_MONITOR_DEFAULT, LayoutManager, default_layout_for,
                                    operator_screens)


class FakeMainWindow(QtWidgets.QMainWindow):
    """
    Just enough of the OpenLP main window for the layout manager: the View menu, status bar and the six docks
    """
    def __init__(self):
        super().__init__()
        # Like the real main window: no central area, panels can nest anywhere
        self.setCentralWidget(QtWidgets.QWidget())
        self.centralWidget().hide()
        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks | QtWidgets.QMainWindow.AllowNestedDocks |
                            QtWidgets.QMainWindow.AllowTabbedDocks)
        self.view_menu = QtWidgets.QMenu(self)
        self.view_menu.addAction('existing item')
        self.lock_panel = QtWidgets.QAction(self)
        self.status_bar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.set_lock_panel = MagicMock()
        for name in ('media_manager_dock', 'preview_dock', 'live_dock', 'service_manager_dock',
                     'theme_manager_dock', 'projector_manager_dock'):
            dock = QtWidgets.QDockWidget(name, self)
            dock.setObjectName(name)
            dock.setWidget(QtWidgets.QWidget())
            setattr(self, name, dock)
        # The same starting arrangement as MainWindow.setup_ui
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.media_manager_dock)
        for dock in (self.service_manager_dock, self.theme_manager_dock, self.projector_manager_dock):
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        self.projector_manager_dock.setVisible(False)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.preview_dock)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.live_dock)
        self.splitDockWidget(self.media_manager_dock, self.preview_dock, QtCore.Qt.Horizontal)
        self.splitDockWidget(self.preview_dock, self.live_dock, QtCore.Qt.Horizontal)
        self.preview_controller = self._fake_controller()
        self.live_controller = self._fake_controller()

    @staticmethod
    def _fake_controller():
        controller = MagicMock()
        controller.splitter = QtWidgets.QSplitter()
        controller.slide_list_position = 'top'

        def set_slide_list_position(position):
            controller.slide_list_position = position
        controller.set_slide_list_position.side_effect = set_slide_list_position
        return controller

    def layout_docks(self):
        return [self.media_manager_dock, self.preview_dock, self.live_dock, self.service_manager_dock,
                self.theme_manager_dock, self.projector_manager_dock]


def _fake_screen(x, width=1280, height=720):
    screen = MagicMock()
    screen.geometry.return_value = QtCore.QRect(x, 0, width, height)
    screen.availableGeometry.return_value = QtCore.QRect(x, 0, width, height - 40)
    return screen


@pytest.fixture
def window(qapp, registry, settings):
    main_window = FakeMainWindow()
    yield main_window
    main_window.close()


@pytest.fixture
def manager(window):
    with patch('openlp.core.ui.layouts.operator_screens', return_value=[_fake_screen(0)]):
        yield LayoutManager(window)


def test_default_layout_for():
    """
    Test the built-in layout is chosen by the number of monitors
    """
    assert default_layout_for(1) == ONE_MONITOR_DEFAULT
    assert default_layout_for(2) == TWO_MONITOR_DEFAULT
    assert default_layout_for(3) == TWO_MONITOR_DEFAULT


@pytest.mark.parametrize('display_custom, expected_count', [(None, 1), (QtCore.QRect(0, 0, 480, 270), 2)])
def test_operator_screens(display_custom, expected_count):
    """
    Test that a screen given over entirely to the live display is not an operator monitor, but a screen with a
    smaller (simulated) display window still is
    """
    # GIVEN: A laptop screen and an external screen used as the live display
    laptop = _fake_screen(0, 1366, 768)
    external = _fake_screen(-1280)
    display = MagicMock(is_display=True, geometry=QtCore.QRect(-1280, 0, 1280, 720), custom_geometry=display_custom)
    with patch('openlp.core.ui.layouts.ScreenList', return_value=[display]), \
            patch('openlp.core.ui.layouts.QtGui.QGuiApplication.screens', return_value=[external, laptop]), \
            patch('openlp.core.ui.layouts.QtGui.QGuiApplication.primaryScreen', return_value=laptop):
        # WHEN: The operator screens are worked out
        screens = operator_screens()

    # THEN: The primary screen is first, and the display screen only counts when it is not full screen
    assert len(screens) == expected_count
    assert screens[0] is laptop


def test_setup_ui(manager, window):
    """
    Test the Layout menu goes at the top of the View menu, the old Lock item is hidden and the picker is filled in
    """
    assert window.view_menu.actions()[0].menu() is manager.layout_menu
    assert window.lock_panel.isVisible() is False
    assert manager.setup_bar.isHidden()


def test_populate_layout_menu(manager, settings):
    """
    Test the Layout menu lists the built-in layouts, then the user's own, then the tools
    """
    # GIVEN: One custom layout
    settings.setValue('user interface/layouts', {'Sunday': manager.capture_layout()})

    # WHEN: The menu is about to show
    manager.populate_layout_menu()

    # THEN: The layouts and tools are listed
    texts = [action.text() for action in manager.layout_menu.actions() if not action.isSeparator()]
    assert texts[:3] == [ONE_MONITOR_DEFAULT, TWO_MONITOR_DEFAULT, 'Sunday']
    assert 'Layout &Setup Mode' in texts


def test_remembered_layout_falls_back(manager, settings):
    """
    Test a remembered layout that has been deleted falls back to the built-in one
    """
    settings.setValue('user interface/layout for 2 monitors', 'Deleted layout')
    assert manager.remembered_layout(2) == TWO_MONITOR_DEFAULT


def test_apply_startup_layout_uses_monitor_count(manager):
    """
    Test the layout for the connected number of monitors is used at startup, and the panels are locked
    """
    with patch('openlp.core.ui.layouts.operator_monitor_count', return_value=2), \
            patch.object(manager, '_apply_built_in_layout') as mocked_apply:
        manager.apply_startup_layout()

    mocked_apply.assert_called_once_with(TWO_MONITOR_DEFAULT)
    assert manager.active_layout == TWO_MONITOR_DEFAULT
    manager.window.set_lock_panel.assert_called_with(True)
    assert manager.layout_combo.currentText() == TWO_MONITOR_DEFAULT


def test_two_monitor_default_moves_preview_and_live(manager, window):
    """
    Test the 2 Monitor Default layout puts Preview and Live side by side on the second monitor
    """
    # GIVEN: Two monitors
    second = _fake_screen(1366)
    with patch('openlp.core.ui.layouts.operator_screens', return_value=[_fake_screen(0, 1366, 768), second]):
        # WHEN: The layout is applied
        manager.apply_layout(TWO_MONITOR_DEFAULT)

    # THEN: Preview and Live float on the second monitor, the rest stay in the main window
    assert window.preview_dock.isFloating() and window.live_dock.isFloating()
    assert window.preview_dock.geometry().left() == 1366
    assert window.live_dock.geometry().left() == 1366 + 640
    assert not window.media_manager_dock.isFloating()
    assert not window.service_manager_dock.isFloating()


def test_one_monitor_default_after_two_monitors_matches_original(manager, window, qapp):
    """
    Test switching from 2 Monitor Default back to 1 Monitor Default gives the original OpenLP arrangement:
    Library | Preview | Live | Service over Themes, with no empty gaps
    """
    # GIVEN: The 2 Monitor Default layout is in use, on screen
    screens = [_fake_screen(0, 1366, 768), _fake_screen(1366)]
    with patch('openlp.core.ui.layouts.operator_screens', return_value=screens):
        manager.apply_layout(TWO_MONITOR_DEFAULT)
        window.show()
        for _ in range(5):
            QtWidgets.QApplication.processEvents()

    # WHEN: Switching to 1 Monitor Default
    with patch('openlp.core.ui.layouts.operator_screens', return_value=screens[:1]):
        manager.apply_layout(ONE_MONITOR_DEFAULT)
        for _ in range(5):
            QtWidgets.QApplication.processEvents()

    # THEN: The panels are docked left to right in the original order, Themes under Service
    library, preview, live = window.media_manager_dock, window.preview_dock, window.live_dock
    service, themes = window.service_manager_dock, window.theme_manager_dock
    assert not any(dock.isFloating() for dock in window.layout_docks())
    assert library.geometry().right() < preview.geometry().left()
    assert preview.geometry().right() < live.geometry().left()
    assert live.geometry().right() < service.geometry().left()
    assert themes.geometry().top() > service.geometry().bottom()
    assert abs(themes.geometry().left() - service.geometry().left()) <= 1
    # No empty columns: each panel starts right after the previous one (allowing for the splitter handle)
    for left_dock, right_dock in ((library, preview), (preview, live), (live, service)):
        assert right_dock.geometry().left() - left_dock.geometry().right() <= 12
    # Preview and Live get the most room
    assert preview.width() > library.width() and live.width() > service.width()


def test_startup_layout_applied_before_window_shown(manager, window):
    """
    Test a layout applied before the window is on screen doesn't show it (so the web views are never moved on
    screen), but prepares it maximised
    """
    manager.apply_layout(ONE_MONITOR_DEFAULT)
    assert not window.isVisible()
    assert window.windowState() & QtCore.Qt.WindowMaximized


def test_one_monitor_default_docks_everything(manager, window):
    """
    Test the 1 Monitor Default layout puts every panel back in the main window and hides the projector panel
    """
    window.preview_dock.setFloating(True)
    manager.apply_layout(ONE_MONITOR_DEFAULT)
    assert not any(dock.isFloating() for dock in window.layout_docks())
    assert window.projector_manager_dock.isHidden()


def test_store_and_apply_custom_layout(manager, window, settings):
    """
    Test a saved layout is stored and can be applied again
    """
    # GIVEN: A saved layout
    manager.store_layout('Mine')
    assert 'Mine' in settings.value('user interface/layouts')

    # WHEN: It is applied
    with patch.object(window, 'restoreState', wraps=window.restoreState) as mocked_restore:
        manager.choose_layout('Mine')

    # THEN: The saved state is restored and remembered for this number of monitors
    mocked_restore.assert_called_once()
    assert manager.active_layout == 'Mine'
    assert settings.value('user interface/layout for 1 monitors') == 'Mine'


def test_apply_broken_custom_layout_falls_back(manager, settings):
    """
    Test a damaged saved layout falls back to the built-in layout instead of crashing
    """
    settings.setValue('user interface/layouts', {'Broken': {'geometry': 'not base64!'}})
    with patch.object(manager, '_apply_built_in_layout') as mocked_built_in:
        manager.apply_layout('Broken')
    mocked_built_in.assert_called_once_with(ONE_MONITOR_DEFAULT)


def test_rescue_off_screen_panels(manager, window):
    """
    Test a panel left on a monitor that is no longer connected is put back into the main window
    """
    window.live_dock.setFloating(True)
    window.live_dock.setGeometry(50000, 50000, 300, 300)
    manager.rescue_off_screen_panels()
    assert not window.live_dock.isFloating()


def test_enter_and_leave_setup_mode_without_changes(manager, window):
    """
    Test Layout Setup Mode unlocks the panels and shows the bar, and Done locks them again without asking
    """
    manager.active_layout = ONE_MONITOR_DEFAULT
    manager.enter_setup_mode()
    assert manager.in_setup_mode()
    window.set_lock_panel.assert_called_with(False)
    assert not manager.setup_bar.isHidden()
    assert not manager.setup_save_button.isEnabled(), 'Built-in layouts can only be saved as a new layout'

    with patch.object(manager, 'ask_save_changes') as mocked_ask:
        assert manager.leave_setup_mode() is True
    mocked_ask.assert_not_called()
    assert not manager.in_setup_mode()
    window.set_lock_panel.assert_called_with(True)
    assert manager.setup_bar.isHidden()


def test_leave_setup_mode_cancel(manager):
    """
    Test cancelling the save question keeps Layout Setup Mode on
    """
    manager.active_layout = ONE_MONITOR_DEFAULT
    manager.enter_setup_mode()
    with patch.object(manager, 'layout_changed', return_value=True), \
            patch.object(manager, 'ask_save_changes', return_value=QtWidgets.QMessageBox.Cancel):
        assert manager.leave_setup_mode() is False
    assert manager.in_setup_mode()


def test_leave_setup_mode_discard(manager):
    """
    Test discarding changes puts the layout back as it was
    """
    manager.active_layout = ONE_MONITOR_DEFAULT
    manager.enter_setup_mode()
    with patch.object(manager, 'layout_changed', return_value=True), \
            patch.object(manager, 'ask_save_changes', return_value=QtWidgets.QMessageBox.Discard), \
            patch.object(manager, 'apply_layout') as mocked_apply:
        assert manager.leave_setup_mode() is True
    mocked_apply.assert_called_once_with(ONE_MONITOR_DEFAULT)
    assert not manager.in_setup_mode()


def test_leave_setup_mode_save_custom(manager, settings):
    """
    Test saving changes to a custom layout overwrites it
    """
    manager.store_layout('Mine')
    manager.active_layout = 'Mine'
    manager.enter_setup_mode()
    with patch.object(manager, 'layout_changed', return_value=True), \
            patch.object(manager, 'ask_save_changes', return_value=QtWidgets.QMessageBox.Save), \
            patch.object(manager, 'store_layout') as mocked_store:
        assert manager.leave_setup_mode() is True
    mocked_store.assert_called_once_with('Mine')


@patch('openlp.core.ui.layouts.QtWidgets.QInputDialog.getText', return_value=(' Sunday ', True))
def test_save_layout_as(mocked_get_text, manager, settings):
    """
    Test saving a new layout under a name makes it the active layout
    """
    assert manager.save_layout_as() is True
    assert 'Sunday' in settings.value('user interface/layouts')
    assert manager.active_layout == 'Sunday'
    assert manager.layout_combo.findText('Sunday') >= 0


@patch('openlp.core.ui.layouts.QtWidgets.QMessageBox.information')
@patch('openlp.core.ui.layouts.QtWidgets.QInputDialog.getText', return_value=(ONE_MONITOR_DEFAULT, True))
def test_save_layout_as_built_in_name(mocked_get_text, mocked_information, manager, settings):
    """
    Test a built-in layout's name can't be used for a saved layout
    """
    assert manager.save_layout_as() is False
    mocked_information.assert_called_once()
    assert settings.value('user interface/layouts') == {}


@patch('openlp.core.ui.layouts.QtWidgets.QMessageBox.question', return_value=QtWidgets.QMessageBox.Yes)
@patch('openlp.core.ui.layouts.QtWidgets.QInputDialog.getItem', return_value=('Mine', True))
def test_delete_active_layout(mocked_get_item, mocked_question, manager, settings):
    """
    Test deleting the active layout removes it and switches to the built-in layout
    """
    manager.store_layout('Mine')
    manager.active_layout = 'Mine'
    with patch('openlp.core.ui.layouts.operator_monitor_count', return_value=1), \
            patch.object(manager, '_apply_built_in_layout'):
        manager.delete_layout()
    assert 'Mine' not in settings.value('user interface/layouts')
    assert manager.active_layout == ONE_MONITOR_DEFAULT


def test_on_screens_changed(manager):
    """
    Test plugging in a monitor switches to the layout for the new number of monitors
    """
    manager.last_monitor_count = 1
    with patch('openlp.core.ui.layouts.operator_monitor_count', return_value=2), \
            patch.object(manager, 'apply_layout') as mocked_apply:
        manager.on_screens_changed()
    mocked_apply.assert_called_once_with(TWO_MONITOR_DEFAULT)
    assert manager.last_monitor_count == 2


def test_on_screens_changed_ignored_in_setup_mode(manager):
    """
    Test a monitor change doesn't rearrange the panels while the user is setting up a layout
    """
    manager.last_monitor_count = 1
    manager.enter_setup_mode()
    with patch('openlp.core.ui.layouts.operator_monitor_count', return_value=2), \
            patch.object(manager, 'apply_layout') as mocked_apply:
        manager.on_screens_changed()
    mocked_apply.assert_not_called()


def test_registered_for_screen_changes(manager):
    """
    Test the layout manager listens for monitors being connected or disconnected
    """
    assert manager.on_screens_changed in Registry().functions_list['config_screen_changed']


def test_module_constants():
    assert layouts.BUILT_IN_LAYOUTS == (ONE_MONITOR_DEFAULT, TWO_MONITOR_DEFAULT)


def test_slide_list_position_saved_in_layout(manager, window, settings):
    """
    Test the Preview/Live slide list position is part of a saved layout, and the built-in layouts put it on top
    """
    # GIVEN: Live's slide list moved to the right and the layout saved
    window.live_controller.set_slide_list_position('right')
    manager.store_layout('Lists right')

    # WHEN: A built-in layout is applied
    manager.apply_layout(ONE_MONITOR_DEFAULT)

    # THEN: The lists are back on top
    assert window.live_controller.slide_list_position == 'top'

    # WHEN: The saved layout is applied again
    manager.apply_layout('Lists right')

    # THEN: Live's list is on the right again, Preview's on top
    assert window.live_controller.slide_list_position == 'right'
    assert window.preview_controller.slide_list_position == 'top'


def test_setup_mode_slide_list_choice(manager, window):
    """
    Test Layout Setup Mode shows the current slide list positions and changing one moves the list and counts as a
    change to the layout
    """
    window.preview_controller.set_slide_list_position('right')
    manager.active_layout = ONE_MONITOR_DEFAULT
    manager.enter_setup_mode()
    assert manager.preview_list_combo.currentIndex() == 1
    assert manager.live_list_combo.currentIndex() == 0

    manager.live_list_combo.activated.emit(1)

    assert window.live_controller.slide_list_position == 'right'
    assert manager.layout_changed()


def test_floating_display_panel_redrawn_after_drag(manager, window, qapp):
    """
    Test Preview/Live are redrawn (hidden and shown again) once dragged out into their own window, but only after
    the mouse button is released, and keep their place
    """
    window.show()
    window.preview_dock.setFloating(True)
    window.preview_dock.setGeometry(300, 200, 400, 600)
    with patch.object(window.preview_dock, 'hide', wraps=window.preview_dock.hide) as mocked_hide:
        # WHEN: The mouse button is still held
        with patch('openlp.core.ui.layouts.QtWidgets.QApplication.mouseButtons', return_value=QtCore.Qt.LeftButton), \
                patch('openlp.core.ui.layouts.QtCore.QTimer.singleShot') as mocked_single_shot:
            manager._redraw_after_drag(window.preview_dock)
        # THEN: It waits
        mocked_hide.assert_not_called()
        mocked_single_shot.assert_called_once()

        # WHEN: The button is released
        with patch('openlp.core.ui.layouts.QtWidgets.QApplication.mouseButtons', return_value=QtCore.Qt.NoButton):
            manager._redraw_after_drag(window.preview_dock)

    # THEN: It was redrawn in the same place
    mocked_hide.assert_called_once()
    assert window.preview_dock.isVisible()
    assert window.preview_dock.geometry() == QtCore.QRect(300, 200, 400, 600)


def test_floating_display_panel_hooked_up(manager, window):
    """
    Test dragging Preview or Live out (or back in) asks for a redraw
    """
    with patch.object(manager, 'on_display_panel_moved') as mocked_moved:
        window.live_dock.topLevelChanged.emit(True)
    mocked_moved.assert_called_once_with(window.live_dock)
