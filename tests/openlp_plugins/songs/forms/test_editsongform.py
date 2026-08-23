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
Package to test the openlp.plugins.songs.forms.editsongform package.
"""
import pytest
from unittest.mock import MagicMock, patch

from PyQt5 import QtWidgets, QtTest, QtCore

from openlp.core.common.i18n import UiStrings
from openlp.core.common.registry import Registry
from openlp.plugins.songs.forms.editsongform import EditSongForm


@pytest.fixture()
def form(settings):
    main_window = QtWidgets.QMainWindow()
    Registry().register('main_window', main_window)
    Registry().register('theme_manager', MagicMock())
    frm = EditSongForm(MagicMock(), main_window, MagicMock())
    yield frm
    del frm
    del main_window


def test_ui_defaults(form):
    """
    Test that the EditSongForm defaults are correct
    """
    assert form.verse_edit_button.isEnabled() is False, 'The verse edit button should not be enabled'
    assert form.verse_delete_button.isEnabled() is False, 'The verse delete button should not be enabled'
    assert form.author_remove_button.isEnabled() is False, 'The author remove button should not be enabled'
    assert form.topic_remove_button.isEnabled() is False, 'The topic remove button should not be enabled'


def test_verse_order_no_warning(form):
    """
    Test if the verse order warning is not shown
    """
    # GIVEN: Mocked methods.
    given_verse_order = 'V1 V2'
    form.verse_list_widget.rowCount = MagicMock(return_value=2)
    # Mock out the verse.
    first_verse = MagicMock()
    first_verse.data.return_value = 'V1'
    second_verse = MagicMock()
    second_verse.data.return_value = 'V2'
    form.verse_list_widget.item = MagicMock(side_effect=[first_verse, second_verse])
    form._extract_verse_order = MagicMock(return_value=given_verse_order.split())

    # WHEN: Call the method.
    form.on_verse_order_text_changed(given_verse_order)

    # THEN: No text should be shown.
    assert form.warning_label.text() == '', 'There should be no warning.'


def test_verse_order_incomplete_warning(form):
    """
    Test if the verse-order-incomple warning is shown
    """
    # GIVEN: Mocked methods.
    given_verse_order = 'V1'
    form.verse_list_widget.rowCount = MagicMock(return_value=2)
    # Mock out the verse.
    first_verse = MagicMock()
    first_verse.data.return_value = 'V1'
    second_verse = MagicMock()
    second_verse.data.return_value = 'V2'
    form.verse_list_widget.item = MagicMock(side_effect=[first_verse, second_verse])
    form._extract_verse_order = MagicMock(return_value=[given_verse_order])

    # WHEN: Call the method.
    form.on_verse_order_text_changed(given_verse_order)

    # THEN: The verse-order-incomplete text should be shown.
    assert form.warning_label.text() == form.not_all_verses_used_warning, \
        'The verse-order-incomplete warning should be shown.'


def test_bug_1170435(form):
    """
    Regression test for bug 1170435 (test if "no verse order" message is shown)
    """
    # GIVEN: Mocked methods.
    given_verse_order = ''
    form.verse_list_widget.rowCount = MagicMock(return_value=1)
    # Mock out the verse. (We want a verse type to be returned).
    mocked_verse = MagicMock()
    mocked_verse.data.return_value = 'V1'
    form.verse_list_widget.item = MagicMock(return_value=mocked_verse)
    form._extract_verse_order = MagicMock(return_value=[])
    form.verse_order_edit.text = MagicMock(return_value=given_verse_order)
    # WHEN: Call the method.
    form.on_verse_order_text_changed(given_verse_order)

    # THEN: The no-verse-order message should be shown.
    assert form.warning_label.text() == form.no_verse_order_entered_warning,  \
        'The no-verse-order message should be shown.'


def test_bug_1404967(form):
    """
    Test for CCLI label showing correct text
    """
    # GIVEN; Mocked methods
    # THEN: CCLI label should be CCLI song label
    assert form.ccli_label.text() is not UiStrings().CCLINumberLabel, \
        'CCLI label should not be "{}"'.format(UiStrings().CCLINumberLabel)
    assert form.ccli_label.text() == UiStrings().CCLISongNumberLabel, \
        'CCLI label text should be "{}"'.format(UiStrings().CCLISongNumberLabel)


def test_verse_order_lowercase(form):
    """
    Test that entering a verse order in lowercase automatically converts to uppercase
    """
    # GIVEN; Mocked methods

    # WHEN: We enter a verse order in lowercase
    form.verse_order_edit.setText('v1 v2 c1 v3 c1 v4 c1')
    # Need to manually trigger this method as it is only triggered by manual input
    form.on_verse_order_text_changed(form.verse_order_edit.text())

    # THEN: The verse order should be converted to uppercase
    assert form.verse_order_edit.text() == 'V1 V2 C1 V3 C1 V4 C1'


@patch.object(EditSongForm, 'provide_help')
def test_help(mocked_help, settings):
    """
    Test the help button
    """
    # GIVEN: An edit song form and a patched help function
    main_window = QtWidgets.QMainWindow()
    Registry().register('main_window', main_window)
    Registry().register('theme_manager', MagicMock())
    edit_song_form = EditSongForm(MagicMock(), main_window, MagicMock())

    # WHEN: The Help button is clicked
    QtTest.QTest.mouseClick(edit_song_form.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Help),
                            QtCore.Qt.LeftButton)

    # THEN: The Help function should be called
    mocked_help.assert_called_once()
