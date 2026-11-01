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
Tests for the Video Trigger Manager and the Live panel's clip boxes
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt5 import QtCore, QtGui, QtWidgets

from openlp.core.lib.serviceitem import MAX_SLIDE_CLIPS, make_slide_clip
from openlp.core.ui.themedesigner import MOVE
from openlp.core.ui.videotriggers import LiveClipView, TriggerCanvas, VideoTriggerForm, fraction_to_rect, \
    new_clip_rect, rect_to_fraction

SIZE = QtCore.QSize(1920, 1080)


def _mouse(kind, x, y, buttons=QtCore.Qt.LeftButton):
    button = QtCore.Qt.LeftButton if kind != QtCore.QEvent.MouseMove else QtCore.Qt.NoButton
    return QtGui.QMouseEvent(kind, QtCore.QPointF(x, y), button, buttons, QtCore.Qt.NoModifier)


@pytest.fixture
def form(settings):
    trigger_form = VideoTriggerForm(None, SIZE)
    yield trigger_form
    trigger_form.close()


def _open(form, clips):
    with patch.object(QtWidgets.QDialog, 'exec', return_value=QtWidgets.QDialog.Rejected):
        form.exec(clips, None, 'Deck - Slide 2')


def test_fraction_round_trip():
    """A box converts to pixels and back to the same fractions"""
    rect = fraction_to_rect((0.1, 0.2, 0.25, 0.5), SIZE)
    assert rect == QtCore.QRect(192, 216, 480, 540)
    assert rect_to_fraction(rect, SIZE) == (0.1, 0.2, 0.25, 0.5)


def test_new_clip_rects_do_not_overlap():
    """The first ten new boxes are all in different places, on screen"""
    rects = [fraction_to_rect(new_clip_rect(index), SIZE) for index in range(MAX_SLIDE_CLIPS)]
    for index, rect in enumerate(rects):
        assert QtCore.QRect(QtCore.QPoint(0, 0), SIZE).contains(rect)
        assert not any(rect.intersects(other) for other in rects[index + 1:])


def test_canvas_drag_move_square(qapp, tmp_path: Path):
    """Dragging the selected box's move square moves it without resizing it"""
    # GIVEN: A canvas the size of half the screen, with one box selected
    canvas = TriggerCanvas(None, SIZE)
    canvas.resize(980, 560)
    canvas.set_clips([make_slide_clip(tmp_path / 'a.mp4', rect=(0.25, 0.25, 0.5, 0.5))], selected=0)
    centre = canvas.to_view(canvas.rects[0]).center()
    assert canvas.hit_test(centre.toPoint()) == (0, MOVE)

    # WHEN: The move square is dragged 48 widget pixels right
    canvas.mousePressEvent(_mouse(QtCore.QEvent.MouseButtonPress, centre.x(), centre.y()))
    canvas.mouseMoveEvent(_mouse(QtCore.QEvent.MouseMove, centre.x() + 48, centre.y()))
    canvas.mouseReleaseEvent(_mouse(QtCore.QEvent.MouseButtonRelease, centre.x() + 48, centre.y(),
                                    QtCore.Qt.NoButton))

    # THEN: The box moved about 96 screen pixels, and is the same size
    assert abs(canvas.rects[0].x() - (480 + 96)) <= 2
    assert canvas.rects[0].size() == QtCore.QSize(960, 540)


def test_canvas_click_selects_other_box(qapp, tmp_path: Path):
    """Clicking another box selects it"""
    # GIVEN: A canvas with two boxes, the first selected
    canvas = TriggerCanvas(None, SIZE)
    canvas.resize(980, 560)
    canvas.set_clips([make_slide_clip(tmp_path / 'a.mp4', rect=(0.0, 0.0, 0.2, 0.2)),
                      make_slide_clip(tmp_path / 'b.mp4', rect=(0.6, 0.6, 0.2, 0.2))], selected=0)
    selected = []
    canvas.clip_selected.connect(selected.append)
    point = canvas.to_view(canvas.rects[1]).topLeft() + QtCore.QPointF(30, 30)

    # WHEN: The second box is clicked
    canvas.mousePressEvent(_mouse(QtCore.QEvent.MouseButtonPress, point.x(), point.y()))

    # THEN: It is selected
    assert canvas.selected == 1
    assert selected == [1]


@patch('openlp.core.ui.videotriggers.FileDialog.getOpenFileName')
def test_add_video(mocked_get_open_file_name, form, settings, tmp_path: Path):
    """Add video puts a new clip, named after the file, in its own box"""
    # GIVEN: A slide with one clip
    _open(form, [make_slide_clip(tmp_path / 'first.mp4')])
    mocked_get_open_file_name.return_value = (tmp_path / 'Second clip.mp4', '')

    # WHEN: Add video is clicked
    form.on_add_clicked()

    # THEN: There are two clips, the new one selected and described by its file name
    assert len(form.clips) == 2
    assert form.clips[1]['description'] == 'Second clip'
    assert form.clips[1]['rect'] == new_clip_rect(1)
    assert form.current_index() == 1
    assert form.description_edit.text() == 'Second clip'
    assert settings.value('servicemanager/last video directory') == tmp_path


@patch('openlp.core.ui.videotriggers.FileDialog.getOpenFileName')
def test_add_video_stops_at_ten(mocked_get_open_file_name, form, tmp_path: Path):
    """Add video is turned off once a slide has ten clips"""
    # GIVEN: A slide with ten clips
    _open(form, [make_slide_clip(tmp_path / '{n}.mp4'.format(n=n)) for n in range(MAX_SLIDE_CLIPS)])

    # WHEN: Add video is clicked anyway
    form.on_add_clicked()

    # THEN: Nothing is asked or added
    assert form.add_button.isEnabled() is False
    mocked_get_open_file_name.assert_not_called()
    assert len(form.clips) == MAX_SLIDE_CLIPS


def test_description_edit(form, tmp_path: Path):
    """Typing a description changes the clip, the list and the box"""
    # GIVEN: A slide with one clip
    _open(form, [make_slide_clip(tmp_path / 'clip.mp4')])

    # WHEN: A description is typed
    form.description_edit.setText('Testimony')
    form.description_edit.textEdited.emit('Testimony')

    # THEN: It is used everywhere
    assert form.clips[0]['description'] == 'Testimony'
    assert form.clip_list.item(0).text() == '1. Testimony'
    assert form.canvas.descriptions[0] == 'Testimony'


def test_only_one_autoplay(form, tmp_path: Path):
    """Ticking autoplay on one clip unticks it on the others"""
    # GIVEN: Two clips, the first playing automatically
    _open(form, [make_slide_clip(tmp_path / 'a.mp4', autoplay=True), make_slide_clip(tmp_path / 'b.mp4')])

    # WHEN: The second clip is selected and set to play automatically
    form.clip_list.setCurrentRow(1)
    form.autoplay_check.setChecked(True)

    # THEN: Only the second plays automatically
    assert [clip['autoplay'] for clip in form.clips] == [False, True]


def test_remove(form, tmp_path: Path):
    """Remove takes the selected clip away, and selects the next one"""
    # GIVEN: Three clips, the second selected
    _open(form, [make_slide_clip(tmp_path / '{n}.mp4'.format(n=n)) for n in range(3)])
    form.clip_list.setCurrentRow(1)

    # WHEN: Remove is clicked
    form.on_remove_clicked()

    # THEN: The second clip is gone
    assert [clip['name'] for clip in form.clips] == ['0.mp4', '2.mp4']
    assert form.current_index() == 1


def test_save_keeps_dragged_boxes_and_original_untouched(form, tmp_path: Path):
    """Saving stores the dragged boxes in the clips, and the slide's own clips are only changed by the caller"""
    # GIVEN: A slide with one clip
    original = make_slide_clip(tmp_path / 'clip.mp4', rect=(0.1, 0.1, 0.2, 0.2))
    _open(form, [original])

    # WHEN: Its box is dragged, its description cleared, and the form saved
    form.canvas.rects[0] = QtCore.QRect(960, 540, 480, 270)
    form.clips[0]['description'] = ' '
    with patch.object(QtWidgets.QDialog, 'accept'):
        form.accept()

    # THEN: The form's clip has the new box and the file name as description; the original is unchanged
    assert form.clips[0]['rect'] == (0.5, 0.5, 0.25, 0.25)
    assert form.clips[0]['description'] == 'clip'
    assert original['rect'] == (0.1, 0.1, 0.2, 0.2)


def test_live_view_click_and_cursor(qapp, tmp_path: Path):
    """In the Live panel the mouse becomes a pointing hand over a box, and a click reports the clip"""
    # GIVEN: The Live panel's box view with two clips
    view = LiveClipView(None)
    view.resize(400, 225)
    view.set_clips([make_slide_clip(tmp_path / 'a.mp4', rect=(0.0, 0.0, 0.5, 0.5)),
                    make_slide_clip(tmp_path / 'b.mp4', rect=(0.5, 0.5, 0.5, 0.5))])
    clicked = []
    view.clip_clicked.connect(clicked.append)

    # WHEN: The mouse moves over the second box and clicks, then moves off the boxes
    view.mouseMoveEvent(_mouse(QtCore.QEvent.MouseMove, 300, 170, QtCore.Qt.NoButton))
    hand = view.cursor().shape()
    view.mousePressEvent(_mouse(QtCore.QEvent.MouseButtonPress, 300, 170))
    view.mouseMoveEvent(_mouse(QtCore.QEvent.MouseMove, 300, 50, QtCore.Qt.NoButton))

    # THEN: The cursor was a pointing hand, the second clip was clicked, and the cursor is back to normal
    assert hand == QtCore.Qt.PointingHandCursor
    assert clicked == [1]
    assert view.hot == -1
    assert view.cursor().shape() == QtCore.Qt.ArrowCursor


def test_live_view_paints(qapp, tmp_path: Path):
    """The box view paints the slide and the boxes without errors, including a playing clip"""
    view = LiveClipView(None)
    view.resize(400, 225)
    picture = QtGui.QPixmap(1920, 1080)
    picture.fill(QtCore.Qt.darkBlue)
    view.set_picture(picture)
    view.set_clips([make_slide_clip(tmp_path / 'a.mp4', description='A long description that will be cut short')])
    view.set_playing(0)
    image = view.grab().toImage()
    assert image.pixelColor(200, 200) != QtGui.QColor(QtCore.Qt.black)
    view.close()


def test_live_view_ignores_clicks_outside_boxes(qapp, tmp_path: Path):
    """Clicking the slide outside the boxes does nothing"""
    view = LiveClipView(None)
    view.resize(400, 225)
    view.set_clips([make_slide_clip(tmp_path / 'a.mp4', rect=(0.0, 0.0, 0.2, 0.2))])
    view.clip_clicked = MagicMock()
    view.mousePressEvent(_mouse(QtCore.QEvent.MouseButtonPress, 300, 200))
    view.clip_clicked.emit.assert_not_called()
