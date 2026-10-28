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
The Theme Manager window (Keystone): edit a theme on a picture of the projector screen. The text areas are dashed
boxes that can be dragged and resized; their settings are on the tabs on the right.
"""
import copy
import logging

from PyQt5 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.display.render import ThemePreviewRenderer
from openlp.core.lib.theme import BackgroundType
from openlp.core.lib.ui import critical_error_message_box


log = logging.getLogger(__name__)

MAIN_AREA = 'main'
FOOTER_AREA = 'footer'
AREAS = (MAIN_AREA, FOOTER_AREA)
AREA_COLOURS = {MAIN_AREA: QtGui.QColor('#1e88e5'), FOOTER_AREA: QtGui.QColor('#fb8c00')}
HANDLES = ('top_left', 'top', 'top_right', 'right', 'bottom_right', 'bottom', 'bottom_left', 'left')
HANDLE_SIZE = 9
MIN_AREA_SIZE = 40
HANDLE_CURSORS = {
    'top_left': QtCore.Qt.SizeFDiagCursor, 'bottom_right': QtCore.Qt.SizeFDiagCursor,
    'top_right': QtCore.Qt.SizeBDiagCursor, 'bottom_left': QtCore.Qt.SizeBDiagCursor,
    'top': QtCore.Qt.SizeVerCursor, 'bottom': QtCore.Qt.SizeVerCursor,
    'left': QtCore.Qt.SizeHorCursor, 'right': QtCore.Qt.SizeHorCursor,
}


def area_label(area):
    if area == MAIN_AREA:
        return translate('OpenLP.ThemeDesigner', 'Main text')
    return translate('OpenLP.ThemeDesigner', 'Footer')


def theme_area_rect(theme, area):
    """
    The position of a text area of a theme, in projector pixels
    """
    prefix = 'font_{area}_'.format(area=area)
    return QtCore.QRect(int(getattr(theme, prefix + 'x')), int(getattr(theme, prefix + 'y')),
                        int(getattr(theme, prefix + 'width')), int(getattr(theme, prefix + 'height')))


def set_theme_area_rect(theme, area, rect):
    prefix = 'font_{area}_'.format(area=area)
    setattr(theme, prefix + 'x', rect.x())
    setattr(theme, prefix + 'y', rect.y())
    setattr(theme, prefix + 'width', rect.width())
    setattr(theme, prefix + 'height', rect.height())


def move_rect(rect, delta, bounds):
    """
    Move a rectangle, keeping it inside the bounds
    """
    moved = rect.translated(delta)
    x = min(max(moved.x(), bounds.left()), bounds.right() + 1 - moved.width())
    y = min(max(moved.y(), bounds.top()), bounds.bottom() + 1 - moved.height())
    moved.moveTo(x, y)
    return moved


def resize_rect(rect, handle, delta, bounds):
    """
    Drag one handle of a rectangle, keeping it inside the bounds and at least MIN_AREA_SIZE big
    """
    left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
    if 'left' in handle:
        left = min(max(left + delta.x(), bounds.left()), right + 1 - MIN_AREA_SIZE)
    if 'right' in handle:
        right = max(min(right + delta.x(), bounds.right()), left - 1 + MIN_AREA_SIZE)
    if handle.startswith('top'):
        top = min(max(top + delta.y(), bounds.top()), bottom + 1 - MIN_AREA_SIZE)
    if handle.startswith('bottom'):
        bottom = max(min(bottom + delta.y(), bounds.bottom()), top - 1 + MIN_AREA_SIZE)
    return QtCore.QRect(QtCore.QPoint(left, top), QtCore.QPoint(right, bottom))


class AreaOverlay(QtWidgets.QWidget):
    """
    Drawn over the slide preview: the dashed text area boxes, with handles on the selected one
    """
    area_selected = QtCore.pyqtSignal(str)
    area_changed = QtCore.pyqtSignal(str)
    area_released = QtCore.pyqtSignal(str)

    def __init__(self, parent, screen_size):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.screen_rect = QtCore.QRect(QtCore.QPoint(0, 0), screen_size)
        self.areas = {area: QtCore.QRect() for area in AREAS}
        self.selected = MAIN_AREA
        self._drag = None

    @property
    def scale(self):
        return self.width() / self.screen_rect.width() if self.screen_rect.width() else 1

    def to_view(self, rect):
        scale = self.scale
        return QtCore.QRectF(rect.x() * scale, rect.y() * scale, rect.width() * scale, rect.height() * scale)

    def handle_rects(self, area):
        view = self.to_view(self.areas[area])
        half = HANDLE_SIZE / 2
        xs = {'left': view.left(), 'middle': view.center().x(), 'right': view.right()}
        ys = {'top': view.top(), 'middle': view.center().y(), 'bottom': view.bottom()}
        spots = {'top_left': ('left', 'top'), 'top': ('middle', 'top'), 'top_right': ('right', 'top'),
                 'right': ('right', 'middle'), 'bottom_right': ('right', 'bottom'), 'bottom': ('middle', 'bottom'),
                 'bottom_left': ('left', 'bottom'), 'left': ('left', 'middle')}
        return {handle: QtCore.QRectF(xs[x] - half, ys[y] - half, HANDLE_SIZE, HANDLE_SIZE)
                for handle, (x, y) in spots.items()}

    def hit_test(self, pos):
        """
        What is under the mouse: (area, handle), (area, None) for inside an area, or (None, None)
        """
        for handle, rect in self.handle_rects(self.selected).items():
            if rect.adjusted(-3, -3, 3, 3).contains(QtCore.QPointF(pos)):
                return self.selected, handle
        # The smaller footer first, so it can still be picked where the main area overlaps it
        for area in (FOOTER_AREA, MAIN_AREA):
            if self.to_view(self.areas[area]).contains(QtCore.QPointF(pos)):
                return area, None
        return None, None

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        order = [area for area in AREAS if area != self.selected] + [self.selected]
        for area in order:
            colour = AREA_COLOURS[area]
            view = self.to_view(self.areas[area])
            fill = QtGui.QColor(colour)
            fill.setAlpha(40 if area == self.selected else 18)
            painter.fillRect(view, fill)
            pen = QtGui.QPen(colour, 3 if area == self.selected else 2, QtCore.Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(view)
            # Name tag in the top left corner
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            text = area_label(area)
            metrics = QtGui.QFontMetrics(font)
            tag_height = metrics.height() + 4
            # Just above the box if there is room, so it doesn't cover the text in it
            tag_top = view.top() - tag_height if view.top() >= tag_height else view.top()
            tag = QtCore.QRectF(view.left(), tag_top, metrics.horizontalAdvance(text) + 10, tag_height)
            painter.fillRect(tag, colour)
            painter.setPen(QtCore.Qt.white)
            painter.drawText(tag, QtCore.Qt.AlignCenter, text)
        painter.setPen(QtGui.QPen(QtGui.QColor('#333333'), 1))
        painter.setBrush(QtCore.Qt.white)
        for rect in self.handle_rects(self.selected).values():
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        area, handle = self.hit_test(event.pos())
        if area is None:
            return
        if area != self.selected:
            self.selected = area
            self.area_selected.emit(area)
            self.update()
        self._drag = {'area': area, 'handle': handle, 'start': event.pos(), 'rect': QtCore.QRect(self.areas[area])}

    def mouseMoveEvent(self, event):
        if not self._drag:
            area, handle = self.hit_test(event.pos())
            if handle:
                self.setCursor(HANDLE_CURSORS[handle])
            elif area:
                self.setCursor(QtCore.Qt.SizeAllCursor)
            else:
                self.unsetCursor()
            return
        offset = event.pos() - self._drag['start']
        delta = QtCore.QPoint(round(offset.x() / self.scale), round(offset.y() / self.scale))
        area = self._drag['area']
        if self._drag['handle']:
            self.areas[area] = resize_rect(self._drag['rect'], self._drag['handle'], delta, self.screen_rect)
        else:
            self.areas[area] = move_rect(self._drag['rect'], delta, self.screen_rect)
        self.update()
        self.area_changed.emit(area)

    def mouseReleaseEvent(self, event):
        if self._drag and event.button() == QtCore.Qt.LeftButton:
            area = self._drag['area']
            self._drag = None
            self.area_released.emit(area)


class ThemeCanvas(QtWidgets.QWidget):
    """
    The projector screen picture: a real slide preview, kept at the projector's shape, with the text areas over it
    """
    def __init__(self, parent, screen_size):
        super().__init__(parent)
        self.screen_size = screen_size
        self.setMinimumSize(480, 270)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor('#3c3c3c'))
        self.setPalette(palette)
        # The preview raises itself after every script it runs: keep it in its own holder, so it can only come to the
        # front inside the holder and the text area boxes stay on top
        self.preview_holder = QtWidgets.QWidget(self)
        self.preview = ThemePreviewRenderer(self.preview_holder, window_title='Theme Manager Preview')
        # The display sets itself up as a separate window: make it part of this one
        self.preview.setParent(self.preview_holder, QtCore.Qt.Widget)
        self.overlay = AreaOverlay(self, screen_size)

    def view_rect(self):
        """
        The biggest rectangle with the projector's shape that fits, centred
        """
        margin = 8
        available = self.rect().adjusted(margin, margin, -margin, -margin)
        size = QtCore.QSize(self.screen_size)
        size.scale(available.size(), QtCore.Qt.KeepAspectRatio)
        rect = QtCore.QRect(QtCore.QPoint(0, 0), size)
        rect.moveCenter(available.center())
        return rect

    def resizeEvent(self, event):
        super().resizeEvent(event)
        rect = self.view_rect()
        self.preview_holder.setGeometry(rect)
        self.preview.setGeometry(0, 0, rect.width(), rect.height())
        self.overlay.setGeometry(rect)
        self.overlay.raise_()
        self.preview.set_scale(rect.width() / self.screen_size.width())


class ThemeDesignerForm(QtWidgets.QDialog, RegistryProperties):
    """
    The Theme Manager window
    """
    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint |
                         QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMaximizeButtonHint)
        self.setObjectName('theme_designer')
        self.theme = None
        self.edit_mode = False
        self.overrides = {area: False for area in AREAS}
        self._updating = False
        self.screen_size = QtCore.QSize(self.renderer.width(), self.renderer.height())
        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(250)
        self.refresh_timer.timeout.connect(self.refresh_preview)
        self.setup_ui()

    # ---- Building the window ----

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        self.canvas = ThemeCanvas(splitter, self.screen_size)
        self.canvas.overlay.area_selected.connect(self.on_area_selected)
        self.canvas.overlay.area_changed.connect(self.on_area_dragged)
        self.canvas.overlay.area_released.connect(lambda area: self.refresh_timer.start())
        self.tabs = QtWidgets.QTabWidget(splitter)
        self.tabs.setMinimumWidth(300)
        self.tabs.addTab(self._build_properties_tab(), translate('OpenLP.ThemeDesigner', 'Properties'))
        self.tabs.addTab(self._build_background_tab(), translate('OpenLP.ThemeDesigner', 'Background'))
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([900, 320])
        layout.addWidget(splitter, stretch=1)
        bottom = QtWidgets.QHBoxLayout()
        self.name_label = QtWidgets.QLabel(translate('OpenLP.ThemeDesigner', 'Theme name:'), self)
        self.name_edit = QtWidgets.QLineEdit(self)
        bottom.addWidget(self.name_label)
        bottom.addWidget(self.name_edit, stretch=1)
        bottom.addStretch()
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save |
                                                     QtWidgets.QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        bottom.addWidget(self.button_box)
        layout.addLayout(bottom)

    def _build_properties_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        area_row = QtWidgets.QHBoxLayout()
        area_row.addWidget(QtWidgets.QLabel(translate('OpenLP.ThemeDesigner', 'Text area:'), tab))
        self.area_combo = QtWidgets.QComboBox(tab)
        for area in AREAS:
            self.area_combo.addItem(area_label(area), area)
        self.area_combo.currentIndexChanged.connect(self.on_area_combo_changed)
        area_row.addWidget(self.area_combo, stretch=1)
        layout.addLayout(area_row)
        self.position_group = QtWidgets.QGroupBox(translate('OpenLP.ThemeDesigner', 'Position and size'), tab)
        form = QtWidgets.QFormLayout(self.position_group)
        self.default_position_check = QtWidgets.QCheckBox(
            translate('OpenLP.ThemeDesigner', 'Use the default position'), self.position_group)
        self.default_position_check.toggled.connect(self.on_default_position_toggled)
        form.addRow(self.default_position_check)
        self.position_spins = {}
        largest = max(self.screen_size.width(), self.screen_size.height())
        for key, text in (('x', translate('OpenLP.ThemeDesigner', 'X (left):')),
                          ('y', translate('OpenLP.ThemeDesigner', 'Y (top):')),
                          ('width', translate('OpenLP.ThemeDesigner', 'Width:')),
                          ('height', translate('OpenLP.ThemeDesigner', 'Height:'))):
            spin = QtWidgets.QSpinBox(self.position_group)
            spin.setRange(0 if key in ('x', 'y') else MIN_AREA_SIZE, largest)
            spin.setSuffix(translate('OpenLP.ThemeDesigner', ' px'))
            spin.valueChanged.connect(self.on_position_spin_changed)
            form.addRow(text, spin)
            self.position_spins[key] = spin
        hint = QtWidgets.QLabel(translate('OpenLP.ThemeDesigner',
                                          'Pixels on the {width} x {height} projector screen. You can also drag a '
                                          'box, or its handles, on the picture.').format(
                                              width=self.screen_size.width(), height=self.screen_size.height()),
                                self.position_group)
        hint.setWordWrap(True)
        form.addRow(hint)
        layout.addWidget(self.position_group)
        layout.addStretch()
        return tab

    def _build_background_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        note = QtWidgets.QLabel(translate('OpenLP.ThemeDesigner',
                                          'Background settings are coming in the next update. Until then, use '
                                          'right-click > "Edit with classic wizard" in the Themes list.'), tab)
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        return tab

    # ---- Opening and saving ----

    def exec(self, theme, edit=False):
        """
        Edit a theme (edit=True) or create a new one

        :return: True if the theme was saved
        """
        self.theme = copy.deepcopy(theme)
        self.edit_mode = edit
        self.name_label.setVisible(not edit)
        self.name_edit.setVisible(not edit)
        self.name_edit.setText('' if not edit else self.theme.theme_name)
        if edit:
            self.setWindowTitle(translate('OpenLP.ThemeDesigner', 'Theme Manager - {name}').format(
                name=self.theme.theme_name))
        else:
            self.setWindowTitle(translate('OpenLP.ThemeDesigner', 'Theme Manager - New Theme'))
        self.overrides = {MAIN_AREA: bool(self.theme.font_main_override),
                          FOOTER_AREA: bool(self.theme.font_footer_override)}
        for area in AREAS:
            if not self.overrides[area]:
                self._set_default_area(area)
            self.canvas.overlay.areas[area] = theme_area_rect(self.theme, area)
        self.canvas.overlay.selected = MAIN_AREA
        self.area_combo.setCurrentIndex(0)
        self.update_position_fields()
        self._fit_on_screen()
        QtCore.QTimer.singleShot(0, self.refresh_preview)
        return QtWidgets.QDialog.exec(self) == QtWidgets.QDialog.Accepted

    def _fit_on_screen(self):
        screen = (self.parentWidget().screen() if self.parentWidget() else None) or \
            QtWidgets.QApplication.primaryScreen()
        available = screen.availableGeometry()
        self.resize(min(1300, available.width() - 40), min(780, available.height() - 60))
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def accept(self):
        """
        Save the theme
        """
        name = self.theme.theme_name if self.edit_mode else self.name_edit.text().strip()
        if not name:
            critical_error_message_box(translate('OpenLP.ThemeWizard', 'Theme Name Missing'),
                                       translate('OpenLP.ThemeWizard', 'There is no name for this theme. '
                                                 'Please enter one.'))
            return
        if name in ('-1', 'None'):
            critical_error_message_box(translate('OpenLP.ThemeWizard', 'Theme Name Invalid'),
                                       translate('OpenLP.ThemeWizard', 'Invalid theme name. Please enter one.'))
            return
        if not self.edit_mode and not self.theme_manager.check_if_theme_exists(name):
            return
        self.apply_areas_to_theme()
        self.theme.theme_name = name
        # Keep the background in the theme's own folder, as the classic wizard does
        if self.theme.background_type in (BackgroundType.to_string(BackgroundType.Image),
                                          BackgroundType.to_string(BackgroundType.Video)):
            self.theme.background_filename = self.theme_manager.theme_path / name / \
                self.theme.background_filename.name
        elif self.theme.background_type == BackgroundType.to_string(BackgroundType.Stream):
            self.theme.background_filename = self.theme.background_source
        self.theme_manager.save_theme(self.theme)
        self.theme_manager.save_preview(name, self.canvas.preview.save_screenshot())
        return QtWidgets.QDialog.accept(self)

    # ---- Text areas ----

    def selected_area(self):
        return self.canvas.overlay.selected

    def _set_default_area(self, area):
        if area == MAIN_AREA:
            self.theme.set_default_header()
        else:
            self.theme.set_default_footer()
        self.canvas.overlay.areas[area] = theme_area_rect(self.theme, area)

    def apply_areas_to_theme(self):
        self.theme.font_main_override = self.overrides[MAIN_AREA]
        self.theme.font_footer_override = self.overrides[FOOTER_AREA]
        for area in AREAS:
            set_theme_area_rect(self.theme, area, self.canvas.overlay.areas[area])

    def update_position_fields(self):
        """
        Show the selected area's position in the Properties tab
        """
        area = self.selected_area()
        rect = self.canvas.overlay.areas[area]
        self._updating = True
        try:
            self.default_position_check.setChecked(not self.overrides[area])
            for key, value in (('x', rect.x()), ('y', rect.y()), ('width', rect.width()),
                               ('height', rect.height())):
                self.position_spins[key].setValue(value)
        finally:
            self._updating = False

    def on_area_selected(self, area):
        self._updating = True
        self.area_combo.setCurrentIndex(AREAS.index(area))
        self._updating = False
        self.update_position_fields()

    def on_area_combo_changed(self, index):
        if self._updating or index < 0:
            return
        self.canvas.overlay.selected = AREAS[index]
        self.canvas.overlay.update()
        self.update_position_fields()

    def on_area_dragged(self, area):
        self.overrides[area] = True
        if area == self.selected_area():
            self.update_position_fields()

    def on_position_spin_changed(self, value):
        if self._updating:
            return
        area = self.selected_area()
        spins = self.position_spins
        rect = QtCore.QRect(spins['x'].value(), spins['y'].value(), spins['width'].value(), spins['height'].value())
        # Keep it on the screen
        rect = rect.intersected(self.canvas.overlay.screen_rect)
        if rect.width() < MIN_AREA_SIZE or rect.height() < MIN_AREA_SIZE:
            return
        self.canvas.overlay.areas[area] = rect
        self.overrides[area] = True
        self._updating = True
        self.default_position_check.setChecked(False)
        self._updating = False
        self.canvas.overlay.update()
        self.refresh_timer.start()

    def on_default_position_toggled(self, checked):
        if self._updating:
            return
        area = self.selected_area()
        self.overrides[area] = not checked
        if checked:
            self._set_default_area(area)
            self.update_position_fields()
            self.canvas.overlay.update()
            self.refresh_timer.start()

    # ---- Preview ----

    def refresh_preview(self):
        """
        Draw the sample slide with the current settings
        """
        if not self.isVisible():
            return
        if not self.canvas.preview.is_initialised:
            self.refresh_timer.start()
            return
        self.apply_areas_to_theme()
        self.canvas.preview.set_scale(self.canvas.view_rect().width() / self.screen_size.width())
        self.canvas.preview.show_sample(self.theme)
