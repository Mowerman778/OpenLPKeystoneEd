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
Package to test the openlp.core.lib package.
"""
from sqlite3 import OperationalError as SQLiteOperationalError
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import OperationalError as SQLAlchemyOperationalError

from openlp.core.common.settings import Settings
from openlp.core.db.manager import DBManager


@patch('openlp.core.db.manager.text')
@patch('openlp.core.db.manager.init_url')
@patch('openlp.core.db.manager.create_engine')
def test_manager_finalise_exception(mocked_create_engine: MagicMock, mocked_init_url: MagicMock,
                                    mocked_text: MagicMock, temp_folder: str, settings: Settings):
    """Test that the finalise method silently fails on an exception"""
    # GIVEN: A db Manager object
    mocked_init_url.return_value = f'sqlite:///{temp_folder}/test_db.sqlite'
    mocked_session = MagicMock()
    mocked_text.side_effect = lambda t: t

    def init_schema(url):
        return mocked_session

    mocked_create_engine.return_value.connect.return_value.execute.side_effect = SQLAlchemyOperationalError(
        statement='vacuum',
        params=[],
        orig=SQLiteOperationalError('database is locked')
    )
    manager = DBManager('test', init_schema)
    manager.is_dirty = True

    # WHEN: finalise() is called
    manager.finalise()

    # THEN: vacuum should have been called on the database
    mocked_create_engine.return_value.connect.return_value.execute.assert_called_once_with('vacuum')


@patch('openlp.core.db.manager.text')
@patch('openlp.core.db.manager.init_url')
@patch('openlp.core.db.manager.create_engine')
def test_manager_finalise(mocked_create_engine: MagicMock, mocked_init_url: MagicMock, mocked_text: MagicMock,
                          temp_folder: str, settings: Settings):
    """Test that the finalise method works correctly"""
    # GIVEN: A db Manager object
    mocked_init_url.return_value = f'sqlite:///{temp_folder}/test_db.sqlite'
    mocked_session = MagicMock()
    mocked_text.side_effect = lambda t: t

    def init_schema(url):
        return mocked_session

    manager = DBManager('test', init_schema)
    manager.is_dirty = True

    # WHEN: finalise() is called
    manager.finalise()

    # THEN: vacuum should have been called on the database
    mocked_create_engine.return_value.connect.return_value.execute.assert_called_once_with('vacuum')
