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
The :mod:`~openlp.core.ui.debugreport` module builds a debug report: one zip file with the logs, system details and
settings (with passwords and other secrets removed), for sending to whoever looks after the software.
"""
import logging
import platform
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from PyQt5 import QtCore, QtGui

from openlp.core.common.applocation import AppLocation
from openlp.core.common.keystone import KEYSTONE_NAME, KEYSTONE_VERSION, OPENLP_BASE_VERSION
from openlp.core.common.registry import Registry

log = logging.getLogger(__name__)

# Settings whose key contains any of these are left out of the report
SECRET_KEY_PARTS = ('password', 'secret', 'username', 'api_key', 'apikey', 'token', 'application_id', 'pin')
LOG_FILES = ('openlp.log', 'error.log')


def is_secret_setting(key):
    """
    Whether a setting might hold a password or other private detail
    """
    lower_key = key.lower()
    return any(part in lower_key for part in SECRET_KEY_PARTS)


def get_vlc_version():
    try:
        from openlp.core.ui.media.vlcplayer import get_vlc
        vlc = get_vlc()
        return vlc.libvlc_get_version().decode() if vlc else 'not available'
    except Exception:
        return 'not available'


def system_info():
    """
    The details that help when tracking down a problem: versions, Windows, screens
    """
    lines = [
        '{name} {version} (based on OpenLP {base})'.format(name=KEYSTONE_NAME, version=KEYSTONE_VERSION,
                                                           base=OPENLP_BASE_VERSION),
        'Report created: {now}'.format(now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        'Operating system: {os} ({machine})'.format(os=platform.platform(), machine=platform.machine()),
        'Python: {version}'.format(version=sys.version.replace('\n', ' ')),
        'Qt: {qt}  PyQt: {pyqt}'.format(qt=QtCore.QT_VERSION_STR, pyqt=QtCore.PYQT_VERSION_STR),
        'VLC: {vlc}'.format(vlc=get_vlc_version()),
        '',
        'Screens:',
    ]
    primary = QtGui.QGuiApplication.primaryScreen()
    for number, screen in enumerate(QtGui.QGuiApplication.screens()):
        geometry = screen.geometry()
        lines.append('  {number}: {name} {width}x{height} at ({x}, {y}), scale {scale}{primary}'.format(
            number=number, name=screen.name(), width=geometry.width(), height=geometry.height(), x=geometry.x(),
            y=geometry.y(), scale=screen.devicePixelRatio(), primary=' (primary)' if screen is primary else ''))
    return '\n'.join(lines) + '\n'


def settings_text(settings):
    """
    All settings as "key = value" lines, leaving out secrets and big binary values (window layouts)
    """
    lines = []
    for key in sorted(settings.allKeys()):
        if is_secret_setting(key):
            lines.append('{key} = <removed>'.format(key=key))
            continue
        value = QtCore.QSettings.value(settings, key)
        if isinstance(value, (QtCore.QByteArray, bytes)):
            value = '<binary, {size} bytes>'.format(size=len(value))
        lines.append('{key} = {value}'.format(key=key, value=value))
    return '\n'.join(lines) + '\n'


def create_debug_report(folder):
    """
    Write the debug report zip into ``folder``

    :param pathlib.Path folder: Where to save the report
    :return: The path of the zip file
    :rtype: pathlib.Path
    """
    report_path = Path(folder) / 'OpenLP-debug-report-{stamp}.zip'.format(
        stamp=datetime.now().strftime('%Y%m%d-%H%M%S'))
    log_folder = AppLocation.get_directory(AppLocation.CacheDir)
    # Make sure everything logged so far is in the file
    for handler in logging.getLogger().handlers:
        handler.flush()
    with zipfile.ZipFile(report_path, 'w', zipfile.ZIP_DEFLATED) as report:
        report.writestr('system-info.txt', system_info())
        report.writestr('settings.txt', settings_text(Registry().get('settings')))
        for log_name in LOG_FILES:
            log_path = log_folder / log_name
            if log_path.is_file():
                report.write(log_path, log_name)
    log.info('Debug report saved to {path}'.format(path=report_path))
    return report_path
