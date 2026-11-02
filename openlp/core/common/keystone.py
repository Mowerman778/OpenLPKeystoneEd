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
The :mod:`~openlp.core.common.keystone` module holds the version and change history of Keystone's OpenLP Custom.

Versioning: MAJOR.MINOR.PATCH. Bump PATCH for fixes, MINOR for new features, MAJOR for big changes. When releasing,
change KEYSTONE_VERSION and add an entry to the top of VERSION_HISTORY.
"""

KEYSTONE_NAME = "Keystone's OpenLP Custom"
KEYSTONE_VERSION = '1.0.0'
OPENLP_BASE_VERSION = '3.1.7'

# Newest first: (version, date, [changes])
VERSION_HISTORY = [
    ('1.0.0', '2026-11-03', [
        'Help > User Manual (F1): a short guide to Keystone, its shortcuts and handy tips',
        'Help > Updates: install new versions of Keystone from the internet, and check once a day at start-up',
        'Installs next to a normal OpenLP with its own songs, Bibles and settings, and offers to copy them from '
        'OpenLP the first time',
        'Presentations: LibreOffice is more reliable on Windows, and restarts itself if it closes or crashes',
        'Video Trigger Manager: up to ten video clips on a presentation slide, played by clicking their boxes in Live',
        'A warning when a presentation has videos that LibreOffice may not play well',
        'Theme Manager: drag and resize the main text and footer boxes, and set fonts and backgrounds',
        'View > Hide Projector Window (Ctrl+F12) when it covers the Live panel or other windows',
        'Long footer lines, such as copyright, wrap onto the next line instead of running off the screen',
        'Screen layouts: "1 Monitor Default", "2 Monitor Default" and your own named layouts (View > Layout)',
        'Layout Setup Mode: unlock panels to move them, including onto a second monitor',
        'Preview and Live are now movable panels',
        'Library buttons under the menu: one click shows just that library',
        'SongSelect: search box, opens results in your browser, downloaded songs import automatically',
        'Songs: optional credits slide at the end of each song',
        'Media: audio delay (lip sync) setting',
        'Splash screen shows the whole logo, centred',
        'Help menu: Version History, Create Debug Report and Debug Logging',
        'View > Simulated Projector Mode: no projector connected? The live output goes to a movable window, laid '
        'out exactly as on an HD (1920x1080) projector',
        'Layout Setup Mode: put the Preview and Live slide lists above or to the right of the picture',
    ]),
]


def version_label():
    """
    The version line shown to users, e.g. in the About box
    """
    return "{name}: Ver. : {version}".format(name=KEYSTONE_NAME, version=KEYSTONE_VERSION)


def version_history_html():
    """
    The version history as HTML for the Version History window
    """
    html = '<h2>{name}</h2><p>Version {version}, based on OpenLP {base}</p>'.format(
        name=KEYSTONE_NAME, version=KEYSTONE_VERSION, base=OPENLP_BASE_VERSION)
    for version, date, changes in VERSION_HISTORY:
        html += '<h3>{version} <span style="font-weight: normal; color: #666;">({date})</span></h3><ul>'.format(
            version=version, date=date)
        html += ''.join('<li>{change}</li>'.format(change=change) for change in changes)
        html += '</ul>'
    return html
