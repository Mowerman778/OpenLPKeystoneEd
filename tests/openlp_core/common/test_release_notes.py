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
Tests for the release notes taken from the Version History when a release is built
"""
import importlib.util
from pathlib import Path

from openlp.core.common.keystone import KEYSTONE_VERSION, VERSION_HISTORY

SCRIPT_PATH = Path(__file__).resolve().parents[3] / 'scripts' / 'release_notes.py'
spec = importlib.util.spec_from_file_location('release_notes', SCRIPT_PATH)
release_notes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_notes)

SOURCE = """
KEYSTONE_VERSION = '1.0.1'
VERSION_HISTORY = [
    ('1.0.1', '2026-12-01', ['Fixed a thing', 'Added another']),
    ('1.0.0', '2026-11-03', ['First release']),
]
"""


def test_get_release_notes():
    """A version's changes become its release notes, one line each"""
    assert release_notes.get_release_notes('1.0.1', SOURCE) == '- Fixed a thing\n- Added another'
    assert release_notes.get_release_notes('1.0.0', SOURCE) == '- First release'


def test_get_release_notes_none():
    """Test builds, and versions without an entry, have no notes"""
    assert release_notes.get_release_notes('0.0.4', SOURCE) == ''


def test_current_version_has_release_notes():
    """The version being released has an entry in the Version History, read the same way the app reads it"""
    expected = '\n'.join('- ' + change for version, _date, changes in VERSION_HISTORY if version == KEYSTONE_VERSION
                         for change in changes)
    assert release_notes.get_release_notes(KEYSTONE_VERSION) == expected != ''
