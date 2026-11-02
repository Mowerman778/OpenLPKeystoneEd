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
Tests for the Help > Updates window
"""
from unittest.mock import MagicMock, patch

import pytest
from PyQt5 import QtWidgets

from openlp.core.ui.updateform import UpdateForm

INFO = {'version': '1.0.1', 'notes': 'Fixes', 'installer': {'name': 'OpenLPUG-Setup-1.0.1.exe', 'size': 104857600}}


@pytest.mark.parametrize('current_version, can_install, is_offered', [('1.0.0', True, True),
                                                                      ('1.0.1', True, False),
                                                                      ('1.0.0', False, False)])
def test_on_checked(current_version, can_install, is_offered, settings):
    """Download and Install is offered only for a newer version, in the installed Keystone"""
    # GIVEN: The Updates window
    form = UpdateForm()

    # WHEN: The latest release is found
    with patch('openlp.core.ui.updateform.get_current_version', return_value=current_version), \
            patch('openlp.core.ui.updateform.can_install_updates', return_value=can_install):
        form.on_checked(INFO)

    # THEN: Its version and notes are shown, and it can be installed only when it should
    assert form.latest_label.text() == '1.0.1'
    assert form.notes_edit.toPlainText() == 'Fixes'
    assert form.install_button.isEnabled() is is_offered


def test_on_downloaded_runs_installer_when_closed(settings, registry):
    """Once downloaded, Keystone closes and the installer runs after it has closed"""
    # GIVEN: A downloaded installer, and a user who agrees to install
    form = UpdateForm()
    form.info = INFO
    main_window = MagicMock()
    main_window.close.return_value = True
    registry.register('main_window', main_window)
    application = MagicMock()

    # WHEN: The download finishes
    with patch('openlp.core.ui.updateform.QtWidgets.QMessageBox.question',
               return_value=QtWidgets.QMessageBox.Ok), \
            patch('openlp.core.ui.updateform.QtWidgets.QApplication.instance', return_value=application), \
            patch('openlp.core.ui.updateform.start_installer') as mocked_start_installer:
        form.on_downloaded('setup.exe')
        run_installer = application.aboutToQuit.connect.call_args[0][0]
        run_installer()

    # THEN: Keystone is closed, and the installer is started as it quits
    main_window.close.assert_called_once_with()
    mocked_start_installer.assert_called_once_with('setup.exe')
    application.aboutToQuit.disconnect.assert_not_called()


def test_on_downloaded_close_cancelled(settings, registry):
    """If the user decides not to close Keystone after all, the installer is not run later"""
    # GIVEN: A downloaded installer, and a user who cancels closing
    form = UpdateForm()
    form.info = INFO
    main_window = MagicMock()
    main_window.close.return_value = False
    registry.register('main_window', main_window)
    application = MagicMock()

    # WHEN: The download finishes
    with patch('openlp.core.ui.updateform.QtWidgets.QMessageBox.question',
               return_value=QtWidgets.QMessageBox.Ok), \
            patch('openlp.core.ui.updateform.QtWidgets.QApplication.instance', return_value=application):
        form.on_downloaded('setup.exe')

    # THEN: The installer is no longer waiting for Keystone to quit
    application.aboutToQuit.disconnect.assert_called_once()
