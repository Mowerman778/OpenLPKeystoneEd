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
Test the alerts settings tab
"""
import pytest

from openlp.plugins.alerts.lib.alertstab import AlertsTab


@pytest.fixture()
def alerts_tab(settings):
    return AlertsTab(None, 'Alerts', None, None)


def test_repeat_cannot_be_set_to_zero(alerts_tab):
    """
    Test that the scroll repeat count cannot be set to 0.

    A repeat of 0 gives the scrolling alert a CSS animation-iteration-count of 0, so the animation never runs,
    never reports that it finished, and the alert stays on the display until OpenLP is restarted.
    """
    # GIVEN: The alerts settings tab
    # WHEN: The repeat spin box is wound all the way down
    alerts_tab.repeat_spin_box.setValue(0)

    # THEN: It should clamp to a single pass
    assert alerts_tab.repeat_spin_box.minimum() == 1
    assert alerts_tab.repeat_spin_box.value() == 1


def test_timeout_cannot_be_set_to_zero(alerts_tab):
    """
    Test that the alert timeout cannot be set to 0, which would hide a non-scrolling alert instantly
    """
    # GIVEN: The alerts settings tab
    # WHEN: The timeout spin box is wound all the way down
    alerts_tab.timeout_spin_box.setValue(0)

    # THEN: It should clamp to one second
    assert alerts_tab.timeout_spin_box.minimum() == 1
    assert alerts_tab.timeout_spin_box.value() == 1


def test_speed_is_bounded(alerts_tab):
    """
    Test that the scroll speed is constrained to a usable range
    """
    # GIVEN: The alerts settings tab
    # WHEN/THEN: The speed spin box should not accept a zero or negative duration
    assert alerts_tab.speed_spin_box.minimum() == 1
    assert alerts_tab.speed_spin_box.maximum() == 60
