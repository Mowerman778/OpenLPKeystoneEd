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
The :mod:`~openlp.core.ui.media.mediaplayer` module contains the MediaPlayer class.
"""
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.platform import is_macosx, is_win
from openlp.core.display.screens import ScreenList
from openlp.core.display.window import DisplayWindow
from openlp.core.ui.media import MediaState
from openlp.core.ui.slidecontroller import SlideController


class MediaPlayer(RegistryProperties):
    """
    This is the base class media Player class to provide OpenLP with a pluggable media display framework.
    """

    def __init__(self, parent, name='media_player'):
        """
        Constructor
        """
        self.parent = parent
        self.name = name
        self.available = self.check_available()
        self.can_background = False
        self.can_folder = False
        self.state = {0: MediaState.Off, 1: MediaState.Off}
        self.has_own_widget = False
        self.can_repeat = False

    def check_available(self):
        """
        Player is available on this machine
        """
        return False

    def setup(self, controller, display):
        """
        Create the related widgets for the current display

        :param controller: Which Controller is running the show.
        :param display: The display to be updated.
        """
        pass

    def load(self, controller, display, file):
        """
        Load a new media file and check if it is valid
        :param controller: Which Controller is running the show.
        :param display: The display to be updated.
        :param file: The file to be loaded
        """
        return True

    def add_display(self, controller: SlideController):
        # The media player has to be 'connected' to the QFrame.
        # (otherwise a video would be displayed in it's own window)
        # This is platform specific!
        # You have to give the id of the QFrame (or similar object)
        # to vlc, different platforms have different functions for this.
        win_id = int(controller.vlc_widget.winId())
        if is_win():
            controller.vlc_media_player.set_hwnd(win_id)
        elif is_macosx():
            # We have to use 'set_nsobject' since Qt5 on OSX uses Cocoa
            # framework and not the old Carbon.
            controller.vlc_media_player.set_nsobject(win_id)
        else:
            # for Linux/*BSD using the X Server
            controller.vlc_media_player.set_xwindow(win_id)
        self.has_own_widget = True

    def resize(self, controller: SlideController) -> None:
        """
        Resize the player

        :param controller: The display where the media is stored within the controller.
        :return:
        """
        if controller.is_live:
            controller.vlc_widget.setGeometry(ScreenList().current.display_geometry)
        else:
            controller.vlc_widget.resize(controller.preview_display.size())

    def play(self, controller, display):
        """
        Starts playing of current Media File, media player is expected to loop automatically

        :param controller: Which Controller is running the show.
        :param display: The display to be updated.
        """
        pass

    def pause(self, controller):
        """
        Pause of current Media File

        :param controller: Which Controller is running the show.
        """
        pass

    def stop(self, controller):
        """
        Stop playing of current Media File

        :param controller: Which Controller is running the show.
        """
        pass

    def volume(self, controller: SlideController, vol: int) -> None:
        """
        Set the volume

        :param vol: The volume to be sets
        :param controller: The controller where the media is
        :return:
        """
        controller.vlc_media_player.audio_set_volume(vol)

    def seek(self, controller: SlideController, seek_value: int) -> None:
        """
        Go to a particular position

        :param seek_value: The position of where a seek goes to
        :param controller: The controller where the media is
        """
        if controller.vlc_media_player.is_seekable():
            controller.vlc_media_player.set_time(seek_value)

    def reset(self, controller: SlideController) -> None:
        """
        Reset the player

        :param controller: The controller where the media is
        """
        controller.vlc_media_player.stop()
        self.set_state(MediaState.Off, controller)

    def set_visible(self, controller: SlideController, status: bool) -> None:
        """
        Set the visibility

        :param controller: The controller where the media display is
        :param status: The visibility status
        """
        controller.vlc_widget.setVisible(status)

    def update_ui(self, controller: SlideController, output_display: DisplayWindow) -> None:
        """
        Update the UI

        :param controller: Which Controller is running the show.
        :param output_display: The display where the media is
        """
        if not controller.mediabar.seek_slider.isSliderDown():
            controller.mediabar.seek_slider.blockSignals(True)
            controller.mediabar.seek_slider.setSliderPosition(controller.vlc_media_player.get_time())
            controller.mediabar.seek_slider.blockSignals(False)

    def toggle_loop(self, controller, loop_required: bool) -> None:
        """
        Changes the looping style
        :param controller: Which Controller is running the show.
        :param loop_required: Are we to be toggled or not
        :return: none
        """
        pass

    def get_live_state(self):
        """
        Get the state of the live player
        :return: Live state
        """
        return self.state[0]

    def set_live_state(self, state):
        """
        Set the State of the Live player
        :param state: State to be set
        :return: None
        """
        self.state[0] = state

    def get_preview_state(self):
        """
        Get the state of the preview player
        :return: Preview State
        """
        return self.state[1]

    def set_preview_state(self, state):
        """
        Set the state of the Preview Player
        :param state: State to be set
        :return: None
        """
        self.state[1] = state

    def set_state(self, state, controller):
        """
        Set the State based on the display being processed within the controller
        :param state: State to be set
        :param controller: Identify the Display type
        :return: None
        """
        if controller.is_live:
            self.set_live_state(state)
        else:
            self.set_preview_state(state)
