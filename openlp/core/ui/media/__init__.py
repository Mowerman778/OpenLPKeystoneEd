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
The :mod:`~openlp.core.ui.media` module contains classes and objects for media player integration.
"""
import logging

from openlp.core.common.registry import Registry

log = logging.getLogger(__name__ + '.__init__')

# Audio and video extensions copied from 'include/vlc_interface.h' from vlc 2.2.0 source
AUDIO_EXT = ['*.3ga', '*.669', '*.a52', '*.aac', '*.ac3', '*.adt', '*.adts', '*.aif', '*.aifc', '*.aiff', '*.amr',
             '*.aob', '*.ape', '*.awb', '*.caf', '*.dts', '*.flac', '*.it', '*.kar', '*.m4a', '*.m4b', '*.m4p', '*.m5p',
             '*.mid', '*.mka', '*.mlp', '*.mod', '*.mpa', '*.mp1', '*.mp2', '*.mp3', '*.mpc', '*.mpga', '*.mus',
             '*.oga', '*.ogg', '*.oma', '*.opus', '*.qcp', '*.ra', '*.rmi', '*.s3m', '*.sid', '*.spx', '*.thd', '*.tta',
             '*.voc', '*.vqf', '*.w64', '*.wav', '*.wma', '*.wv', '*.xa', '*.xm']
VIDEO_EXT = ['*.3g2', '*.3gp', '*.3gp2', '*.3gpp', '*.amv', '*.asf', '*.avi', '*.bik', '*.divx', '*.drc', '*.dv',
             '*.f4v', '*.flv', '*.gvi', '*.gxf', '*.iso', '*.m1v', '*.m2v', '*.m2t', '*.m2ts', '*.m4v', '*.mkv',
             '*.mov', '*.mp2', '*.mp2v', '*.mp4', '*.mp4v', '*.mpe', '*.mpeg', '*.mpeg1', '*.mpeg2', '*.mpeg4', '*.mpg',
             '*.mpv2', '*.mts', '*.mtv', '*.mxf', '*.mxg', '*.nsv', '*.nuv', '*.ogg', '*.ogm', '*.ogv', '*.ogx', '*.ps',
             '*.rec', '*.rm', '*.rmvb', '*.rpl', '*.thp', '*.tod', '*.ts', '*.tts', '*.txd', '*.vob', '*.vro', '*.webm',
             '*.wm', '*.wmv', '*.wtv', '*.xesc', '*.nut', '*.rv', '*.xvid']


class MediaState(object):
    """
    An enumeration for possible States of the Media Player
    """
    Off = 0
    Loaded = 1
    Playing = 2
    Paused = 3
    Stopped = 4


class VlCState(object):
    """
    A copy of the VLC States to allow for readable code
    From https://www.olivieraubert.net/vlc/python-ctypes/doc/vlc.State-class.html
    """
    NothingSpecial = 0
    Opening = 1
    Buffering = 2
    Playing = 3
    Paused = 4
    Stopped = 5
    Ended = 6
    Error = 7


class MediaType(object):
    """
    An enumeration of possible Media Types
    """
    Unused = 0
    Audio = 1
    Video = 2
    CD = 3
    DVD = 4
    Folder = 5
    Stream = 6


class ItemMediaInfo(object):
    """
    This class hold the media related info
    """
    file_info = None
    is_background = False
    is_theme_background = None
    length = 0
    start_time = 0
    end_time = 0
    title_track = 0
    is_playing = False
    timer = 1000
    audio_track = 0
    subtitle_track = 0
    media_type = MediaType()


def get_volume(controller) -> int:
    """
    The volume needs to be retrieved

    :param controller: the controller in use
    :return: Are we looping
    """
    if controller.is_live:
        return Registry().get('settings').value('media/live volume')
    else:
        return Registry().get('settings').value('media/preview volume')


def save_volume(controller, volume: int) -> None:
    """
    The volume needs to be saved

    :param controller: the controller in use
    :param volume: The volume to use and save
    :return: Are we looping
    """
    if controller.is_live:
        return Registry().get('settings').setValue('media/live volume', volume)
    else:
        return Registry().get('settings').setValue('media/preview volume', volume)


def is_looping_playback(controller) -> bool:
    """
    :param controller: the controller in use
    :return: Are we looping
    """
    if controller.is_live:
        return Registry().get('settings').value('media/live loop')
    else:
        return Registry().get('settings').value('media/preview loop')


def toggle_looping_playback(controller) -> None:
    """

    :param controller: the controller in use
    :return: None
    """
    if controller.is_live:
        Registry().get('settings').setValue('media/live loop', not Registry().get('settings').value('media/live loop'))
    else:
        Registry().get('settings').setValue('media/preview loop',
                                            not Registry().get('settings').value('media/preview loop'))


def parse_optical_path(input_string):
    """
    Split the optical path info.

    :param input_string: The string to parse
    :return: The elements extracted from the string:  filename, title, audio_track, subtitle_track, start, end
    """
    log.debug('parse_optical_path, about to parse: "{text}"'.format(text=input_string))
    clip_info = input_string.split(sep=':')
    title = str(clip_info[1])
    audio_track = int(clip_info[2])
    subtitle_track = int(clip_info[3])
    start = float(clip_info[4])
    end = float(clip_info[5])
    clip_name = clip_info[6]
    filename = clip_info[7]
    # Windows path usually contains a colon after the drive letter
    if len(clip_info) > 8:
        filename += ':' + clip_info[8]
    return filename, title, audio_track, subtitle_track, start, end, clip_name


def parse_stream_path(input_string):
    """
    Split the device stream path info.

    :param input_string: The string to parse
    :return: The elements extracted from the string:  streamname, MRL, VLC-options
    """
    log.debug('parse_stream_path, about to parse: "{text}"'.format(text=input_string))
    # skip the header: 'devicestream:' or 'networkstream:'
    header, data = input_string.split(':', 1)
    # split at '&&'
    stream_info = data.split('&&')
    name = stream_info[0]
    mrl = stream_info[1]
    options = stream_info[2]
    return name, mrl, options


def format_milliseconds(milliseconds):
    """
    Format milliseconds into a human readable time string.
    :param milliseconds: Milliseconds to format
    :return: Time string in format: hh:mm:ss,ttt
    """
    milliseconds = int(milliseconds)
    seconds, millis = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return "{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}".format(hours=hours,
                                                                         minutes=minutes,
                                                                         seconds=seconds,
                                                                         millis=millis)


media_empty_song = [{"title": "", "text": "", "verse": 0, "footer": ""}]
