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
Tests for the player of videos attached to presentation slides
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from openlp.core.common.settings import Settings
from openlp.core.ui.media.slidevideo import SlideVideoPlayer


@pytest.fixture()
def mocked_vlc():
    """A mocked VLC module, with threads run straight away so the calls can be checked"""
    vlc = MagicMock()
    with patch('openlp.core.ui.media.vlcplayer.get_vlc', return_value=vlc), \
            patch('openlp.core.ui.media.slidevideo.threading.Thread') as mocked_thread, \
            patch('openlp.core.ui.media.slidevideo.ScreenList'), \
            patch('openlp.core.ui.media.slidevideo.QtWidgets.QFrame'):
        mocked_thread.side_effect = lambda target: MagicMock(start=target)
        yield vlc


def test_play(mocked_vlc: MagicMock, settings: Settings, tmp_path: Path):
    """play() shows the window and plays the video at the live volume"""
    # GIVEN: A video file and a player
    video_path = tmp_path / 'clip.mp4'
    video_path.write_bytes(b'video')
    settings.setValue('media/live volume', 80)
    player = SlideVideoPlayer()

    # WHEN: The video is played
    player.play(video_path)

    # THEN: VLC plays it in the window, which is shown
    vlc_player = mocked_vlc.Instance.return_value.media_player_new.return_value
    mocked_vlc.Instance.return_value.media_new_path.assert_called_once_with(str(video_path))
    vlc_player.audio_set_volume.assert_called_once_with(80)
    vlc_player.play.assert_called_once_with()
    player.window.show.assert_called_once_with()
    assert player.is_playing() is True


def test_play_same_video_again_does_nothing(mocked_vlc: MagicMock, settings: Settings, tmp_path: Path):
    """Being asked to play the video already playing does not restart it"""
    # GIVEN: A player playing a video
    video_path = tmp_path / 'clip.mp4'
    video_path.write_bytes(b'video')
    player = SlideVideoPlayer()
    player.play(video_path)

    # WHEN: The same video is played again
    player.play(video_path)

    # THEN: It was only started once
    mocked_vlc.Instance.return_value.media_player_new.return_value.play.assert_called_once_with()


def test_play_missing_video(mocked_vlc: MagicMock, settings: Settings, tmp_path: Path):
    """A missing video is not played, and the presentation stays on screen"""
    # GIVEN: A player
    player = SlideVideoPlayer()

    # WHEN: A missing video is played
    player.play(tmp_path / 'missing.mp4')

    # THEN: Nothing is played
    mocked_vlc.Instance.assert_not_called()
    assert player.is_playing() is False


def test_play_without_vlc(settings: Settings, tmp_path: Path):
    """Without VLC nothing is played"""
    # GIVEN: A video file, and VLC not installed
    video_path = tmp_path / 'clip.mp4'
    video_path.write_bytes(b'video')
    player = SlideVideoPlayer()

    # WHEN: The video is played
    with patch('openlp.core.ui.media.vlcplayer.get_vlc', return_value=None):
        player.play(video_path)

    # THEN: Nothing is playing
    assert player.is_playing() is False


def test_stop(mocked_vlc: MagicMock, settings: Settings, tmp_path: Path):
    """stop() stops the video and hides the window"""
    # GIVEN: A player playing a video
    video_path = tmp_path / 'clip.mp4'
    video_path.write_bytes(b'video')
    player = SlideVideoPlayer()
    player.play(video_path)

    # WHEN: It is stopped
    player.stop()

    # THEN: VLC is stopped and the window hidden
    mocked_vlc.Instance.return_value.media_player_new.return_value.stop.assert_called_once_with()
    player.window.hide.assert_called_once_with()
    assert player.is_playing() is False


def test_stop_when_not_playing(settings: Settings):
    """stop() does nothing when no video was ever played"""
    # GIVEN: A player that has not played anything
    player = SlideVideoPlayer()

    # WHEN: It is stopped
    player.stop()

    # THEN: Nothing was set up
    assert player.window is None


def test_video_end_hides_window(mocked_vlc: MagicMock, settings: Settings, tmp_path: Path):
    """When VLC reports the end of the video the window is hidden so the slide is back on screen"""
    # GIVEN: A player playing a video
    video_path = tmp_path / 'clip.mp4'
    video_path.write_bytes(b'video')
    player = SlideVideoPlayer()
    player.play(video_path)

    # WHEN: VLC reports the end of the video
    player.on_ended()

    # THEN: The window is hidden, and the video can be played again
    player.window.hide.assert_called_once_with()
    assert player.is_playing() is False


def test_show_slide_without_autoplay_plays_nothing(mocked_vlc: MagicMock, settings: Settings, tmp_path: Path):
    """A slide whose clips wait for a click plays nothing yet"""
    # GIVEN: A player
    video_path = tmp_path / 'clip.mp4'
    video_path.write_bytes(b'video')
    player = SlideVideoPlayer()

    # WHEN: A slide with a clip that waits for a click is shown
    player.show_slide([video_path])

    # THEN: Nothing plays
    assert player.is_playing() is False


def test_show_slide_autoplay_plays(mocked_vlc: MagicMock, settings: Settings, tmp_path: Path):
    """A slide with a clip that plays automatically plays it straight away"""
    # GIVEN: A player
    video_path = tmp_path / 'clip.mp4'
    video_path.write_bytes(b'video')
    player = SlideVideoPlayer()
    playing = []
    player.playing_changed.connect(playing.append)

    # WHEN: A slide whose clip plays automatically is shown
    player.show_slide([video_path], video_path)

    # THEN: The clip plays, and the change is reported
    assert player.current_path == video_path
    assert playing == [video_path]


def test_show_slide_keeps_own_clip_playing(mocked_vlc: MagicMock, settings: Settings, tmp_path: Path):
    """Showing the same slide again, such as after unblanking, does not stop its clip"""
    # GIVEN: A slide whose clip is playing
    video_path = tmp_path / 'clip.mp4'
    video_path.write_bytes(b'video')
    player = SlideVideoPlayer()
    player.show_slide([video_path])
    player.play(video_path)

    # WHEN: The slide is shown again
    player.show_slide([video_path])

    # THEN: The clip is still playing
    assert player.current_path == video_path


def test_show_slide_stops_other_slides_clip(mocked_vlc: MagicMock, settings: Settings, tmp_path: Path):
    """Moving to another slide with clips stops the clip of the slide before"""
    # GIVEN: A slide whose clip is playing
    first = tmp_path / 'first.mp4'
    first.write_bytes(b'video')
    second = tmp_path / 'second.mp4'
    second.write_bytes(b'video')
    player = SlideVideoPlayer()
    player.show_slide([first], first)
    playing = []
    player.playing_changed.connect(playing.append)

    # WHEN: Another slide, whose clip waits for a click, is shown
    player.show_slide([second])

    # THEN: The first clip was stopped
    assert player.is_playing() is False
    assert playing == [None]


def test_clear_slide_stops(mocked_vlc: MagicMock, settings: Settings, tmp_path: Path):
    """Moving to a slide without clips stops the clip"""
    # GIVEN: A slide whose clip is playing
    video_path = tmp_path / 'clip.mp4'
    video_path.write_bytes(b'video')
    player = SlideVideoPlayer()
    player.show_slide([video_path], video_path)

    # WHEN: A slide without clips is shown
    player.clear_slide()

    # THEN: Nothing plays
    assert player.is_playing() is False
    assert player.slide_paths == []
