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

#
# Most of this file is heavily inspired by (and in some cases copied from)
# the VLC open capture GUIs, available in the VLC source tree at:
# * modules/gui/qt/dialogs/open/open_panels.cpp (Linux/Windows)
# * modules/gui/macosx/windows/VLCOpenWindowController.m (Mac)
# Both are licensed under GPL2 or later.
#

import glob
import re
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtMultimedia import QCameraInfo, QAudioDeviceInfo, QAudio

from openlp.core.common.i18n import translate
from openlp.core.common.platform import is_linux, is_macosx, is_win
from openlp.plugins.media.forms import VLCOptionsWidget

# Copied from VLC source code: modules/access/v4l2/v4l2.c
VIDEO_STANDARDS_VLC = [
    '', 'ALL',
    # Pseudo standards
    'PAL', 'PAL_BG', 'PAL_DK',
    'NTSC',
    'SECAM', 'SECAM_DK',
    'MTS', '525_60', '625_50',
    'ATSC',
    # Chroma-agnostic ITU standards (PAL/NTSC or PAL/SECAM)
    'B', 'G', 'H', 'L',
    'GH', 'DK', 'BG', 'MN',
    # Individual standards
    'PAL_B', 'PAL_B1', 'PAL_G', 'PAL_H',
    'PAL_I', 'PAL_D', 'PAL_D1', 'PAL_K',
    'PAL_M', 'PAL_N', 'PAL_Nc', 'PAL_60',
    'NTSC_M', 'NTSC_M_JP', 'NTSC_443', 'NTSC_M_KR',
    'SECAM_B', 'SECAM_D', 'SECAM_G', 'SECAM_H',
    'SECAM_K', 'SECAM_K1', 'SECAM_L', 'SECAM_LC',
    'ATSC_8_VSB', 'ATSC_16_VSB',
]
VIDEO_STANDARDS_USER = [
    'Undefined', 'All',
    'PAL', 'PAL B/G', 'PAL D/K',
    'NTSC',
    'SECAM', 'SECAM D/K',
    'Multichannel television sound (MTS)',
    '525 lines / 60 Hz', '625 lines / 50 Hz',
    'ATSC',
    'PAL/SECAM B', 'PAL/SECAM G', 'PAL/SECAM H', 'PAL/SECAM L',
    'PAL/SECAM G/H', 'PAL/SECAM D/K', 'PAL/SECAM B/G', 'PAL/NTSC M/N',
    'PAL B', 'PAL B1', 'PAL G', 'PAL H',
    'PAL I', 'PAL D', 'PAL D1', 'PAL K',
    'PAL M', 'PAL N', 'PAL N Argentina', 'PAL 60',
    'NTSC M', 'NTSC M Japan', 'NTSC 443', 'NTSC M South Korea',
    'SECAM B', 'SECAM D', 'SECAM G', 'SECAM H',
    'SECAM K', 'SECAM K1', 'SECAM L', 'SECAM L/C',
    'ATSC 8-VSB', 'ATSC 16-VSB',
]
# Copied from VLC source code: modules/gui/qt/dialogs/open/open_panels.cpp
DIGITAL_TV_STANDARDS = [('DVB-T', 'dvb-t'), ('DVB-T2', 'dvb-t2'), ('DVB-C', 'dvb-c'), ('DVB-S', 'dvb-s'),
                        ('DVB-S2', 'dvb-s2'), ('ATSC', 'atsc'), ('Clear QAM', 'cqam')]
DIGITAL_TV_BANDWIDTH = [('Automatic', '0'), ('10 MHz', '10'), ('8 MHz', '8'), ('7 MHz', '7'), ('6 MHz', '6'),
                        ('5 MHz', '5'), ('1.712 MHz', '2')]
DIGITAL_TV_QAM = [('Automatic', 'QAM'), ('256-QAM', '256QAM'), ('128-QAM', '128QAM'), ('64-QAM', '64QAM'),
                  ('32-QAM', '32QAM'), ('16-QAM', '16QAM')]
DIGITAL_TV_PSK = [('QPSK', 'QPSK'), ('DQPSK', 'DQPSK'), ('8-PSK', '8PSK'), ('16-APSK', '16APSK'), ('32-APSK', '32APSK')]


class CaptureModeWidget(QtWidgets.QWidget):
    """
    Simple widget containing a groupbox to hold devices and a groupbox for options
    """
    def __init__(self, parent=None, disable_audio=False):
        super().__init__(parent)
        self.disable_audio = disable_audio
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName('capture_mode_widget')
        self.capture_mode_widget_layout = QtWidgets.QVBoxLayout(self)
        self.capture_mode_widget_layout.setObjectName('capture_mode_widget_layout')
        self.device_group = QtWidgets.QGroupBox(self)
        self.device_group.setObjectName('device_group')
        self.device_group_layout = QtWidgets.QFormLayout(self.device_group)
        self.device_group_layout.setObjectName('device_group_layout')
        self.capture_mode_widget_layout.addWidget(self.device_group)
        self.options_group = QtWidgets.QGroupBox(self)
        self.options_group.setObjectName('options_group')
        self.options_group_layout = QtWidgets.QFormLayout(self.options_group)
        self.options_group_layout.setObjectName('options_group_layout')
        self.capture_mode_widget_layout.addWidget(self.options_group)

    def retranslate_ui(self):
        self.device_group.setTitle(translate('MediaPlugin.StreamSelector', 'Device Selection'))
        self.options_group.setTitle(translate('MediaPlugin.StreamSelector', 'Options'))

    def find_devices(self):
        pass

    def update_mrl(self):
        pass

    def colon_escape(self, s):
        return s.replace(':', '\\:')

    def set_callback(self, callback):
        self.callback = callback

    def has_support_for_mrl(self, mrl, options):
        return False

    def set_mrl(self, main, options):
        pass


class CaptureVideoWidget(CaptureModeWidget):
    """
    Widget inherits groupboxes from CaptureModeWidget and inserts comboboxes for audio and video devices
    """
    def __init__(self, parent=None, disable_audio=False):
        super().__init__(parent, disable_audio)

    def setup_ui(self):
        super().setup_ui()
        # Video devices
        self.video_devices_label = QtWidgets.QLabel(self)
        self.video_devices_label.setObjectName('video_devices_label')
        self.video_devices_combo_box = QtWidgets.QComboBox(self)
        self.video_devices_combo_box.addItems([''])
        self.video_devices_combo_box.setObjectName('video_devices_combo_box')
        if is_linux():
            self.video_devices_combo_box.setEditable(True)
        self.device_group_layout.addRow(self.video_devices_label, self.video_devices_combo_box)
        # Audio devices
        self.audio_devices_label = QtWidgets.QLabel(self)
        self.audio_devices_label.setObjectName('audio_devices_label')
        self.audio_devices_combo_box = QtWidgets.QComboBox(self)
        self.audio_devices_combo_box.addItems([''])
        self.audio_devices_combo_box.setObjectName('audio_devices_combo_box')
        if is_linux():
            self.audio_devices_combo_box.setEditable(True)
        if self.disable_audio:
            self.audio_devices_combo_box.hide()
            self.audio_devices_label.hide()
        self.device_group_layout.addRow(self.audio_devices_label, self.audio_devices_combo_box)
        # connect
        self.video_devices_combo_box.currentIndexChanged.connect(self.update_mrl)
        self.audio_devices_combo_box.currentIndexChanged.connect(self.update_mrl)

    def retranslate_ui(self):
        super().retranslate_ui()
        self.video_devices_label.setText(translate('MediaPlugin.StreamSelector', 'Video device name'))
        self.audio_devices_label.setText(translate('MediaPlugin.StreamSelector', 'Audio device name'))


class CaptureVideoLinuxWidget(CaptureVideoWidget):
    """
    Widget inherits groupboxes from CaptureVideoWidget and inserts widgets for linux
    """
    def __init__(self, parent=None, disable_audio=False):
        super().__init__(parent, disable_audio)

    def setup_ui(self):
        super().setup_ui()
        # Options
        self.video_std_label = QtWidgets.QLabel(self)
        self.video_std_label.setObjectName('video_std_label')
        self.video_std_combobox = QtWidgets.QComboBox(self)
        self.video_std_combobox.setObjectName('video_std_combobox')
        self.video_std_combobox.addItems(VIDEO_STANDARDS_USER)
        self.options_group_layout.addRow(self.video_std_label, self.video_std_combobox)
        # connect
        self.video_std_combobox.currentIndexChanged.connect(self.update_mrl)

    def retranslate_ui(self):
        super().retranslate_ui()
        self.video_std_label.setText(translate('MediaPlugin.StreamSelector', 'Video standard'))

    def find_devices(self):
        """
        Insert devices for V4L2
        """
        video_devs = glob.glob('/dev/video*')
        self.video_devices_combo_box.addItems(video_devs)
        audio_devs = glob.glob('/dev/snd/pcmC*D*c')
        vlc_audio_devs = []
        for dev in audio_devs:
            vlc_dev = dev.replace('/dev/snd/pcmC', 'hw:')
            vlc_dev = re.sub(r'c$', '', vlc_dev).replace('D', ',')
            vlc_audio_devs.append(vlc_dev)
        self.audio_devices_combo_box.addItems(vlc_audio_devs)

    def update_mrl(self):
        vdev = self.video_devices_combo_box.currentText().strip()
        adev = self.audio_devices_combo_box.currentText().strip()
        vstd = VIDEO_STANDARDS_VLC[self.video_std_combobox.currentIndex()]
        main_file = 'v4l2://{vdev}'.format(vdev=vdev)
        options = ':v4l2-standard={vstd} '.format(vstd=vstd)
        if adev:
            options += ' :input-slave={adev}'.format(adev=adev)
        self.callback(main_file, options)

    def has_support_for_mrl(self, mrl, options):
        return mrl.startswith('v4l2://') and 'v4l2-tuner-frequency' not in options

    def set_mrl(self, main, options):
        # find video dev
        vdev = re.search(r'v4l2://([\w/-]+)', main)
        if vdev:
            for i in range(self.video_devices_combo_box.count()):
                if self.video_devices_combo_box.itemText(i) == vdev.group(1):
                    self.video_devices_combo_box.setCurrentIndex(i)
                    break
        # find audio dev
        adev = re.search(r'input-slave=([\w/-:]+)', options)
        if adev:
            for i in range(self.audio_devices_combo_box.count()):
                if self.audio_devices_combo_box.itemText(i) == adev.group(1):
                    self.audio_devices_combo_box.setCurrentIndex(i)
                    break
        # find video std
        vstd = re.search(r'v4l2-standard=(\w+)', options)
        if vstd and vstd.group(1) in VIDEO_STANDARDS_VLC:
            idx = VIDEO_STANDARDS_VLC.index(vstd.group(1))
            self.video_std_combobox.setCurrentIndex(idx)


class CaptureAnalogTVWidget(CaptureVideoLinuxWidget):
    """
    """
    def __init__(self, parent=None, disable_audio=False):
        super().__init__(parent, disable_audio)

    def setup_ui(self):
        super().setup_ui()
        # frequency
        self.freq_label = QtWidgets.QLabel(self)
        self.freq_label.setObjectName('freq_label')
        self.freq = QtWidgets.QSpinBox(self)
        self.freq.setAlignment(QtCore.Qt.AlignRight)
        self.freq.setSuffix(' kHz')
        self.freq.setSingleStep(1)
        self.freq.setMaximum(2147483647)  # Max value
        self.options_group_layout.addRow(self.freq_label, self.freq)
        # connect
        self.freq.valueChanged.connect(self.update_mrl)

    def retranslate_ui(self):
        super().retranslate_ui()
        self.video_std_label.setText(translate('MediaPlugin.StreamSelector', 'Video standard'))
        self.freq_label.setText(translate('MediaPlugin.StreamSelector', 'Frequency'))

    def update_mrl(self):
        vdev = self.video_devices_combo_box.currentText().strip()
        adev = self.audio_devices_combo_box.currentText().strip()
        freq = self.freq.value()
        vstd = VIDEO_STANDARDS_VLC[self.video_std_combobox.currentIndex()]
        main_file = 'v4l2://{vdev}'.format(vdev=vdev)
        options = ':v4l2-standard={vstd} '.format(vstd=vstd)
        if freq:
            options += ':v4l2-tuner-frequency={freq}'.format(freq=freq)
        if adev:
            options += ' :input-slave={adev}'.format(adev=adev)
        self.callback(main_file, options)

    def has_support_for_mrl(self, mrl, options):
        return mrl.startswith('v4l2://') and 'v4l2-tuner-frequency' in options

    def set_mrl(self, main, options):
        # let super class handle most
        super().set_mrl(main, options)
        # find tuner freq
        freq = re.search(r'v4l2-tuner-frequency=(\d+)', options)
        if freq:
            self.freq.setValue(int(freq.group(1)))


class CaptureDigitalTVWidget(CaptureModeWidget):
    """
    Widget inherits groupboxes from CaptureModeWidget and inserts widgets for digital TV
    """
    def __init__(self, parent=None, disable_audio=False):
        super().__init__(parent, disable_audio)

    def setup_ui(self):
        super().setup_ui()
        # Tuner card
        self.tuner_card_label = QtWidgets.QLabel(self)
        self.tuner_card_label.setObjectName('tuner_card_label')
        self.tuner_card = QtWidgets.QSpinBox(self)
        self.tuner_card.setObjectName('tuner_card')
        self.tuner_card.setAlignment(QtCore.Qt.AlignRight)
        if is_linux():
            self.tuner_card.setPrefix('/dev/dvb/adapter')
        self.device_group_layout.addRow(self.tuner_card_label, self.tuner_card)
        # Delivery system
        self.delivery_system_label = QtWidgets.QLabel(self)
        self.delivery_system_label.setObjectName('delivery_system_label')
        self.delivery_system_combo_box = QtWidgets.QComboBox(self)
        for std in DIGITAL_TV_STANDARDS:
            self.delivery_system_combo_box.addItem(*std)
        self.delivery_system_combo_box.setObjectName('delivery_system_combo_box')
        self.device_group_layout.addRow(self.delivery_system_label, self.delivery_system_combo_box)
        # Options
        # DVB frequency
        self.dvb_freq_label = QtWidgets.QLabel(self)
        self.dvb_freq_label.setObjectName('dvb_freq_label')
        self.dvb_freq = QtWidgets.QSpinBox(self)
        self.dvb_freq.setAlignment(QtCore.Qt.AlignRight)
        self.dvb_freq.setSuffix(' kHz')
        self.dvb_freq.setSingleStep(1000)
        self.dvb_freq.setMaximum(2147483647)  # Max value
        self.options_group_layout.addRow(self.dvb_freq_label, self.dvb_freq)
        # Bandwidth
        self.dvb_bandwidth_label = QtWidgets.QLabel(self)
        self.dvb_bandwidth_label.setObjectName('dvb_bandwidth_label')
        self.dvb_bandwidth_combo_box = QtWidgets.QComboBox(self)
        for bandwidth in DIGITAL_TV_BANDWIDTH:
            self.dvb_bandwidth_combo_box.addItem(*bandwidth)
        self.dvb_bandwidth_combo_box.setObjectName('dvb_bandwidth_combo_box')
        self.options_group_layout.addRow(self.dvb_bandwidth_label, self.dvb_bandwidth_combo_box)
        # QAM
        self.qam_label = QtWidgets.QLabel(self)
        self.qam_label.setObjectName('qam_label')
        self.qam_combo_box = QtWidgets.QComboBox(self)
        for qam in DIGITAL_TV_QAM:
            self.qam_combo_box.addItem(*qam)
        self.qam_combo_box.setObjectName('dvb_bandwidth_combo_box')
        self.options_group_layout.addRow(self.qam_label, self.qam_combo_box)
        # PSK
        self.psk_label = QtWidgets.QLabel(self)
        self.psk_label.setObjectName('psk_label')
        self.psk_combo_box = QtWidgets.QComboBox(self)
        for psk in DIGITAL_TV_PSK:
            self.psk_combo_box.addItem(*psk)
        self.psk_combo_box.setObjectName('dvb_bandwidth_combo_box')
        self.options_group_layout.addRow(self.psk_label, self.psk_combo_box)
        # DVB-S baud rate
        self.dvbs_rate_label = QtWidgets.QLabel(self)
        self.dvbs_rate_label.setObjectName('dvbs_rate_label')
        self.dvbs_rate = QtWidgets.QSpinBox(self)
        self.dvbs_rate.setObjectName('dvbs_rate')
        self.dvbs_rate.setAlignment(QtCore.Qt.AlignRight)
        self.dvbs_rate.setSuffix(' bauds')
        self.options_group_layout.addRow(self.dvbs_rate_label, self.dvbs_rate)
        # connect
        self.delivery_system_combo_box.currentIndexChanged.connect(self.update_dvb_widget)
        self.delivery_system_combo_box.currentIndexChanged.connect(self.update_mrl)
        self.tuner_card.valueChanged.connect(self.update_mrl)
        self.dvb_freq.valueChanged.connect(self.update_mrl)
        self.dvb_bandwidth_combo_box.currentIndexChanged.connect(self.update_mrl)
        self.qam_combo_box.currentIndexChanged.connect(self.update_mrl)
        self.psk_combo_box.currentIndexChanged.connect(self.update_mrl)
        self.dvbs_rate.valueChanged.connect(self.update_mrl)
        # Arrange the widget
        self.update_dvb_widget()

    def set_mrl(self, main, options):
        card = re.search(r'dvb-adapter=(\d+)', options)
        if card:
            self.tuner_card.setValue(int(card.group(1)))
        system = re.search(r'([\w-]+)://', main)
        if system:
            for i in range(len(DIGITAL_TV_STANDARDS)):
                if DIGITAL_TV_STANDARDS[i][1] == system.group(1):
                    self.delivery_system_combo_box.setCurrentIndex(i)
                    break
        freq = re.search(r'frequency=(\d+)000', main)
        if freq:
            self.dvb_freq.setValue(int(freq.group(1)))
        modulation = re.search(r'modulation=([\w-]+)', main)
        if modulation and system:
            if system.group(1) in ['dvb-c', 'cqam']:
                for i in range(len(DIGITAL_TV_QAM)):
                    if DIGITAL_TV_QAM[i][1] == modulation.group(1):
                        self.qam_combo_box.setCurrentIndex(i)
                        break
            if system.group(1) == 'dvb-s2':
                for i in range(len(DIGITAL_TV_QAM)):
                    if DIGITAL_TV_PSK[i][1] == modulation.group(1):
                        self.psk_combo_box.setCurrentIndex(i)
                        break
        bandwidth = re.search(r'bandwidth=(\d+)', main)
        if bandwidth:
            for i in range(len(DIGITAL_TV_BANDWIDTH)):
                if DIGITAL_TV_BANDWIDTH[i][1] == bandwidth.group(1):
                    self.dvb_bandwidth_combo_box.setCurrentIndex(i)
                    break
        srate = re.search(r'srate=(\d+)', main)
        if srate:
            self.dvbs_rate.setValue(int(srate.group()))

    def update_mrl(self):
        card = self.tuner_card.value()
        system = self.delivery_system_combo_box.currentData()
        freq = self.dvb_freq.value()
        qam = self.qam_combo_box.currentData()
        psk = self.psk_combo_box.currentData()
        dvbs_rate = self.dvbs_rate.value()
        dvb_bandwidth = self.dvb_bandwidth_combo_box.currentData()
        main_file = '{system}://frequency={freq}000'.format(system=system, freq=freq)
        if system in ['dvb-c', 'cqam']:
            main_file += ':modulation={qam}'.format(qam=qam)
        if system == 'dvb-s2':
            main_file += ':modulation={psk}'.format(psk=psk)
        if system in ['dvb-c', 'dvb-s', 'dvb-s2']:
            main_file += ':srate={rate}'.format(rate=dvbs_rate)
        if system in ['dvb-t', 'dvb-t2']:
            main_file += ':bandwidth={bandwidth}'.format(bandwidth=dvb_bandwidth)
        options = ' :dvb-adapter={card}'.format(card=card)
        self.callback(main_file, options)

    def update_dvb_widget(self):
        """
        Show and hides widgets if they are needed with the current selected system
        """
        system = self.delivery_system_combo_box.currentText()
        # Bandwidth
        if system in ['DVB-T', 'DVB-T2']:
            self.dvb_bandwidth_label.show()
            self.dvb_bandwidth_combo_box.show()
        else:
            self.dvb_bandwidth_label.hide()
            self.dvb_bandwidth_combo_box.hide()
        # QAM
        if system == 'DVB-C':
            self.qam_label.show()
            self.qam_combo_box.show()
        else:
            self.qam_label.hide()
            self.qam_combo_box.hide()
        # PSK
        if system == 'DVB-S2':
            self.psk_label.show()
            self.psk_combo_box.show()
        else:
            self.psk_label.hide()
            self.psk_combo_box.hide()
        # Baud rate
        if system in ['DVB-C', 'DVB-S', 'DVB-S2']:
            self.dvbs_rate_label.show()
            self.dvbs_rate.show()
        else:
            self.dvbs_rate_label.hide()
            self.dvbs_rate.hide()

    def retranslate_ui(self):
        super().retranslate_ui()
        self.tuner_card_label.setText(translate('MediaPlugin.StreamSelector', 'Tuner card'))
        self.delivery_system_label.setText(translate('MediaPlugin.StreamSelector', 'Delivery system'))
        self.dvb_freq_label.setText(translate('MediaPlugin.StreamSelector', 'Transponder/multiplexer frequency'))
        self.dvb_bandwidth_label.setText(translate('MediaPlugin.StreamSelector', 'Bandwidth'))
        self.qam_label.setText(translate('MediaPlugin.StreamSelector', 'Modulation / Constellation'))
        self.psk_label.setText(translate('MediaPlugin.StreamSelector', 'Modulation / Constellation'))
        self.dvbs_rate_label.setText(translate('MediaPlugin.StreamSelector', 'Transponder symbol rate'))

    def has_support_for_mrl(self, mrl, options):
        return '//frequency=' in mrl


class JackAudioKitWidget(CaptureModeWidget):
    """
    Widget for JACK Audio Connection Kit
    """
    def __init__(self, parent=None, disable_audio=False):
        super().__init__(parent, disable_audio)

    def setup_ui(self):
        super().setup_ui()
        # Selected ports
        self.ports_label = QtWidgets.QLabel(self)
        self.ports_label.setObjectName('ports_label')
        self.ports = QtWidgets.QLineEdit(self)
        self.ports.setText('.*')
        self.ports.setObjectName('ports')
        self.ports.setAlignment(QtCore.Qt.AlignRight)
        self.device_group_layout.addRow(self.ports_label, self.ports)
        # channels
        self.channels_label = QtWidgets.QLabel(self)
        self.channels_label.setObjectName('channels_label')
        self.channels = QtWidgets.QSpinBox(self)
        self.channels.setObjectName('channels')
        self.channels.setMaximum(255)
        self.channels.setValue(2)
        self.channels.setAlignment(QtCore.Qt.AlignRight)
        self.device_group_layout.addRow(self.channels_label, self.channels)
        # Options
        self.jack_pace = QtWidgets.QCheckBox(translate('MediaPlugin.StreamSelector', 'Use VLC pace'))
        self.jack_connect = QtWidgets.QCheckBox(translate('MediaPlugin.StreamSelector', 'Auto connection'))
        self.options_group_layout.addRow(self.jack_pace, self.jack_connect)
        # connect
        self.ports.editingFinished.connect(self.update_mrl)
        self.channels.valueChanged.connect(self.update_mrl)
        self.jack_pace.stateChanged.connect(self.update_mrl)
        self.jack_connect.stateChanged.connect(self.update_mrl)

    def retranslate_ui(self):
        super().retranslate_ui()
        self.ports_label.setText(translate('MediaPlugin.StreamSelector', 'Selected ports'))
        self.channels_label.setText(translate('MediaPlugin.StreamSelector', 'Channels'))

    def update_mrl(self):
        ports = self.ports.text().strip()
        channels = self.channels.value()
        main_file = 'jack://channels={channel}:ports={ports}'.format(channel=channels, ports=ports)
        options = ''
        if self.jack_pace.isChecked():
            options += ' :jack-input-use-vlc-pace'
        if self.jack_connect.isChecked():
            options += ' :jack-input-auto-connect'
        self.callback(main_file, options)

    def has_support_for_mrl(self, mrl, options):
        return mrl.startswith('jack')

    def set_mrl(self, main, options):
        channels = re.search(r'channels=(\d+)', main)
        if channels:
            self.channels.setValue(int(channels.group(1)))
        ports = re.search(r'ports=([\w\.\*-]+)', main)
        if ports:
            self.ports.setText(ports.group(1))
        if 'jack-input-use-vlc-pace' in options:
            self.jack_pace.setChecked(True)
        if 'jack-input-auto-connect' in options:
            self.jack_connect.setChecked(True)


class CaptureVideoQtDetectWidget(CaptureVideoWidget):
    """
    Widget inherits groupboxes from CaptureVideoWidget and detects device using Qt
    """
    def __init__(self, parent=None, disable_audio=False):
        super().__init__(parent, disable_audio)

    def find_devices(self):
        """
        Insert devices detected by Qt
        """
        for cam in QCameraInfo.availableCameras():
            self.video_devices_combo_box.addItem(cam.description(), cam.deviceName())
        for au in QAudioDeviceInfo.availableDevices(QAudio.AudioInput):
            self.audio_devices_combo_box.addItem(au.deviceName())


class MacInputWidget(CaptureVideoQtDetectWidget):
    """
    Widget for macOS
https://github.com/videolan/vlc/blob/13e18f3182e2a7b425411ce70ed83161108c3d1f/modules/gui/macosx/windows/VLCOpenWindowController.m#L472
    """
    def __init__(self, parent=None, disable_audio=False):
        super().__init__(parent, disable_audio)

    def setup_ui(self):
        super().setup_ui()
        # There are no options available on Mac
        self.options_group.hide()

    def update_mrl(self):
        vdev = self.video_devices_combo_box.currentData()
        # Audio is not supported on Mac since we currently don't have a way to
        # extract the needed HW ids.
        # adev = self.audio_devices_combo_box.currentText()
        main_file = 'avcapture://{vdev}'.format(vdev=vdev)
        # options = 'input-slave=qtsound://{adev}'.format(adev=adev)
        self.callback(main_file, '')

    def has_support_for_mrl(self, mrl, options):
        return mrl.startswith('avcapture')

    def set_mrl(self, main, options):
        vdev = re.search(r'avcapture=(\w+)', main)
        if vdev:
            for i in range(self.video_devices_combo_box.count()):
                if self.video_devices_combo_box.itemData(i) == vdev.group(1):
                    self.video_devices_combo_box.setCurrentIndex(i)
                    break


class CaptureVideoDirectShowWidget(CaptureVideoQtDetectWidget):
    """
    Widget for directshow input
    """
    def __init__(self, parent=None, disable_audio=False):
        super().__init__(parent, disable_audio)

    def setup_ui(self):
        super().setup_ui()
        # Options
        self.video_size_label = QtWidgets.QLabel(self)
        self.video_size_label.setObjectName('video_size_label')
        self.video_size_lineedit = QtWidgets.QLineEdit(self)
        self.video_size_lineedit.setObjectName('video_size_lineedit')
        self.options_group_layout.addRow(self.video_size_label, self.video_size_lineedit)
        # connect
        self.video_size_lineedit.editingFinished.connect(self.update_mrl)

    def retranslate_ui(self):
        super().retranslate_ui()
        self.video_size_label.setText(translate('MediaPlugin.StreamSelector', 'Video size'))

    def update_mrl(self):
        vdev = self.video_devices_combo_box.currentText().strip()
        adev = self.audio_devices_combo_box.currentText().strip()
        vsize = self.video_size_lineedit.text().strip()
        main_file = 'dshow://'
        options = ''
        if vdev:
            options = ':"dshow-vdev={vdev}" '.format(vdev=self.colon_escape(vdev))
        if adev:
            options += ':"dshow-adev={adev}" '.format(adev=self.colon_escape(adev))
        if vsize:
            options += ':dshow-size={vsize}'.format(vsize=vsize)
        self.callback(main_file, options)

    def has_support_for_mrl(self, mrl, options):
        return mrl.startswith('dshow')

    def set_mrl(self, main, options):
        vsize = re.search(r'dshow-size=(\d+)', options)
        vdev = re.search(r'"dshow-vdev=(.+)"', options)
        if vdev:
            for i in range(self.video_devices_combo_box.count()):
                if self.video_devices_combo_box.itemText(i) == vdev.group(1):
                    self.video_devices_combo_box.setCurrentIndex(i)
                    if vsize:
                        self.video_size_lineedit.setText(vsize.group(1))
                    break
        adev = re.search(r'"dshow-adev=(.+)"', options)
        if adev:
            for i in range(self.audio_devices_combo_box.count()):
                if self.audio_devices_combo_box.itemText(i) == adev.group(1):
                    self.audio_devices_combo_box.setCurrentIndex(i)
                    break


class Ui_StreamSelector(object):
    def setup_ui(self, stream_selector):
        # Mode combobox
        self.capture_mode_label = QtWidgets.QLabel(self.top_widget)
        self.capture_mode_label.setObjectName('capture_mode_label')
        self.capture_mode_combo_box = QtWidgets.QComboBox(self.top_widget)
        self.capture_mode_combo_box.setObjectName('capture_mode_combo_box')
        self.top_layout.addRow(self.capture_mode_label, self.capture_mode_combo_box)
        self.main_layout.addWidget(self.top_widget)
        # Stacked Layout for capture modes
        self.stacked_modes = QtWidgets.QWidget(stream_selector)
        self.stacked_modes.setObjectName('stacked_modes')
        self.stacked_modes_layout = QtWidgets.QStackedLayout(self.stacked_modes)
        self.stacked_modes_layout.setObjectName('stacked_modes_layout')
        # Widget for DirectShow - Windows only
        if is_win():
            self.direct_show_widget = CaptureVideoDirectShowWidget(stream_selector, self.theme_stream)
            self.stacked_modes_layout.addWidget(self.direct_show_widget)
            self.capture_mode_combo_box.addItem(translate('MediaPlugin.StreamSelector', 'DirectShow'))
        elif is_linux():
            # Widget for V4L2 - Linux only
            self.v4l2_widget = CaptureVideoLinuxWidget(stream_selector, self.theme_stream)
            self.stacked_modes_layout.addWidget(self.v4l2_widget)
            self.capture_mode_combo_box.addItem(translate('MediaPlugin.StreamSelector', 'Video Camera'))
            # Widget for analog TV - Linux only
            self.analog_tv_widget = CaptureAnalogTVWidget(stream_selector, self.theme_stream)
            self.stacked_modes_layout.addWidget(self.analog_tv_widget)
            self.capture_mode_combo_box.addItem(translate('MediaPlugin.StreamSelector', 'TV - analog'))
            # Do not allow audio streams for themes
            if not self.theme_stream:
                # Widget for JACK - Linux only
                self.jack_widget = JackAudioKitWidget(stream_selector, self.theme_stream)
                self.stacked_modes_layout.addWidget(self.jack_widget)
                self.capture_mode_combo_box.addItem(translate('MediaPlugin.StreamSelector',
                                                              'JACK Audio Connection Kit'))
        # Digital TV - both linux and windows
        if is_win() or is_linux():
            self.digital_tv_widget = CaptureDigitalTVWidget(stream_selector, self.theme_stream)
            self.stacked_modes_layout.addWidget(self.digital_tv_widget)
            self.capture_mode_combo_box.addItem(translate('MediaPlugin.StreamSelector', 'TV - digital'))
        # for macs
        if is_macosx():
            self.mac_input_widget = MacInputWidget(stream_selector, self.theme_stream)
            self.stacked_modes_layout.addWidget(self.mac_input_widget)
            self.capture_mode_combo_box.addItem(translate('MediaPlugin.StreamSelector', 'Input devices'))
        # Setup the stacked widgets
        self.main_layout.addWidget(self.stacked_modes)
        self.stacked_modes_layout.setCurrentIndex(0)
        for i in range(self.stacked_modes_layout.count()):
            self.stacked_modes_layout.widget(i).find_devices()
            self.stacked_modes_layout.widget(i).retranslate_ui()
        # Add groupbox for VLC options
        self.more_options_group = VLCOptionsWidget(self)
        # Add groupbox for more options to main layout
        self.main_layout.addWidget(self.more_options_group)
        # Save and close buttons
        self.button_box = QtWidgets.QDialogButtonBox(stream_selector)
        self.button_box.addButton(QtWidgets.QDialogButtonBox.StandardButton.Save)
        self.button_box.addButton(QtWidgets.QDialogButtonBox.StandardButton.Close)
        self.close_button = self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Close)
        self.save_button = self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Save)
        self.main_layout.addWidget(self.button_box)

        # translate
        self.retranslate_ui(stream_selector)
        # connect
        self.capture_mode_combo_box.currentIndexChanged.connect(stream_selector.on_capture_mode_combo_box)
        self.more_options_group.caching.valueChanged.connect(stream_selector.on_capture_mode_combo_box)
        self.button_box.accepted.connect(stream_selector.accept)
        self.button_box.rejected.connect(stream_selector.reject)

    def retranslate_ui(self, stream_selector):
        stream_selector.setWindowTitle(translate('MediaPlugin.StreamSelector', 'Select Input Stream'))
        if not self.theme_stream:
            self.stream_name_label.setText(translate('MediaPlugin.StreamSelector', 'Stream name'))
        self.capture_mode_label.setText(translate('MediaPlugin.StreamSelector', 'Capture Mode'))
