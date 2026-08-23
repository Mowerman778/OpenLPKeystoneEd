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
The :mod:`~openlp.plugins.planningcenter.lib.planningcentertab` module contains
the settings tab for the PlanningCenter plugin
"""
from PyQt5 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.lib.settingstab import SettingsTab
from openlp.plugins.planningcenter.lib.planningcenter_api import PlanningCenterAPI


class PlanningCenterTab(SettingsTab):
    """
    PlanningCenterTab is the alerts settings tab in the settings dialog.
    """
    def setup_ui(self):
        self.setObjectName('PlanningCenterTab')
        self.tab_layout = QtWidgets.QVBoxLayout(self)
        self.tab_layout.setObjectName('tab_layout')
        self.tab_layout.setAlignment(QtCore.Qt.AlignTop)
        self.auth_group_box = QtWidgets.QGroupBox(self)
        self.tab_layout.addWidget(self.auth_group_box)
        self.auth_layout = QtWidgets.QFormLayout(self.auth_group_box)
        self.auth_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        # notice
        self.notice_label = QtWidgets.QLabel(self.auth_group_box)
        self.notice_label.setWordWrap(True)
        self.auth_layout.addRow(self.notice_label)
        # instructions
        self.instructions_label = QtWidgets.QLabel(self.auth_group_box)
        self.instructions_label.setWordWrap(True)
        self.auth_layout.addRow(self.instructions_label)
        # application_id
        self.application_id_label = QtWidgets.QLabel(self.auth_group_box)
        self.application_id_line_edit = QtWidgets.QLineEdit(self.auth_group_box)
        self.application_id_line_edit.setMaxLength(64)
        self.auth_layout.addRow(self.application_id_label, self.application_id_line_edit)
        # secret
        self.secret_label = QtWidgets.QLabel(self.auth_group_box)
        self.secret_line_edit = QtWidgets.QLineEdit(self.auth_group_box)
        self.secret_line_edit.setMaxLength(64)
        self.auth_layout.addRow(self.secret_label, self.secret_line_edit)
        # Buttons
        self.button_layout = QtWidgets.QDialogButtonBox(self.auth_group_box)
        self.test_credentials_button = QtWidgets.QPushButton(self.auth_group_box)
        self.button_layout.addButton(self.test_credentials_button, QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        self.auth_layout.addRow(self.button_layout)
        # signals
        self.test_credentials_button.clicked.connect(self.on_test_credentials_button_clicked)

    def retranslate_ui(self):
        self.auth_group_box.setTitle(translate('PlanningCenterPlugin.PlanningCenterTab', 'Authentication Settings'))
        self.application_id_label.setText(translate('PlanningCenterPlugin.PlanningCenterTab', 'Application ID:'))
        self.secret_label.setText(translate('PlanningCenterPlugin.PlanningCenterTab', 'Secret:'))

        self.notice_label.setText(
            translate('PlanningCenterPlugin.PlanningCenterTab', '<strong>Note:</strong> '
                      'An Internet connection and a Planning Center Online Account are '
                      'required in order to import plans from Planning Center Online.')
        )
        self.instructions_label.setText(
            translate('PlanningCenterPlugin.PlanningCenterTab',
                      """Enter your <b>Planning Center Online</b> <i>Personal Access Token</i> details in the text \
boxes below. Personal Access Tokens are created by doing the following:
<ol>
  <li>Login to your Planning Center Online account at<br>
      <a href=https://api.planningcenteronline.com/oauth/applications>
      https://api.planningcenteronline.com/oauth/applications</a></li>
  <li>Click the "New Personal Access Token" button at the bottom of the screen.</li>
  <li>Enter a description of your use case (eg. "OpenLP Integration")</li>
  <li>Copy and paste the provided Application ID and Secret values below.</li>
</ol>"""))

        self.test_credentials_button.setText(translate('PlanningCenterPlugin.PlanningCenterAuthForm',
                                                       'Test Credentials'))

    def resizeEvent(self, event=None):
        """
        Don't call SettingsTab resize handler because we are not using left/right columns.
        """
        QtWidgets.QWidget.resizeEvent(self, event)

    def load(self):
        """
        Load the settings into the UI.
        """
        self.application_id = self.settings.value('planningcenter/application_id')
        self.secret = self.settings.value('planningcenter/secret')
        self.application_id_line_edit.setText(self.application_id)
        self.secret_line_edit.setText(self.secret)

    def save(self):
        """
        Save the changes on exit of the Settings dialog.
        """
        self.settings.setValue('planningcenter/application_id', self.application_id_line_edit.text())
        self.settings.setValue('planningcenter/secret', self.secret_line_edit.text())

    def on_test_credentials_button_clicked(self):
        """
        Tests if the credentials are valid
        """
        application_id = self.application_id_line_edit.text()
        secret = self.secret_line_edit.text()
        if len(application_id) == 0 or len(secret) == 0:
            QtWidgets.QMessageBox.warning(self, "Authentication Failed",
                                          "Please enter values for both Application ID and Secret",
                                          QtWidgets.QMessageBox.Ok)
            return
        test_auth = PlanningCenterAPI(application_id, secret)
        organization = test_auth.check_credentials()
        if len(organization):
            QtWidgets.QMessageBox.information(self, 'Planning Center Online Authentication Test',
                                              "Authentication successful for organization: {0}".format(organization),
                                              QtWidgets.QMessageBox.Ok)
        else:
            QtWidgets.QMessageBox.warning(self, "Authentication Failed",
                                          "Authentiation Failed",
                                          QtWidgets.QMessageBox.Ok)
