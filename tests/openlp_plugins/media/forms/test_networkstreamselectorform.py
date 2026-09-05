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
This module contains tests for the NetworkStreamSelectorForm.
"""
from unittest.mock import MagicMock, patch

from openlp.plugins.media.forms.networkstreamselectorform import NetworkStreamSelectorForm


def test_search_online_button_uses_typed_text_as_query(settings, registry):
    """
    Test that clicking "Search Online..." opens a YouTube search for whatever's typed in the URL field
    """
    # GIVEN: A NetworkStreamSelectorForm with some non-URL text typed into the Network URL field
    form = NetworkStreamSelectorForm(None, MagicMock())
    form.net_mrl_lineedit.setText('amazing grace hymn')

    # WHEN: The "Search Online..." button is clicked
    with patch('openlp.plugins.media.forms.networkstreamselectorform.QtGui.QDesktopServices') as mocked_services:
        form.on_search_online_button_clicked()

    # THEN: The browser should be opened to a YouTube search for that text
    opened_url = mocked_services.openUrl.call_args[0][0].toString()
    assert opened_url == 'https://www.youtube.com/results?search_query=amazing+grace+hymn'


def test_search_online_button_with_existing_url_opens_youtube_home(settings, registry):
    """
    Test that clicking "Search Online..." doesn't try to search for a URL that's already been entered
    """
    # GIVEN: A NetworkStreamSelectorForm with an actual stream URL already typed in
    form = NetworkStreamSelectorForm(None, MagicMock())
    form.net_mrl_lineedit.setText('rtsp://example.com/stream')

    # WHEN: The "Search Online..." button is clicked
    with patch('openlp.plugins.media.forms.networkstreamselectorform.QtGui.QDesktopServices') as mocked_services:
        form.on_search_online_button_clicked()

    # THEN: The browser should just be opened to YouTube, rather than searching for the URL
    opened_url = mocked_services.openUrl.call_args[0][0].toString()
    assert opened_url == 'https://www.youtube.com/'


def test_search_online_button_with_empty_field_opens_youtube_home(settings, registry):
    """
    Test that clicking "Search Online..." with nothing typed in just opens YouTube
    """
    # GIVEN: A NetworkStreamSelectorForm with nothing typed in
    form = NetworkStreamSelectorForm(None, MagicMock())

    # WHEN: The "Search Online..." button is clicked
    with patch('openlp.plugins.media.forms.networkstreamselectorform.QtGui.QDesktopServices') as mocked_services:
        form.on_search_online_button_clicked()

    # THEN: The browser should just be opened to YouTube
    opened_url = mocked_services.openUrl.call_args[0][0].toString()
    assert opened_url == 'https://www.youtube.com/'
