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
Plays the video attached to a presentation slide, full screen on top of the running presentation.

LibreOffice crashes or garbles video in slide shows on Windows, so the video is left out of the presentation and
attached to the slide in OpenLP instead. The presentation keeps running underneath, so when the video ends or is
stopped the window is hidden and the slide is on screen again.

While the slide is showing and its video is not playing, a small film strip icon sits in the corner of the screen.
Clicking it plays the video, so the slide can be talked about before and after it.
"""
import logging
import threading

import qtawesome as qta
from PyQt5 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.platform import is_macosx, is_win
from openlp.core.display.screens import ScreenList


log = logging.getLogger(__name__)

TRIGGER_SIZE = 25
TRIGGER_MARGIN = 10
TRIGGER_OPACITY = 0.6


class SlideVideoTrigger(QtWidgets.QToolButton):
    """
    A small film strip button that floats over the presentation, in the bottom right corner of the display screen.
    It does not take the focus, so the presentation keeps its keyboard and clicker control.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowType.Tool |
                            QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip(translate('OpenLP.SlideVideo', 'Play the video'))
        self.setIcon(qta.icon('mdi.filmstrip', color='white'))
        self.setIconSize(QtCore.QSize(TRIGGER_SIZE - 6, TRIGGER_SIZE - 6))
        self.setFixedSize(TRIGGER_SIZE, TRIGGER_SIZE)
        self.setStyleSheet('QToolButton { background-color: black; border: 1px solid grey; border-radius: 3px; }')
        self.setWindowOpacity(TRIGGER_OPACITY)

    def show_on_screen(self):
        """
        Place the icon in the bottom right corner of the display screen and show it.
        """
        screen = ScreenList().current.display_geometry
        self.move(screen.right() - TRIGGER_MARGIN - TRIGGER_SIZE, screen.bottom() - TRIGGER_MARGIN - TRIGGER_SIZE)
        self.show()
        self.raise_()

    def enterEvent(self, event):
        self.setWindowOpacity(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setWindowOpacity(TRIGGER_OPACITY)
        super().leaveEvent(event)


class SlideVideoPlayer(QtCore.QObject, LogMixin, RegistryProperties):
    """
    A frameless, stay-on-top window covering the display screen, with its own VLC player, and the trigger icon that
    plays the video of the slide being shown
    """
    # VLC reports the end of the video on its own thread, so it is passed to the Qt thread through this signal
    ended = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.window = None
        self.vlc_instance = None
        self.vlc_player = None
        self.current_path = None
        self.slide_path = None
        self.trigger = None
        self.ended.connect(self.on_ended)

    def show_slide(self, file_path, autoplay):
        """
        A slide with a video is being shown: play the video now, or show the trigger icon to play it on a click.

        :param Path file_path: The slide's video
        :param bool autoplay: True to play the video straight away
        """
        self.slide_path = file_path
        if autoplay:
            self.play(file_path)
        else:
            # Stopping another slide's video also shows the trigger icon
            if self.current_path != file_path:
                self.stop()
            else:
                self._update_trigger()

    def clear_slide(self):
        """
        The slide being shown has no video, or the screen is hidden: stop any video and hide the trigger icon.
        """
        self.slide_path = None
        self.stop()

    def on_trigger_clicked(self):
        """
        The trigger icon was clicked: play the video of the slide being shown.
        """
        if self.slide_path:
            self.play(self.slide_path)

    def _update_trigger(self):
        """
        Show the trigger icon while the slide being shown has a video that is not playing.
        """
        if self.slide_path and not self.is_playing():
            if not self.trigger:
                self.trigger = SlideVideoTrigger(self.parent_widget)
                self.trigger.clicked.connect(self.on_trigger_clicked)
            self.trigger.show_on_screen()
        elif self.trigger:
            self.trigger.hide()

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
        self._update_trigger()
        # VLC can block if started or stopped on the Qt thread, which is why OpenLP's VLC player uses threads too
        threading.Thread(target=self.vlc_player.play).start()

    def stop(self):
        """
        Stop the video, if one is playing, and hide the window so the presentation shows again. The trigger icon comes
        back while the slide is still being shown, so the video can be played again.
        """
        if self.current_path is not None:
            self.log_debug('Stopping slide video')
            self.current_path = None
            threading.Thread(target=self.vlc_player.stop).start()
            self.window.hide()
        self._update_trigger()

    def on_ended(self):
        """
        The video has played to the end: hide the window so the slide is back on screen, and wait for the operator.
        """
        self.stop()
