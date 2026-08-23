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
import pytest
from unittest.mock import MagicMock, patch

from PyQt5 import QtCore

from openlp.core.api import app as flask_app
from openlp.core.state import State

# Mock QtWebEngineWidgets
# sys.modules['PyQt5.QtWebEngineWidgets'] = MagicMock()

from openlp.core.common.registry import Registry
from openlp.core.lib.serviceitem import ServiceItem
from tests.utils import convert_file_service_item
from tests.utils.constants import RESOURCE_PATH


TEST_PATH = RESOURCE_PATH / 'service'

SCREEN = {
    'primary': False,
    'number': 1,
    'size': QtCore.QRect(0, 0, 1024, 768)
}


@pytest.fixture
def test_controller_env(settings):
    mocked_live_controller = MagicMock()
    desktop = MagicMock()
    desktop.primaryScreen.return_value = SCREEN['primary']
    desktop.screenCount.return_value = SCREEN['number']
    desktop.screenGeometry.return_value = SCREEN['size']
    with patch('openlp.core.display.screens.QtWidgets.QApplication.screens') as mocked_screens:
        mocked_screens.return_value = [
            MagicMock(**{'geometry.return_value': SCREEN['size']})
        ]
    # Mock the renderer and its format_slide method
    mocked_renderer = MagicMock()

    def side_effect_return_arg(arg1, arg2):
        return [arg1]

    mocked_slide_formater = MagicMock(side_effect=side_effect_return_arg)
    mocked_renderer.format_slide = mocked_slide_formater
    Registry().register('live_controller', mocked_live_controller)
    Registry().register('renderer', mocked_renderer)
    flask_app.config['TESTING'] = True
    client = flask_app.test_client()
    return mocked_live_controller, client


def test_controller_text_empty(test_controller_env):
    """
    Remote API Tests : test the controller text method can be called with empty service item
    """
    # GIVEN: A mocked service with a dummy service item
    mocked_live_controller = test_controller_env[0]
    client = test_controller_env[1]
    mocked_service_item = MagicMock()
    mocked_service_item.get_frames.return_value = []
    mocked_service_item.unique_identifier = 'mock-service-item'
    mocked_live_controller.service_item = mocked_service_item

    # WHEN: I trigger the method
    ret = client.get('/api/controller/live/text').get_json()

    # THEN: I get a basic set of results
    assert ret['results']['item'] == 'mock-service-item'
    assert len(ret['results']['slides']) == 0


def test_controller_text(test_controller_env):
    """
    Remote API Tests : test the controller text method can be called with a real service item
    """
    # GIVEN: A mocked service with a dummy service item
    mocked_live_controller = test_controller_env[0]
    client = test_controller_env[1]
    line = convert_file_service_item(TEST_PATH, 'serviceitem_custom_1.osj')
    mocked_live_controller.service_item = ServiceItem(None)
    State().load_settings()
    State().add_service("media", 0)
    State().update_pre_conditions("media", True)
    State().flush_preconditions()
    mocked_live_controller.service_item.set_from_service(line)
    mocked_live_controller.service_item._create_slides()
    # WHEN: I trigger the method
    ret = client.get('/api/controller/live/text').get_json()

    # THEN: I get a basic set of results
    results = ret['results']
    assert isinstance(ret, dict)
    assert len(results['slides']) == 2


def test_controller_direction_next(test_controller_env):
    """
    Text the live next method is triggered
    """
    # GIVEN: A mocked service with a dummy service item
    mocked_emit = MagicMock()
    mocked_live_controller = test_controller_env[0]
    client = test_controller_env[1]
    mocked_live_controller.slidecontroller_live_next.emit = mocked_emit
    mocked_live_controller.service_item = MagicMock()

    # WHEN: I trigger the method
    client.get('/api/controller/live/next')
    # THEN: The correct method is called
    mocked_emit.assert_called_once_with()


def test_controller_direction_previous(test_controller_env):
    """
    Text the live next method is triggered
    """
    # GIVEN: A mocked service with a dummy service item
    mocked_emit = MagicMock()
    mocked_live_controller = test_controller_env[0]
    client = test_controller_env[1]
    mocked_live_controller.slidecontroller_live_previous.emit = mocked_emit
    mocked_live_controller.service_item = MagicMock()

    # WHEN: I trigger the method
    client.get('/api/controller/live/previous')
    # THEN: The correct method is called
    mocked_emit.assert_called_once_with()
