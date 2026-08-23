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

import logging
import re

from openlp.plugins.media.forms.streamselectordialog import Ui_StreamSelector
from openlp.core.ui.media import parse_stream_path
from openlp.plugins.media.forms import StreamSelectorFormBase

log = logging.getLogger(__name__)


class StreamSelectorForm(StreamSelectorFormBase, Ui_StreamSelector):
    """
    Class to manage the clip selection
    """
    log.info('{name} StreamSelectorForm loaded'.format(name=__name__))

    def __init__(self, parent, callback, theme_stream=False):
        """
        Constructor
        """
        super(StreamSelectorForm, self).__init__(parent, callback, theme_stream)
        self.type = 'devicestream'
        self.setup_ui(self)
        # setup callbacks
        for i in range(self.stacked_modes_layout.count()):
            self.stacked_modes_layout.widget(i).set_callback(self.update_mrl_options)
        self.stacked_modes_layout.currentWidget().update_mrl()

    def on_capture_mode_combo_box(self):
        self.stacked_modes_layout.setCurrentIndex(self.capture_mode_combo_box.currentIndex())
        self.stacked_modes_layout.currentWidget().update_mrl()

    def set_mrl(self, device_stream_str):
        """
        Setup the stream widgets based on the saved devicestream. This is best effort as the string is
        editable for the user.
        """
        (name, mrl, options) = parse_stream_path(device_stream_str)
        for i in range(self.stacked_modes_layout.count()):
            if self.stacked_modes_layout.widget(i).has_support_for_mrl(mrl, options):
                self.stacked_modes_layout.setCurrentIndex(i)
                self.capture_mode_combo_box.setCurrentIndex(i)
                self.stacked_modes_layout.widget(i).set_mrl(mrl, options)
                break
        cache = re.search(r'live-caching=(\d+)', options)
        if cache:
            self.more_options_group.caching.setValue(int(cache.group(1)))
        self.more_options_group.mrl_lineedit.setText(mrl)
        self.more_options_group.vlc_options_lineedit.setText(options)
