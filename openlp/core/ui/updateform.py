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
The Help > Updates window: checks the update source for a newer version, then downloads, checks and installs it.
"""
import logging
from pathlib import Path
from tempfile import gettempdir

from PyQt5 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.updater import UpdateCheckWorker, UpdateDownloadWorker, can_install_updates, \
    get_current_version, is_newer, start_installer, today_text
from openlp.core.threading import is_thread_finished, run_thread


log = logging.getLogger(__name__)

CHECK_THREAD = 'update_check_manual'
DOWNLOAD_THREAD = 'update_download'


class UpdateForm(QtWidgets.QDialog, RegistryProperties):
    """
    Help > Updates
    """
    cancel_download = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint |
                         QtCore.Qt.WindowCloseButtonHint)
        self.info = None
        self.installer_path = None
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName('UpdateForm')
        self.setWindowTitle(translate('OpenLP.UpdateForm', 'Updates'))
        self.resize(560, 440)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.source_edit = QtWidgets.QLineEdit(self)
        self.source_edit.setToolTip(translate('OpenLP.UpdateForm', 'The GitHub repository whose releases hold the '
                                              'updates'))
        form.addRow(translate('OpenLP.UpdateForm', 'Update source:'), self.source_edit)
        self.current_label = QtWidgets.QLabel(self)
        form.addRow(translate('OpenLP.UpdateForm', 'This version:'), self.current_label)
        self.latest_label = QtWidgets.QLabel(translate('OpenLP.UpdateForm', 'Not checked yet'), self)
        form.addRow(translate('OpenLP.UpdateForm', 'Latest version:'), self.latest_label)
        layout.addLayout(form)
        self.startup_check = QtWidgets.QCheckBox(translate('OpenLP.UpdateForm', 'Check for updates once a day, '
                                                           'when Keystone starts'), self)
        layout.addWidget(self.startup_check)
        layout.addWidget(QtWidgets.QLabel(translate('OpenLP.UpdateForm', "What's new:"), self))
        self.notes_edit = QtWidgets.QPlainTextEdit(self)
        self.notes_edit.setReadOnly(True)
        layout.addWidget(self.notes_edit)
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        self.status_label = QtWidgets.QLabel(self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        buttons = QtWidgets.QHBoxLayout()
        self.check_button = QtWidgets.QPushButton(translate('OpenLP.UpdateForm', '&Check Now'), self)
        self.check_button.clicked.connect(self.on_check_clicked)
        buttons.addWidget(self.check_button)
        self.install_button = QtWidgets.QPushButton(translate('OpenLP.UpdateForm', '&Download and Install'), self)
        self.install_button.clicked.connect(self.on_install_clicked)
        buttons.addWidget(self.install_button)
        self.cancel_button = QtWidgets.QPushButton(translate('OpenLP.UpdateForm', 'Cancel &Download'), self)
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        buttons.addWidget(self.cancel_button)
        buttons.addStretch()
        self.close_button = QtWidgets.QPushButton(translate('OpenLP.UpdateForm', 'C&lose'), self)
        self.close_button.clicked.connect(self.close)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

    def exec(self, info=None):
        """
        Show the window. Given a release found at startup, show it straight away, otherwise check for one.

        :param dict | None info: The latest release's details, if already known
        """
        self.source_edit.setText(self.settings.value('core/update source'))
        self.startup_check.setChecked(bool(self.settings.value('core/update check')))
        self.current_label.setText(get_current_version())
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.install_button.setEnabled(False)
        self.status_label.clear()
        if info:
            self.on_checked(info)
        else:
            QtCore.QTimer.singleShot(0, self.on_check_clicked)
        return super().exec()

    def save_settings(self):
        self.settings.setValue('core/update source', self.source_edit.text().strip())
        self.settings.setValue('core/update check', self.startup_check.isChecked())

    def done(self, result):
        """
        Keep the settings when the window is closed, but not while a download is running
        """
        if not is_thread_finished(DOWNLOAD_THREAD):
            self.status_label.setText(translate('OpenLP.UpdateForm', 'Cancel the download before closing.'))
            return
        self.save_settings()
        super().done(result)

    def on_check_clicked(self):
        if not is_thread_finished(CHECK_THREAD):
            return
        self.save_settings()
        self.info = None
        self.install_button.setEnabled(False)
        self.check_button.setEnabled(False)
        self.latest_label.setText(translate('OpenLP.UpdateForm', 'Checking...'))
        self.notes_edit.clear()
        self.status_label.clear()
        worker = UpdateCheckWorker(self.source_edit.text().strip())
        worker.checked.connect(self.on_checked)
        worker.failed.connect(self.on_check_failed)
        run_thread(worker, CHECK_THREAD)

    def on_checked(self, info):
        """
        Show the latest release, and let it be installed if it is newer
        """
        self.settings.setValue('core/last version test', today_text())
        self.info = info
        self.check_button.setEnabled(True)
        self.install_button.setEnabled(False)
        self.latest_label.setText(info['version'])
        self.notes_edit.setPlainText(info['notes'] or translate('OpenLP.UpdateForm', 'No notes for this version.'))
        if not is_newer(info['version'], get_current_version()):
            self.status_label.setText(translate('OpenLP.UpdateForm', 'Keystone is up to date.'))
        elif not can_install_updates():
            self.status_label.setText(translate('OpenLP.UpdateForm', 'A newer version is available, but this copy '
                                                'runs from source code, so it is updated with git instead.'))
        else:
            size = info['installer']['size'] / (1024 * 1024)
            self.status_label.setText(translate('OpenLP.UpdateForm', 'Version {version} is available ({size:.0f} '
                                                'MB).').format(version=info['version'], size=size))
            self.install_button.setEnabled(True)

    def on_check_failed(self, message):
        self.check_button.setEnabled(True)
        self.latest_label.setText(translate('OpenLP.UpdateForm', 'Unknown'))
        self.status_label.setText(message)

    def on_install_clicked(self):
        if not self.info or not is_thread_finished(DOWNLOAD_THREAD):
            return
        if self.live_controller.service_item is not None:
            answer = QtWidgets.QMessageBox.question(
                self, translate('OpenLP.UpdateForm', 'Something Is Live'),
                translate('OpenLP.UpdateForm', 'Installing closes Keystone, which stops what is live. '
                          'Download the update now anyway?'))
            if answer != QtWidgets.QMessageBox.Yes:
                return
        installer = self.info['installer']
        self.installer_path = Path(gettempdir()) / 'openlpkeystone-update' / installer['name']
        self.progress_bar.setRange(0, installer['size'])
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.install_button.setEnabled(False)
        self.check_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.status_label.setText(translate('OpenLP.UpdateForm', 'Downloading...'))
        worker = UpdateDownloadWorker(self.info, self.installer_path)
        worker.progress.connect(self.progress_bar.setValue)
        worker.downloaded.connect(self.on_downloaded)
        worker.failed.connect(self.on_download_failed)
        worker.cancelled.connect(self.on_download_cancelled)
        self.cancel_download.connect(worker.cancel, QtCore.Qt.DirectConnection)
        run_thread(worker, DOWNLOAD_THREAD)

    def on_cancel_clicked(self):
        self.cancel_download.emit()

    def _download_ended(self, message):
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.check_button.setEnabled(True)
        self.install_button.setEnabled(True)
        self.status_label.setText(message)
        try:
            self.cancel_download.disconnect()
        except TypeError:
            pass

    def on_download_failed(self, message):
        self._download_ended(message)

    def on_download_cancelled(self):
        self._download_ended(translate('OpenLP.UpdateForm', 'Download cancelled.'))

    def on_downloaded(self, file_path):
        """
        The installer is downloaded and checked: close Keystone, asking to save the service, and run it
        """
        self._download_ended(translate('OpenLP.UpdateForm', 'Downloaded and checked.'))
        answer = QtWidgets.QMessageBox.question(
            self, translate('OpenLP.UpdateForm', 'Install Update'),
            translate('OpenLP.UpdateForm', 'Version {version} is downloaded and checked.\n\n'
                      'Keystone will now close (you will be asked to save the service if it has changes). '
                      'Windows may ask to allow the installer to make changes: click Yes. '
                      'Keystone starts again when the update is installed.').format(version=self.info['version']),
            QtWidgets.QMessageBox.StandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel),
            QtWidgets.QMessageBox.Ok)
        if answer != QtWidgets.QMessageBox.Ok:
            self.status_label.setText(translate('OpenLP.UpdateForm', 'Click Download and Install when you are ready.'))
            return
        application = QtWidgets.QApplication.instance()

        def run_installer():
            start_installer(file_path)

        # Run once Keystone has closed, so the installer can replace its files
        application.aboutToQuit.connect(run_installer)
        self.done(QtWidgets.QDialog.Accepted)
        if not self.main_window.close():
            # The user chose not to close after all, e.g. to save the service first
            application.aboutToQuit.disconnect(run_installer)
