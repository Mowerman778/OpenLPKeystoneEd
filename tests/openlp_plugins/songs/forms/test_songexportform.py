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
This module contains tests for the song export form.
"""
from unittest.mock import MagicMock, patch

from PyQt5 import QtCore

from openlp.plugins.songs.forms.songexportform import SongExportForm


def _bare_form():
    """Build a SongExportForm shell with only the attributes validateCurrentPage touches."""
    form = SongExportForm.__new__(SongExportForm)
    form.welcome_page = object()
    form.available_songs_page = object()
    form.export_song_page = object()
    form.progress_page = object()
    form.currentPage = MagicMock(return_value=form.available_songs_page)
    form.available_list_widget = MagicMock()
    form.selected_list_widget = MagicMock()
    return form


def _item(check_state, text, song):
    """A fake list item whose checkState() returns the given value."""
    item = MagicMock()
    item.checkState.return_value = check_state
    item.text.return_value = text
    item.data.return_value = song
    return item


@patch('openlp.plugins.songs.forms.songexportform.critical_error_message_box')
@patch('openlp.plugins.songs.forms.songexportform.find_list_widget_items')
def test_validate_exports_only_checked_songs(mocked_find, mocked_box):
    """Test that only checked songs are carried to the export list (issue #1995)"""
    # GIVEN: One checked song and two "unchecked" songs whose checkState() is truthy-but-not-Checked
    #        (emulating newer PyQt5, where Qt.CheckState is a Python enum and every member is truthy)
    form = _bare_form()
    truthy_unchecked = object()
    mocked_find.return_value = [
        _item(truthy_unchecked, 'Unchecked A', 'song-a'),
        _item(QtCore.Qt.Checked, 'Checked B', 'song-b'),
        _item(truthy_unchecked, 'Unchecked C', 'song-c'),
    ]

    # WHEN: The available-songs page is validated
    result = form.validateCurrentPage()

    # THEN: It passes, and exactly the one checked song is added to the selected list
    assert result is True
    mocked_box.assert_not_called()
    added = [call.args[0].text() for call in form.selected_list_widget.addItem.call_args_list]
    assert added == ['Checked B']


@patch('openlp.plugins.songs.forms.songexportform.critical_error_message_box')
@patch('openlp.plugins.songs.forms.songexportform.find_list_widget_items')
def test_validate_errors_when_nothing_checked(mocked_find, mocked_box):
    """Test that validation fails with an error when no song is actually checked (issue #1995)"""
    # GIVEN: Only "unchecked" songs (truthy checkState, as newer PyQt5 reports for Unchecked)
    form = _bare_form()
    truthy_unchecked = object()
    mocked_find.return_value = [
        _item(truthy_unchecked, 'Unchecked A', 'song-a'),
        _item(truthy_unchecked, 'Unchecked B', 'song-b'),
    ]

    # WHEN: The available-songs page is validated
    result = form.validateCurrentPage()

    # THEN: Validation is blocked and the user is told to select at least one song
    assert result is False
    mocked_box.assert_called_once()
    form.selected_list_widget.addItem.assert_not_called()
