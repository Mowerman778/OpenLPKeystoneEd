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
Tests for the Theme Manager window
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt5 import QtCore, QtWidgets

from openlp.core.common.registry import Registry
from openlp.core.lib.theme import Theme
from openlp.core.ui.themedesigner import (FOOTER_AREA, MAIN_AREA, AreaOverlay, ThemeDesignerForm, move_rect,
                                          resize_rect, theme_area_rect)

SCREEN = QtCore.QRect(0, 0, 1920, 1080)


class FakePreview(QtWidgets.QWidget):
    """Stands in for the web engine slide preview"""
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.is_initialised = True
        self.set_scale = MagicMock()
        self.show_sample = MagicMock()
        self.save_screenshot = MagicMock(return_value='screenshot')


@pytest.fixture
def form(settings):
    renderer = MagicMock()
    renderer.width.return_value = 1920
    renderer.height.return_value = 1080
    Registry().register('renderer', renderer)
    Registry().register('theme_manager', MagicMock(theme_path=Path('themes')))
    with patch('openlp.core.ui.themedesigner.ThemePreviewRenderer', FakePreview), \
            patch('openlp.core.lib.theme.ScreenList') as screens:
        screens.return_value.current.render_size = QtCore.QSize(1920, 1080)
        designer = ThemeDesignerForm(None)
        yield designer
    designer.close()


def _theme(main_override=True, footer_override=True):
    theme = Theme()
    theme.theme_name = 'Test'
    theme.font_main_override = main_override
    theme.font_main_x, theme.font_main_y, theme.font_main_width, theme.font_main_height = 100, 50, 1700, 800
    theme.font_footer_override = footer_override
    theme.font_footer_x, theme.font_footer_y, theme.font_footer_width, theme.font_footer_height = 10, 950, 1900, 100
    return theme


def _open(form, theme, edit=True):
    with patch.object(QtWidgets.QDialog, 'exec', return_value=QtWidgets.QDialog.Rejected):
        form.exec(theme, edit=edit)


def test_move_rect_stays_on_screen():
    """
    Test a box dragged past the edge of the screen stops at the edge
    """
    rect = QtCore.QRect(100, 100, 400, 300)
    assert move_rect(rect, QtCore.QPoint(-500, 50), SCREEN) == QtCore.QRect(0, 150, 400, 300)
    assert move_rect(rect, QtCore.QPoint(5000, 5000), SCREEN) == QtCore.QRect(1520, 780, 400, 300)


def test_resize_rect_handles():
    """
    Test dragging handles changes the right edges, within the screen and not smaller than the minimum
    """
    rect = QtCore.QRect(100, 100, 400, 300)
    assert resize_rect(rect, 'bottom_right', QtCore.QPoint(50, 20), SCREEN) == QtCore.QRect(100, 100, 450, 320)
    assert resize_rect(rect, 'top_left', QtCore.QPoint(-200, -200), SCREEN) == QtCore.QRect(0, 0, 500, 400)
    assert resize_rect(rect, 'left', QtCore.QPoint(1000, 0), SCREEN).width() == 40
    assert resize_rect(rect, 'top', QtCore.QPoint(30, -10), SCREEN) == QtCore.QRect(100, 90, 400, 310)


@patch('openlp.core.lib.theme.ScreenList')
def test_theme_area_rect(mocked_screens):
    """
    Test the text areas are read from the theme
    """
    theme = _theme()
    assert theme_area_rect(theme, MAIN_AREA) == QtCore.QRect(100, 50, 1700, 800)
    assert theme_area_rect(theme, FOOTER_AREA) == QtCore.QRect(10, 950, 1900, 100)


def test_overlay_hit_test(qapp):
    """
    Test clicking finds the handle of the selected box, or the box under the mouse
    """
    overlay = AreaOverlay(None, QtCore.QSize(1920, 1080))
    overlay.resize(960, 540)  # half size
    overlay.areas = {MAIN_AREA: QtCore.QRect(100, 50, 1700, 800), FOOTER_AREA: QtCore.QRect(10, 950, 1900, 100)}
    overlay.selected = MAIN_AREA
    assert overlay.hit_test(QtCore.QPoint(50, 25)) == (MAIN_AREA, 'top_left')
    assert overlay.hit_test(QtCore.QPoint(400, 200)) == (MAIN_AREA, None)
    assert overlay.hit_test(QtCore.QPoint(400, 500)) == (FOOTER_AREA, None)
    assert overlay.hit_test(QtCore.QPoint(2, 2)) == (None, None)


def test_open_shows_main_area_position(form):
    """
    Test opening a theme shows the main text area's position in the fields
    """
    _open(form, _theme())
    assert form.canvas.overlay.areas[FOOTER_AREA] == QtCore.QRect(10, 950, 1900, 100)
    assert [form.position_spins[key].value() for key in ('x', 'y', 'width', 'height')] == [100, 50, 1700, 800]
    assert not form.default_position_check.isChecked()
    assert form.name_edit.isHidden()


def test_open_does_not_change_the_theme(form):
    """
    Test the window works on a copy, so cancelling leaves the theme as it was
    """
    theme = _theme()
    _open(form, theme)
    form.position_spins['x'].setValue(300)
    assert theme.font_main_x == 100


def test_typing_a_position_moves_the_box(form):
    """
    Test changing a field moves the box on the picture
    """
    _open(form, _theme(main_override=False))
    form.position_spins['y'].setValue(200)
    assert form.canvas.overlay.areas[MAIN_AREA].y() == 200
    assert form.overrides[MAIN_AREA] is True
    assert not form.default_position_check.isChecked()


def test_dragging_a_box_updates_the_fields(form):
    """
    Test dragging the selected box on the picture updates its fields
    """
    _open(form, _theme())
    form.canvas.overlay.areas[MAIN_AREA] = QtCore.QRect(200, 60, 1500, 700)
    form.canvas.overlay.area_changed.emit(MAIN_AREA)
    assert [form.position_spins[key].value() for key in ('x', 'y', 'width', 'height')] == [200, 60, 1500, 700]


def test_selecting_footer_shows_its_fields(form):
    """
    Test clicking the footer box shows the footer's position
    """
    _open(form, _theme())
    form.canvas.overlay.selected = FOOTER_AREA
    form.canvas.overlay.area_selected.emit(FOOTER_AREA)
    assert form.area_combo.currentIndex() == 1
    assert form.position_spins['y'].value() == 950


def test_default_position(form):
    """
    Test ticking "Use the default position" puts the box back where OpenLP would put it
    """
    _open(form, _theme())
    form.default_position_check.setChecked(True)
    assert form.overrides[MAIN_AREA] is False
    assert form.canvas.overlay.areas[MAIN_AREA] == QtCore.QRect(10, 0, 1900, 972)


def test_save_new_theme(form):
    """
    Test saving a new theme stores the areas and a preview picture
    """
    _open(form, _theme(), edit=False)
    form.name_edit.setText('Sunday')
    form.position_spins['x'].setValue(120)
    with patch.object(QtWidgets.QDialog, 'accept'):
        form.accept()
    saved = form.theme_manager.save_theme.call_args[0][0]
    assert saved.theme_name == 'Sunday'
    assert saved.font_main_x == 120 and saved.font_main_override is True
    form.theme_manager.save_preview.assert_called_once_with('Sunday', 'screenshot')


def test_save_needs_a_name(form):
    """
    Test a new theme isn't saved without a name
    """
    _open(form, _theme(), edit=False)
    with patch('openlp.core.ui.themedesigner.critical_error_message_box') as message:
        form.accept()
    message.assert_called_once()
    form.theme_manager.save_theme.assert_not_called()
