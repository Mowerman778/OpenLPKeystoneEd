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
Module to test the MediaClipSelectorForm.
"""
import pytest
import os
from unittest import SkipTest
from unittest.mock import MagicMock, patch

from PyQt5 import QtCore, QtTest, QtWidgets

from openlp.core.ui.media.vlcplayer import get_vlc
from openlp.plugins.media.forms.mediaclipselectorform import MediaClipSelectorForm


if os.name == 'nt' and not get_vlc():
    raise SkipTest('Windows without VLC, skipping this test since it cannot run without vlc')


@pytest.fixture()
def form(settings):
    main_window = QtWidgets.QMainWindow()
    vlc_patcher = patch('openlp.plugins.media.forms.mediaclipselectorform.get_vlc')
    vlc_patcher.start()
    timer_patcher = patch('openlp.plugins.media.forms.mediaclipselectorform.QtCore.QTimer')
    timer_patcher.start()
    # Mock the media item
    mock_media_item = MagicMock()
    # create form to test
    frm = MediaClipSelectorForm(mock_media_item, main_window, None)
    mock_media_state_wait = MagicMock()
    mock_media_state_wait.return_value = True
    frm.media_state_wait = mock_media_state_wait
    frm.application.set_busy_cursor = MagicMock()
    frm.application.set_normal_cursor = MagicMock()
    frm.find_optical_devices = MagicMock()
    yield frm
    del frm
    vlc_patcher.stop()
    timer_patcher.stop()
    del main_window


def test_basic(form):
    """
    Test if the dialog is correctly set up.
    """
    # GIVEN: A mocked QDialog.exec() method
    with patch('PyQt5.QtWidgets.QDialog.exec'):
        # WHEN: Show the dialog.
        form.exec()

        # THEN: The media path should be empty.
        assert form.media_path_combobox.currentText() == '', 'There should not be any text in the media path.'


def test_click_load_button(form):
    """
    Test that the correct function is called when load is clicked, and that it behaves as expected.
    """
    # GIVEN: Mocked methods.
    with patch('openlp.plugins.media.forms.mediaclipselectorform.critical_error_message_box') as \
            mocked_critical_error_message_box, \
            patch('openlp.plugins.media.forms.mediaclipselectorform.os.path.exists') as mocked_os_path_exists, \
            patch('PyQt5.QtWidgets.QDialog.exec'):
        form.exec()

        # WHEN: The load button is clicked with no path set
        QtTest.QTest.mouseClick(form.load_disc_button, QtCore.Qt.LeftButton)

        # THEN: we should get an error
        mocked_critical_error_message_box.assert_called_with(message='No path was given')

        # WHEN: The load button is clicked with a non-existing path
        mocked_os_path_exists.return_value = False
        form.media_path_combobox.insertItem(0, '/non-existing/test-path.test')
        form.media_path_combobox.setCurrentIndex(0)
        QtTest.QTest.mouseClick(form.load_disc_button, QtCore.Qt.LeftButton)

        # THEN: we should get an error
        assert form.media_path_combobox.currentText() == '/non-existing/test-path.test', \
            'The media path should be the given one.'
        mocked_critical_error_message_box.assert_called_with(message='Given path does not exist')

        # WHEN: The load button is clicked with a mocked existing path
        mocked_os_path_exists.return_value = True
        form.vlc_media_player = MagicMock()
        form.vlc_media_player.play.return_value = -1
        form.media_path_combobox.insertItem(0, '/existing/test-path.test')
        form.media_path_combobox.setCurrentIndex(0)
        QtTest.QTest.mouseClick(form.load_disc_button, QtCore.Qt.LeftButton)

        # THEN: we should get an error
        assert form.media_path_combobox.currentText() == '/existing/test-path.test', \
            'The media path should be the given one.'
        mocked_critical_error_message_box.assert_called_with(message='VLC player failed playing the media')


def test_title_combobox(form):
    """
    Test the behavior when the title combobox is updated
    """
    # GIVEN: Mocked methods and some entries in the title combobox.
    with patch('PyQt5.QtWidgets.QDialog.exec'):
        form.exec()
        form.vlc_media_player.get_length.return_value = 1000
        form.audio_tracks_combobox.itemData = MagicMock()
        form.subtitle_tracks_combobox.itemData = MagicMock()
        form.audio_tracks_combobox.itemData.return_value = None
        form.subtitle_tracks_combobox.itemData.return_value = None
        form.titles_combo_box.insertItem(0, 'Test Title 0')
        form.titles_combo_box.insertItem(1, 'Test Title 1')

        # WHEN: There exists audio and subtitle tracks and the index is updated.
        form.vlc_media_player.audio_get_track_description.return_value = [(-1, b'Disabled'),
                                                                          (0, b'Audio Track 1')]
        form.vlc_media_player.video_get_spu_description.return_value = [(-1, b'Disabled'),
                                                                        (0, b'Subtitle Track 1')]
        form.titles_combo_box.setCurrentIndex(1)

        # THEN: The subtitle and audio track comboboxes should be updated and get signals and call itemData.
        form.audio_tracks_combobox.itemData.assert_any_call(0)
        form.audio_tracks_combobox.itemData.assert_any_call(1)
        form.subtitle_tracks_combobox.itemData.assert_any_call(0)


def test_click_save_button(form):
    """
    Test that the correct function is called when save is clicked, and that it behaves as expected.
    """
    # GIVEN: Mocked methods.
    with patch('openlp.plugins.media.forms.mediaclipselectorform.critical_error_message_box') as \
            mocked_critical_error_message_box, \
            patch('PyQt5.QtWidgets.QDialog.exec'):
        form.exec()

        # WHEN: The save button is clicked with a NoneType in start_time_ms or end_time_ms
        form.accept()

        # THEN: we should get an error message
        mocked_critical_error_message_box.assert_called_with('DVD not loaded correctly',
                                                             'The DVD was not loaded correctly, '
                                                             'please re-load and try again.')
