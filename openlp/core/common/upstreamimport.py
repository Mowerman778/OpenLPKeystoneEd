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
Copies the songs, Bibles, themes and settings of a normal OpenLP installed on the same computer.

Keystone Edition keeps its own data and settings, so it can be installed next to a normal OpenLP without changing it.
The first time it starts it offers to copy the normal OpenLP's data, which is only ever read.
"""
import logging
import shutil

from PyQt5 import QtCore

from openlp.core.common.applocation import AppLocation
from openlp.core.common.settings import Settings


log = logging.getLogger(__name__)

UPSTREAM_ORGANIZATION = 'OpenLP'
UPSTREAM_APPLICATION = 'OpenLP'
# Not copied: the data path points at the normal OpenLP's data, and the version is OpenLP's, not Keystone's, so
# copying it would make Keystone think it had been downgraded and start afresh
SKIPPED_KEYS = ('advanced/data path', 'advanced/is portable', 'core/application version')


def get_upstream_settings():
    """
    :return: The normal OpenLP's settings, or None if it has not been set up on this computer
    :rtype: QtCore.QSettings | None
    """
    settings = QtCore.QSettings(QtCore.QSettings.NativeFormat, QtCore.QSettings.UserScope, UPSTREAM_ORGANIZATION,
                                UPSTREAM_APPLICATION)
    return settings if settings.contains('core/has run wizard') else None


def get_upstream_data_path():
    """
    :return: Where the normal OpenLP keeps its songs, Bibles, themes and so on
    :rtype: Path
    """
    settings = Settings(QtCore.QSettings.NativeFormat, QtCore.QSettings.UserScope, UPSTREAM_ORGANIZATION,
                        UPSTREAM_APPLICATION)
    custom_path = settings.value('advanced/data path')
    return custom_path if custom_path else AppLocation.get_upstream_data_directory()


def should_offer_import(settings):
    """
    :param Settings settings: Keystone's settings
    :return: True on Keystone's first start, when a normal OpenLP has data to copy
    """
    return not settings.contains('core/has run wizard') and get_upstream_settings() is not None


def import_upstream(settings, data_path):
    """
    Copy the normal OpenLP's settings and data folder. The normal OpenLP's are only read.

    :param Settings settings: Keystone's settings, copied into
    :param Path data_path: Keystone's data folder, copied into
    :return: True if everything was copied
    """
    upstream_settings = get_upstream_settings()
    if upstream_settings is None:
        return False
    upstream_data_path = get_upstream_data_path()
    for key in upstream_settings.allKeys():
        if key not in SKIPPED_KEYS:
            # Copied as stored, without the conversions Settings does when reading and writing values
            QtCore.QSettings.setValue(settings, key, upstream_settings.value(key))
    settings.sync()
    if not upstream_data_path.is_dir():
        log.warning(f'OpenLP data folder {upstream_data_path} not found, only the settings were copied')
        return True
    try:
        # The normal OpenLP's lock file would stop Keystone from starting while the normal OpenLP is open
        shutil.copytree(upstream_data_path, data_path, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('openlp-data.lock'))
    except (OSError, shutil.Error):
        log.exception(f'Failed to copy {upstream_data_path} to {data_path}')
        return False
    log.info(f'Copied OpenLP data from {upstream_data_path} to {data_path}')
    return True
