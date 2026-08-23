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
Package to test the openlp.core.ui.media.vlcplayer package.
This class is for DVD and Streaming using a Player.
"""
import os
import sys
from datetime import timedelta
from unittest.mock import MagicMock, call, patch, ANY

import pytest

from openlp.core.common.registry import Registry
from openlp.core.ui.media import ItemMediaInfo, MediaState, MediaType, VlCState
from openlp.core.ui.media.vlcplayer import VlcPlayer
from tests.helpers import MockDateTime


@pytest.fixture
def vlc_env():
    """Local test setup"""
    if 'VLC_PLUGIN_PATH' in os.environ:
        del os.environ['VLC_PLUGIN_PATH']
    if 'openlp.core.ui.media.vendor.vlc' in sys.modules:
        del sys.modules['openlp.core.ui.media.vendor.vlc']
    yield
    MockDateTime.revert()


def test_init(mock_settings):
    """
    Test that the VLC player class initialises correctly
    """
    # GIVEN: A mocked out list of extensions
    # TODO: figure out how to mock out the lists of extensions

    # WHEN: The VlcPlayer class is instantiated
    vlc_player = VlcPlayer(None)

    # THEN: The correct variables are set
    assert 'VLC' == vlc_player.original_name
    assert '&VLC' == vlc_player.display_name
    assert vlc_player.parent is None
    assert vlc_player.can_folder is True


@patch('openlp.core.ui.media.mediaplayer.is_win')
@patch('openlp.core.ui.media.mediaplayer.is_macosx')
@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.QtWidgets')
def test_setup(MockedQtWidgets, mocked_get_vlc, mocked_is_macosx, mocked_is_win, mock_settings):
    """
    Test the setup method
    """
    # GIVEN: A bunch of mocked out stuff and a VlcPlayer object
    mocked_is_macosx.return_value = False
    mocked_is_win.return_value = False
    mock_settings.value.return_value = ''
    mocked_qframe = MagicMock()
    mocked_qframe.winId.return_value = 2
    MockedQtWidgets.QFrame.NoFrame = 1
    MockedQtWidgets.QFrame.return_value = mocked_qframe
    mocked_media_player_new = MagicMock()
    mocked_instance = MagicMock()
    mocked_instance.media_player_new.return_value = mocked_media_player_new
    mocked_vlc = MagicMock()
    mocked_vlc.Instance.return_value = mocked_instance
    mocked_get_vlc.return_value = mocked_vlc
    mocked_output_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.is_live = True
    mocked_output_display.size.return_value = (10, 10)
    vlc_player = VlcPlayer(None)

    # WHEN: setup() is run
    vlc_player.setup(mocked_output_display, mocked_controller)

    # THEN: The VLC widget should be set up correctly
    assert mocked_output_display.vlc_widget == mocked_qframe
    mocked_qframe.setFrameStyle.assert_called_with(1)
    mock_settings.value.assert_any_call('advanced/hide mouse')
    mock_settings.value.assert_any_call('media/vlc arguments')
    mocked_vlc.Instance.assert_called_with('--no-video-title-show --input-repeat=99999999 ')
    assert mocked_output_display.vlc_instance == mocked_instance
    mocked_instance.media_player_new.assert_called_with()
    assert mocked_output_display.vlc_media_player == mocked_media_player_new
    mocked_output_display.size.assert_called_with()
    mocked_qframe.resize.assert_called_with((10, 10))
    mocked_qframe.hide.assert_called_with()
    mocked_media_player_new.set_xwindow.assert_called_with(2)
    assert vlc_player.has_own_widget is True


@patch('openlp.core.ui.media.mediaplayer.is_win')
@patch('openlp.core.ui.media.mediaplayer.is_macosx')
@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.QtWidgets')
def test_setup_has_audio(MockedQtWidgets, mocked_get_vlc, mocked_is_macosx, mocked_is_win, mock_settings):
    """
    Test the setup method when has_audio is True
    """
    # GIVEN: A bunch of mocked out stuff and a VlcPlayer object
    mocked_is_macosx.return_value = False
    mocked_is_win.return_value = False
    mock_settings.value.return_value = ''
    mocked_qframe = MagicMock()
    mocked_qframe.winId.return_value = 2
    MockedQtWidgets.QFrame.NoFrame = 1
    MockedQtWidgets.QFrame.return_value = mocked_qframe
    mocked_media_player_new = MagicMock()
    mocked_instance = MagicMock()
    mocked_instance.media_player_new.return_value = mocked_media_player_new
    mocked_vlc = MagicMock()
    mocked_vlc.Instance.return_value = mocked_instance
    mocked_get_vlc.return_value = mocked_vlc
    mocked_output_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.is_live = True
    mocked_output_display.size.return_value = (10, 10)
    vlc_player = VlcPlayer(None)

    # WHEN: setup() is run
    vlc_player.setup(mocked_output_display, mocked_controller)

    # THEN: The VLC instance should be created with the correct options
    mocked_vlc.Instance.assert_called_with('--no-video-title-show --input-repeat=99999999 ')


@patch('openlp.core.ui.media.mediaplayer.is_win')
@patch('openlp.core.ui.media.mediaplayer.is_macosx')
@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.QtWidgets')
def test_setup_visible_mouse(MockedQtWidgets, mocked_get_vlc, mocked_is_macosx, mocked_is_win, mock_settings):
    """
    Test the setup method when Settings().value("hide mouse") is False
    """
    # GIVEN: A bunch of mocked out stuff and a VlcPlayer object
    mocked_is_macosx.return_value = False
    mocked_is_win.return_value = False
    mock_settings.value.return_value = ''
    mocked_qframe = MagicMock()
    mocked_qframe.winId.return_value = 2
    MockedQtWidgets.QFrame.NoFrame = 1
    MockedQtWidgets.QFrame.return_value = mocked_qframe
    mocked_media_player_new = MagicMock()
    mocked_instance = MagicMock()
    mocked_instance.media_player_new.return_value = mocked_media_player_new
    mocked_vlc = MagicMock()
    mocked_vlc.Instance.return_value = mocked_instance
    mocked_get_vlc.return_value = mocked_vlc
    mocked_output_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.is_live = True
    mocked_output_display.size.return_value = (10, 10)
    vlc_player = VlcPlayer(None)

    # WHEN: setup() is run
    vlc_player.setup(mocked_output_display, mocked_controller)

    # THEN: The VLC instance should be created with the correct options
    mocked_vlc.Instance.assert_called_with('--no-video-title-show --input-repeat=99999999 ')


@patch('openlp.core.ui.media.mediaplayer.is_win')
@patch('openlp.core.ui.media.mediaplayer.is_macosx')
@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.QtWidgets')
def test_setup_windows(MockedQtWidgets, mocked_get_vlc, mocked_is_macosx, mocked_is_win, mock_settings):
    """
    Test the setup method when running on Windows
    """
    # GIVEN: A bunch of mocked out stuff and a VlcPlayer object
    mocked_is_macosx.return_value = False
    mocked_is_win.return_value = True
    mock_settings.value.return_value = False
    mocked_qframe = MagicMock()
    mocked_qframe.winId.return_value = 2
    MockedQtWidgets.QFrame.NoFrame = 1
    MockedQtWidgets.QFrame.return_value = mocked_qframe
    mocked_media_player_new = MagicMock()
    mocked_instance = MagicMock()
    mocked_instance.media_player_new.return_value = mocked_media_player_new
    mocked_vlc = MagicMock()
    mocked_vlc.Instance.return_value = mocked_instance
    mocked_get_vlc.return_value = mocked_vlc
    mocked_output_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.is_live = True
    mocked_output_display.size.return_value = (10, 10)
    vlc_player = VlcPlayer(None)

    # WHEN: setup() is run
    vlc_player.setup(mocked_output_display, mocked_controller)

    # THEN: set_hwnd should be called
    mocked_media_player_new.set_hwnd.assert_called_with(2)


@patch('openlp.core.ui.media.mediaplayer.is_win')
@patch('openlp.core.ui.media.mediaplayer.is_macosx')
@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.QtWidgets')
def test_setup_osx(MockedQtWidgets, mocked_get_vlc, mocked_is_macosx, mocked_is_win, mock_settings):
    """
    Test the setup method when running on OS X
    """
    # GIVEN: A bunch of mocked out stuff and a VlcPlayer object
    mocked_is_macosx.return_value = True
    mocked_is_win.return_value = False
    mock_settings.value.return_value = False
    mocked_qframe = MagicMock()
    mocked_qframe.winId.return_value = 2
    MockedQtWidgets.QFrame.NoFrame = 1
    MockedQtWidgets.QFrame.return_value = mocked_qframe
    mocked_media_player_new = MagicMock()
    mocked_instance = MagicMock()
    mocked_instance.media_player_new.return_value = mocked_media_player_new
    mocked_vlc = MagicMock()
    mocked_vlc.Instance.return_value = mocked_instance
    mocked_get_vlc.return_value = mocked_vlc
    mocked_output_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.is_live = True
    mocked_output_display.size.return_value = (10, 10)
    vlc_player = VlcPlayer(None)

    # WHEN: setup() is run
    vlc_player.setup(mocked_output_display, mocked_controller)

    # THEN: set_nsobject should be called
    mocked_media_player_new.set_nsobject.assert_called_with(2)


@patch('openlp.core.ui.media.vlcplayer.get_vlc')
def test_check_available(mocked_get_vlc):
    """
    Check that when the "vlc" module is available, then VLC is set as available
    """
    # GIVEN: A mocked out get_vlc() method and a VlcPlayer instance
    mocked_get_vlc.return_value = MagicMock()
    vlc_player = VlcPlayer(None)

    # WHEN: vlc
    is_available = vlc_player.check_available()

    # THEN: VLC should be available
    assert is_available is True


@patch('openlp.core.ui.media.vlcplayer.get_vlc')
def test_check_not_available(mocked_get_vlc):
    """
    Check that when the "vlc" module is not available, then VLC is set as unavailable
    """
    # GIVEN: A mocked out get_vlc() method and a VlcPlayer instance
    mocked_get_vlc.return_value = None
    vlc_player = VlcPlayer(None)

    # WHEN: vlc
    is_available = vlc_player.check_available()

    # THEN: VLC should NOT be available
    assert is_available is False


@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.os.path.normcase')
def test_load_stream(mocked_normcase, mocked_get_vlc, settings):
    """
    Test loading a video into VLC
    """
    # GIVEN: A mocked out get_vlc() method
    media_path = '/path/to/media.mp4'
    mocked_normcase.side_effect = lambda x: x
    mocked_vlc = MagicMock()
    mocked_get_vlc.return_value = mocked_vlc
    mocked_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.media_info.media_type = MediaType.Stream
    mocked_controller.media_info.file_info.absoluteFilePath.return_value = media_path
    mocked_controller.vlc_media = MagicMock()
    mocked_media = MagicMock()
    mocked_media.get_duration.return_value = 10000
    mocked_controller.vlc_media_player.get_media.return_value = mocked_media
    vlc_player = VlcPlayer(None)
    # WHEN: A video is loaded into VLC
    result = vlc_player.load(mocked_controller, mocked_display, media_path)
    # THEN: The video should be loaded
    mocked_controller.vlc_instance.media_new_path.assert_not_called()
    mocked_controller.vlc_media_player.set_media.assert_called_with(mocked_controller.vlc_media)
    mocked_controller.vlc_media.parse.assert_called_with()
    assert result is True


@patch('openlp.core.ui.media.vlcplayer.is_win')
@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.os.path.normcase')
def test_load_audio_cd(mocked_normcase, mocked_get_vlc, mocked_is_win, settings):
    """
    Test loading an audio CD into VLC
    """
    # GIVEN: A mocked out get_vlc() method
    mocked_is_win.return_value = False
    media_path = '/dev/sr0'
    mocked_normcase.side_effect = lambda x: x
    mocked_vlc = MagicMock()
    mocked_get_vlc.return_value = mocked_vlc
    mocked_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.media_info.media_type = MediaType.CD
    mocked_controller.media_info.title_track = 1
    mocked_vlc_media = MagicMock()
    mocked_media = MagicMock()
    mocked_controller.media_info.volume = 100
    mocked_controller.media_info.start_time = 20000
    mocked_controller.media_info.end_time = 30000
    mocked_controller.media_info.length = 10000
    mocked_controller.vlc_instance.media_new_location.return_value = mocked_vlc_media
    mocked_controller.vlc_media_player.get_media.return_value = mocked_media
    mocked_subitems = MagicMock()
    mocked_subitems.count.return_value = 1
    mocked_subitems.item_at_index.return_value = mocked_vlc_media
    mocked_vlc_media.subitems.return_value = mocked_subitems
    vlc_player = VlcPlayer(None)

    # WHEN: An audio CD is loaded into VLC
    with patch.object(vlc_player, 'media_state_wait') as mocked_media_state_wait:
        result = vlc_player.load(mocked_controller, mocked_display, media_path)

    # THEN: The video should be loaded
    mocked_normcase.assert_called_with(media_path)
    mocked_controller.vlc_instance.media_new_location.assert_called_with('cdda://' + media_path)
    assert mocked_vlc_media == mocked_controller.vlc_media
    mocked_controller.vlc_media_player.set_media.assert_called_with(mocked_vlc_media)
    mocked_vlc_media.parse.assert_called_with()
    mocked_media_state_wait.assert_called_with(mocked_controller, ANY)
    mocked_controller.mediabar.seek_slider.setMinimum.assert_called_with(20000)
    mocked_controller.mediabar.seek_slider.setMaximum.assert_called_with(30000)
    assert result is True


@patch('openlp.core.ui.media.vlcplayer.is_win')
@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.os.path.normcase')
def test_load_audio_cd_on_windows(mocked_normcase, mocked_get_vlc, mocked_is_win, settings):
    """
    Test loading an audio CD into VLC on Windows
    """
    # GIVEN: A mocked out get_vlc() method
    mocked_is_win.return_value = True
    media_path = '/dev/sr0'
    mocked_normcase.side_effect = lambda x: x
    mocked_vlc = MagicMock()
    mocked_get_vlc.return_value = mocked_vlc
    mocked_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.media_info.media_type = MediaType.CD
    mocked_controller.media_info.file_info.absoluteFilePath.return_value = media_path
    mocked_controller.media_info.title_track = 1
    mocked_vlc_media = MagicMock()
    mocked_media = MagicMock()
    mocked_media.get_duration.return_value = 10000
    mocked_controller.vlc_instance.media_new_location.return_value = mocked_vlc_media
    mocked_controller.vlc_media_player.get_media.return_value = mocked_media
    mocked_subitems = MagicMock()
    mocked_subitems.count.return_value = 1
    mocked_subitems.item_at_index.return_value = mocked_vlc_media
    mocked_vlc_media.subitems.return_value = mocked_subitems

    vlc_player = VlcPlayer(None)

    # WHEN: An audio CD is loaded into VLC
    with patch.object(vlc_player, 'media_state_wait') as mocked_media_state_wait:
        result = vlc_player.load(mocked_controller, mocked_display, media_path)

    # THEN: The video should be loaded
    mocked_normcase.assert_called_with(media_path)
    mocked_controller.vlc_instance.media_new_location.assert_called_with('cdda:///' + media_path)
    assert mocked_vlc_media == mocked_controller.vlc_media
    mocked_controller.vlc_media_player.set_media.assert_called_with(mocked_vlc_media)
    mocked_vlc_media.parse.assert_called_with()
    mocked_media_state_wait.assert_called_with(mocked_controller, ANY)
    assert result is True


@patch('openlp.core.ui.media.vlcplayer.is_win')
@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.os.path.normcase')
def test_load_audio_cd_no_tracks(mocked_normcase, mocked_get_vlc, mocked_is_win):
    """
    Test loading an audio CD that has no tracks into VLC
    """
    # GIVEN: A mocked out get_vlc() method
    mocked_is_win.return_value = False
    media_path = '/dev/sr0'
    mocked_normcase.side_effect = lambda x: x
    mocked_vlc = MagicMock()
    mocked_get_vlc.return_value = mocked_vlc
    mocked_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.media_info.volume = 100
    mocked_controller.media_info.media_type = MediaType.CD
    mocked_controller.media_info.file_info.absoluteFilePath.return_value = media_path
    mocked_controller.media_info.title_track = 1
    mocked_vlc_media = MagicMock()
    mocked_vlc_media_player = MagicMock()
    mocked_controller.vlc_media = mocked_vlc_media
    mocked_controller.vlc_media_player = mocked_vlc_media_player
    mocked_media = MagicMock()
    mocked_media.get_duration.return_value = 10000
    mocked_controller.vlc_instance.media_new_location.return_value = mocked_vlc_media
    mocked_controller.vlc_media_player.get_media.return_value = mocked_media
    mocked_subitems = MagicMock()
    mocked_subitems.count.return_value = 0
    mocked_subitems.item_at_index.return_value = mocked_vlc_media
    mocked_vlc_media.subitems.return_value = mocked_subitems
    vlc_player = VlcPlayer(None)

    # WHEN: An audio CD is loaded into VLC
    with patch.object(vlc_player, 'media_state_wait'):
        result = vlc_player.load(mocked_controller, mocked_display, media_path)

    # THEN: The video should be loaded
    mocked_normcase.assert_called_with(media_path)
    mocked_controller.vlc_instance.media_new_location.assert_called_with('cdda://' + media_path)
    assert mocked_vlc_media == mocked_controller.vlc_media
    assert 0 == mocked_subitems.item_at_index.call_count
    mocked_controller.vlc_media_player.set_media.assert_called_with(mocked_vlc_media)
    assert 0 == mocked_vlc_media.parse.call_count
    assert result is False


@patch('openlp.core.ui.media.vlcplayer.is_win')
@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.os.path.normcase')
def test_load_dvd(mocked_normcase, mocked_get_vlc, mocked_is_win, settings):
    """
    Test loading a DVD into VLC
    """
    # GIVEN: A mocked out get_vlc() method
    mocked_is_win.return_value = False
    media_path = '/dev/sr0'
    mocked_normcase.side_effect = lambda x: x
    mocked_vlc = MagicMock()
    mocked_get_vlc.return_value = mocked_vlc
    mocked_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.media_info.media_type = MediaType.DVD
    mocked_controller.media_info.title_track = '2'
    mocked_controller.media_info.audio_track = 2
    mocked_controller.media_info.subtitle_track = 4
    mocked_vlc_media = MagicMock()
    mocked_media = MagicMock()
    mocked_controller.media_info.start_time = 20000
    mocked_controller.media_info.end_time = 30000
    mocked_controller.media_info.length = 10000
    mocked_controller.vlc_instance.media_new_location.return_value = mocked_vlc_media
    mocked_controller.vlc_media_player.get_media.return_value = mocked_media
    vlc_player = VlcPlayer(None)

    # WHEN: A DVD clip is loaded into VLC
    with patch.object(vlc_player, 'media_state_wait') as mocked_media_state_wait:
        result = vlc_player.load(mocked_controller, mocked_display, media_path)

    # THEN: The video should be loaded
    mocked_normcase.assert_called_with(media_path)
    mocked_controller.vlc_instance.media_new_location.assert_called_with('dvd://' + media_path + '#2')
    assert mocked_vlc_media == mocked_controller.vlc_media
    mocked_controller.vlc_media_player.set_media.assert_called_with(mocked_vlc_media)
    mocked_controller.vlc_media_player.audio_set_track.assert_called_with(2)
    mocked_controller.vlc_media_player.video_set_spu.assert_called_with(4)
    mocked_vlc_media.parse.assert_called_with()
    mocked_media_state_wait.assert_called_with(mocked_controller, ANY)
    mocked_controller.mediabar.seek_slider.setMinimum.assert_called_with(20000)
    mocked_controller.mediabar.seek_slider.setMaximum.assert_called_with(30000)
    assert result is True


@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.datetime', MockDateTime)
def test_media_state_wait(mocked_get_vlc):
    """
    Check that waiting for a state change works
    """
    # GIVEN: A mocked out get_vlc method
    mocked_vlc = MagicMock()
    mocked_vlc.State.Error = 1
    mocked_get_vlc.return_value = mocked_vlc
    mocked_controller = MagicMock()
    mocked_controller.vlc_media.get_state.return_value = VlCState.Buffering
    Registry.create()
    mocked_application = MagicMock()
    Registry().register('application', mocked_application)
    vlc_player = VlcPlayer(None)

    # WHEN: media_state_wait() is called
    result = vlc_player.media_state_wait(mocked_controller, VlCState.Buffering)

    # THEN: The results should be True
    assert result is True


@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.datetime', MockDateTime)
def test_media_state_wait_error(mocked_get_vlc, vlc_env):
    """
    Check that getting an error when waiting for a state change returns False
    """
    # GIVEN: A mocked out get_vlc method
    mocked_vlc = MagicMock()
    mocked_vlc.State.Error = 1
    mocked_get_vlc.return_value = mocked_vlc
    mocked_controller = MagicMock()
    mocked_controller.vlc_media.get_state.return_value = VlCState.Error
    Registry.create()
    mocked_application = MagicMock()
    Registry().register('application', mocked_application)
    vlc_player = VlcPlayer(None)

    # WHEN: media_state_wait() is called
    result = vlc_player.media_state_wait(mocked_controller, VlCState.Buffering)

    # THEN: The results should be True
    assert result is False


@patch('openlp.core.ui.media.vlcplayer.get_vlc')
@patch('openlp.core.ui.media.vlcplayer.datetime', MockDateTime)
def test_media_state_wait_times_out(mocked_get_vlc, vlc_env):
    """
    Check that waiting for a state returns False when it times out after 60 seconds
    """
    # GIVEN: A mocked out get_vlc method
    timeout = MockDateTime.return_values[0] + timedelta(seconds=61)
    MockDateTime.return_values.append(timeout)
    mocked_vlc = MagicMock()
    mocked_vlc.State.Error = 1
    mocked_get_vlc.return_value = mocked_vlc
    mocked_controller = MagicMock()
    mocked_controller.vlc_media.get_state.return_value = VlCState.Buffering
    Registry.create()
    mocked_application = MagicMock()
    Registry().register('application', mocked_application)
    vlc_player = VlcPlayer(None)

    # WHEN: media_state_wait() is called
    result = vlc_player.media_state_wait(mocked_controller, VlCState.Playing)

    # THEN: The results should be True
    assert result is False


def test_resize():
    """
    Test resizing the player
    """
    # GIVEN: A display object and a VlcPlayer instance
    mocked_controller = MagicMock()
    mocked_controller.preview_display.size.return_value = (10, 10)
    mocked_controller.is_live = False
    vlc_player = VlcPlayer(None)

    # WHEN: resize is called
    vlc_player.resize(mocked_controller)

    # THEN: The right methods should have been called
    mocked_controller.preview_display.size.assert_called_with()
    mocked_controller.vlc_widget.resize.assert_called_with((10, 10))


@patch('openlp.core.ui.media.vlcplayer.threading')
@patch('openlp.core.ui.media.vlcplayer.get_vlc')
def test_play(mocked_get_vlc, mocked_threading, settings):
    """
    Test the play() method
    """
    # GIVEN: A bunch of mocked out things
    mocked_thread = MagicMock()
    mocked_threading.Thread.return_value = mocked_thread
    mocked_vlc = MagicMock()
    mocked_get_vlc.return_value = mocked_vlc
    mocked_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_media = MagicMock()
    mocked_controller.vlc_media_player.get_media.return_value = mocked_media
    vlc_player = VlcPlayer(None)
    vlc_player.set_state(MediaState.Paused, mocked_controller)

    # WHEN: play() is called
    with patch.object(vlc_player, 'media_state_wait') as mocked_media_state_wait:
        mocked_media_state_wait.return_value = True
        result = vlc_player.play(mocked_controller, mocked_display)

    # THEN: A bunch of things should happen to play the media
    mocked_thread.start.assert_called_with()
    assert MediaState.Playing == vlc_player.get_live_state()
    assert result is True, 'The value returned from play() should be True'


@patch('openlp.core.ui.media.vlcplayer.threading')
@patch('openlp.core.ui.media.vlcplayer.get_vlc')
def test_play_media_wait_state_not_playing(mocked_get_vlc, mocked_threading):
    """
    Test the play() method when media_wait_state() returns False
    """
    # GIVEN: A bunch of mocked out things
    mocked_thread = MagicMock()
    mocked_threading.Thread.return_value = mocked_thread
    mocked_vlc = MagicMock()
    mocked_get_vlc.return_value = mocked_vlc
    mocked_controller = MagicMock()
    mocked_controller.media_info.start_time = 0
    mocked_output_display = MagicMock()
    vlc_player = VlcPlayer(None)
    vlc_player.set_state(MediaState.Paused, mocked_output_display)

    # WHEN: play() is called
    with patch.object(vlc_player, 'media_state_wait') as mocked_media_state_wait, \
            patch.object(vlc_player, 'volume'):
        mocked_media_state_wait.return_value = False
        result = vlc_player.play(mocked_controller, mocked_output_display)

    # THEN: A thread should be started, but the method should return False
    mocked_thread.start.assert_called_with()
    assert result is False


@patch('openlp.core.ui.media.vlcplayer.get_vlc')
def test_pause(mocked_get_vlc):
    """
    Test that the pause method works correctly
    """
    # GIVEN: A mocked out get_vlc method
    mocked_vlc = MagicMock()
    mocked_vlc.State.Playing = VlCState.Playing
    mocked_vlc.State.Paused = VlCState.Paused
    mocked_get_vlc.return_value = mocked_vlc
    mocked_display = MagicMock()
    mocked_display.vlc_media.get_state.return_value = VlCState.Playing
    vlc_player = VlcPlayer(None)

    # WHEN: The media is paused
    with patch.object(vlc_player, 'media_state_wait') as mocked_media_state_wait:
        mocked_media_state_wait.return_value = True
        vlc_player.pause(mocked_display)

    # THEN: The pause method should exit early
    mocked_display.vlc_media.get_state.assert_called_with()
    mocked_display.vlc_media_player.pause.assert_called_with()
    mocked_media_state_wait.assert_called_with(mocked_display, VlCState.Paused)
    assert MediaState.Paused == vlc_player.get_live_state()


@patch('openlp.core.ui.media.vlcplayer.get_vlc')
def test_pause_not_playing(mocked_get_vlc):
    """
    Test the pause method when the player is not playing
    """
    # GIVEN: A mocked out get_vlc method
    mocked_vlc = MagicMock()
    mocked_vlc.State.Playing = 1
    mocked_get_vlc.return_value = mocked_vlc
    mocked_display = MagicMock()
    mocked_display.vlc_media.get_state.return_value = VlCState.Paused
    vlc_player = VlcPlayer(None)

    # WHEN: The media is paused
    vlc_player.pause(mocked_display)

    # THEN: The pause method should exit early
    mocked_display.vlc_media.get_state.assert_called_with()
    assert 0 == mocked_display.vlc_media_player.pause.call_count


@patch('openlp.core.ui.media.vlcplayer.get_vlc')
def test_pause_fail(mocked_get_vlc):
    """
    Test the pause method when the player fails to pause the media
    """
    # GIVEN: A mocked out get_vlc method
    mocked_vlc = MagicMock()
    mocked_vlc.State.Playing = 1
    mocked_vlc.State.Paused = 2
    mocked_get_vlc.return_value = mocked_vlc
    mocked_display = MagicMock()
    mocked_display.vlc_media.get_state.return_value = VlCState.Playing
    vlc_player = VlcPlayer(None)

    # WHEN: The media is paused
    with patch.object(vlc_player, 'media_state_wait') as mocked_media_state_wait:
        mocked_media_state_wait.return_value = False
        vlc_player.pause(mocked_display)

    # THEN: The pause method should exit early
    mocked_display.vlc_media.get_state.assert_called_with()
    mocked_display.vlc_media_player.pause.assert_called_with()
    mocked_media_state_wait.assert_called_with(mocked_display, VlCState.Paused)
    assert MediaState.Paused is not vlc_player.state


@patch('openlp.core.ui.media.vlcplayer.threading')
def test_stop(mocked_threading):
    """
    Test stopping the current item
    """
    # GIVEN: A display object and a VlcPlayer instance and some mocked threads
    mocked_thread = MagicMock()
    mocked_threading.Thread.return_value = mocked_thread
    mocked_stop = MagicMock()
    mocked_display = MagicMock()
    mocked_display.vlc_media_player.stop = mocked_stop
    vlc_player = VlcPlayer(None)

    # WHEN: stop is called
    vlc_player.stop(mocked_display)

    # THEN: A thread should have been started to stop VLC
    mocked_threading.Thread.assert_called_with(target=mocked_stop)
    mocked_thread.start.assert_called_with()
    assert MediaState.Stopped == vlc_player.get_live_state()


def test_volume():
    """
    Test setting the volume
    """
    # GIVEN: A display object and a VlcPlayer instance
    mocked_display = MagicMock()
    mocked_display.has_audio = True
    vlc_player = VlcPlayer(None)

    # WHEN: The volume is set
    vlc_player.volume(mocked_display, 10)

    # THEN: The volume should have been set
    mocked_display.vlc_media_player.audio_set_volume.assert_called_with(10)


def test_seek_unseekable_media():
    """
    Test seeking something that can't be seeked
    """
    # GIVEN: Unseekable media
    mocked_display = MagicMock()
    mocked_display.controller.media_info.media_type = MediaType.Audio
    mocked_display.vlc_media_player.is_seekable.return_value = False
    vlc_player = VlcPlayer(None)

    # WHEN: seek() is called
    vlc_player.seek(mocked_display, 100)

    # THEN: nothing should happen
    mocked_display.vlc_media_player.is_seekable.assert_called_with()
    assert 0 == mocked_display.vlc_media_player.set_time.call_count


def test_seek_seekable_media():
    """
    Test seeking something that is seekable, but not a DVD
    """
    # GIVEN: Unseekable media
    mocked_display = MagicMock()
    mocked_display.controller.media_info.media_type = MediaType.Audio
    mocked_display.vlc_media_player.is_seekable.return_value = True
    vlc_player = VlcPlayer(None)

    # WHEN: seek() is called
    vlc_player.seek(mocked_display, 100)

    # THEN: nothing should happen
    mocked_display.vlc_media_player.is_seekable.assert_called_with()
    mocked_display.vlc_media_player.set_time.assert_called_with(100)


def test_seek_dvd():
    """
    Test seeking a DVD
    """
    # GIVEN: Unseekable media
    mocked_display = MagicMock()
    mocked_display.controller.media_info.media_type = MediaType.DVD
    mocked_display.vlc_media_player.is_seekable.return_value = True
    mocked_display.controller.media_info.start_time = 3000
    vlc_player = VlcPlayer(None)

    # WHEN: seek() is called
    vlc_player.seek(mocked_display, 2000)

    # THEN: nothing should happen
    mocked_display.vlc_media_player.is_seekable.assert_called_with()
    mocked_display.vlc_media_player.set_time.assert_called_with(2000)


def test_reset():
    """
    Test the reset() method
    """
    # GIVEN: Some mocked out stuff
    mocked_display = MagicMock()
    vlc_player = VlcPlayer(None)

    # WHEN: reset() is called
    vlc_player.reset(mocked_display)

    # THEN: The media should be stopped and invisible
    mocked_display.vlc_media_player.stop.assert_called_with()
    mocked_display.vlc_widget.setVisible.assert_not_called()
    assert MediaState.Off == vlc_player.get_live_state()


def test_set_visible_has_own_widget():
    """
    Test the set_visible() method when the player has its own widget
    """
    # GIVEN: Some mocked out stuff
    mocked_display = MagicMock()
    vlc_player = VlcPlayer(None)
    vlc_player.has_own_widget = True

    # WHEN: reset() is called
    vlc_player.set_visible(mocked_display, True)

    # THEN: The media should be stopped and invsibile
    mocked_display.vlc_widget.setVisible.assert_called_with(True)


@patch('openlp.core.ui.media.vlcplayer.get_vlc')
def test_update_ui(mocked_get_vlc):
    """
    Test updating the UI
    """
    # GIVEN: A whole bunch of mocks
    mocked_vlc = MagicMock()
    mocked_vlc.State.Ended = 1
    mocked_get_vlc.return_value = mocked_vlc
    mocked_controller = MagicMock()
    mocked_controller.media_info.end_time = 300
    mocked_controller.mediabar.seek_slider.isSliderDown.return_value = False
    mocked_display = MagicMock()
    mocked_controller.vlc_media.get_state.return_value = 1
    mocked_controller.vlc_media_player.get_time.return_value = 400000
    vlc_player = VlcPlayer(None)

    # WHEN: update_ui() is called
    vlc_player.update_ui(mocked_controller, mocked_display)

    # THEN: Certain methods should be called
    mocked_controller.vlc_media_player.get_time.assert_called_with()
    mocked_controller.mediabar.seek_slider.setSliderPosition.assert_called_with(400000)
    expected_calls = [call(True), call(False)]
    assert expected_calls == mocked_controller.mediabar.seek_slider.blockSignals.call_args_list


@patch('openlp.core.ui.media.vlcplayer.get_vlc')
def test_update_ui_dvd(mocked_get_vlc):
    """
    Test updating the UI for a CD or DVD
    """
    # GIVEN: A whole bunch of mocks
    mocked_vlc = MagicMock()
    mocked_vlc.State.Ended = 1
    mocked_get_vlc.return_value = mocked_vlc
    mocked_controller = MagicMock()
    mocked_controller.media_info = ItemMediaInfo()
    mocked_controller.media_info.start_time = 100
    mocked_controller.media_info.end_time = 300
    mocked_controller.mediabar.seek_slider.isSliderDown.return_value = False
    mocked_display = MagicMock()
    mocked_controller.vlc_media.get_state.return_value = 1
    mocked_controller.vlc_media_player.get_time.return_value = 200
    mocked_controller.media_info.media_type = MediaType.DVD
    vlc_player = VlcPlayer(None)

    # WHEN: update_ui() is called
    vlc_player.update_ui(mocked_controller, mocked_display)

    # THEN: Certain methods should be called
    mocked_controller.vlc_media_player.get_time.assert_called_with()
    mocked_controller.mediabar.seek_slider.setSliderPosition.assert_called_with(200)
    expected_calls = [call(True), call(False)]
    assert expected_calls == mocked_controller.mediabar.seek_slider.blockSignals.call_args_list
