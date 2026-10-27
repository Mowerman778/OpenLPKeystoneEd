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
Tests for Simulated Projector Mode
"""
from unittest.mock import MagicMock

import pytest
from PyQt5 import QtCore

from openlp.core.display import simulatedprojector
from openlp.core.display.screens import Screen, ScreenList


def _raw_screen(geometry, taskbar=40):
    raw_screen = MagicMock()
    available = QtCore.QRect(geometry)
    available.setHeight(geometry.height() - taskbar)
    raw_screen.availableGeometry.return_value = available
    return raw_screen


@pytest.fixture
def two_screens(settings):
    """A laptop (primary) and an external monitor, the external one showing the live output full screen"""
    laptop_geometry = QtCore.QRect(0, 0, 1366, 768)
    external_geometry = QtCore.QRect(-1280, 0, 1280, 720)
    screen_list = ScreenList()
    screen_list.screens = [
        Screen(number=0, geometry=external_geometry, is_display=True, raw_screen=_raw_screen(external_geometry)),
        Screen(number=1, geometry=laptop_geometry, is_primary=True, raw_screen=_raw_screen(laptop_geometry)),
    ]
    screen_list.save_screen_settings()
    yield screen_list
    del ScreenList._instances[ScreenList]


def test_turn_on_and_off(two_screens, settings):
    """
    Test turning the mode on puts a 16:9 HD-simulating box on the external monitor, and off restores the real setup
    """
    external, laptop = two_screens.screens

    # WHEN: Simulated Projector Mode is turned on
    simulatedprojector.turn_on()

    # THEN: The live output goes to a 480x270 box in the bottom-right of the external monitor, laid out at HD
    assert simulatedprojector.is_simulating()
    assert external.is_display and not laptop.is_display
    assert external.simulated_resolution == QtCore.QSize(1920, 1080)
    assert external.custom_geometry.size() == QtCore.QSize(480, 270)
    assert external.custom_geometry.right() == 1280 - 1 - simulatedprojector.MARGIN
    assert external.custom_geometry.bottom() == 720 - 40 - 1 - simulatedprojector.MARGIN
    assert settings.value('core/simulated projector') is True

    # WHEN: It is turned off again
    simulatedprojector.turn_off()

    # THEN: The external monitor is the full-screen display again
    assert not simulatedprojector.is_simulating()
    assert external.is_display and external.custom_geometry is None and external.simulated_resolution is None
    assert settings.value('core/simulated projector') is False


def test_turn_on_single_monitor(settings):
    """
    Test with only the laptop screen the simulated projector goes on the laptop screen
    """
    geometry = QtCore.QRect(0, 0, 1366, 768)
    screen_list = ScreenList()
    screen_list.screens = [Screen(number=0, geometry=geometry, is_primary=True, is_display=True,
                                  raw_screen=_raw_screen(geometry))]
    try:
        simulatedprojector.turn_on()
        assert screen_list.screens[0].is_display
        assert screen_list.screens[0].simulated_resolution == QtCore.QSize(1920, 1080)
    finally:
        del ScreenList._instances[ScreenList]


def test_turn_on_reuses_remembered_box(two_screens, settings):
    """
    Test the window goes back where the user last put it
    """
    external = two_screens.screens[0]
    simulatedprojector.turn_on()

    # GIVEN: The user moved and resized the window
    simulatedprojector.remember_box(external, QtCore.QRect(-1200, 100, 640, 360))
    simulatedprojector.turn_off()

    # WHEN: The mode is turned on again
    simulatedprojector.turn_on()

    # THEN: The box is where the user left it (relative to the external monitor)
    assert external.custom_geometry == QtCore.QRect(80, 100, 640, 360)


def test_turn_off_without_backup_finds_a_display(two_screens, settings):
    """
    Test turning off without a saved setup still leaves a display screen
    """
    simulatedprojector.turn_on()
    settings.setValue('core/screens before simulation', {})
    simulatedprojector.turn_off()
    assert any(screen.is_display for screen in two_screens.screens)
