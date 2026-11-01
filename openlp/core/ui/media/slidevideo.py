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
Plays the video clips attached to a presentation slide, full screen on top of the running presentation.

LibreOffice crashes or garbles video in slide shows on Windows, so the videos are left out of the presentation and
attached to the slide in OpenLP instead, with the Video Trigger Manager. The presentation keeps running underneath, so
when a clip ends or is stopped the window is hidden and the slide is on screen again.

The operator plays a clip by clicking its box in the Live panel, or one clip per slide plays as soon as the slide is
shown.
"""
import logging
import threading

from PyQt5 import QtCore, QtWidgets

from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.platform import is_macosx, is_win
from openlp.core.display.screens import ScreenList


log = logging.getLogger(__name__)


class SlideVideoPlayer(QtCore.QObject, LogMixin, RegistryProperties):
    """
    A frameless, stay-on-top window covering the display screen, with its own VLC player
    """
    # VLC reports the end of the video on its own thread, so it is passed to the Qt thread through this signal
    ended = QtCore.pyqtSignal()
    # The clip now playing, or None when stopped
    playing_changed = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.window = None
        self.vlc_instance = None
        self.vlc_player = None
        self.current_path = None
        self.slide_paths = []
        self.ended.connect(self.on_ended)

    def show_slide(self, clip_paths, autoplay_path=None):
        """
        A slide with video clips is being shown: play its autoplay clip, if it has one. A clip of another slide that is
        still playing is stopped.

        :param list[Path] clip_paths: The slide's clips
        :param Path | None autoplay_path: The clip to play straight away
        """
        self.slide_paths = list(clip_paths)
        if autoplay_path:
            self.play(autoplay_path)
        elif self.current_path not in self.slide_paths:
            self.stop()

    def clear_slide(self):
        """
        The slide being shown has no clips, or the screen is hidden: stop any clip.
        """
        self.slide_paths = []
        self.stop()

    def _setup(self):
        """
        Create the window and VLC player the first time a video is played.

        :return: True if VLC is available
        """
        if self.vlc_player:
            return True
        # Imported here, the VLC player module imports the slide controller which uses this one
        from openlp.core.ui.media.vlcplayer import get_vlc
        vlc = get_vlc()
        if not vlc:
            log.warning('VLC is not available, slide videos cannot be played')
            return False
        options = '--no-video-title-show '
        if self.settings.value('advanced/hide mouse'):
            options += '--mouse-hide-timeout=0 '
        extra_options = self.settings.value('media/vlc arguments')
        self.vlc_instance = (extra_options and vlc.Instance(options + extra_options)) or vlc.Instance(options)
        if not self.vlc_instance:
            log.warning('VLC could not be started, slide videos cannot be played')
            return False
        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached,
                                                     lambda event: self.ended.emit())
        # The same kind of window OpenLP uses for live video
        self.window = QtWidgets.QFrame(self.parent_widget)
        self.window.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowType.Tool |
                                   QtCore.Qt.WindowStaysOnTopHint)
        self.window.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.window.setStyleSheet('background-color: black;')
        win_id = int(self.window.winId())
        if is_win():
            self.vlc_player.set_hwnd(win_id)
        elif is_macosx():
            self.vlc_player.set_nsobject(win_id)
        else:
            self.vlc_player.set_xwindow(win_id)
        return True

    def is_playing(self):
        """
        :return: True while a slide video is on screen
        """
        return self.current_path is not None

    def play(self, file_path):
        """
        Show the window over the display screen and play the video. Does nothing if it is already playing.

        :param Path file_path: The video to play
        """
        if self.current_path == file_path:
            return
        if not file_path.exists():
            log.warning('Slide video {path} is missing'.format(path=file_path))
            self.stop()
            return
        if not self._setup():
            return
        self.log_debug('Playing slide video {path}'.format(path=file_path))
        self.current_path = file_path
        self.vlc_player.set_media(self.vlc_instance.media_new_path(str(file_path)))
        self.vlc_player.audio_set_volume(self.settings.value('media/live volume'))
        self.window.setGeometry(ScreenList().current.display_geometry)
        self.window.show()
        self.window.raise_()
        self.playing_changed.emit(file_path)
        # VLC can block if started or stopped on the Qt thread, which is why OpenLP's VLC player uses threads too
        threading.Thread(target=self.vlc_player.play).start()

    def stop(self):
        """
        Stop the video, if one is playing, and hide the window so the presentation shows again
        """
        if self.current_path is not None:
            self.log_debug('Stopping slide video')
            self.current_path = None
            threading.Thread(target=self.vlc_player.stop).start()
            self.window.hide()
            self.playing_changed.emit(None)

    def on_ended(self):
        """
        The video has played to the end: hide the window so the slide is back on screen, and wait for the operator.
        """
        self.stop()
