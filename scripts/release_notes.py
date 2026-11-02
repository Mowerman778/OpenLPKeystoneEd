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
Print a version's changes from the Version History in openlp/core/common/keystone.py, as release notes.

    python scripts/release_notes.py 1.0.1

Test builds (0.x.y) and versions without an entry print nothing. The file is read, not imported, so this needs nothing
installed.
"""
import ast
import sys
from pathlib import Path

KEYSTONE_FILE = Path(__file__).resolve().parent.parent / 'openlp' / 'core' / 'common' / 'keystone.py'


def get_release_notes(version, source=None):
    """
    :param str version: The version, e.g. 1.0.1
    :param str | None source: The text of keystone.py, read from the file if not given
    :return: The version's changes, one "- " line each
    """
    tree = ast.parse(source if source is not None else KEYSTONE_FILE.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(target, 'id', None) == 'VERSION_HISTORY'
                                                for target in node.targets):
            for entry_version, _date, changes in ast.literal_eval(node.value):
                if entry_version == version:
                    return '\n'.join('- ' + change for change in changes)
    return ''


if __name__ == '__main__':
    print(get_release_notes(sys.argv[1]))
