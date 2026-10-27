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
Tests for the debug report and the Keystone version information
"""
import zipfile
from unittest.mock import patch

from openlp.core.common.keystone import (KEYSTONE_VERSION, VERSION_HISTORY, version_history_html,
                                         version_label)
from openlp.core.ui.debugreport import create_debug_report, is_secret_setting, settings_text


def test_version_label():
    """
    Test the version line shown in the About box
    """
    assert version_label() == "Keystone's OpenLP Custom: Ver. : {version}".format(version=KEYSTONE_VERSION)


def test_current_version_is_first_in_history():
    """
    Test the version history starts with the current version, so the two can't drift apart
    """
    assert VERSION_HISTORY[0][0] == KEYSTONE_VERSION
    assert KEYSTONE_VERSION in version_history_html()
    assert '3.1.7' in version_history_html()


def test_is_secret_setting():
    assert is_secret_setting('songs/songselect password')
    assert is_secret_setting('songs/songselect username')
    assert is_secret_setting('planningcenter/secret')
    assert is_secret_setting('api/pin')
    assert not is_secret_setting('songs/footer template')


def test_settings_text_removes_secrets(settings):
    """
    Test passwords never make it into the report, but ordinary settings do
    """
    settings.setValue('songs/songselect password', 'hunter2')
    settings.setValue('media/audio delay', 250)
    text = settings_text(settings)
    assert 'hunter2' not in text
    assert 'songs/songselect password = <removed>' in text
    assert 'media/audio delay = 250' in text


def test_create_debug_report(qapp, settings, tmp_path):
    """
    Test the report zip holds the system details, settings and logs
    """
    # GIVEN: A log folder with a log file and a password in the settings
    log_folder = tmp_path / 'logs'
    log_folder.mkdir()
    (log_folder / 'openlp.log').write_text('something went wrong', encoding='utf-8')
    settings.setValue('songs/songselect password', 'hunter2')
    with patch('openlp.core.ui.debugreport.AppLocation.get_directory', return_value=log_folder):
        # WHEN: The report is created
        report_path = create_debug_report(tmp_path)

    # THEN: It contains everything, minus the password
    with zipfile.ZipFile(report_path) as report:
        names = report.namelist()
        assert {'system-info.txt', 'settings.txt', 'openlp.log'} <= set(names)
        assert "Keystone's OpenLP Custom" in report.read('system-info.txt').decode()
        assert 'hunter2' not in report.read('settings.txt').decode()
        assert report.read('openlp.log').decode() == 'something went wrong'
