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
This module contains tests for the openlp.core.widgets.buttons module
"""
import pytest
from unittest.mock import MagicMock, call, patch

from openlp.core.widgets.buttons import ColorButton


@pytest.fixture()
def buttons_env():
    change_color_patcher = patch('openlp.core.widgets.buttons.ColorButton.change_color')
    clicked_patcher = patch('openlp.core.widgets.buttons.ColorButton.clicked')
    color_changed_patcher = patch('openlp.core.widgets.buttons.ColorButton.colorChanged')
    qt_gui_patcher = patch('openlp.core.widgets.buttons.QtWidgets')
    translate_patcher = patch('openlp.core.widgets.buttons.translate', **{'return_value': 'Tool Tip Text'})
    mocked_change_color = change_color_patcher.start()
    mocked_clicked = clicked_patcher.start()
    mocked_color_changed = color_changed_patcher.start()
    mocked_qt_widgets = qt_gui_patcher.start()
    translate_patcher.start()
    yield mocked_clicked, mocked_color_changed, mocked_qt_widgets, mocked_change_color
    change_color_patcher.stop()
    clicked_patcher.stop()
    color_changed_patcher.stop()
    qt_gui_patcher.stop()
    translate_patcher.stop()


@patch('openlp.core.widgets.buttons.ColorButton.setToolTip')
def test_constructor(mocked_set_tool_tip, buttons_env):
    """
    Test that constructing a ColorButton object works correctly
    """

    # GIVEN: The ColorButton class, a mocked change_color, setToolTip methods and clicked signal
    # WHEN: The ColorButton object is instantiated
    mocked_clicked = buttons_env[0]
    mocked_change_color = buttons_env[3]
    widget = ColorButton()

    # THEN: The widget __init__ method should have the correct properties and methods called
    assert widget.parent is None, 'The parent should be the same as the one that the class was instianted with'
    mocked_change_color.assert_called_once_with('#ffffff')
    mocked_set_tool_tip.assert_called_once_with('Tool Tip Text')
    mocked_clicked.connect.assert_called_once_with(widget.on_clicked)


@patch('openlp.core.widgets.buttons.ColorButton.setStyleSheet')
def test_change_color(mocked_set_style_sheet):
    """
    Test that change_color sets the new color and the stylesheet
    """
    # GIVEN: An instance of the ColorButton object, and a mocked out setStyleSheet
    widget = ColorButton()

    # WHEN: Changing the color
    widget.change_color('#000000')

    # THEN: The _color attribute should be set to #000000 and setStyleSheet should have been called twice
    assert widget._color == '#000000', '_color should have been set to #000000'
    mocked_set_style_sheet.assert_has_calls(
        [call('background-color: #ffffff'), call('background-color: #000000')])


def test_color():
    """
    Test that the color property method returns the set color
    """
    # GIVEN: An instance of ColorButton, with a set _color attribute
    widget = ColorButton()
    widget._color = '#000000'

    # WHEN: Accesing the color property
    value = widget.color

    # THEN: The value set in _color should be returned
    assert value == '#000000', 'The value returned should be equal to the one we set'


def test_color_setter(buttons_env):
    """
    Test that the color property setter method sets the color
    """
    # GIVEN: An instance of ColorButton, with a mocked __init__
    mocked_change_color = buttons_env[3]
    widget = ColorButton()

    # WHEN: Setting the color property
    widget.color = '#000000'

    # THEN: Then change_color should have been called with the value we set
    mocked_change_color.assert_called_with('#000000')


def test_on_clicked_invalid_color(buttons_env):
    """
    Test the on_click method when an invalid color has been supplied
    """
    # GIVEN: An instance of ColorButton, and a set _color attribute
    mocked_color_changed = buttons_env[1]
    mocked_qt_widgets = buttons_env[2]
    mocked_change_color = buttons_env[3]
    widget = ColorButton()
    mocked_change_color.reset_mock()
    mocked_color_changed.reset_mock()
    widget._color = '#000000'

    # WHEN: The on_clicked method is called, and the color is invalid
    mocked_qt_widgets.QColorDialog.getColor.return_value = MagicMock(**{'isValid.return_value': False})
    widget.on_clicked()

    # THEN: change_color should not have been called and the colorChanged signal should not have been emitted
    assert mocked_change_color.called is False, \
        'change_color should not have been called with an invalid color'
    assert mocked_color_changed.emit.called is False, \
        'colorChange signal should not have been emitted with an invalid color'


def test_on_clicked_same_color(buttons_env):
    """
    Test the on_click method when a new color has not been chosen
    """
    # GIVEN: An instance of ColorButton, and a set _color attribute
    mocked_color_changed = buttons_env[1]
    mocked_qt_widgets = buttons_env[2]
    mocked_change_color = buttons_env[3]
    widget = ColorButton()
    mocked_change_color.reset_mock()
    mocked_color_changed.reset_mock()
    widget._color = '#000000'

    # WHEN: The on_clicked method is called, and the color is valid, but the same as the existing color
    mocked_qt_widgets.QColorDialog.getColor.return_value = MagicMock(
        **{'isValid.return_value': True, 'name.return_value': '#000000'})
    widget.on_clicked()

    # THEN: change_color should not have been called and the colorChanged signal should not have been emitted
    assert mocked_change_color.called is False, \
        'change_color should not have been called when the color has not changed'
    assert mocked_color_changed.emit.called is False, \
        'colorChange signal should not have been emitted when the color has not changed'


def test_on_clicked_new_color(buttons_env):
    """
    Test the on_click method when a new color has been chosen and is valid
    """
    # GIVEN: An instance of ColorButton, and a set _color attribute
    mocked_color_changed = buttons_env[1]
    mocked_qt_widgets = buttons_env[2]
    mocked_change_color = buttons_env[3]
    widget = ColorButton()
    mocked_change_color.reset_mock()
    mocked_color_changed.reset_mock()
    widget._color = '#000000'

    # WHEN: The on_clicked method is called, and the color is valid, and different to the existing color
    mocked_qt_widgets.QColorDialog.getColor.return_value = MagicMock(
        **{'isValid.return_value': True, 'name.return_value': '#ffffff'})
    widget.on_clicked()

    # THEN: change_color should have been called and the colorChanged signal should have been emitted
    mocked_change_color.assert_called_once_with('#ffffff')
    mocked_color_changed.emit.assert_called_once_with('#ffffff')
