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
The Video Trigger Manager places up to ten video clips on a presentation slide, each in a box on the slide. In the Live
panel the boxes are drawn over the slide with their descriptions, and clicking one plays its clip full screen. The
boxes are only seen by the operator, never on the display screen.

Boxes are kept as fractions of the display screen, (x, y, width, height), so they fit the Live panel at any size.
"""
import copy
import logging
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.lib.serviceitem import DESCRIPTION_LENGTH, MAX_SLIDE_CLIPS, make_slide_clip
from openlp.core.ui.media import VIDEO_EXT
from openlp.core.ui.themedesigner import HANDLE_CURSORS, MOVE, box_handle_rects, box_move_grip_rect, move_rect, \
    paint_box_handles, resize_rect
from openlp.core.widgets.dialogs import FileDialog


log = logging.getLogger(__name__)

CLIP_COLOURS = ('#e53935', '#1e88e5', '#43a047', '#fb8c00', '#8e24aa', '#00acc1', '#c0ca33', '#6d4c41', '#d81b60',
                '#546e7a')
# Where new boxes go, so they don't land on top of each other: a 5 x 2 grid of fractions of the screen
NEW_CLIP_SIZE = (0.18, 0.12)


def clip_colour(index):
    return QtGui.QColor(CLIP_COLOURS[index % len(CLIP_COLOURS)])


def fraction_to_rect(fractions, size):
    """
    :param fractions: (x, y, width, height) as fractions of the screen
    :param QtCore.QSize size: The screen size
    :return: The box in screen pixels
    """
    x, y, width, height = fractions
    return QtCore.QRect(round(x * size.width()), round(y * size.height()),
                        round(width * size.width()), round(height * size.height()))


def rect_to_fraction(rect, size):
    """
    :param QtCore.QRect rect: A box in screen pixels
    :param QtCore.QSize size: The screen size
    :return: (x, y, width, height) as fractions of the screen
    """
    return (round(rect.x() / size.width(), 4), round(rect.y() / size.height(), 4),
            round(rect.width() / size.width(), 4), round(rect.height() / size.height(), 4))


def new_clip_rect(index):
    """
    The box for a newly added clip, in a 5 x 2 grid so new boxes don't cover each other
    """
    column, row = index % 5, index // 5 % 2
    return (0.02 + column * 0.196, 0.06 + row * 0.8, NEW_CLIP_SIZE[0], NEW_CLIP_SIZE[1])


def fit_rect(outer, aspect):
    """
    The biggest rectangle of the given aspect ratio, centred in outer

    :param QtCore.QRectF outer: The space to fit into
    :param float aspect: Width / height
    """
    width = min(outer.width(), outer.height() * aspect)
    height = width / aspect
    rect = QtCore.QRectF(0, 0, width, height)
    rect.moveCenter(outer.center())
    return rect


def paint_clip_box(painter, view, number, description, colour, hot=False, playing=False):
    """
    A clip's box: a dashed outline with its number and underlined description in a tag along the top

    :param QtGui.QPainter painter: The painter
    :param QtCore.QRectF view: The box, in widget coordinates
    :param int number: The clip's number, from 1
    :param str description: The clip's description
    :param QtGui.QColor colour: The clip's colour
    :param bool hot: True while the mouse is over it, or it is selected
    :param bool playing: True while the clip is playing
    """
    fill = QtGui.QColor(colour)
    fill.setAlpha(110 if playing else 60 if hot else 25)
    painter.fillRect(view, fill)
    painter.setPen(QtGui.QPen(colour, 3 if hot else 2, QtCore.Qt.DashLine))
    painter.setBrush(QtCore.Qt.NoBrush)
    painter.drawRect(view)
    font = QtGui.QFont(painter.font())
    font.setBold(True)
    font.setUnderline(True)
    painter.setFont(font)
    metrics = QtGui.QFontMetrics(font)
    prefix = '▶ ' if playing else ''
    text = metrics.elidedText('{prefix}{number}. {text}'.format(prefix=prefix, number=number, text=description),
                              QtCore.Qt.ElideRight, max(int(view.width()) - 8, 10))
    tag = QtCore.QRectF(view.left(), view.top(), min(metrics.horizontalAdvance(text) + 8, view.width()),
                        metrics.height() + 4)
    painter.fillRect(tag, colour)
    painter.setPen(QtCore.Qt.white)
    painter.drawText(tag, QtCore.Qt.AlignCenter, text)


class TriggerCanvas(QtWidgets.QWidget):
    """
    The slide as it looks on the display screen, with a box for each clip. The selected box has sizing handles and a
    move square, and the others can be clicked to select them.
    """
    clip_selected = QtCore.pyqtSignal(int)
    clip_changed = QtCore.pyqtSignal(int)

    def __init__(self, parent, screen_size):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(480, 300)
        self.screen_size = QtCore.QSize(screen_size)
        self.screen_rect = QtCore.QRect(QtCore.QPoint(0, 0), self.screen_size)
        self.picture = None
        self.rects = []
        self.descriptions = []
        self.selected = -1
        self._drag = None

    def set_picture(self, picture):
        """
        :param QtGui.QPixmap | None picture: The slide
        """
        self.picture = picture
        self.update()

    def set_clips(self, clips, selected=-1):
        self.rects = [fraction_to_rect(clip['rect'], self.screen_size) for clip in clips]
        self.descriptions = [clip['description'] for clip in clips]
        self.selected = selected
        self.update()

    def view_rect(self):
        """
        Where the display screen is drawn: as big as fits, with a margin for the handles
        """
        return fit_rect(QtCore.QRectF(self.rect()).adjusted(10, 10, -10, -10),
                        self.screen_size.width() / self.screen_size.height())

    @property
    def scale(self):
        return self.view_rect().width() / self.screen_size.width()

    def to_view(self, rect):
        view = self.view_rect()
        scale = self.scale
        return QtCore.QRectF(view.x() + rect.x() * scale, view.y() + rect.y() * scale, rect.width() * scale,
                             rect.height() * scale)

    def hit_test(self, pos):
        """
        What is under the mouse: (index, handle name), (index, MOVE) for the move square, (index, None) for elsewhere in
        a box, or (-1, None). The selected box comes first, then the boxes on top.
        """
        point = QtCore.QPointF(pos)
        if 0 <= self.selected < len(self.rects):
            view = self.to_view(self.rects[self.selected])
            for handle, rect in box_handle_rects(view).items():
                if rect.adjusted(-3, -3, 3, 3).contains(point):
                    return self.selected, handle
            if box_move_grip_rect(view).adjusted(-2, -2, 2, 2).contains(point):
                return self.selected, MOVE
        for index in reversed(range(len(self.rects))):
            if self.to_view(self.rects[index]).contains(point):
                return index, None
        return -1, None

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        view = self.view_rect()
        painter.fillRect(view, QtCore.Qt.black)
        if self.picture and not self.picture.isNull():
            # The presentation keeps its own shape on the display screen, with black bars if it doesn't fill it
            slide = fit_rect(view, self.picture.width() / self.picture.height())
            painter.drawPixmap(slide, self.picture, QtCore.QRectF(self.picture.rect()))
        else:
            painter.setPen(QtCore.Qt.gray)
            painter.drawText(view, QtCore.Qt.AlignCenter, translate('OpenLP.VideoTriggers', 'No picture of the slide'))
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        # The selected box last, so it is on top
        order = [index for index in range(len(self.rects)) if index != self.selected]
        if 0 <= self.selected < len(self.rects):
            order.append(self.selected)
        for index in order:
            box = self.to_view(self.rects[index])
            paint_clip_box(painter, box, index + 1, self.descriptions[index], clip_colour(index),
                           hot=index == self.selected)
            if index == self.selected:
                paint_box_handles(painter, box, clip_colour(index))

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        index, handle = self.hit_test(event.pos())
        if index < 0:
            return
        if index != self.selected:
            self.selected = index
            self.clip_selected.emit(index)
            self.update()
        self._drag = {'index': index, 'handle': handle, 'start': event.pos(), 'rect': QtCore.QRect(self.rects[index])}

    def mouseMoveEvent(self, event):
        if not self._drag:
            index, handle = self.hit_test(event.pos())
            if handle in HANDLE_CURSORS:
                self.setCursor(HANDLE_CURSORS[handle])
            elif index >= 0:
                self.setCursor(QtCore.Qt.SizeAllCursor)
            else:
                self.unsetCursor()
            return
        offset = event.pos() - self._drag['start']
        delta = QtCore.QPoint(round(offset.x() / self.scale), round(offset.y() / self.scale))
        index = self._drag['index']
        if self._drag['handle'] not in (None, MOVE):
            self.rects[index] = resize_rect(self._drag['rect'], self._drag['handle'], delta, self.screen_rect)
        else:
            self.rects[index] = move_rect(self._drag['rect'], delta, self.screen_rect)
        self.update()
        self.clip_changed.emit(index)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag = None


class VideoTriggerForm(QtWidgets.QDialog, RegistryProperties):
    """
    Place up to ten video clips on a presentation slide
    """
    def __init__(self, parent=None, screen_size=None):
        super().__init__(parent, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint |
                         QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMaximizeButtonHint)
        self.setObjectName('VideoTriggerForm')
        self.clips = []
        self._loading = False
        self.setup_ui(screen_size or QtCore.QSize(1920, 1080))

    def setup_ui(self, screen_size):
        self.setWindowTitle(translate('OpenLP.VideoTriggers', 'Video Trigger Manager'))
        layout = QtWidgets.QVBoxLayout(self)
        self.title_label = QtWidgets.QLabel(self)
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        self.canvas = TriggerCanvas(splitter, screen_size)
        self.canvas.clip_selected.connect(self.on_canvas_clip_selected)
        splitter.addWidget(self.canvas)
        panel = QtWidgets.QWidget(splitter)
        panel_layout = QtWidgets.QVBoxLayout(panel)
        panel_layout.setContentsMargins(6, 0, 0, 0)
        self.count_label = QtWidgets.QLabel(panel)
        panel_layout.addWidget(self.count_label)
        self.clip_list = QtWidgets.QListWidget(panel)
        self.clip_list.currentRowChanged.connect(self.on_list_row_changed)
        panel_layout.addWidget(self.clip_list)
        buttons = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton(translate('OpenLP.VideoTriggers', '&Add video...'), panel)
        self.add_button.clicked.connect(self.on_add_clicked)
        buttons.addWidget(self.add_button)
        self.remove_button = QtWidgets.QPushButton(translate('OpenLP.VideoTriggers', '&Remove'), panel)
        self.remove_button.clicked.connect(self.on_remove_clicked)
        buttons.addWidget(self.remove_button)
        panel_layout.addLayout(buttons)
        self.clip_group = QtWidgets.QGroupBox(translate('OpenLP.VideoTriggers', 'Selected clip'), panel)
        form = QtWidgets.QFormLayout(self.clip_group)
        self.description_edit = QtWidgets.QLineEdit(self.clip_group)
        self.description_edit.setMaxLength(DESCRIPTION_LENGTH)
        self.description_edit.textEdited.connect(self.on_description_edited)
        form.addRow(translate('OpenLP.VideoTriggers', 'Description:'), self.description_edit)
        self.file_label = QtWidgets.QLabel(self.clip_group)
        self.file_label.setWordWrap(True)
        form.addRow(translate('OpenLP.VideoTriggers', 'Video:'), self.file_label)
        self.change_button = QtWidgets.QPushButton(translate('OpenLP.VideoTriggers', '&Change video...'),
                                                   self.clip_group)
        self.change_button.clicked.connect(self.on_change_clicked)
        form.addRow('', self.change_button)
        self.autoplay_check = QtWidgets.QCheckBox(translate('OpenLP.VideoTriggers',
                                                            'Play as soon as the slide is shown'), self.clip_group)
        self.autoplay_check.toggled.connect(self.on_autoplay_toggled)
        form.addRow('', self.autoplay_check)
        panel_layout.addWidget(self.clip_group)
        self.help_label = QtWidgets.QLabel(translate(
            'OpenLP.VideoTriggers', 'Drag a box on the slide to move it, or its handles to size it. In the Live '
            'panel, click a box to play its clip, or press Ctrl and its number (Ctrl+0 for clip 10). Only you see '
            'the boxes, not the audience.'), panel)
        self.help_label.setWordWrap(True)
        panel_layout.addWidget(self.help_label)
        panel_layout.addStretch()
        splitter.addWidget(panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save |
                                                     QtWidgets.QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.resize(1100, 620)

    def exec(self, clips, picture_path=None, title=''):
        """
        :param list clips: The slide's clips. They are copied, so they are only changed if the operator saves.
        :param Path | None picture_path: A picture of the slide
        :param str title: The slide's name
        :return: True if saved. The clips are then in self.clips.
        """
        self.clips = [copy.copy(clip) for clip in clips]
        self.title_label.setText(title)
        picture = QtGui.QPixmap(str(picture_path)) if picture_path else None
        self.canvas.set_picture(picture)
        self.refresh(0 if self.clips else -1)
        self._fit_on_screen()
        return super().exec()

    def _fit_on_screen(self):
        screen = self.screen() if hasattr(self, 'screen') else None
        if screen:
            available = screen.availableGeometry()
            self.resize(min(self.width(), available.width() - 40), min(self.height(), available.height() - 60))

    def refresh(self, selected):
        """
        Show the clips in the list and on the slide, with one selected
        """
        self._loading = True
        self.clip_list.clear()
        for index, clip in enumerate(self.clips):
            item = QtWidgets.QListWidgetItem('{number}. {text}'.format(number=index + 1, text=clip['description']))
            item.setForeground(clip_colour(index))
            item.setToolTip(clip['name'])
            self.clip_list.addItem(item)
        self.canvas.set_clips(self.clips, selected)
        self.clip_list.setCurrentRow(selected)
        self._loading = False
        self.count_label.setText(translate('OpenLP.VideoTriggers', 'Clips ({count} of {most}):').format(
            count=len(self.clips), most=MAX_SLIDE_CLIPS))
        self.add_button.setEnabled(len(self.clips) < MAX_SLIDE_CLIPS)
        self.show_clip_fields(selected)

    def show_clip_fields(self, index):
        has_clip = 0 <= index < len(self.clips)
        self.clip_group.setEnabled(has_clip)
        self.remove_button.setEnabled(has_clip)
        self._loading = True
        if has_clip:
            clip = self.clips[index]
            self.description_edit.setText(clip['description'])
            self.file_label.setText(clip['name'] if clip['path'].exists() else
                                    translate('OpenLP.VideoTriggers', '{name} (missing)').format(name=clip['name']))
            self.file_label.setToolTip(str(clip['path']))
            self.autoplay_check.setChecked(clip['autoplay'])
        else:
            self.description_edit.clear()
            self.file_label.clear()
            self.autoplay_check.setChecked(False)
        self._loading = False

    def current_index(self):
        return self.canvas.selected if 0 <= self.canvas.selected < len(self.clips) else -1

    def on_canvas_clip_selected(self, index):
        self._loading = True
        self.clip_list.setCurrentRow(index)
        self._loading = False
        self.show_clip_fields(index)

    def on_list_row_changed(self, row):
        if self._loading:
            return
        self.canvas.selected = row
        self.canvas.update()
        self.show_clip_fields(row)

    def on_description_edited(self, text):
        index = self.current_index()
        if index < 0:
            return
        self.clips[index]['description'] = text
        self.canvas.descriptions[index] = text
        self.clip_list.item(index).setText('{number}. {text}'.format(number=index + 1, text=text))
        self.canvas.update()

    def on_autoplay_toggled(self, checked):
        index = self.current_index()
        if self._loading or index < 0:
            return
        # Only one clip per slide can play by itself
        for other, clip in enumerate(self.clips):
            clip['autoplay'] = checked and other == index

    def choose_video(self):
        """
        :return: The chosen video file, or None
        """
        file_filter = '{videos} ({extensions});;{all} (*)'.format(
            videos=translate('OpenLP', 'Video Files'), extensions=' '.join(VIDEO_EXT), all=UiStrings().AllFiles)
        file_path, _ = FileDialog.getOpenFileName(self, translate('OpenLP.VideoTriggers', 'Choose a video'),
                                                  self.settings.value('servicemanager/last video directory'),
                                                  file_filter)
        if not file_path:
            return None
        self.settings.setValue('servicemanager/last video directory', file_path.parent)
        return Path(file_path)

    def on_add_clicked(self):
        if len(self.clips) >= MAX_SLIDE_CLIPS:
            return
        file_path = self.choose_video()
        if not file_path:
            return
        self.store_rects()
        self.clips.append(make_slide_clip(file_path, rect=new_clip_rect(len(self.clips))))
        self.refresh(len(self.clips) - 1)
        self.description_edit.setFocus()
        self.description_edit.selectAll()

    def on_change_clicked(self):
        index = self.current_index()
        if index < 0:
            return
        file_path = self.choose_video()
        if not file_path:
            return
        clip = self.clips[index]
        # Keep a description the operator typed, but follow the file name if it was left as the old one
        description = clip['description']
        if description == Path(clip['name']).stem[:DESCRIPTION_LENGTH]:
            description = None
        self.store_rects()
        self.clips[index] = make_slide_clip(file_path, description=description, rect=clip['rect'],
                                            autoplay=clip['autoplay'])
        self.refresh(index)

    def on_remove_clicked(self):
        index = self.current_index()
        if index < 0:
            return
        self.store_rects()
        del self.clips[index]
        self.refresh(min(index, len(self.clips) - 1))

    def store_rects(self):
        """
        Copy the boxes, as the operator dragged them, into the clips
        """
        for clip, rect in zip(self.clips, self.canvas.rects):
            clip['rect'] = rect_to_fraction(rect, self.canvas.screen_size)

    def accept(self):
        self.store_rects()
        for clip in self.clips:
            if not clip['description'].strip():
                clip['description'] = Path(clip['name']).stem[:DESCRIPTION_LENGTH]
        super().accept()


class LiveClipView(QtWidgets.QWidget):
    """
    Sits over the Live panel's picture of a slide that has video clips. It draws the slide, as captured from the
    display screen, with the clips' boxes on it. The mouse becomes a pointing hand over a box, and a click plays the
    clip, or stops it if it is playing.

    It is a native window and paints every pixel itself, so it stays above the preview display's web view.
    """
    clip_clicked = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_NativeWindow)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
        self.setMouseTracking(True)
        self.picture = None
        self.clips = []
        self.hot = -1
        self.playing = -1

    def set_clips(self, clips):
        self.clips = list(clips)
        self.hot = -1
        self.playing = -1
        self.update()

    def set_picture(self, picture):
        """
        :param QtGui.QPixmap | QtGui.QImage | None picture: The display screen
        """
        if isinstance(picture, QtGui.QImage):
            picture = QtGui.QPixmap.fromImage(picture)
        self.picture = picture
        self.update()

    def set_playing(self, index):
        self.playing = index
        self.update()

    def box_rect(self, index):
        x, y, width, height = self.clips[index]['rect']
        return QtCore.QRectF(x * self.width(), y * self.height(), width * self.width(), height * self.height())

    def clip_at(self, pos):
        """
        :return: The clip whose box is under the mouse, the last added on top, or -1
        """
        point = QtCore.QPointF(pos)
        for index in reversed(range(len(self.clips))):
            if self.box_rect(index).contains(point):
                return index
        return -1

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtCore.Qt.black)
        if self.picture and not self.picture.isNull():
            painter.drawPixmap(QtCore.QRectF(self.rect()), self.picture, QtCore.QRectF(self.picture.rect()))
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        for index, clip in enumerate(self.clips):
            paint_clip_box(painter, self.box_rect(index), index + 1, clip['description'], clip_colour(index),
                           hot=index == self.hot, playing=index == self.playing)

    def mouseMoveEvent(self, event):
        index = self.clip_at(event.pos())
        if index != self.hot:
            self.hot = index
            if index >= 0:
                self.setCursor(QtCore.Qt.PointingHandCursor)
                self.setToolTip(translate('OpenLP.VideoTriggers', 'Click to play {name}').format(
                    name=self.clips[index]['name']))
            else:
                self.unsetCursor()
                self.setToolTip('')
            self.update()

    def leaveEvent(self, event):
        self.hot = -1
        self.unsetCursor()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            index = self.clip_at(event.pos())
            if index >= 0:
                self.clip_clicked.emit(index)
