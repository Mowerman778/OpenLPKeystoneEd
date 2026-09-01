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
The :mod:`~openlp.core.common.platform` module contains functions related to the platform that
OpenLP is currently running on.
"""
import os
import sys

try:
    from distro import id as distro_id
except ImportError:
    # The distro module is only valid for Linux, so if it doesn't exist, create a function that always
    # returns False
    def distro_id():
        return False


def is_win():
    """
    Returns true if running on a system with a nt kernel e.g. Windows, Wine

    :return: True if system is running a nt kernel false otherwise
    """
    return os.name.startswith('nt')


def is_macosx():
    """
    Returns true if running on a system with a darwin kernel e.g. Mac OS X

    :return: True if system is running a darwin kernel false otherwise
    """
    return sys.platform.startswith('darwin')


def is_linux(distro=None):
    """
    Returns true if running on a system with a linux kernel e.g. Ubuntu, Debian, etc

    :param distro: If not None, check if running that Linux distro
    :return: True if system is running a linux kernel false otherwise
    """
    result = sys.platform.startswith('linux')
    if result and distro:
        result = result and distro == distro_id()
    return result


def is_64bit_instance():
    """
    Returns true if the python/OpenLP instance running is 64 bit. If running a 32 bit instance on
    a 64 bit system this will return false.

    :return: True if the python/OpenLP instance running is 64 bit, otherwise False.
    """
    return (sys.maxsize > 2**32)


__IS_WAYLAND_COMPOSITOR = None


def is_wayland_compositor():
    """
    Returns true if the OpenLP/Qt instance is running in a Wayland compositor.
    NOTE: This checks is only about compositor. Returns True if the application is running in a Wayland compositor.
    Will also return True if application is running on X11/X.org mode in a Wayland compositor/desktop environment

    :return: True if the OpenLP/Qt instance is running in a Wayland compositor, otherwise False
    """
    global __IS_WAYLAND_COMPOSITOR
    if __IS_WAYLAND_COMPOSITOR is None:
        __IS_WAYLAND_COMPOSITOR = bool(os.getenv('WAYLAND_DISPLAY', False))
    return __IS_WAYLAND_COMPOSITOR


def is_xwayland_server():
    """
    Returns true if the OpenLP/Qt instance is running in a XWayland X11 server.
    NOTE: This will be True only if OpenLP is running on X11 mode on a XWayland server

    :return: True if the OpenLP/Qt instance is running in a XWayland X11 server, otherwise False
    """
    return is_wayland_compositor() and is_xorg_platform()


def is_xorg_platform():
    """
    Returns True if the Qt is running on X.org/XWayland platform (Linux/*nix).
    NOTE: This will return True if user is running the OpenLP as X.org application, but on a Wayland/XWayland
    environment.

    :return: True if the Qt is running on X.org/XWayland display server (Linux/*nix), otherwise False.
    """
    from PyQt5 import QtGui
    return QtGui.QGuiApplication.platformName() == 'xcb'


def is_wayland_platform():
    """
    Returns true if the OpenLP/Qt instance is running using Qt's Wayland platform and running in a Wayland compositor

    :return: True if the OpenLP/Qt instance is running in a Wayland compositor, otherwise False
    """
    from PyQt5 import QtGui
    return QtGui.QGuiApplication.platformName() == 'wayland'


# A "modest older PC" baseline (see the OpenLPUG low-resource-mode design): a dual-core CPU and/or
# no more than ~4 GiB of RAM. These are the thresholds below which the low-resource default turns on.
# Kept as named constants so they can be tuned from real measurements without touching the logic.
LOW_SPEC_CPU_COUNT = 2
LOW_SPEC_MEMORY_BYTES = 4 * 1024 ** 3


def get_installed_memory():
    """
    Return the total physical RAM installed, in bytes, or None if it cannot be determined.

    :return: Total physical memory in bytes, or None if the platform can't be queried.
    """
    try:
        if is_win():
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong),
                    ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong),
                    ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong),
                    ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
            return None
        # Linux and macOS both expose the physical page count via sysconf
        if hasattr(os, 'sysconf') and 'SC_PHYS_PAGES' in os.sysconf_names and 'SC_PAGE_SIZE' in os.sysconf_names:
            return int(os.sysconf('SC_PHYS_PAGES')) * int(os.sysconf('SC_PAGE_SIZE'))
    except (OSError, ValueError, AttributeError):
        pass
    return None


__IS_LOW_SPEC_HARDWARE = None


def is_low_spec_hardware():
    """
    Return True if this machine looks like modest/older hardware (few CPU cores and/or little RAM).

    Used to pick the default for low-resource mode so OpenLP stays light on the kind of PC many small
    churches run, while leaving heavier features available (and gate-able) on better hardware. The result
    is cached because the hardware does not change while OpenLP is running.

    :return: True if the machine is at or below the modest-hardware thresholds, otherwise False.
    """
    global __IS_LOW_SPEC_HARDWARE
    if __IS_LOW_SPEC_HARDWARE is None:
        cpu_count = os.cpu_count()
        memory = get_installed_memory()
        low_cpu = cpu_count is not None and cpu_count <= LOW_SPEC_CPU_COUNT
        low_memory = memory is not None and memory <= LOW_SPEC_MEMORY_BYTES
        __IS_LOW_SPEC_HARDWARE = bool(low_cpu or low_memory)
    return __IS_LOW_SPEC_HARDWARE
