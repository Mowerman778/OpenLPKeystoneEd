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
Tests for updating Keystone Edition from GitHub releases
"""
import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from openlp.core.common.updater import UpdateError, download_installer, fetch_update_info, get_manifest_url, \
    is_newer, parse_update_source

SOURCE = 'https://github.com/Owner/Repo'
INSTALLER = b'installer bytes'


def make_info(**installer_changes):
    """The details of a release, as update.json holds them"""
    installer = {'name': 'OpenLPUG-Setup-1.0.1.exe',
                 'url': 'https://github.com/Owner/Repo/releases/download/v1.0.1/OpenLPUG-Setup-1.0.1.exe',
                 'size': len(INSTALLER), 'sha256': hashlib.sha256(INSTALLER).hexdigest()}
    installer.update(installer_changes)
    return {'version': '1.0.1', 'released': '2026-11-03', 'notes': 'Fixes', 'installer': installer}


def mock_response(status_code=200, text='', chunks=()):
    response = MagicMock(status_code=status_code, text=text)
    response.iter_content.return_value = list(chunks)
    response.__enter__.return_value = response
    return response


@pytest.mark.parametrize('source', ['https://github.com/Owner/Repo', 'https://github.com/Owner/Repo/',
                                    'https://github.com/Owner/Repo.git', ' https://github.com/Owner/Repo '])
def test_parse_update_source(source):
    """GitHub repository links are accepted, with or without a trailing slash or .git"""
    assert parse_update_source(source) == ('Owner', 'Repo')
    assert get_manifest_url(source) == 'https://github.com/Owner/Repo/releases/latest/download/update.json'


@pytest.mark.parametrize('source', ['', 'http://github.com/Owner/Repo', 'https://example.com/Owner/Repo',
                                    'https://github.com/Owner', 'https://github.com.evil.com/Owner/Repo'])
def test_parse_update_source_refuses(source):
    """Only https links to a repository on github.com are accepted"""
    with pytest.raises(UpdateError):
        parse_update_source(source)


@pytest.mark.parametrize('latest, current, expected', [('1.0.1', '1.0.0', True), ('1.0.0', '1.0.0', False),
                                                       ('1.0.10', '1.0.9', True), ('0.9.9', '1.0.0', False),
                                                       ('1.0.1', '3.1.7.dev5+abc', False)])
def test_is_newer(latest, current, expected):
    """Versions are compared as numbers; a copy run from source code is never offered an update"""
    assert is_newer(latest, current) is expected


@patch('openlp.core.common.updater.get_proxy_settings', return_value=None)
@patch('openlp.core.common.updater.requests.get')
def test_fetch_update_info(mocked_get, mocked_proxy):
    """The latest release's update.json is read from the repository"""
    # GIVEN: A release on GitHub
    mocked_get.return_value = mock_response(text=json.dumps(make_info()))

    # WHEN: Checking for an update
    info = fetch_update_info(SOURCE)

    # THEN: Its details are returned
    assert info['version'] == '1.0.1'
    assert mocked_get.call_args[0][0] == 'https://github.com/Owner/Repo/releases/latest/download/update.json'


@pytest.mark.parametrize('changes', [{'url': 'https://example.com/OpenLPUG-Setup-1.0.1.exe'},
                                     {'url': 'https://github.com/Other/Repo/releases/download/v1/Setup.exe'},
                                     {'name': '../../Setup.exe'}, {'name': 'Setup.msi'}, {'size': 0},
                                     {'sha256': 'not a hash'}])
@patch('openlp.core.common.updater.get_proxy_settings', return_value=None)
@patch('openlp.core.common.updater.requests.get')
def test_fetch_update_info_refuses_untrusted(mocked_get, mocked_proxy, changes):
    """An installer from anywhere but the repository's releases, or without a proper size and hash, is refused"""
    # GIVEN: A release whose installer details cannot be trusted
    mocked_get.return_value = mock_response(text=json.dumps(make_info(**changes)))

    # WHEN / THEN: Checking for an update fails
    with pytest.raises(UpdateError):
        fetch_update_info(SOURCE)


@pytest.mark.parametrize('response', [mock_response(status_code=404), mock_response(text='not json')])
@patch('openlp.core.common.updater.get_proxy_settings', return_value=None)
@patch('openlp.core.common.updater.requests.get')
def test_fetch_update_info_fails(mocked_get, mocked_proxy, response):
    """No release, or a broken update.json, is reported to the user"""
    mocked_get.return_value = response
    with pytest.raises(UpdateError):
        fetch_update_info(SOURCE)


@patch('openlp.core.common.updater.get_proxy_settings', return_value=None)
@patch('openlp.core.common.updater.requests.get')
def test_download_installer(mocked_get, mocked_proxy, tmp_path: Path):
    """The installer is downloaded, with progress, and kept when its size and SHA-256 match"""
    # GIVEN: The installer on GitHub
    mocked_get.return_value = mock_response(chunks=[INSTALLER[:5], INSTALLER[5:]])
    progress = MagicMock()
    file_path = tmp_path / 'update' / 'OpenLPUG-Setup-1.0.1.exe'

    # WHEN: It is downloaded
    result = download_installer(make_info(), file_path, progress)

    # THEN: It is saved, and the progress was reported
    assert result is True
    assert file_path.read_bytes() == INSTALLER
    assert progress.call_args_list[-1][0][0] == len(INSTALLER)


@pytest.mark.parametrize('chunks', [[b'tampered bytes!'], [INSTALLER[:5]], [INSTALLER, b'more']])
@patch('openlp.core.common.updater.get_proxy_settings', return_value=None)
@patch('openlp.core.common.updater.requests.get')
def test_download_installer_mismatch(mocked_get, mocked_proxy, chunks, tmp_path: Path):
    """An installer that does not match update.json is deleted, never run"""
    # GIVEN: A download that is different from the installer described
    mocked_get.return_value = mock_response(chunks=chunks)
    file_path = tmp_path / 'OpenLPUG-Setup-1.0.1.exe'

    # WHEN / THEN: The download fails and nothing is left behind
    with pytest.raises(UpdateError):
        download_installer(make_info(), file_path)
    assert not file_path.exists()


@patch('openlp.core.common.updater.get_proxy_settings', return_value=None)
@patch('openlp.core.common.updater.requests.get')
def test_download_installer_cancelled(mocked_get, mocked_proxy, tmp_path: Path):
    """A cancelled download is deleted"""
    # GIVEN: A download the user cancels
    mocked_get.return_value = mock_response(chunks=[INSTALLER[:5], INSTALLER[5:]])
    file_path = tmp_path / 'OpenLPUG-Setup-1.0.1.exe'

    # WHEN: It is downloaded
    result = download_installer(make_info(), file_path, is_cancelled=lambda: True)

    # THEN: It stops and nothing is left behind
    assert result is False
    assert not file_path.exists()
