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
This module contains tests for the db submodule of the Bibles plugin.
"""
from unittest.mock import MagicMock, patch

import pytest

from openlp.plugins.bibles.lib.db import BibleDB, is_in_gui_thread


@pytest.fixture()
def bible_db(registry):
    """A BibleDB instance with its heavy _setup patched out."""
    with patch('openlp.plugins.bibles.lib.db.BibleDB._setup'):
        instance = BibleDB(MagicMock())
    # A missing book takes the error branch without touching the session
    instance.get_book_by_book_ref_id = MagicMock(return_value=None)
    return instance


def test_is_in_gui_thread_true_on_main_thread():
    """Test is_in_gui_thread() is True when the current thread is the application thread"""
    # GIVEN: An application whose thread is the current thread
    with patch('openlp.plugins.bibles.lib.db.QtCore') as mocked_qt:
        app = MagicMock()
        mocked_qt.QCoreApplication.instance.return_value = app
        mocked_qt.QThread.currentThread.return_value = app.thread.return_value

        # WHEN/THEN: We are reported to be in the GUI thread
        assert is_in_gui_thread() is True


def test_is_in_gui_thread_false_on_background_thread():
    """Test is_in_gui_thread() is False when running on a different thread (e.g. the web server)"""
    # GIVEN: An application whose thread differs from the current thread
    with patch('openlp.plugins.bibles.lib.db.QtCore') as mocked_qt:
        mocked_qt.QCoreApplication.instance.return_value = MagicMock()
        mocked_qt.QThread.currentThread.return_value = MagicMock()  # a different object

        # WHEN/THEN: We are reported to be off the GUI thread
        assert is_in_gui_thread() is False


def test_is_in_gui_thread_false_without_application():
    """Test is_in_gui_thread() is False when there is no QApplication instance"""
    with patch('openlp.plugins.bibles.lib.db.QtCore') as mocked_qt:
        mocked_qt.QCoreApplication.instance.return_value = None
        assert is_in_gui_thread() is False


@patch('openlp.plugins.bibles.lib.db.critical_error_message_box')
@patch('openlp.plugins.bibles.lib.db.is_in_gui_thread', return_value=True)
def test_get_verses_book_error_in_gui_thread_shows_dialog(mocked_in_gui, mocked_box, bible_db):
    """Test that an unknown book raises the error dialog when on the GUI thread"""
    # GIVEN: A bible where the book cannot be found, and we are on the GUI thread
    # WHEN: get_verses is called for an unknown book with show_error on
    result = bible_db.get_verses([('99', 1, 1, 1)], show_error=True)

    # THEN: The dialog is shown and no verses are returned
    mocked_box.assert_called_once()
    assert result == []


@patch('openlp.plugins.bibles.lib.db.critical_error_message_box')
@patch('openlp.plugins.bibles.lib.db.is_in_gui_thread', return_value=False)
def test_get_verses_book_error_off_thread_logs_instead_of_dialog(mocked_in_gui, mocked_box, bible_db, caplog):
    """Test that an unknown book from a background thread logs instead of crashing with a dialog (#2200)"""
    # GIVEN: A bible where the book cannot be found, and we are on a background thread (e.g. remote server)
    # WHEN: get_verses is called for an unknown book with show_error on
    result = bible_db.get_verses([('99', 1, 1, 1)], show_error=True)

    # THEN: No Qt dialog is raised (which would abort the process on macOS); the error is logged instead
    mocked_box.assert_not_called()
    assert result == []
    assert any(record.levelname == 'ERROR' for record in caplog.records)


@patch('openlp.plugins.bibles.lib.db.critical_error_message_box')
@patch('openlp.plugins.bibles.lib.db.is_in_gui_thread', return_value=False)
def test_get_verses_book_error_suppressed_when_show_error_false(mocked_in_gui, mocked_box, bible_db):
    """Test that show_error=False neither shows a dialog nor logs an error"""
    # GIVEN: A bible where the book cannot be found
    # WHEN: get_verses is called with show_error off
    result = bible_db.get_verses([('99', 1, 1, 1)], show_error=False)

    # THEN: Nothing is surfaced
    mocked_box.assert_not_called()
    assert result == []
