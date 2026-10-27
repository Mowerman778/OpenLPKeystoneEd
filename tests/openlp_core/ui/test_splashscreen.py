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
Package to test the openlp.core.ui package.
"""
from PyQt5 import QtCore, QtWidgets

import openlp.core.resources  # noqa: F401  (registers the :/graphics images)
from openlp.core.ui.splashscreen import SplashScreen


def test_splashscreen(qapp):
    """
    Test that the SpashScreen is created correctly
    """
    # GIVEN: the SplashScreen class
    # WHEN: An object is created

    ss = SplashScreen()
    # THEN: Nothing should go wrong and the instance should have the correct values
    assert ss.objectName() == 'splashScreen', 'The ObjectName should have be ' \
        'splashScreen'
    assert ss.frameSize() == QtCore.QSize(370, 370), 'The frameSize should be (370, 370)'
    assert ss.contextMenuPolicy() == QtCore.Qt.PreventContextMenu, 'The ContextMenuPolicy ' \
        'should have been QtCore.Qt.PreventContextMenu or 4'


def test_splashscreen_whole_image_fits(qapp):
    """
    Test that the high resolution splash image is scaled so the whole logo fits the window, not just a corner
    """
    # GIVEN / WHEN: A splash screen is created
    ss = SplashScreen()

    # THEN: The image's logical size should match the window
    pixmap = ss.pixmap()
    logical_size = pixmap.size() / pixmap.devicePixelRatioF()
    assert abs(logical_size.width() - 370) <= 1
    assert abs(logical_size.height() - 370) <= 1


def test_splashscreen_centred(qapp):
    """
    Test that the splash screen is centred on the primary screen
    """
    # GIVEN / WHEN: A splash screen is created
    ss = SplashScreen()

    # THEN: Its centre should be the centre of the primary screen
    screen_centre = QtWidgets.QApplication.primaryScreen().availableGeometry().center()
    assert (ss.frameGeometry().center() - screen_centre).manhattanLength() <= 2
