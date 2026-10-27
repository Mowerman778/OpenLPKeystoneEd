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
The splash screen
"""

from PyQt5 import QtCore, QtGui, QtWidgets

SPLASH_SIZE = 370


class SplashScreen(QtWidgets.QSplashScreen):
    """
    The splash screen
    """
    def __init__(self):
        """
        Constructor
        """
        super(SplashScreen, self).__init__()
        self.setup_ui()

    def setup_ui(self):
        """
        Set up the UI
        """
        self.setObjectName('splashScreen')
        self.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        # The image is a high resolution (3x) asset: scale it to SPLASH_SIZE logical pixels for this screen's pixel
        # ratio, otherwise a normal (1x) screen shows only its top-left corner.
        pixel_ratio = self.devicePixelRatioF()
        splash_image = QtGui.QPixmap(':/graphics/openlp-splash-screen.png').scaled(
            round(SPLASH_SIZE * pixel_ratio), round(SPLASH_SIZE * pixel_ratio),
            QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        splash_image.setDevicePixelRatio(pixel_ratio)
        self.setPixmap(splash_image)
        self.resize(SPLASH_SIZE, SPLASH_SIZE)
        self.centre_on_screen()

    def centre_on_screen(self):
        """
        Centre the splash screen on the primary screen
        """
        screen = QtWidgets.QApplication.primaryScreen()
        if screen:
            frame = self.frameGeometry()
            frame.moveCenter(screen.availableGeometry().center())
            self.move(frame.topLeft())
