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
The About dialog.
"""
import webbrowser

from PyQt5 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.version import get_version

from .aboutdialog import UiAboutDialog


class AboutForm(QtWidgets.QDialog, UiAboutDialog):
    """
    The About dialog
    """

    def __init__(self, parent):
        """
        Do some initialisation stuff
        """
        super(AboutForm, self).__init__(parent, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint |
                                        QtCore.Qt.WindowCloseButtonHint)
        self._setup()

    def _setup(self):
        """
        Set up the dialog. This method is mocked out in tests.
        """
        self.setup_ui(self)
        self.button_box.buttons()[0].setFocus()
        application_version = get_version()
        about_text = self.about_text_edit.toHtml()
        about_text = about_text.replace('{version}', application_version['version'])
        if application_version['build']:
            build_text = translate('OpenLP.AboutForm', ' build {version}').format(version=application_version['build'])
        else:
            build_text = ''
        about_text = about_text.replace('{revision}', build_text)
        self.about_text_edit.setHtml(about_text)
        self.contribute_button.clicked.connect(self.on_contribute_button_clicked)

    def on_contribute_button_clicked(self):
        """
        Launch a web browser and go to the contribute page on the site.
        """
        webbrowser.open_new('http://openlp.org/contribute')
