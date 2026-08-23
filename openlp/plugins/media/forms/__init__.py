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

import re

from PyQt5 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.lib.ui import critical_error_message_box
from openlp.core.ui.media import parse_stream_path


class StreamSelectorFormBase(QtWidgets.QDialog):
    """
    Class to manage the clip selection
    """

    def __init__(self, parent, callback, theme_stream=False):
        """
        Constructor
        """
        super(StreamSelectorFormBase, self).__init__(parent, QtCore.Qt.WindowSystemMenuHint |
                                                     QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)
        self.callback = callback
        self.theme_stream = theme_stream
        self.setup_base_ui()
        self.type = ''

    def setup_base_ui(self):
        self.setObjectName('stream_selector')
        self.combobox_size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                                          QtWidgets.QSizePolicy.Policy.Fixed)
        self.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                  QtWidgets.QSizePolicy.Policy.MinimumExpanding))
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setObjectName('main_layout')

        self.top_widget = QtWidgets.QWidget(self)
        self.top_widget.setObjectName('top_widget')
        self.top_layout = QtWidgets.QFormLayout(self.top_widget)
        self.top_layout.setObjectName('top_layout')
        # Stream name
        if not self.theme_stream:
            self.stream_name_label = QtWidgets.QLabel(self.top_widget)
            self.stream_name_label.setObjectName('stream_name_label')
            self.stream_name_edit = QtWidgets.QLineEdit(self.top_widget)
            self.stream_name_edit.setObjectName('stream_name_edit')
            self.top_layout.addRow(self.stream_name_label, self.stream_name_edit)

    def exec(self):
        """
        Start dialog
        """
        return QtWidgets.QDialog.exec(self)

    def accept(self):
        """
        Saves the current stream as a clip to the mediamanager
        """
        if not self.theme_stream:
            # Verify that a stream name exists
            if not self.stream_name_edit.text().strip():
                critical_error_message_box(message=translate('MediaPlugin.StreamSelector', 'A Stream name is needed.'))
                return
            stream_name = self.stream_name_edit.text().strip()
        else:
            stream_name = ' '
        # Verify that a MRL exists
        if not self.more_options_group.mrl_lineedit.text().strip():
            critical_error_message_box(message=translate('MediaPlugin.StreamSelector', 'A MRL is needed.'), parent=self)
            return
        stream_string = '{type}:{name}&&{mrl}&&{options}'.format(
            type=self.type, name=stream_name, mrl=self.more_options_group.mrl_lineedit.text().strip(),
            options=self.more_options_group.vlc_options_lineedit.text().strip())
        self.callback(stream_string)
        return QtWidgets.QDialog.accept(self)

    def update_mrl_options(self, mrl, options):
        """
        Callback method used to fill the MRL and Options text fields
        """
        options += ' :live-caching={cache}'.format(cache=self.more_options_group.caching.value())
        self.more_options_group.mrl_lineedit.setText(mrl)
        self.more_options_group.vlc_options_lineedit.setText(options)

    def set_mrl(self, stream_str):
        """
        Setup the stream widgets based on the saved stream string. This is best effort as the string is
        editable for the user.
        """
        (name, mrl, options) = parse_stream_path(stream_str)
        cache = re.search(r'live-caching=(\d+)', options)
        if cache:
            self.more_options_group.caching.setValue(int(cache.group(1)))

        self.more_options_group.mrl_lineedit.setText(mrl)
        self.more_options_group.vlc_options_lineedit.setText(options)


class VLCOptionsWidget(QtWidgets.QGroupBox):
    """
    Groupbox widget for VLC options: caching, mrl and VLC options
    """
    def __init__(self, parent=None):
        """
        Initialise the widget.

        :param QtWidgets.QWidget | None parent: The widgets parent
        """
        super().__init__(parent)
        self.setup_ui()
        self.retranslate_ui()

    def setup_ui(self):
        """
        Create the widget layout and sub widgets
        """
        # Groupbox for VLC options
        self.vlc_options_group_layout = QtWidgets.QFormLayout(self)
        self.vlc_options_group_layout.setObjectName('more_options_group_layout')
        # Caching spinbox
        self.caching_label = QtWidgets.QLabel(self)
        self.caching_label.setObjectName('caching_label')
        self.caching = QtWidgets.QSpinBox(self)
        self.caching.setAlignment(QtCore.Qt.AlignRight)
        self.caching.setSuffix(' ms')
        self.caching.setSingleStep(100)
        self.caching.setMaximum(65535)
        self.caching.setValue(300)
        self.vlc_options_group_layout.addRow(self.caching_label, self.caching)
        # MRL
        self.mrl_label = QtWidgets.QLabel(self)
        self.mrl_label.setObjectName('mrl_label')
        self.mrl_lineedit = QtWidgets.QLineEdit(self)
        self.mrl_lineedit.setObjectName('mrl_lineedit')
        self.vlc_options_group_layout.addRow(self.mrl_label, self.mrl_lineedit)
        # VLC options
        self.vlc_options_label = QtWidgets.QLabel(self)
        self.vlc_options_label.setObjectName('vlc_options_label')
        self.vlc_options_lineedit = QtWidgets.QLineEdit(self)
        self.vlc_options_lineedit.setObjectName('vlc_options_lineedit')
        self.vlc_options_group_layout.addRow(self.vlc_options_label, self.vlc_options_lineedit)

    def retranslate_ui(self):
        self.setTitle(translate('MediaPlugin.StreamSelector', 'More options'))
        self.caching_label.setText(translate('MediaPlugin.StreamSelector', 'Caching'))
        self.mrl_label.setText(translate('MediaPlugin.StreamSelector', 'MRL'))
        self.vlc_options_label.setText(translate('MediaPlugin.StreamSelector', 'VLC options'))
