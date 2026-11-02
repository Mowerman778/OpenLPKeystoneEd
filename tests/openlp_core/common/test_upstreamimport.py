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
Tests for copying a normal OpenLP's data and settings into Keystone Edition
"""
from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt5 import QtCore

from openlp.core.common.applocation import AppLocation, _get_os_dir_path
from openlp.core.common.settings import Settings
from openlp.core.common.upstreamimport import import_upstream, should_offer_import


@pytest.fixture()
def upstream(tmp_path: Path):
    """A normal OpenLP's settings, in an INI file rather than the registry, and its data folder"""
    # Written through Settings, so values are stored the way OpenLP stores them
    upstream_settings = Settings(str(tmp_path / 'upstream.ini'), QtCore.QSettings.IniFormat)
    upstream_settings.setValue('core/has run wizard', True)
    upstream_settings.setValue('core/application version', '3.1.7')
    upstream_settings.setValue('advanced/data path', tmp_path / 'somewhere else')
    upstream_settings.setValue('songs/last directory import', Path('C:/Songs'))
    upstream_settings.sync()
    data_path = tmp_path / 'openlp' / 'data'
    (data_path / 'songs').mkdir(parents=True)
    (data_path / 'songs' / 'songs.sqlite').write_bytes(b'songs')
    (data_path / 'openlp-data.lock').write_text('locked')
    with patch('openlp.core.common.upstreamimport.get_upstream_settings', return_value=upstream_settings), \
            patch('openlp.core.common.upstreamimport.get_upstream_data_path', return_value=data_path):
        yield upstream_settings


def test_import_upstream(upstream: QtCore.QSettings, settings: Settings, tmp_path: Path):
    """The normal OpenLP's settings and data are copied, except what would tie Keystone to the normal OpenLP"""
    # GIVEN: A normal OpenLP with settings and songs, and an empty Keystone
    keystone_data_path = tmp_path / 'openlpkeystone' / 'data'

    # WHEN: Its data is copied
    result = import_upstream(settings, keystone_data_path)

    # THEN: The settings and songs are copied, but not its data path, version or lock file
    assert result is True
    assert settings.value('core/has run wizard') is True
    assert settings.value('songs/last directory import') == Path('C:/Songs')
    assert settings.contains('advanced/data path') is False
    assert settings.value('core/application version') == '0.0'
    assert (keystone_data_path / 'songs' / 'songs.sqlite').read_bytes() == b'songs'
    assert not (keystone_data_path / 'openlp-data.lock').exists()
    # AND: The normal OpenLP's own data is untouched
    assert (tmp_path / 'openlp' / 'data' / 'songs' / 'songs.sqlite').exists()


@pytest.mark.parametrize('has_upstream, has_run_wizard, is_offered', [(True, False, True),
                                                                      (True, True, False),
                                                                      (False, False, False)])
def test_should_offer_import(has_upstream, has_run_wizard, is_offered, settings: Settings):
    """The copy is offered only on Keystone's first start, and only when a normal OpenLP has been set up"""
    # GIVEN: Keystone, maybe already set up, and maybe a normal OpenLP
    if has_run_wizard:
        settings.setValue('core/has run wizard', True)

    # WHEN: Checking whether to offer the copy
    with patch('openlp.core.common.upstreamimport.get_upstream_settings',
               return_value=object() if has_upstream else None):
        result = should_offer_import(settings)

    # THEN: It is offered only on the first start with a normal OpenLP
    assert result is is_offered


@patch('openlp.core.common.applocation.is_win', return_value=True)
@patch('openlp.core.common.applocation.os.getenv', return_value='C:\\Users\\Someone\\AppData\\Roaming')
def test_keystone_data_folder_is_apart_from_openlp(mocked_getenv, mocked_is_win):
    """Keystone keeps its data in its own folder, next to a normal OpenLP's"""
    # GIVEN: Windows
    # WHEN: The data folders are asked for
    keystone_path = _get_os_dir_path(AppLocation.DataDir)
    upstream_path = AppLocation.get_upstream_data_directory()

    # THEN: They are different folders
    assert keystone_path == Path('C:\\Users\\Someone\\AppData\\Roaming', 'openlpkeystonedev', 'data')
    assert upstream_path.parts[-2:] == ('openlp', 'data')
