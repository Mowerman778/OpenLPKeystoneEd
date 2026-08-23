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
Package to test the openlp.plugins.planningcenter.lib.planningcentertab package.
"""
from unittest.mock import MagicMock, patch

import pytest
from PyQt5 import QtCore, QtTest, QtWidgets

from openlp.core.state import State
from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.plugins.planningcenter.lib.planningcentertab import PlanningCenterTab
from openlp.plugins.planningcenter.planningcenterplugin import PlanningCenterPlugin


@pytest.fixture
def plugin(registry: Registry, settings: Settings, state: State) -> PlanningCenterPlugin:
    settings.setValue('planningcenter/application_id', 'abc')
    settings.setValue('planningcenter/secret', '123')
    return PlanningCenterPlugin()


@pytest.fixture
def tab(plugin: PlanningCenterPlugin) -> PlanningCenterTab:
    dialog = QtWidgets.QDialog()
    tab = PlanningCenterTab(dialog, 'PlanningCenter')
    tab.setup_ui()
    tab.retranslate_ui()
    tab.load()
    tab.resizeEvent()
    yield tab
    del tab
    del dialog


@patch('openlp.plugins.planningcenter.lib.planningcentertab.PlanningCenterAPI.check_credentials')
@patch('openlp.plugins.planningcenter.lib.planningcentertab.QtWidgets.QMessageBox.warning')
def test_bad_authentication_credentials(mocked_warning: MagicMock, mocked_check_credentials: MagicMock,
                                        tab: PlanningCenterTab):
    """
    Test that the tab can be created and Test authentication clicked for bad application id and secret
    """
    # GIVEN: A PlanningCenterTab Class with bad credentials
    # WHEN: The test button is clicked
    mocked_check_credentials.return_value = ''
    QtTest.QTest.mouseClick(tab.test_credentials_button, QtCore.Qt.LeftButton)
    # THEN: The warning messagebox should be called
    mocked_warning.assert_called_once()


@patch('openlp.plugins.planningcenter.lib.planningcentertab.QtWidgets.QMessageBox.warning')
def test_empty_authentication_credentials(mocked_warning: MagicMock, tab: PlanningCenterTab):
    """
    Test that the tab can be created and Test authentication clicked for missing application id and secret
    """
    # GIVEN: A PlanningCenterTab Class with empty credentials
    # WHEN: The test button is clicked
    tab.application_id_line_edit.setText('')
    tab.secret_line_edit.setText('')
    QtTest.QTest.mouseClick(tab.test_credentials_button, QtCore.Qt.LeftButton)
    # THEN: The warning messagebox should be called
    mocked_warning.assert_called_once()


@patch('openlp.plugins.planningcenter.lib.planningcentertab.PlanningCenterAPI.check_credentials')
@patch('openlp.plugins.planningcenter.lib.planningcentertab.QtWidgets.QMessageBox.information')
def test_good_authentication_credentials(mocked_information: MagicMock, mocked_check_credentials: MagicMock,
                                         tab: PlanningCenterTab):
    """
    Test that the tab can be created and Test authentication clicked for good application id and secret
    """
    # GIVEN: A PlanningCenterTab Class and good credentials
    # WHEN: The test button is clicked
    mocked_check_credentials.return_value = 'good'
    QtTest.QTest.mouseClick(tab.test_credentials_button, QtCore.Qt.LeftButton)
    # THEN: The information messagebox should be called
    mocked_information.assert_called_once()


def test_save_credentials(settings: Settings, tab: PlanningCenterTab):
    """
    Test that credentials are saved in settings when the save function is called
    """
    # GIVEN: A PlanningCenterTab Class
    # WHEN: application id and secret values are set to something and the save function is called
    tab.application_id_line_edit.setText('planningcenter')
    tab.secret_line_edit.setText('woohoo')
    tab.save()
    # THEN: The settings version of application_id and secret should reflect the new values
    application_id = settings.value('planningcenter/application_id')
    secret = settings.value('planningcenter/secret')
    assert application_id == 'planningcenter'
    assert secret == 'woohoo'
