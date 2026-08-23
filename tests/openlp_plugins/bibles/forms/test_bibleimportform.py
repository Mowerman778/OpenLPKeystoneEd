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
Package to test the openlp.plugins.bibles.forms.bibleimportform package.
"""
from unittest.mock import MagicMock, patch

import pytest
from PyQt5 import QtWidgets, QtTest, QtCore

from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.plugins.bibles.forms.bibleimportform import BibleImportForm


pytestmark = pytest.mark.skip('One of the QFormLayouts in the BibleImportForm is causing a segfault')


@pytest.fixture
def form(registry: Registry, settings: Settings) -> BibleImportForm:
    # main_window = QtWidgets.QMainWindow()
    registry.register('main_window', None)
    yield BibleImportForm(None, MagicMock(), MagicMock())


@patch('openlp.plugins.bibles.forms.bibleimportform.CWExtract.get_bibles_from_http')
@patch('openlp.plugins.bibles.forms.bibleimportform.BGExtract.get_bibles_from_http')
@patch('openlp.plugins.bibles.forms.bibleimportform.BSExtract.get_bibles_from_http')
def test_on_web_update_button_clicked(mocked_bsextract: MagicMock, mocked_bgextract: MagicMock,
                                      mocked_cwextract: MagicMock, form: BibleImportForm):
    """
    Test that on_web_update_button_clicked handles problems correctly
    """
    # GIVEN: Some mocked GUI components and mocked bibleextractors
    form.web_source_combo_box = MagicMock()
    form.web_translation_combo_box = MagicMock()
    form.web_update_button = MagicMock()
    form.web_progress_bar = MagicMock()
    mocked_bsextract.return_value = None
    mocked_bgextract.return_value = None
    mocked_cwextract.return_value = None

    # WHEN: Running on_web_update_button_clicked
    form.on_web_update_button_clicked()

    # THEN: The webbible list should still be empty
    assert form.web_bible_list == {}, 'The webbible list should be empty'


def test_custom_init(form: BibleImportForm):
    """
    Test that custom_init works as expected if pysword is unavailable
    """
    # GIVEN: A mocked sword_tab_widget
    form.sword_tab_widget = MagicMock()

    # WHEN: Running custom_init
    form.custom_init()

    # THEN: sword_tab_widget.setDisabled(True) should have been called
    form.sword_tab_widget.setDisabled.assert_called_with(True)


@patch.object(BibleImportForm, 'provide_help')
def test_help(mocked_help: MagicMock, settings: Settings):
    """
    Test the help button
    """
    # GIVEN: A bible import wizard and a patched help function
    bible_import_form = BibleImportForm(None, MagicMock(), None)

    # WHEN: The Help button is clicked
    QtTest.QTest.mouseClick(bible_import_form.button(QtWidgets.QWizard.WizardButton.HelpButton),
                            QtCore.Qt.LeftButton)

    # THEN: The Help function should be called
    mocked_help.assert_called_once()
