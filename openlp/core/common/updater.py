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
Updates Keystone Edition from the releases of a GitHub repository.

Each release holds the Windows installer and update.json, which describes it::

    {"version": "1.0.1", "released": "2026-11-03", "notes": "What's new",
     "installer": {"name": "OpenLPUG-Setup-1.0.1.exe", "url": "https://github.com/.../OpenLPUG-Setup-1.0.1.exe",
                   "size": 103464969, "sha256": "b664..."}}

The latest release's update.json is always at https://github.com/<owner>/<repo>/releases/latest/download/update.json.
Only files from that repository on github.com are downloaded, and the installer is only run if its size and SHA-256
match update.json.
"""
import hashlib
import json
import logging
import re
import subprocess
import sys
from datetime import date

import requests
from PyQt5 import QtCore

from openlp.core.common.httputils import get_proxy_settings
from openlp.core.common.platform import is_win
from openlp.core.common.registry import Registry
from openlp.core.threading import ThreadWorker, run_thread
from openlp.core.version import get_version


log = logging.getLogger(__name__)

DEFAULT_UPDATE_SOURCE = 'https://github.com/Mowerman778/OpenLPKeystoneEd'
CONNECTION_TIMEOUT = 30
CHUNK_SIZE = 256 * 1024
REPOSITORY_PATTERN = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$')
VERSION_PATTERN = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')
SHA256_PATTERN = re.compile(r'^[0-9a-f]{64}$')


class UpdateError(Exception):
    """
    Checking for, or downloading, an update failed. The message is shown to the user.
    """


def parse_update_source(source):
    """
    :param str source: The link to the GitHub repository the updates come from
    :return: The repository's owner and name
    :rtype: tuple[str, str]
    """
    match = REPOSITORY_PATTERN.match((source or '').strip())
    if not match:
        raise UpdateError('The update source must be a GitHub repository link, like {link}'.format(
            link=DEFAULT_UPDATE_SOURCE))
    return match.group(1), match.group(2)


def get_manifest_url(source):
    """
    :param str source: The link to the GitHub repository the updates come from
    :return: The address of the latest release's update.json
    """
    owner, repo = parse_update_source(source)
    return 'https://github.com/{owner}/{repo}/releases/latest/download/update.json'.format(owner=owner, repo=repo)


def parse_version(text):
    """
    :param str text: A version such as 1.0.2
    :return: The version as numbers, to compare
    :rtype: tuple[int, int, int]
    """
    match = VERSION_PATTERN.match(str(text).strip())
    if not match:
        raise UpdateError('"{text}" is not a version number'.format(text=text))
    return tuple(int(part) for part in match.groups())


def is_newer(latest_version, current_version):
    """
    :return: True if the latest version is newer than the one running
    """
    try:
        current = parse_version(current_version)
    except UpdateError:
        # Running from source code, whose version is not a release's
        return False
    return parse_version(latest_version) > current


def get_current_version():
    """
    :return: The version of Keystone running, as published in its release
    """
    return get_version()['version']


def can_install_updates():
    """
    :return: True for the installed Keystone on Windows. Running from source code, updates come from git instead.
    """
    return is_win() and bool(getattr(sys, 'frozen', False))


def fetch_update_info(source):
    """
    Download and check the latest release's update.json.

    :param str source: The link to the GitHub repository the updates come from
    :return: The release's details
    :rtype: dict
    """
    owner, repo = parse_update_source(source)
    try:
        response = requests.get(get_manifest_url(source), proxies=get_proxy_settings(), timeout=CONNECTION_TIMEOUT)
    except OSError:
        log.exception('Unable to download update.json')
        raise UpdateError('Could not connect to GitHub. Check the internet connection.')
    if response.status_code == 404:
        raise UpdateError('No release with an update was found at {source}'.format(source=source))
    if response.status_code != 200:
        raise UpdateError('GitHub answered with error {code}. Try again later.'.format(code=response.status_code))
    try:
        info = json.loads(response.text)
        installer = info['installer']
        parse_version(info['version'])
        url_prefix = 'https://github.com/{owner}/{repo}/releases/download/'.format(owner=owner, repo=repo)
        is_valid = (str(installer['url']).startswith(url_prefix) and str(installer['name']).lower().endswith('.exe')
                    and '/' not in installer['name'] and '\\' not in installer['name']
                    and isinstance(installer['size'], int) and installer['size'] > 0
                    and SHA256_PATTERN.match(str(installer['sha256'])))
    except (ValueError, KeyError, TypeError, UpdateError):
        log.exception('update.json is not valid')
        is_valid = False
    if not is_valid:
        raise UpdateError('The update description from GitHub is not valid, so the update cannot be trusted.')
    info.setdefault('notes', '')
    return info


def download_installer(info, file_path, progress=None, is_cancelled=None):
    """
    Download the release's installer, and check its size and SHA-256 against update.json.

    :param dict info: The release's details, from :func:`fetch_update_info`
    :param Path file_path: Where to save the installer
    :param progress: Called with the number of bytes downloaded so far
    :param is_cancelled: Called to check whether to stop
    :return: True if downloaded and checked, False if cancelled
    """
    installer = info['installer']
    file_path.parent.mkdir(parents=True, exist_ok=True)
    hasher = hashlib.sha256()
    downloaded = 0
    try:
        with requests.get(installer['url'], proxies=get_proxy_settings(), timeout=CONNECTION_TIMEOUT,
                          stream=True) as response, file_path.open('wb') as installer_file:
            if response.status_code != 200:
                raise UpdateError('GitHub answered with error {code}. Try again later.'.format(
                    code=response.status_code))
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if is_cancelled and is_cancelled():
                    break
                installer_file.write(chunk)
                hasher.update(chunk)
                downloaded += len(chunk)
                if downloaded > installer['size']:
                    break
                if progress:
                    progress(downloaded)
    except OSError:
        log.exception('Unable to download the installer')
        file_path.unlink(missing_ok=True)
        raise UpdateError('The download failed. Check the internet connection and try again.')
    except UpdateError:
        file_path.unlink(missing_ok=True)
        raise
    if is_cancelled and is_cancelled():
        file_path.unlink(missing_ok=True)
        return False
    if downloaded != installer['size'] or hasher.hexdigest() != installer['sha256']:
        log.error('Installer check failed: {size} bytes, sha256 {sha}'.format(size=downloaded, sha=hasher.hexdigest()))
        file_path.unlink(missing_ok=True)
        raise UpdateError('The downloaded installer does not match the update description, so it was deleted. '
                          'Try again.')
    return True


def start_installer(file_path):
    """
    Run the installer without its wizard. It replaces Keystone once Keystone has closed, then starts it again.

    :param Path file_path: The checked installer
    """
    log.info('Starting the installer {path}'.format(path=file_path))
    creation_flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if is_win() else 0
    subprocess.Popen([str(file_path), '/SILENT', '/NORESTART'], close_fds=True, creationflags=creation_flags)


class UpdateCheckWorker(ThreadWorker):
    """
    Checks for an update without holding up the user interface
    """
    checked = QtCore.pyqtSignal(dict)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, source):
        super().__init__()
        self.source = source

    def start(self):
        try:
            self.checked.emit(fetch_update_info(self.source))
        except UpdateError as error:
            self.failed.emit(str(error))
        finally:
            self.quit.emit()


class UpdateDownloadWorker(ThreadWorker):
    """
    Downloads and checks the installer without holding up the user interface
    """
    progress = QtCore.pyqtSignal(int)
    downloaded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal()

    def __init__(self, info, file_path):
        super().__init__()
        self.info = info
        self.file_path = file_path
        self.is_cancelled = False

    def start(self):
        try:
            if download_installer(self.info, self.file_path, self.progress.emit, lambda: self.is_cancelled):
                self.downloaded.emit(self.file_path)
            else:
                self.cancelled.emit()
        except UpdateError as error:
            self.failed.emit(str(error))
        finally:
            self.quit.emit()

    @QtCore.pyqtSlot()
    def cancel(self):
        self.is_cancelled = True


def check_for_updates_on_startup(main_window):
    """
    Once a day, if the user wants it, check for an update in the background and tell the user if there is one

    :param MainWindow main_window: The main window, whose on_update_checked is given the latest release's details
    """
    settings = Registry().get('settings')
    if not settings.value('core/update check') or settings.value('core/last version test') >= today_text():
        return
    worker = UpdateCheckWorker(settings.value('core/update source'))
    # A method of the main window, so it runs in the user interface's thread
    worker.checked.connect(main_window.on_update_checked)
    run_thread(worker, 'update_check_startup')


def today_text():
    """
    :return: Today's date, as stored in the 'core/last version test' setting
    """
    return date.today().strftime('%Y-%m-%d')
