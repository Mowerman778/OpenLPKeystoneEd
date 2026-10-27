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
The :mod:`~openlp.core.ui.layouts` module holds named screen layouts ("layout profiles").

A layout is the position, size and visibility of every panel (Library, Preview, Live, Service, Themes, Projectors),
including panels moved onto another monitor. There are two built-in layouts, picked automatically by how many
monitors the operator has, and users can save their own. Outside Layout Setup Mode the panels are locked so they
can't be dragged around by accident.
"""
import base64
import logging

from PyQt5 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.registry import Registry
from openlp.core.display.screens import ScreenList
from openlp.core.ui.slidecontroller import SLIDE_LIST_RIGHT, SLIDE_LIST_TOP

log = logging.getLogger(__name__)

ONE_MONITOR_DEFAULT = '1 Monitor Default'
TWO_MONITOR_DEFAULT = '2 Monitor Default'
BUILT_IN_LAYOUTS = (ONE_MONITOR_DEFAULT, TWO_MONITOR_DEFAULT)
# Slide list positions in the Preview and Live panels, in the order shown in Layout Setup Mode
LIST_POSITIONS = (SLIDE_LIST_TOP, SLIDE_LIST_RIGHT)


def operator_screens():
    """
    The screens the operator works on, primary first: every screen except one given over entirely to the live
    display. A live display using a custom size (such as a simulated projector window) still leaves room for panels.

    :rtype: list[QtGui.QScreen]
    """
    full_display_geometries = [screen.geometry for screen in ScreenList()
                               if screen.is_display and not screen.custom_geometry]
    primary = QtGui.QGuiApplication.primaryScreen()
    screens = [screen for screen in QtGui.QGuiApplication.screens()
               if screen.geometry() not in full_display_geometries]
    screens.sort(key=lambda screen: screen is not primary)
    return screens or [primary]


def operator_monitor_count():
    """
    How many monitors the operator has, as used to choose a layout: 1 or 2.
    """
    return min(len(operator_screens()), 2)


def default_layout_for(monitor_count):
    """
    The built-in layout for a number of monitors
    """
    return TWO_MONITOR_DEFAULT if monitor_count >= 2 else ONE_MONITOR_DEFAULT


def _encode(data):
    return base64.b64encode(bytes(data)).decode('ascii')


def _decode(text):
    return QtCore.QByteArray(base64.b64decode(text))


class LayoutManager(QtCore.QObject, RegistryProperties):
    """
    Applies, saves and deletes screen layouts, and runs Layout Setup Mode.
    """
    def __init__(self, main_window):
        super().__init__(main_window)
        self.window = main_window
        # The arrangement the main window was built with (the original OpenLP layout), for the built-in layouts
        self.pristine_state = main_window.saveState()
        self.active_layout = None
        self.setup_mode_snapshot = None
        self.last_monitor_count = None
        self.setup_ui()
        Registry().register_function('config_screen_changed', self.on_screens_changed)

    # ---- User interface ----

    def setup_ui(self):
        """
        Build the View > Layout menu, the layout picker in the status bar and the Layout Setup Mode bar
        """
        main_window = self.window
        self.layout_menu = QtWidgets.QMenu(main_window.view_menu)
        self.layout_menu.setObjectName('layout_menu')
        self.layout_menu.aboutToShow.connect(self.populate_layout_menu)
        self.layout_group = QtWidgets.QActionGroup(self.layout_menu)
        self.layout_group.setExclusive(True)
        self.setup_mode_action = QtWidgets.QAction(main_window)
        self.setup_mode_action.setObjectName('layout_setup_mode_action')
        self.setup_mode_action.setCheckable(True)
        self.setup_mode_action.triggered.connect(self.on_setup_mode_triggered)
        self.save_as_action = QtWidgets.QAction(main_window)
        self.save_as_action.setObjectName('layout_save_as_action')
        self.save_as_action.triggered.connect(self.save_layout_as)
        self.delete_action = QtWidgets.QAction(main_window)
        self.delete_action.setObjectName('layout_delete_action')
        self.delete_action.triggered.connect(self.delete_layout)
        first_view_action = main_window.view_menu.actions()[0] if main_window.view_menu.actions() else None
        main_window.view_menu.insertMenu(first_view_action, self.layout_menu)
        main_window.view_menu.insertSeparator(first_view_action)
        # The old "Lock panels" item is replaced by Layout Setup Mode
        main_window.lock_panel.setVisible(False)
        # Layout picker in the status bar
        self.layout_label = QtWidgets.QLabel(main_window.status_bar)
        self.layout_combo = QtWidgets.QComboBox(main_window.status_bar)
        self.layout_combo.setObjectName('layout_combo')
        self.layout_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.layout_combo.activated.connect(self.on_layout_combo_activated)
        main_window.status_bar.addPermanentWidget(self.layout_label)
        main_window.status_bar.addPermanentWidget(self.layout_combo)
        # Layout Setup Mode bar, shown across the top of the main window
        self.setup_bar = QtWidgets.QToolBar(main_window)
        self.setup_bar.setObjectName('layout_setup_bar')
        self.setup_bar.setMovable(False)
        self.setup_bar.setFloatable(False)
        self.setup_bar.setStyleSheet('QToolBar { background: #fff3c4; border-bottom: 1px solid #d9b100; }')
        self.setup_bar_label = QtWidgets.QLabel(self.setup_bar)
        self.setup_bar_label.setContentsMargins(8, 4, 16, 4)
        self.setup_bar.addWidget(self.setup_bar_label)
        self.setup_save_button = QtWidgets.QPushButton(self.setup_bar)
        self.setup_save_button.clicked.connect(self.on_setup_save_clicked)
        self.setup_bar.addWidget(self.setup_save_button)
        self.setup_save_as_button = QtWidgets.QPushButton(self.setup_bar)
        self.setup_save_as_button.clicked.connect(self.on_setup_save_as_clicked)
        self.setup_bar.addWidget(self.setup_save_as_button)
        # Where the slide list sits in the Preview and Live panels
        self.preview_list_label = QtWidgets.QLabel(self.setup_bar)
        self.preview_list_label.setContentsMargins(16, 0, 4, 0)
        self.setup_bar.addWidget(self.preview_list_label)
        self.preview_list_combo = QtWidgets.QComboBox(self.setup_bar)
        self.preview_list_combo.setObjectName('preview_list_combo')
        self.preview_list_combo.addItems(['', ''])
        self.preview_list_combo.activated.connect(
            lambda index: self.window.preview_controller.set_slide_list_position(LIST_POSITIONS[index]))
        self.setup_bar.addWidget(self.preview_list_combo)
        self.live_list_label = QtWidgets.QLabel(self.setup_bar)
        self.live_list_label.setContentsMargins(12, 0, 4, 0)
        self.setup_bar.addWidget(self.live_list_label)
        self.live_list_combo = QtWidgets.QComboBox(self.setup_bar)
        self.live_list_combo.setObjectName('live_list_combo')
        self.live_list_combo.addItems(['', ''])
        self.live_list_combo.activated.connect(
            lambda index: self.window.live_controller.set_slide_list_position(LIST_POSITIONS[index]))
        self.setup_bar.addWidget(self.live_list_combo)
        spacer = QtWidgets.QWidget(self.setup_bar)
        spacer.setFixedWidth(16)
        self.setup_bar.addWidget(spacer)
        self.setup_done_button = QtWidgets.QPushButton(self.setup_bar)
        self.setup_done_button.clicked.connect(self.leave_setup_mode)
        self.setup_bar.addWidget(self.setup_done_button)
        # On its own row, under the Library bar
        main_window.addToolBarBreak(QtCore.Qt.TopToolBarArea)
        main_window.addToolBar(QtCore.Qt.TopToolBarArea, self.setup_bar)
        self.setup_bar.hide()
        self.retranslate_ui()

    def retranslate_ui(self):
        self.layout_menu.setTitle(translate('OpenLP.Layouts', '&Layout'))
        self.setup_mode_action.setText(translate('OpenLP.Layouts', 'Layout &Setup Mode'))
        self.setup_mode_action.setStatusTip(translate('OpenLP.Layouts', 'Unlock the panels so they can be moved, '
                                                                        'resized and dragged to another monitor'))
        self.save_as_action.setText(translate('OpenLP.Layouts', 'Save Layout &As...'))
        self.delete_action.setText(translate('OpenLP.Layouts', '&Delete Layout...'))
        self.layout_label.setText(translate('OpenLP.Layouts', 'Layout:'))
        self.setup_bar_label.setText(translate('OpenLP.Layouts', '<b>Layout Setup Mode</b> - drag panels by their '
                                                                 'title bar, onto either monitor. Drag the edges '
                                                                 'between panels to resize.'))
        self.setup_save_button.setText(translate('OpenLP.Layouts', 'Save'))
        self.setup_save_as_button.setText(translate('OpenLP.Layouts', 'Save As New Layout...'))
        self.setup_done_button.setText(translate('OpenLP.Layouts', 'Done'))
        self.preview_list_label.setText(translate('OpenLP.Layouts', 'Preview slide list:'))
        self.live_list_label.setText(translate('OpenLP.Layouts', 'Live slide list:'))
        for combo in (self.preview_list_combo, self.live_list_combo):
            combo.setItemText(0, translate('OpenLP.Layouts', 'Above the picture'))
            combo.setItemText(1, translate('OpenLP.Layouts', 'Right of the picture'))

    def populate_layout_menu(self):
        """
        Rebuild the Layout menu: built-in layouts, then the user's own, then the layout tools
        """
        self.layout_menu.clear()
        for action in self.layout_group.actions():
            self.layout_group.removeAction(action)
        for name in self.layout_names():
            action = QtWidgets.QAction(name, self.layout_menu)
            action.setCheckable(True)
            action.setChecked(name == self.active_layout)
            action.setEnabled(not self.in_setup_mode())
            action.triggered.connect(lambda checked, layout_name=name: self.choose_layout(layout_name))
            self.layout_group.addAction(action)
            self.layout_menu.addAction(action)
        self.layout_menu.addSeparator()
        self.setup_mode_action.setChecked(self.in_setup_mode())
        self.layout_menu.addAction(self.setup_mode_action)
        self.layout_menu.addAction(self.save_as_action)
        self.delete_action.setEnabled(bool(self.custom_layouts()) and not self.in_setup_mode())
        self.layout_menu.addAction(self.delete_action)

    def refresh_layout_combo(self):
        self.layout_combo.blockSignals(True)
        self.layout_combo.clear()
        self.layout_combo.addItems(self.layout_names())
        if self.active_layout:
            self.layout_combo.setCurrentText(self.active_layout)
        self.layout_combo.setEnabled(not self.in_setup_mode())
        self.layout_combo.blockSignals(False)

    def on_layout_combo_activated(self, index):
        self.choose_layout(self.layout_combo.itemText(index))

    # ---- Stored layouts ----

    def custom_layouts(self):
        """
        The user's own layouts: {name: data}
        """
        return self.settings.value('user interface/layouts') or {}

    def layout_names(self):
        return list(BUILT_IN_LAYOUTS) + sorted(self.custom_layouts(), key=str.lower)

    def remembered_layout(self, monitor_count):
        """
        The layout last chosen for this number of monitors, falling back to the built-in one
        """
        name = self.settings.value('user interface/layout for {count} monitors'.format(count=monitor_count))
        if name in BUILT_IN_LAYOUTS or name in self.custom_layouts():
            return name
        return default_layout_for(monitor_count)

    def capture_layout(self):
        """
        Capture the current arrangement of the main window and every panel
        """
        main_window = self.window
        # The Layout Setup Mode bar is a toolbar, so it is part of the window state: leave it out of layouts
        bar_visible = self.setup_bar.isVisible()
        self.setup_bar.hide()
        state = main_window.saveState()
        self.setup_bar.setVisible(bar_visible)
        return {
            'geometry': _encode(main_window.saveGeometry()),
            'state': _encode(state),
            'maximised': main_window.isMaximized(),
            'monitors': operator_monitor_count(),
            'preview list': main_window.preview_controller.slide_list_position,
            'live list': main_window.live_controller.slide_list_position,
            'preview splitter': _encode(main_window.preview_controller.splitter.saveState()),
            'live splitter': _encode(main_window.live_controller.splitter.saveState()),
        }

    # ---- Applying layouts ----

    def apply_startup_layout(self):
        """
        Called when OpenLP starts: use the layout for however many monitors are connected
        """
        self.last_monitor_count = operator_monitor_count()
        self.apply_layout(self.remembered_layout(self.last_monitor_count))

    def choose_layout(self, name):
        """
        The user picked a layout: apply it and remember it for this number of monitors
        """
        if self.in_setup_mode():
            return
        self.apply_layout(name)
        self.settings.setValue('user interface/layout for {count} monitors'.format(count=operator_monitor_count()),
                               name)

    def apply_layout(self, name):
        """
        Arrange the panels as the named layout says
        """
        custom = self.custom_layouts()
        if name in custom:
            self._apply_custom_layout(custom[name])
        else:
            name = name if name in BUILT_IN_LAYOUTS else ONE_MONITOR_DEFAULT
            self._apply_built_in_layout(name)
        self.active_layout = name
        self.window.set_lock_panel(not self.in_setup_mode())
        self.setup_bar.setVisible(self.in_setup_mode())
        self.refresh_layout_combo()

    def _apply_built_in_layout(self, name):
        """
        1 Monitor Default: everything in the main window: Library | Preview | Live | Service and Themes.
        2 Monitor Default: Library and Service/Themes on the main monitor, Preview and Live side by side filling the
        second monitor.
        """
        main_window = self.window
        screens = operator_screens()
        primary = screens[0].availableGeometry()
        two_monitors = name == TWO_MONITOR_DEFAULT and len(screens) > 1
        # Go back to the arrangement the main window was built with, the original OpenLP one:
        # Library | Preview | Live | Service over Themes. Restoring a state is cleaner than moving panels one by one.
        for dock in main_window.layout_docks():
            dock.setFloating(False)
        main_window.restoreState(self.pristine_state)
        for dock in main_window.layout_docks():
            dock.setVisible(dock is not main_window.projector_manager_dock)
        # Slide lists above the picture, as in the original OpenLP
        for controller in (main_window.preview_controller, main_window.live_controller):
            if controller:
                controller.set_slide_list_position(LIST_POSITIONS[0])
        if two_monitors:
            # Preview and Live side by side, filling the second monitor
            second = screens[1].availableGeometry()
            half = second.width() // 2
            for dock, left in ((main_window.preview_dock, second.left()),
                               (main_window.live_dock, second.left() + half)):
                dock.setFloating(True)
                dock.setGeometry(left, second.top(), half, second.height())
        # Put the main window on the main monitor, filling it
        self._maximise_on(primary)
        # Size the panels once the maximised window has been laid out
        QtCore.QTimer.singleShot(0, lambda: self._size_built_in_panels(two_monitors))

    def _maximise_on(self, geometry):
        """
        Maximise the main window on the screen with this geometry. If the window isn't on screen yet (at startup) it
        is only prepared, so it appears already laid out.
        """
        main_window = self.window
        if main_window.isVisible():
            main_window.showNormal()
            main_window.setGeometry(geometry)
            main_window.showMaximized()
        else:
            main_window.setGeometry(geometry)
            main_window.setWindowState(main_window.windowState() | QtCore.Qt.WindowMaximized)

    def refresh_display_panels(self):
        """
        Preview and Live contain web views, which are separate native windows that don't always redraw when their
        panel moves. Hiding and showing them again makes them redraw in the right place.
        """
        for dock in (self.window.preview_dock, self.window.live_dock):
            if dock.isVisible():
                dock.hide()
                dock.show()

    def _size_built_in_panels(self, two_monitors):
        """
        Share the main window's width between the docked panels, like the original OpenLP layout
        """
        main_window = self.window
        width = main_window.width()
        if two_monitors:
            docks, shares = [main_window.media_manager_dock, main_window.service_manager_dock], [55, 45]
        else:
            docks = [main_window.media_manager_dock, main_window.preview_dock, main_window.live_dock,
                     main_window.service_manager_dock]
            shares = [20, 28, 32, 20]
        main_window.resizeDocks(docks, [width * share // 100 for share in shares], QtCore.Qt.Horizontal)
        height = main_window.height()
        main_window.resizeDocks([main_window.service_manager_dock, main_window.theme_manager_dock],
                                [height * 55 // 100, height * 45 // 100], QtCore.Qt.Vertical)
        self.refresh_display_panels()

    def _apply_custom_layout(self, data):
        main_window = self.window
        try:
            if main_window.isVisible():
                main_window.showNormal()
            main_window.restoreGeometry(_decode(data['geometry']))
            main_window.restoreState(_decode(data['state']))
            self.setup_bar.setVisible(self.in_setup_mode())
            main_window.preview_controller.set_slide_list_position(data.get('preview list', LIST_POSITIONS[0]))
            main_window.live_controller.set_slide_list_position(data.get('live list', LIST_POSITIONS[0]))
            main_window.preview_controller.splitter.restoreState(_decode(data['preview splitter']))
            main_window.live_controller.splitter.restoreState(_decode(data['live splitter']))
            if data.get('maximised'):
                self._maximise_on(main_window.geometry())
        except (KeyError, ValueError, TypeError):
            log.exception('Layout could not be restored, using the built-in layout instead')
            self._apply_built_in_layout(default_layout_for(operator_monitor_count()))
            return
        self.rescue_off_screen_panels()
        QtCore.QTimer.singleShot(0, self.refresh_display_panels)

    def rescue_off_screen_panels(self):
        """
        Panels saved on a monitor that is no longer connected are put back into the main window, and the main
        window is brought back onto a screen
        """
        main_window = self.window
        visible_area = QtGui.QRegion()
        for screen in QtGui.QGuiApplication.screens():
            visible_area = visible_area.united(QtGui.QRegion(screen.availableGeometry()))
        for dock in main_window.layout_docks():
            if dock.isFloating() and not visible_area.contains(dock.geometry().center()):
                dock.setFloating(False)
        if not visible_area.contains(main_window.frameGeometry().topLeft() + QtCore.QPoint(60, 10)):
            main_window.showNormal()
            main_window.setGeometry(operator_screens()[0].availableGeometry())
            main_window.showMaximized()

    def on_screens_changed(self):
        """
        A monitor was connected or disconnected: switch to the layout for the new number of monitors
        """
        monitor_count = operator_monitor_count()
        if self.last_monitor_count is None or monitor_count == self.last_monitor_count or self.in_setup_mode():
            return
        self.last_monitor_count = monitor_count
        self.apply_layout(self.remembered_layout(monitor_count))

    # ---- Layout Setup Mode ----

    def in_setup_mode(self):
        return self.setup_mode_snapshot is not None

    def on_setup_mode_triggered(self, checked):
        if checked:
            self.enter_setup_mode()
        else:
            self.leave_setup_mode()

    def enter_setup_mode(self):
        """
        Unlock the panels so they can be moved, and show the Layout Setup Mode bar
        """
        if self.in_setup_mode():
            return
        self.setup_mode_snapshot = self.capture_layout()
        self.window.set_lock_panel(False)
        self.setup_save_button.setEnabled(self.active_layout not in BUILT_IN_LAYOUTS)
        for combo, controller in ((self.preview_list_combo, self.window.preview_controller),
                                  (self.live_list_combo, self.window.live_controller)):
            position = controller.slide_list_position
            combo.setCurrentIndex(LIST_POSITIONS.index(position) if position in LIST_POSITIONS else 0)
        self.setup_bar.show()
        self.setup_mode_action.setChecked(True)
        self.refresh_layout_combo()

    def leave_setup_mode(self):
        """
        Lock the panels again. If anything was changed, offer to save it first.

        :return: False if the user cancelled, so setup mode is still on
        """
        if not self.in_setup_mode():
            return True
        if self.layout_changed():
            answer = self.ask_save_changes()
            if answer == QtWidgets.QMessageBox.Cancel:
                self.setup_mode_action.setChecked(True)
                return False
            if answer == QtWidgets.QMessageBox.Save:
                if not self.save_current_layout():
                    self.setup_mode_action.setChecked(True)
                    return False
            elif answer == QtWidgets.QMessageBox.Discard:
                self.setup_mode_snapshot = None
                self.apply_layout(self.active_layout)
        self.setup_mode_snapshot = None
        self.setup_bar.hide()
        self.setup_mode_action.setChecked(False)
        self.window.set_lock_panel(True)
        self.refresh_layout_combo()
        return True

    def layout_changed(self):
        current = self.capture_layout()
        compared = ('state', 'preview list', 'live list', 'preview splitter', 'live splitter')
        return any(current[key] != self.setup_mode_snapshot[key] for key in compared)

    def ask_save_changes(self):
        """
        :return: QMessageBox.Save (save to the active layout, or as a new one for built-in layouts),
            QMessageBox.Discard or QMessageBox.Cancel
        """
        if self.active_layout in BUILT_IN_LAYOUTS:
            message = translate('OpenLP.Layouts', 'You changed the layout. "{name}" is built in, so save your '
                                                  'changes as a new layout?').format(name=self.active_layout)
        else:
            message = translate('OpenLP.Layouts', 'Save your changes to the layout "{name}"?'
                                ).format(name=self.active_layout)
        return QtWidgets.QMessageBox.question(
            self.window, translate('OpenLP.Layouts', 'Save Layout'), message,
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Save)

    def on_setup_save_clicked(self):
        if self.save_current_layout():
            self.setup_mode_snapshot = self.capture_layout()

    def on_setup_save_as_clicked(self):
        if self.save_layout_as():
            self.setup_mode_snapshot = self.capture_layout()

    def save_current_layout(self):
        """
        Save to the active layout; built-in layouts can't be changed, so those are saved as a new layout
        """
        if self.active_layout in BUILT_IN_LAYOUTS:
            return self.save_layout_as()
        self.store_layout(self.active_layout)
        return True

    # ---- Saving and deleting ----

    def save_layout_as(self):
        """
        Ask for a name and save the current arrangement under it

        :return: True if a layout was saved
        """
        name, ok = QtWidgets.QInputDialog.getText(
            self.window, translate('OpenLP.Layouts', 'Save Layout As'),
            translate('OpenLP.Layouts', 'Name for this layout (for example "Sunday - 2 screens"):'))
        name = name.strip() if ok else ''
        if not name:
            return False
        if name in BUILT_IN_LAYOUTS:
            QtWidgets.QMessageBox.information(
                self.window, translate('OpenLP.Layouts', 'Save Layout As'),
                translate('OpenLP.Layouts', '"{name}" is built in. Please choose another name.').format(name=name))
            return False
        if name in self.custom_layouts():
            answer = QtWidgets.QMessageBox.question(
                self.window, translate('OpenLP.Layouts', 'Save Layout As'),
                translate('OpenLP.Layouts', 'A layout called "{name}" already exists. Replace it?').format(name=name),
                defaultButton=QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes:
                return False
        self.store_layout(name)
        self.active_layout = name
        self.setup_save_button.setEnabled(True)
        self.settings.setValue('user interface/layout for {count} monitors'.format(count=operator_monitor_count()),
                               name)
        self.refresh_layout_combo()
        return True

    def store_layout(self, name):
        layouts = self.custom_layouts()
        layouts[name] = self.capture_layout()
        self.settings.setValue('user interface/layouts', layouts)

    def delete_layout(self):
        """
        Ask which of the user's layouts to delete, and delete it
        """
        names = sorted(self.custom_layouts(), key=str.lower)
        if not names:
            return
        name, ok = QtWidgets.QInputDialog.getItem(
            self.window, translate('OpenLP.Layouts', 'Delete Layout'),
            translate('OpenLP.Layouts', 'Layout to delete:'), names, 0, False)
        if not ok:
            return
        answer = QtWidgets.QMessageBox.question(
            self.window, translate('OpenLP.Layouts', 'Delete Layout'),
            translate('OpenLP.Layouts', 'Delete the layout "{name}"?').format(name=name),
            defaultButton=QtWidgets.QMessageBox.No)
        if answer != QtWidgets.QMessageBox.Yes:
            return
        layouts = self.custom_layouts()
        layouts.pop(name, None)
        self.settings.setValue('user interface/layouts', layouts)
        if name == self.active_layout:
            self.choose_layout(default_layout_for(operator_monitor_count()))
        self.refresh_layout_combo()
