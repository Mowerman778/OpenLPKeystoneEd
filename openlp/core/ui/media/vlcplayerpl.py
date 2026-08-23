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
The :mod:`~openlp.core.ui.media.vlcplayer` module contains our VLC component wrapper
"""
import logging
import os
import threading
from datetime import datetime
from time import sleep

from PyQt5 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.mixins import LogMixin
from openlp.core.common.registry import Registry
from openlp.core.display.window import DisplayWindow
from openlp.core.lib.ui import critical_error_message_box
from openlp.core.ui.slidecontroller import SlideController
from openlp.core.ui.media import MediaState, VlCState, get_volume
from openlp.core.ui.media.mediaplayer import MediaPlayer
from openlp.core.ui.media.vlcplayer import get_vlc

log = logging.getLogger(__name__)


STATE_WAIT_TIME = 60


def end_reached(event, controller: SlideController) -> None:
    """
    Process the end of a Track, triggered by VLC
    :param event: the vlc event triggered
    :param controller: The controller upon which the event occurs
    :return: None
    """
    if controller.is_live:
        Registry().get('media_controller').vlc_live_media_stop.emit()
    else:
        Registry().get('media_controller').vlc_preview_media_stop.emit()


def pos_callback(event, controller: SlideController) -> None:
    """
    A Tick event triggered by VLC
    :param event: The VLC Event triggered
    :param controller: The controller upon which the event occurs
    :return: None
    """
    controller.media_info.timer = controller.vlc_media_player.get_time()
    if controller.is_live:
        Registry().get('media_controller').vlc_live_media_tick.emit()
    else:
        Registry().get('media_controller').vlc_preview_media_tick.emit()


class VlcPlayerPL(MediaPlayer, LogMixin):
    """
    A specialised version of the MediaPlayer class, which provides a VLC display with a Playlist.
    """
    def __init__(self, parent):
        """
        Constructor
        """
        super(VlcPlayerPL, self).__init__(parent, 'vlc')
        self.original_name = 'VLC'
        self.display_name = '&VLC'
        self.parent = parent
        self.can_folder = True
        self.can_repeat = True
        self.can_background = True

    def setup(self, controller: SlideController, display: DisplayWindow) -> None:
        """
        Set up the media player

        :param controller: The controller where the media is
        :param display: The display where the media is.
        :return:
        """
        vlc = get_vlc()
        if controller.is_live:
            controller.vlc_widget = QtWidgets.QFrame(controller)
            controller.vlc_widget.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowType.Tool |
                                                 QtCore.Qt.WindowStaysOnTopHint)
        else:
            controller.vlc_widget = QtWidgets.QFrame(display)
        controller.vlc_widget.setFrameStyle(QtWidgets.QFrame.NoFrame)
        # creating a basic vlc instance
        command_line_options = '--no-video-title-show '
        if self.settings.value('advanced/hide mouse') and controller.is_live:
            command_line_options += '--mouse-hide-timeout=0 '
        if self.settings.value('media/vlc arguments'):
            options = command_line_options + ' ' + self.settings.value('media/vlc arguments')
            controller.vlc_instance = vlc.Instance(options)
            # if the instance is None, it is likely that the comamndline options were invalid, so try again without
            if not controller.vlc_instance:
                controller.vlc_instance = vlc.Instance(command_line_options)
                if controller.vlc_instance:
                    critical_error_message_box(message=translate('MediaPlugin.VlcPlayer',
                                                                 'The VLC arguments are invalid.'))
                else:
                    return
        else:
            controller.vlc_instance = vlc.Instance(command_line_options)
            if not controller.vlc_instance:
                return
        self.log_debug(f"VLC version: {vlc.libvlc_get_version()}")
        # creating an empty vlc media player
        self.has_own_widget = True

    def check_available(self):
        """
        Return the availability of VLC
        """
        return get_vlc() is not None

    def load(self, controller: SlideController, output_display: DisplayWindow, file: str) -> bool:
        """
        Load a video into VLC

        :param controller: The controller where the media is
        :param output_display: The display where the media is
        :param file: file/stream to be played
        :return:  Success or Failure
        """
        self.log_debug('load video in VLC Controller')
        if not controller.vlc_instance:
            return False
        # The media player moved here to clear the playlist between uses.
        controller.vlc_media_player = controller.vlc_instance.media_player_new()
        controller.vlc_widget.resize(controller.size())
        controller.vlc_widget.hide()
        self.add_display(controller)
        path = os.path.normcase(file)
        controller.vlc_media = controller.vlc_instance.media_list_new()
        controller.vlc_media.add_media(path)
        controller.vlc_media_listPlayer = controller.vlc_instance.media_list_player_new()
        controller.vlc_media_listPlayer.set_media_player(controller.vlc_media_player)
        controller.vlc_media_listPlayer.set_media_list(controller.vlc_media)
        controller.vlc_events = controller.vlc_media_player.event_manager()
        vlc = get_vlc()
        controller.vlc_events.event_attach(vlc.EventType.MediaPlayerTimeChanged, pos_callback, controller)
        controller.vlc_events.event_attach(vlc.EventType.MediaPlayerEndReached, end_reached, controller)
        controller.media_info.start_time = 0
        controller.media_info.end_time = controller.media_info.length
        # parse the metadata of the file
        controller.mediabar.seek_slider.setMinimum(controller.media_info.start_time)
        controller.mediabar.seek_slider.setMaximum(controller.media_info.end_time)
        self.volume(controller, get_volume(controller))
        return True

    def media_state_wait(self, controller: SlideController, media_state: VlCState) -> bool:
        """
        Wait for the video to change its state
        Wait no longer than 60 seconds. (loading an iso file needs a long time)

        :param media_state: The state of the playing media
        :param controller: The controller where the media is
        :return:
        """
        start = datetime.now()
        while media_state != controller.vlc_media_listPlayer.get_state():
            sleep(0.1)
            if controller.vlc_media_listPlayer.get_state() == VlCState.Error:
                return False
            self.application.process_events()
            if (datetime.now() - start).seconds > STATE_WAIT_TIME:
                return False
        return True

    def toggle_loop(self, controller, loop_required: bool) -> None:
        vlc = get_vlc()
        if loop_required:
            controller.vlc_media_listPlayer.set_playback_mode(vlc.PlaybackMode().loop)
        else:
            controller.vlc_media_listPlayer.set_playback_mode(vlc.PlaybackMode().default)

    def play(self, controller: SlideController, output_display: DisplayWindow) -> bool:
        """
        Play the current item

        :param controller: Which Controller is running the show.
        :param output_display: The display where the media is
        :return:
        """
        self.log_debug('vlc play, mediatype: ' + str(controller.media_info.media_type))
        threading.Thread(target=controller.vlc_media_listPlayer.play).start()
        if not self.media_state_wait(controller, VlCState.Playing):
            return False
        self.volume(controller, get_volume(controller))
        self.set_state(MediaState.Playing, controller)
        return True

    def pause(self, controller: SlideController) -> None:
        """
        Pause the current item

        :param controller: The controller which is managing the display
        :return:
        """
        if controller.vlc_media_listPlayer.get_state() != VlCState.Playing:
            return
        controller.vlc_media_listPlayer.pause()
        if self.media_state_wait(controller, VlCState.Paused):
            self.set_state(MediaState.Paused, controller)

    def stop(self, controller: SlideController) -> None:
        """
        Stop the current item

        :param controller: The controller where the media is
        :return:
        """
        threading.Thread(target=controller.vlc_media_listPlayer.stop).start()
        self.set_state(MediaState.Stopped, controller)
