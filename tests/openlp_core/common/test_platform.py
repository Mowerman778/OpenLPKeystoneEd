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
Functional tests to test the :mod:`~openlp.core.common.platform` module.
"""
from unittest.mock import patch

import pytest

import openlp.core.common.platform as platform_module
from openlp.core.common.platform import (LOW_SPEC_CPU_COUNT, LOW_SPEC_MEMORY_BYTES, get_installed_memory,
                                         is_64bit_instance, is_linux, is_low_spec_hardware, is_macosx, is_win)


@pytest.fixture(autouse=True)
def _reset_low_spec_cache():
    """is_low_spec_hardware() caches its result; clear it around every test."""
    setattr(platform_module, '__IS_LOW_SPEC_HARDWARE', None)
    yield
    setattr(platform_module, '__IS_LOW_SPEC_HARDWARE', None)


def test_is_win():
    """
    Test the is_win() function
    """
    # GIVEN: Mocked out objects
    with patch('openlp.core.common.platform.os') as mocked_os, \
            patch('openlp.core.common.platform.sys') as mocked_sys:

        # WHEN: The mocked os.name and sys.platform are set to 'nt' and 'win32' repectivly
        mocked_os.name = 'nt'
        mocked_sys.platform = 'win32'

        # THEN: The three platform functions should perform properly
        assert is_win() is True, 'is_win() should return True'
        assert is_macosx() is False, 'is_macosx() should return False'
        assert is_linux() is False, 'is_linux() should return False'


def test_is_macosx():
    """
    Test the is_macosx() function
    """
    # GIVEN: Mocked out objects
    with patch('openlp.core.common.platform.os') as mocked_os, \
            patch('openlp.core.common.platform.sys') as mocked_sys:

        # WHEN: The mocked os.name and sys.platform are set to 'posix' and 'darwin' repectivly
        mocked_os.name = 'posix'
        mocked_sys.platform = 'darwin'

        # THEN: The three platform functions should perform properly
        assert is_macosx() is True, 'is_macosx() should return True'
        assert is_win() is False, 'is_win() should return False'
        assert is_linux() is False, 'is_linux() should return False'


def test_is_linux():
    """
    Test the is_linux() function
    """
    # GIVEN: Mocked out objects
    with patch('openlp.core.common.platform.os') as mocked_os, \
            patch('openlp.core.common.platform.sys') as mocked_sys:

        # WHEN: The mocked os.name and sys.platform are set to 'posix' and 'linux3' repectively
        mocked_os.name = 'posix'
        mocked_sys.platform = 'linux3'

        # THEN: The three platform functions should perform properly
        assert is_linux() is True, 'is_linux() should return True'
        assert is_win() is False, 'is_win() should return False'
        assert is_macosx() is False, 'is_macosx() should return False'


@pytest.mark.skipif(not is_linux(), reason='This can only run on Linux')
def test_is_linux_distro():
    """
    Test the is_linux() function for a particular Linux distribution
    """
    # GIVEN: Mocked out objects
    with patch('openlp.core.common.platform.os') as mocked_os, \
            patch('openlp.core.common.platform.sys') as mocked_sys, \
            patch('openlp.core.common.platform.distro_id') as mocked_distro_id:

        # WHEN: The mocked os.name and sys.platform are set to 'posix' and 'linux3' repectively
        #       and the distro is Fedora
        mocked_os.name = 'posix'
        mocked_sys.platform = 'linux3'
        mocked_distro_id.return_value = 'fedora'

        # THEN: The three platform functions should perform properly
        assert is_linux(distro='fedora') is True, 'is_linux(distro="fedora") should return True'
        assert is_win() is False, 'is_win() should return False'
        assert is_macosx() is False, 'is_macosx() should return False'


def test_is_64bit_instance():
    """
    Test the is_64bit_instance() function
    """
    # GIVEN: Mocked out objects
    with patch('openlp.core.common.platform.sys') as mocked_sys:

        # WHEN: The mocked sys.maxsize is set to 32-bit
        mocked_sys.maxsize = 2**32

        # THEN: The result should be False
        assert is_64bit_instance() is False, 'is_64bit_instance() should return False'


def test_get_installed_memory_returns_positive_or_none():
    """Test get_installed_memory() returns a plausible byte count on the host (or None)"""
    # GIVEN/WHEN: We query the installed memory on the real host
    memory = get_installed_memory()

    # THEN: It is either None (unknown platform) or a sane positive number of bytes
    assert memory is None or (isinstance(memory, int) and memory > 0)


def test_is_low_spec_hardware_true_on_few_cpus():
    """Test is_low_spec_hardware() is True when the CPU count is at/below the threshold"""
    # GIVEN: A machine with few cores but plenty of RAM
    with patch('openlp.core.common.platform.os.cpu_count', return_value=LOW_SPEC_CPU_COUNT), \
            patch('openlp.core.common.platform.get_installed_memory', return_value=32 * 1024 ** 3):
        # WHEN/THEN: It is judged low-spec because of the CPU count
        assert is_low_spec_hardware() is True


def test_is_low_spec_hardware_true_on_low_memory():
    """Test is_low_spec_hardware() is True when RAM is at/below the threshold"""
    # GIVEN: A machine with many cores but little RAM
    with patch('openlp.core.common.platform.os.cpu_count', return_value=16), \
            patch('openlp.core.common.platform.get_installed_memory', return_value=LOW_SPEC_MEMORY_BYTES):
        # WHEN/THEN: It is judged low-spec because of the RAM
        assert is_low_spec_hardware() is True


def test_is_low_spec_hardware_false_on_capable_machine():
    """Test is_low_spec_hardware() is False on a capable machine"""
    # GIVEN: A machine comfortably above both thresholds
    with patch('openlp.core.common.platform.os.cpu_count', return_value=8), \
            patch('openlp.core.common.platform.get_installed_memory', return_value=16 * 1024 ** 3):
        # WHEN/THEN: It is not low-spec
        assert is_low_spec_hardware() is False


def test_is_low_spec_hardware_handles_unknown_memory():
    """Test is_low_spec_hardware() copes when memory can't be determined"""
    # GIVEN: A capable CPU and unknown memory
    with patch('openlp.core.common.platform.os.cpu_count', return_value=8), \
            patch('openlp.core.common.platform.get_installed_memory', return_value=None):
        # WHEN/THEN: With no low signal, it is not low-spec
        assert is_low_spec_hardware() is False
