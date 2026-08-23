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
Module to test the StreamSelectorForm.
"""
import pytest

from unittest.mock import MagicMock, patch

from PyQt5 import QtCore, QtTest, QtWidgets

from openlp.plugins.media.forms.streamselectorform import StreamSelectorForm
from openlp.plugins.media.forms.streamselectordialog import CaptureVideoDirectShowWidget, CaptureDigitalTVWidget, \
    CaptureVideoLinuxWidget, JackAudioKitWidget, CaptureAnalogTVWidget, MacInputWidget
from openlp.plugins.media.forms import VLCOptionsWidget


# This mocks the callback function BackgroundPage.set_stream() in core/pages/background.py
# This function is used to set the device stream text in the theme wizard
setstream = MagicMock()


@pytest.fixture()
def stream_selector_form_win(settings):
    '''
    Fixture for setting up a StreamSelectorForm on a windows PC with dummy video and audio devices
    '''
    main_window = QtWidgets.QMainWindow()

    camera1 = MagicMock()
    camera1.description.return_value = "Camera 1"
    camera1.deviceName.return_value = "Camera 1 device"
    camera2 = MagicMock()
    camera2.description.return_value = "Camera 2"
    camera2.deviceName.return_value = "Camera 2 device"

    audio1 = MagicMock()
    audio1.deviceName.return_value = "Audio 1"
    audio2 = MagicMock()
    audio2.deviceName.return_value = "Audio 2"

    with patch('openlp.plugins.media.forms.streamselectordialog.is_win', return_value=True), \
            patch('openlp.plugins.media.forms.streamselectordialog.is_linux', return_value=False), \
            patch('openlp.plugins.media.forms.streamselectordialog.is_macosx', return_value=False), \
            patch('openlp.plugins.media.forms.streamselectordialog.QCameraInfo.availableCameras',
                  return_value=[camera1, camera2]), \
            patch('openlp.plugins.media.forms.streamselectordialog.QAudioDeviceInfo.availableDevices',
                  return_value=[audio1, audio2]):
        form = StreamSelectorForm(main_window, setstream)

    yield form
    del form
    del main_window


# This fixture is parameterized as per
# https://docs.pytest.org/en/latest/example/parametrize.html#deferring-the-setup-of-parametrized-resources
# The parameter is passed to StreamSelectorForm param3 (defining whether it's for a theme or not)
# This is because on linux the JackAudioKitWidget is not included if it's for a theme
@pytest.fixture()
def stream_selector_form_linux(request, settings):
    '''
    Fixture for setting up a StreamSelectorForm on a linux computer with dummy video and audio devices
    '''
    main_window = QtWidgets.QMainWindow()

    def return_dummy_devices(*args, **kwargs):
        if isinstance(args[0], str):
            if args[0].startswith('/dev/video'):
                return ['/dev/video1', '/dev/video2']
            if args[0].startswith('/dev/snd'):
                return ['/dev/snd/pcmC0D0p', '/dev/snd/pcmC0D1p']
        return []

    with patch('openlp.plugins.media.forms.streamselectordialog.is_win', return_value=False), \
            patch('openlp.plugins.media.forms.streamselectordialog.is_linux', return_value=True), \
            patch('openlp.plugins.media.forms.streamselectordialog.is_macosx', return_value=False), \
            patch('openlp.plugins.media.forms.streamselectordialog.glob') as patched_glob:
        patched_glob.glob.side_effect = return_dummy_devices
        form = StreamSelectorForm(main_window, setstream, request.param)

    yield form
    del form
    del main_window


@pytest.fixture()
def stream_selector_form_mac(settings):
    '''
    Fixture for setting up a StreamSelectorForm on a mac with dummy video and audio devices
    '''
    main_window = QtWidgets.QMainWindow()

    camera1 = MagicMock()
    camera1.description.return_value = "Camera 1"
    camera1.deviceName.return_value = "Camera 1 device"
    camera2 = MagicMock()
    camera2.description.return_value = "Camera 2"
    camera2.deviceName.return_value = "Camera 2 device"

    audio1 = MagicMock()
    audio1.deviceName.return_value = "Audio 1"
    audio2 = MagicMock()
    audio2.deviceName.return_value = "Audio 2"

    with patch('openlp.plugins.media.forms.streamselectordialog.is_win', return_value=False), \
            patch('openlp.plugins.media.forms.streamselectordialog.is_linux', return_value=False), \
            patch('openlp.plugins.media.forms.streamselectordialog.is_macosx', return_value=True), \
            patch('openlp.plugins.media.forms.streamselectordialog.QCameraInfo.availableCameras',
                  return_value=[camera1, camera2]), \
            patch('openlp.plugins.media.forms.streamselectordialog.QAudioDeviceInfo.availableDevices',
                  return_value=[audio1, audio2]):
        form = StreamSelectorForm(main_window, setstream)

    yield form
    del form
    del main_window


def test_win_setup(stream_selector_form_win):
    '''
    Test that the UI is set up ok on windows
    '''
    # GIVEN: A fixture for a StreamSelectorForm on a windows pc with dummy devices

    # THEN: The UI elements should display the dummy devices correctly
    assert stream_selector_form_win.objectName() == 'stream_selector'
    assert stream_selector_form_win.stacked_modes_layout.objectName() == 'stacked_modes_layout'
    assert stream_selector_form_win.stacked_modes_layout.count() == 2
    assert isinstance(stream_selector_form_win.stacked_modes_layout.widget(0), CaptureVideoDirectShowWidget)

    assert stream_selector_form_win.stacked_modes_layout.widget(0).video_devices_combo_box.count() == 3
    assert stream_selector_form_win.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(0) == ""
    assert stream_selector_form_win.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(1) == "Camera 1"
    assert stream_selector_form_win.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(2) == "Camera 2"

    assert stream_selector_form_win.stacked_modes_layout.widget(0).audio_devices_combo_box.count() == 3
    assert stream_selector_form_win.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(0) == ""
    assert stream_selector_form_win.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(1) == "Audio 1"
    assert stream_selector_form_win.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(2) == "Audio 2"

    assert isinstance(stream_selector_form_win.stacked_modes_layout.widget(1), CaptureDigitalTVWidget)
    assert isinstance(stream_selector_form_win.more_options_group, VLCOptionsWidget)


@pytest.mark.parametrize("stream_selector_form_linux", [True], indirect=True)
def test_linux_setup_for_theme(stream_selector_form_linux):
    '''
    Test that the UI is set up ok on linux for theme (param3 of StreamSelectorForm is True)
    '''
    # GIVEN: A fixture for a StreamSelectorForm on a linux computer with dummy devices

    # THEN: The UI elements should display the dummy devices correctly
    assert stream_selector_form_linux.objectName() == 'stream_selector'
    assert stream_selector_form_linux.stacked_modes_layout.objectName() == 'stacked_modes_layout'
    assert stream_selector_form_linux.stacked_modes_layout.count() == 3
    assert isinstance(stream_selector_form_linux.stacked_modes_layout.widget(0), CaptureVideoLinuxWidget)

    assert stream_selector_form_linux.stacked_modes_layout.widget(0).video_devices_combo_box.count() == 3
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(0) == ""
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(1) ==\
        "/dev/video1"
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(2) ==\
        "/dev/video2"

    assert stream_selector_form_linux.stacked_modes_layout.widget(0).audio_devices_combo_box.count() == 3
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(0) == ""
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(1) ==\
        "hw:0,0p"
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(2) ==\
        "hw:0,1p"

    assert isinstance(stream_selector_form_linux.stacked_modes_layout.widget(1), CaptureAnalogTVWidget)
    assert isinstance(stream_selector_form_linux.stacked_modes_layout.widget(2), CaptureDigitalTVWidget)
    assert isinstance(stream_selector_form_linux.more_options_group, VLCOptionsWidget)


@pytest.mark.parametrize("stream_selector_form_linux", [False], indirect=True)
def test_linux_setup_general(stream_selector_form_linux):
    '''
    Test that the UI is set up ok on linux, not just for themes (param3 of StreamSelectorForm is False)
    '''
    # GIVEN: A fixture for a StreamSelectorForm on a linux computer with dummy devices

    # THEN: The UI elements should display the dummy devices correctly
    assert stream_selector_form_linux.objectName() == 'stream_selector'
    assert stream_selector_form_linux.stacked_modes_layout.objectName() == 'stacked_modes_layout'
    assert stream_selector_form_linux.stacked_modes_layout.count() == 4
    assert isinstance(stream_selector_form_linux.stacked_modes_layout.widget(0), CaptureVideoLinuxWidget)

    assert stream_selector_form_linux.stacked_modes_layout.widget(0).video_devices_combo_box.count() == 3
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(0) == ""
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(1) ==\
        "/dev/video1"
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(2) ==\
        "/dev/video2"

    assert stream_selector_form_linux.stacked_modes_layout.widget(0).audio_devices_combo_box.count() == 3
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(0) == ""
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(1) ==\
        "hw:0,0p"
    assert stream_selector_form_linux.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(2) ==\
        "hw:0,1p"

    assert isinstance(stream_selector_form_linux.stacked_modes_layout.widget(1), CaptureAnalogTVWidget)
    assert isinstance(stream_selector_form_linux.stacked_modes_layout.widget(2), JackAudioKitWidget)
    assert isinstance(stream_selector_form_linux.stacked_modes_layout.widget(3), CaptureDigitalTVWidget)
    assert isinstance(stream_selector_form_linux.more_options_group, VLCOptionsWidget)


def test_mac_setup(stream_selector_form_mac):
    '''
    Test that the UI is set up ok on mac
    '''
    # GIVEN: A fixture for a StreamSelectorForm on a mac with dummy devices

    # THEN: The UI elements should display the dummy devices correctly
    assert stream_selector_form_mac.objectName() == 'stream_selector'
    assert stream_selector_form_mac.stacked_modes_layout.objectName() == 'stacked_modes_layout'
    assert stream_selector_form_mac.stacked_modes_layout.count() == 1
    assert isinstance(stream_selector_form_mac.stacked_modes_layout.widget(0), MacInputWidget)

    assert stream_selector_form_mac.stacked_modes_layout.widget(0).video_devices_combo_box.count() == 3
    assert stream_selector_form_mac.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(0) == ""
    assert stream_selector_form_mac.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(1) == "Camera 1"
    assert stream_selector_form_mac.stacked_modes_layout.widget(0).video_devices_combo_box.itemText(2) == "Camera 2"

    assert stream_selector_form_mac.stacked_modes_layout.widget(0).audio_devices_combo_box.count() == 3
    assert stream_selector_form_mac.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(0) == ""
    assert stream_selector_form_mac.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(1) == "Audio 1"
    assert stream_selector_form_mac.stacked_modes_layout.widget(0).audio_devices_combo_box.itemText(2) == "Audio 2"

    assert isinstance(stream_selector_form_mac.more_options_group, VLCOptionsWidget)


def test_set_mrl_win(stream_selector_form_win):
    '''
    Test that the UI components are prefilled correctly on a windows PC
    '''
    # GIVEN: A fixture for a StreamSelectorForm on a windows computer with dummy devices

    # WHEN: The stream selector form is prefilled

    live_stream_text = 'devicestream:wintest&&dshow://&&:"dshow-vdev=Camera 2" :dshow-size=25 :live-caching=400'
    stream_selector_form_win.set_mrl(live_stream_text)

    # THEN: The form should contain the prefilled values
    stream_selector_form_win.stream_name_edit.text() == "wintest"
    assert stream_selector_form_win.stacked_modes_layout.currentIndex() == 0
    assert stream_selector_form_win.stacked_modes_layout.widget(0).video_devices_combo_box.currentIndex() == 2
    assert stream_selector_form_win.stacked_modes_layout.widget(0).video_devices_combo_box.currentText() == "Camera 2"
    assert stream_selector_form_win.stacked_modes_layout.widget(0).video_size_lineedit.text() == '25'
    assert stream_selector_form_win.more_options_group.caching.text() == '400 ms'


@pytest.mark.parametrize("stream_selector_form_linux", [False], indirect=True)
def test_set_mrl_linux(stream_selector_form_linux):
    '''
    Test that the UI components are prefilled correctly on a linux computer
    '''
    # GIVEN: A fixture for a StreamSelectorForm on a linux computer with dummy devices

    # WHEN: The stream selector form is prefilled

    live_stream_text = 'devicestream:linuxtest&&v4l2://&&:v4l2-standard=PAL :v4l2-tuner-frequency=1 :live-caching=300'
    stream_selector_form_linux.set_mrl(live_stream_text)

    # THEN: The form should contain the prefilled values
    stream_selector_form_linux.stream_name_edit.text() == "linuxtest"
    assert stream_selector_form_linux.stacked_modes_layout.currentIndex() == 1
    assert stream_selector_form_linux.stacked_modes_layout.widget(1).freq.text() == "1 kHz"
    assert stream_selector_form_linux.stacked_modes_layout.widget(1).video_std_combobox.currentText() == "PAL"
    assert stream_selector_form_linux.more_options_group.caching.text() == '300 ms'


def test_win_set_stream_call(stream_selector_form_win):
    '''
    Test that when a stream selector form on windows is run and filled in then set_stream() is called correctly
    '''
    # GIVEN: A fixture for a StreamSelectorForm on a windows computer with dummy devices

    # WHEN: The form is executed and filled in with values

    stream_selector_form_win.stream_name_edit.setText('test')
    # choose direct show
    stream_selector_form_win.stacked_modes_layout.setCurrentIndex(0)
    # choose camera 2
    stream_selector_form_win.stacked_modes_layout.widget(0).video_devices_combo_box.setCurrentIndex(2)
    # increment caching value
    QtTest.QTest.keyClick(stream_selector_form_win.more_options_group.caching, QtCore.Qt.Key_Up)
    # click on Save
    QtTest.QTest.mouseClick(stream_selector_form_win.save_button, QtCore.Qt.LeftButton)

    # THEN: The callback function should be called with the correct values

    setstream.assert_called_with('devicestream:test&&dshow://&&:"dshow-vdev=Camera 2"  :live-caching=400')


@pytest.mark.parametrize("stream_selector_form_linux", [False], indirect=True)
def test_linux_set_stream_call(stream_selector_form_linux):
    '''
    Test that when a stream selector form on linux is run and filled in then set_stream() is called correctly
    '''
    # GIVEN: A fixture for a StreamSelectorForm on a linux computer with dummy devices

    # WHEN: The form is executed and filled in with values

    stream_selector_form_linux.stream_name_edit.setText('test')

    # choose digital TV
    stream_selector_form_linux.stacked_modes_layout.setCurrentIndex(3)
    # choose ATSC delivery system
    stream_selector_form_linux.stacked_modes_layout.widget(3).delivery_system_combo_box.setCurrentIndex(
        stream_selector_form_linux.stacked_modes_layout.widget(3).delivery_system_combo_box.findText('ATSC'))
    # increment transponder / multiplexer frequency
    QtTest.QTest.keyClick(stream_selector_form_linux.stacked_modes_layout.widget(3).dvb_freq, QtCore.Qt.Key_Up)
    # click on Save
    QtTest.QTest.mouseClick(stream_selector_form_linux.save_button, QtCore.Qt.LeftButton)

    # THEN: The callback function should be called with the correct values

    setstream.assert_called_with('devicestream:test&&atsc://frequency=1000000&&:dvb-adapter=0 :live-caching=300')
