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
The :mod:`~openlp.core.display.simulatedprojector` module holds Simulated Projector Mode: for when no projector is
connected, the live output goes to a small, movable "Simulated Projector" window. Slides are laid out exactly as on a
real HD (1920x1080) projector and shrunk to fit the window.
"""
from PyQt5 import QtCore

from openlp.core.common.registry import Registry
from openlp.core.display.screens import ScreenList

SIMULATED_RESOLUTION = QtCore.QSize(1920, 1080)
DEFAULT_WIDTH = 480
MARGIN = 20


def is_simulating():
    """
    Whether the live output is currently going to a simulated projector window
    """
    return any(screen.is_display and screen.simulated_resolution for screen in ScreenList())


def _settings():
    return Registry().get('settings')


def _target_screen(screens):
    """
    Where to put the simulated projector: the last non-primary monitor if there is one, otherwise the primary one
    """
    for screen in reversed(screens.screens):
        if not screen.is_primary:
            return screen
    return screens.screens[0]


def default_box(screen):
    """
    A 16:9 box in the bottom-right corner of the screen, clear of the taskbar. Relative to the screen.

    :param openlp.core.display.screens.Screen screen: The screen the box goes on
    :rtype: QtCore.QRect
    """
    available = screen.raw_screen.availableGeometry() if screen.raw_screen else screen.geometry
    width = min(DEFAULT_WIDTH, available.width() - 2 * MARGIN)
    height = width * 9 // 16
    right = available.right() - screen.geometry.left() - MARGIN
    bottom = available.bottom() - screen.geometry.top() - MARGIN
    return QtCore.QRect(right - width + 1, bottom - height + 1, width, height)


def turn_on():
    """
    Send the live output to a simulated projector window. The real screen setup is kept, to put back afterwards.
    """
    settings = _settings()
    screens = ScreenList()
    if not is_simulating():
        settings.setValue('core/screens before simulation', settings.value('core/screens'))
    target = _target_screen(screens)
    saved_box = settings.value('core/simulated projector geometry')
    box = default_box(target)
    if saved_box and saved_box.get('screen') == target.number:
        box = QtCore.QRect(saved_box['x'], saved_box['y'], saved_box['width'], saved_box['height'])
    for screen in screens:
        screen.is_display = screen is target
        screen.simulated_resolution = None
    target.custom_geometry = box
    target.simulated_resolution = QtCore.QSize(SIMULATED_RESOLUTION)
    screens.save_screen_settings()
    settings.setValue('core/simulated projector', True)


def turn_off():
    """
    Put the real screen setup back
    """
    settings = _settings()
    screens = ScreenList()
    saved_screens = settings.value('core/screens before simulation')
    for screen in screens:
        screen.is_display = False
        screen.custom_geometry = None
        screen.simulated_resolution = None
    if saved_screens:
        settings.setValue('core/screens', saved_screens)
        screens.load_screen_settings()
    else:
        screens.find_new_display_screen()
    if not any(screen.is_display for screen in screens):
        screens.find_new_display_screen()
    screens.save_screen_settings()
    settings.setValue('core/screens before simulation', {})
    settings.setValue('core/simulated projector', False)


def remember_box(screen, window_geometry):
    """
    The user moved or resized the simulated projector window: keep the new place, relative to its screen

    :param openlp.core.display.screens.Screen screen: The simulated display screen
    :param QtCore.QRect window_geometry: The window's new geometry (absolute)
    """
    box = QtCore.QRect(window_geometry)
    box.translate(-screen.geometry.x(), -screen.geometry.y())
    screen.custom_geometry = box
    ScreenList().save_screen_settings()
    _settings().setValue('core/simulated projector geometry', {
        'screen': screen.number, 'x': box.x(), 'y': box.y(), 'width': box.width(), 'height': box.height()})
