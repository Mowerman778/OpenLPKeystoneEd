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
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from openlp.core.common import get_images_filter, is_not_image_file
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.display.render import ThemePreviewRenderer
from openlp.core.lib.theme import BackgroundGradientType, BackgroundType
from openlp.core.lib.ui import critical_error_message_box
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.media import VIDEO_EXT
from openlp.core.widgets.buttons import ColorButton
from openlp.core.widgets.dialogs import FileDialog


log = logging.getLogger(__name__)

MAIN_AREA = 'main'
FOOTER_AREA = 'footer'
AREAS = (MAIN_AREA, FOOTER_AREA)
AREA_COLOURS = {MAIN_AREA: QtGui.QColor('#1e88e5'), FOOTER_AREA: QtGui.QColor('#fb8c00')}
HANDLES = ('top_left', 'top', 'top_right', 'right', 'bottom_right', 'bottom', 'bottom_left', 'left')
HANDLE_SIZE = 9
MOVE_GRIP_SIZE = 22
MOVE = 'move'
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

    def move_grip_rect(self, area):
        """
        The square in the middle of a box that shows where to grab it to move it
        """
        rect = QtCore.QRectF(0, 0, MOVE_GRIP_SIZE, MOVE_GRIP_SIZE)
        rect.moveCenter(self.to_view(self.areas[area]).center())
        return rect

    def hit_test(self, pos):
        """
        What is under the mouse: (area, handle name), (area, MOVE) for the move square, (area, None) for elsewhere
        inside an area, or (None, None)
        """
        point = QtCore.QPointF(pos)
        # The selected box first, then the smaller footer, so it can still be picked where the main area overlaps it
        order = [self.selected] + [area for area in (FOOTER_AREA, MAIN_AREA) if area != self.selected]
        for area in order:
            for handle, rect in self.handle_rects(area).items():
                if rect.adjusted(-3, -3, 3, 3).contains(point):
                    return area, handle
        for area in order:
            if self.move_grip_rect(area).adjusted(-2, -2, 2, 2).contains(point):
                return area, MOVE
        for area in (FOOTER_AREA, MAIN_AREA):
            if self.to_view(self.areas[area]).contains(point):
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
            # Sizing handles on the edges and corners
            painter.setPen(QtGui.QPen(colour.darker(150), 1))
            painter.setBrush(QtCore.Qt.white)
            for rect in self.handle_rects(area).values():
                painter.drawRect(rect)
            self._paint_move_grip(painter, area, colour)
            painter.setBrush(QtCore.Qt.NoBrush)

    def _paint_move_grip(self, painter, area, colour):
        """
        A square with a four-way arrow in the middle of the box: grab it to move the box
        """
        rect = self.move_grip_rect(area)
        painter.setPen(QtGui.QPen(colour.darker(150), 1))
        painter.setBrush(colour)
        painter.drawRect(rect)
        painter.setPen(QtGui.QPen(QtCore.Qt.white, 2))
        centre = rect.center()
        arm = MOVE_GRIP_SIZE / 2 - 4
        tip = 3
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            end = QtCore.QPointF(centre.x() + dx * arm, centre.y() + dy * arm)
            painter.drawLine(centre, end)
            # Arrow head
            painter.drawLine(end, QtCore.QPointF(end.x() - dx * tip + dy * tip, end.y() - dy * tip + dx * tip))
            painter.drawLine(end, QtCore.QPointF(end.x() - dx * tip - dy * tip, end.y() - dy * tip - dx * tip))

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
            if handle in HANDLE_CURSORS:
                self.setCursor(HANDLE_CURSORS[handle])
            elif area:
                self.setCursor(QtCore.Qt.SizeAllCursor)
            else:
                self.unsetCursor()
            return
        offset = event.pos() - self._drag['start']
        delta = QtCore.QPoint(round(offset.x() / self.scale), round(offset.y() / self.scale))
        area = self._drag['area']
        if self._drag['handle'] not in (None, MOVE):
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
        layout.addWidget(self._build_font_group(tab))
        layout.addWidget(self._build_paragraph_group(tab))
        effects = QtWidgets.QHBoxLayout()
        self.outline_group, self.outline_color_button, self.outline_size_spin = \
            self._build_effect_group(tab, translate('OpenLP.ThemeDesigner', 'Outline'))
        self.shadow_group, self.shadow_color_button, self.shadow_size_spin = \
            self._build_effect_group(tab, translate('OpenLP.ThemeDesigner', 'Shadow'))
        effects.addWidget(self.outline_group)
        effects.addWidget(self.shadow_group)
        layout.addLayout(effects)
        layout.addWidget(self._build_position_group(tab))
        layout.addStretch()
        # The tab is taller than a laptop screen allows: let it scroll
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setWidget(tab)
        return scroll

    def _build_font_group(self, parent):
        group = QtWidgets.QGroupBox(translate('OpenLP.ThemeDesigner', 'Font'), parent)
        form = QtWidgets.QFormLayout(group)
        self.font_combo = QtWidgets.QFontComboBox(group)
        self.font_combo.currentFontChanged.connect(self.on_font_changed)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Font:'), self.font_combo)
        self.font_size_spin = QtWidgets.QSpinBox(group)
        self.font_size_spin.setRange(1, 999)
        self.font_size_spin.setSuffix(' {unit}'.format(unit=UiStrings().FontSizePtUnit))
        self.font_size_spin.valueChanged.connect(self.store_text_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Size:'), self.font_size_spin)
        style_row = QtWidgets.QHBoxLayout()
        self.font_color_button = ColorButton(group)
        self.font_color_button.colorChanged.connect(self.store_text_fields)
        style_row.addWidget(self.font_color_button)
        self.bold_button = QtWidgets.QToolButton(group)
        self.bold_button.setCheckable(True)
        self.bold_button.setIcon(UiIcons().bold)
        self.bold_button.setToolTip(translate('OpenLP.ThemeDesigner', 'Bold'))
        self.bold_button.toggled.connect(self.store_text_fields)
        style_row.addWidget(self.bold_button)
        self.italic_button = QtWidgets.QToolButton(group)
        self.italic_button.setCheckable(True)
        self.italic_button.setIcon(UiIcons().italic)
        self.italic_button.setToolTip(translate('OpenLP.ThemeDesigner', 'Italic'))
        self.italic_button.toggled.connect(self.store_text_fields)
        style_row.addWidget(self.italic_button)
        style_row.addStretch()
        form.addRow(translate('OpenLP.ThemeDesigner', 'Colour and style:'), style_row)
        return group

    def _build_paragraph_group(self, parent):
        group = QtWidgets.QGroupBox(translate('OpenLP.ThemeDesigner', 'Paragraph'), parent)
        form = QtWidgets.QFormLayout(group)
        self.horizontal_align_combo = QtWidgets.QComboBox(group)
        # In the order of HorizontalType
        self.horizontal_align_combo.addItems([translate('OpenLP.ThemeDesigner', 'Left'),
                                              translate('OpenLP.ThemeDesigner', 'Right'),
                                              translate('OpenLP.ThemeDesigner', 'Centre'),
                                              translate('OpenLP.ThemeDesigner', 'Justify')])
        self.horizontal_align_combo.currentIndexChanged.connect(self.store_text_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Align across:'), self.horizontal_align_combo)
        self.vertical_align_combo = QtWidgets.QComboBox(group)
        # In the order of VerticalType
        self.vertical_align_combo.addItems([translate('OpenLP.ThemeDesigner', 'Top'),
                                            translate('OpenLP.ThemeDesigner', 'Middle'),
                                            translate('OpenLP.ThemeDesigner', 'Bottom')])
        self.vertical_align_combo.currentIndexChanged.connect(self.store_text_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Align up/down:'), self.vertical_align_combo)
        self.line_spacing_spin = QtWidgets.QSpinBox(group)
        self.line_spacing_spin.setRange(-250, 250)
        self.line_spacing_spin.setSuffix(translate('OpenLP.ThemeDesigner', ' px'))
        self.line_spacing_spin.valueChanged.connect(self.store_text_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Line spacing:'), self.line_spacing_spin)
        self.letter_spacing_spin = QtWidgets.QDoubleSpinBox(group)
        self.letter_spacing_spin.setRange(-250, 250)
        self.letter_spacing_spin.setDecimals(1)
        self.letter_spacing_spin.setSuffix(translate('OpenLP.ThemeDesigner', ' px'))
        self.letter_spacing_spin.valueChanged.connect(self.store_text_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Letter spacing:'), self.letter_spacing_spin)
        self.align_note = QtWidgets.QLabel(translate('OpenLP.ThemeDesigner',
                                                     'Alignment is set on the Main text.'), group)
        self.align_note.setWordWrap(True)
        form.addRow(self.align_note)
        return group

    def _build_effect_group(self, parent, title):
        group = QtWidgets.QGroupBox(title, parent)
        group.setCheckable(True)
        group.toggled.connect(self.store_text_fields)
        form = QtWidgets.QFormLayout(group)
        color_button = ColorButton(group)
        color_button.colorChanged.connect(self.store_text_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Colour:'), color_button)
        size_spin = QtWidgets.QSpinBox(group)
        size_spin.setRange(0, 9999)
        size_spin.setSuffix(translate('OpenLP.ThemeDesigner', ' px'))
        size_spin.valueChanged.connect(self.store_text_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Size:'), size_spin)
        return group, color_button, size_spin

    def _build_position_group(self, parent):
        self.position_group = QtWidgets.QGroupBox(translate('OpenLP.ThemeDesigner', 'Position and size'), parent)
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
                                          'Pixels on the {width} x {height} projector screen. On the picture, drag '
                                          'the square in the middle of a box to move it, or its white handles to '
                                          'size it.').format(width=self.screen_size.width(),
                                                             height=self.screen_size.height()),
                                self.position_group)
        hint.setWordWrap(True)
        form.addRow(hint)
        return self.position_group

    def _build_background_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        type_row = QtWidgets.QHBoxLayout()
        type_row.addWidget(QtWidgets.QLabel(translate('OpenLP.ThemeDesigner', 'Background:'), tab))
        self.background_type_combo = QtWidgets.QComboBox(tab)
        # In the order of BackgroundType
        self.background_type_combo.addItems([translate('OpenLP.ThemeDesigner', 'Solid colour'),
                                             translate('OpenLP.ThemeDesigner', 'Gradient'),
                                             translate('OpenLP.ThemeDesigner', 'Picture or animated GIF'),
                                             translate('OpenLP.ThemeDesigner', 'Transparent'),
                                             translate('OpenLP.ThemeDesigner', 'Video'),
                                             translate('OpenLP.ThemeDesigner', 'Live stream')])
        self.background_type_combo.currentIndexChanged.connect(self.on_background_type_changed)
        type_row.addWidget(self.background_type_combo, stretch=1)
        layout.addLayout(type_row)
        self.background_pages = QtWidgets.QStackedWidget(tab)
        layout.addWidget(self.background_pages)
        layout.addStretch()
        # Solid colour
        page, form = self._background_page()
        self.background_color_button = ColorButton(page)
        self.background_color_button.colorChanged.connect(self.store_background_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Colour:'), self.background_color_button)
        # Gradient
        page, form = self._background_page()
        self.gradient_combo = QtWidgets.QComboBox(page)
        # In the order of BackgroundGradientType
        self.gradient_combo.addItems([translate('OpenLP.ThemeDesigner', 'Left to right'),
                                      translate('OpenLP.ThemeDesigner', 'Top to bottom'),
                                      translate('OpenLP.ThemeDesigner', 'Circular'),
                                      translate('OpenLP.ThemeDesigner', 'Top left to bottom right'),
                                      translate('OpenLP.ThemeDesigner', 'Bottom left to top right')])
        self.gradient_combo.currentIndexChanged.connect(self.store_background_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Direction:'), self.gradient_combo)
        self.gradient_start_button = ColorButton(page)
        self.gradient_start_button.colorChanged.connect(self.store_background_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Start colour:'), self.gradient_start_button)
        self.gradient_end_button = ColorButton(page)
        self.gradient_end_button.colorChanged.connect(self.store_background_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'End colour:'), self.gradient_end_button)
        # Picture
        self.image_file_label, self.image_border_button = self._background_file_page(
            translate('OpenLP.ThemeDesigner', 'Import graphic...'), self.on_import_image_clicked,
            translate('OpenLP.ThemeDesigner', 'Pictures are stretched to fill the screen. Animated GIFs play on the '
                      'projector, and here.'))
        # Transparent
        page, form = self._background_page()
        form.addRow(self._note(page, translate('OpenLP.ThemeDesigner', 'No background: whatever is behind the text '
                                               '(for example a video playing) shows through.')))
        # Video
        self.video_file_label, self.video_border_button = self._background_file_page(
            translate('OpenLP.ThemeDesigner', 'Import video...'), self.on_import_video_clicked,
            translate('OpenLP.ThemeDesigner', 'The video plays behind the words on the projector. This picture '
                      'shows the border colour instead.'))
        # Live stream
        page, form = self._background_page()
        self.stream_label = QtWidgets.QLabel(page)
        self.stream_label.setWordWrap(True)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Stream:'), self.stream_label)
        form.addRow(self._note(page, translate('OpenLP.ThemeDesigner', 'Choose a live stream with right-click > '
                                               '"Edit with classic wizard" in the Themes list.')))
        return tab

    def _background_page(self):
        page = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(page)
        form.setContentsMargins(0, 8, 0, 0)
        self.background_pages.addWidget(page)
        return page, form

    def _background_file_page(self, button_text, on_click, note):
        page, form = self._background_page()
        button = QtWidgets.QPushButton(UiIcons().open, button_text, page)
        button.clicked.connect(on_click)
        form.addRow(button)
        file_label = QtWidgets.QLabel(page)
        file_label.setWordWrap(True)
        form.addRow(translate('OpenLP.ThemeDesigner', 'File:'), file_label)
        border_button = ColorButton(page)
        border_button.colorChanged.connect(self.store_background_fields)
        form.addRow(translate('OpenLP.ThemeDesigner', 'Border colour:'), border_button)
        form.addRow(self._note(page, note))
        return file_label, border_button

    @staticmethod
    def _note(parent, text):
        label = QtWidgets.QLabel(text, parent)
        label.setWordWrap(True)
        label.setStyleSheet('color: palette(mid);')
        return label

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
        # An image or video already in the theme: start from its original file, as the classic wizard does
        if self.theme.background_type in (BackgroundType.to_string(BackgroundType.Image),
                                          BackgroundType.to_string(BackgroundType.Video)):
            source = self.theme.background_source
            if not source or not Path(source).exists():
                source = self.theme.background_filename
            self.theme.background_source = source
            self.theme.background_filename = source
        self.canvas.overlay.selected = MAIN_AREA
        self._updating = True
        self.area_combo.setCurrentIndex(0)
        self._updating = False
        self.show_area_fields()
        self.load_background_fields()
        self.tabs.setCurrentIndex(0)
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
        if not self.background_file_chosen():
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
        else:
            self.theme.background_filename = None
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
        self.show_area_fields()

    def on_area_combo_changed(self, index):
        if self._updating or index < 0:
            return
        self.canvas.overlay.selected = AREAS[index]
        self.canvas.overlay.update()
        self.show_area_fields()

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

    # ---- Font and paragraph ----

    def show_area_fields(self):
        """
        Fill the Properties tab with the selected area's settings
        """
        self.update_position_fields()
        self.load_text_fields()

    def load_text_fields(self):
        theme = self.theme
        area = self.selected_area()
        prefix = 'font_{area}_'.format(area=area)
        is_main = area == MAIN_AREA
        self._updating = True
        try:
            font_name = getattr(theme, prefix + 'name')
            self.font_combo.setCurrentFont(QtGui.QFont(font_name))
            # Not installed here: show the theme's font name anyway
            self.font_combo.setEditText(font_name)
            self.font_size_spin.setValue(int(getattr(theme, prefix + 'size')))
            self.font_color_button.color = getattr(theme, prefix + 'color')
            self.bold_button.setChecked(bool(getattr(theme, prefix + 'bold')))
            self.italic_button.setChecked(bool(getattr(theme, prefix + 'italics')))
            self.line_spacing_spin.setValue(int(getattr(theme, prefix + 'line_adjustment') or 0))
            self.letter_spacing_spin.setValue(float(getattr(theme, prefix + 'letter_adjustment') or 0))
            self.horizontal_align_combo.setCurrentIndex(int(theme.display_horizontal_align))
            self.vertical_align_combo.setCurrentIndex(int(theme.display_vertical_align))
            self.outline_group.setChecked(bool(theme.font_main_outline))
            self.outline_color_button.color = theme.font_main_outline_color
            self.outline_size_spin.setValue(int(theme.font_main_outline_size))
            self.shadow_group.setChecked(bool(theme.font_main_shadow))
            self.shadow_color_button.color = theme.font_main_shadow_color
            self.shadow_size_spin.setValue(int(theme.font_main_shadow_size))
        finally:
            self._updating = False
        # Alignment, outline and shadow belong to the main text only
        for widget in (self.horizontal_align_combo, self.vertical_align_combo):
            widget.setEnabled(is_main)
        self.align_note.setVisible(not is_main)
        self.outline_group.setVisible(is_main)
        self.shadow_group.setVisible(is_main)

    def store_text_fields(self, *args):
        """
        A font or paragraph setting was changed: put it in the theme
        """
        if self._updating or self.theme is None:
            return
        theme = self.theme
        prefix = 'font_{area}_'.format(area=self.selected_area())
        setattr(theme, prefix + 'size', self.font_size_spin.value())
        setattr(theme, prefix + 'color', self.font_color_button.color)
        setattr(theme, prefix + 'bold', self.bold_button.isChecked())
        setattr(theme, prefix + 'italics', self.italic_button.isChecked())
        setattr(theme, prefix + 'line_adjustment', self.line_spacing_spin.value())
        setattr(theme, prefix + 'letter_adjustment', self.letter_spacing_spin.value())
        if self.selected_area() == MAIN_AREA:
            theme.display_horizontal_align = self.horizontal_align_combo.currentIndex()
            theme.display_vertical_align = self.vertical_align_combo.currentIndex()
            theme.font_main_outline = self.outline_group.isChecked()
            theme.font_main_outline_color = self.outline_color_button.color
            theme.font_main_outline_size = self.outline_size_spin.value()
            theme.font_main_shadow = self.shadow_group.isChecked()
            theme.font_main_shadow_color = self.shadow_color_button.color
            theme.font_main_shadow_size = self.shadow_size_spin.value()
        self.refresh_timer.start()

    def on_font_changed(self, font):
        """
        A font was picked. Only then is the name stored: if the theme's font isn't installed on this computer the
        list shows a stand-in, which must not replace it when another setting is changed.
        """
        if self._updating or self.theme is None:
            return
        setattr(self.theme, 'font_{area}_name'.format(area=self.selected_area()), font.family())
        self.refresh_timer.start()

    # ---- Background ----

    def load_background_fields(self):
        theme = self.theme
        self._updating = True
        try:
            self.background_type_combo.setCurrentIndex(BackgroundType.from_string(theme.background_type))
            self.background_pages.setCurrentIndex(self.background_type_combo.currentIndex())
            self.background_color_button.color = theme.background_color
            self.gradient_combo.setCurrentIndex(BackgroundGradientType.from_string(theme.background_direction))
            self.gradient_start_button.color = theme.background_start_color
            self.gradient_end_button.color = theme.background_end_color
            for button in (self.image_border_button, self.video_border_button):
                button.color = theme.background_border_color
            self.show_background_file()
        finally:
            self._updating = False

    def show_background_file(self):
        source = self.theme.background_source
        name = Path(source).name if source and not isinstance(source, str) else (source or '')
        none = translate('OpenLP.ThemeDesigner', '(none chosen)')
        is_image = self.theme.background_type == BackgroundType.to_string(BackgroundType.Image)
        is_video = self.theme.background_type == BackgroundType.to_string(BackgroundType.Video)
        self.image_file_label.setText(name if is_image and name else none)
        self.video_file_label.setText(name if is_video and name else none)
        is_stream = self.theme.background_type == BackgroundType.to_string(BackgroundType.Stream)
        self.stream_label.setText(str(source) if is_stream and source else none)

    def on_background_type_changed(self, index):
        self.background_pages.setCurrentIndex(index)
        if self._updating or self.theme is None:
            return
        old_type = self.theme.background_type
        self.theme.background_type = BackgroundType.to_string(index)
        if old_type != self.theme.background_type and index in (BackgroundType.Image, BackgroundType.Video,
                                                                BackgroundType.Stream):
            # A file chosen for one kind of background doesn't suit another
            self.theme.background_source = None
            self.theme.background_filename = None
        self.show_background_file()
        self.refresh_timer.start()

    def store_background_fields(self, *args):
        if self._updating or self.theme is None:
            return
        theme = self.theme
        theme.background_color = self.background_color_button.color
        theme.background_direction = BackgroundGradientType.to_string(self.gradient_combo.currentIndex())
        theme.background_start_color = self.gradient_start_button.color
        theme.background_end_color = self.gradient_end_button.color
        if theme.background_type == BackgroundType.to_string(BackgroundType.Video):
            theme.background_border_color = self.video_border_button.color
        else:
            theme.background_border_color = self.image_border_button.color
        self.refresh_timer.start()

    def on_import_image_clicked(self):
        file_filter = '{images};;{all} (*)'.format(images=get_images_filter(), all=UiStrings().AllFiles)
        self._import_background(translate('OpenLP.ThemeDesigner', 'Choose a picture or animated GIF'), file_filter)

    def on_import_video_clicked(self):
        file_filter = '{videos} ({extensions});;{all} (*)'.format(
            videos=translate('OpenLP', 'Video Files'), extensions=' '.join(VIDEO_EXT), all=UiStrings().AllFiles)
        self._import_background(translate('OpenLP.ThemeDesigner', 'Choose a video'), file_filter)

    def _import_background(self, caption, file_filter):
        path, _ = FileDialog.getOpenFileName(self, caption, Path.home(), file_filter)
        if not path:
            return
        self.set_background_file(path)

    def set_background_file(self, path):
        """
        Use this picture or video as the background. It is copied into the theme when the theme is saved.
        """
        self.theme.background_source = path
        self.theme.background_filename = path
        self.show_background_file()
        self.refresh_timer.start()

    def background_file_chosen(self):
        """
        A picture or video background needs a file: say so if there isn't one
        """
        kind = self.theme.background_type
        if kind == BackgroundType.to_string(BackgroundType.Image) and is_not_image_file(self.theme.background_source):
            critical_error_message_box(translate('OpenLP.ThemeWizard', 'Background Image Empty'),
                                       translate('OpenLP.ThemeDesigner', 'Click "Import graphic..." on the '
                                                 'Background tab to choose a picture.'))
            return False
        if kind == BackgroundType.to_string(BackgroundType.Video) and not self.theme.background_source:
            critical_error_message_box(translate('OpenLP.ThemeWizard', 'Background Video Empty'),
                                       translate('OpenLP.ThemeDesigner', 'Click "Import video..." on the '
                                                 'Background tab to choose a video.'))
            return False
        return True

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
