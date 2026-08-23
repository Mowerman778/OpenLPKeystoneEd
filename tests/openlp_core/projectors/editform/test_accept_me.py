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
Test ProjectorEditForm.accept_me
"""
import logging

import openlp.core.projectors.db
import openlp.core.projectors.editform

from unittest.mock import DEFAULT, patch

from openlp.core.projectors.constants import PJLINK_VALID_PORTS
from openlp.core.projectors.db import Projector
from tests.resources.projector.data import TEST1_DATA

_test_module = openlp.core.projectors.editform.__name__
_test_module_db = openlp.core.projectors.db.__name__
Message = openlp.core.projectors.editform.Message


def test_name_NameBlank(projector_editform_mtdb, caplog):
    """
    Test when name field blank
    """
    # GIVEN: Test setup
    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received')]
    projector_editform_mtdb.exec()
    projector_editform_mtdb.name_text.setText('')

    # WHEN: Called
    caplog.clear()
    projector_editform_mtdb.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform_mtdb.mock_msg_box.warning.assert_called_once_with(None,
                                                                         Message.NameBlank['title'],
                                                                         Message.NameBlank['text']
                                                                         )


def test_name_DatabaseError_id(projector_editform_mtdb, caplog):
    """
    Test with mismatch ID between Projector() and DB
    """
    # GIVEN: Test setup
    t_id = TEST1_DATA['id']
    t_name = TEST1_DATA['name']
    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name'),
            (_test_module, logging.WARNING,
             f'editform(): No record found but projector had id={t_id}')]
    projector_editform_mtdb.exec()
    projector_editform_mtdb.name_text.setText(t_name)
    projector_editform_mtdb.projector.id = t_id

    # WHEN: Called
    caplog.clear()
    projector_editform_mtdb.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform_mtdb.mock_msg_box.warning.assert_called_once_with(None,
                                                                         Message.DatabaseError['title'],
                                                                         Message.DatabaseError['text']
                                                                         )


def test_name_DatabaseError_name(projector_editform_mtdb, caplog):
    """
    Test with mismatch between name and DB
    """
    # GIVEN: Test setup
    t_name = TEST1_DATA['name']
    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name'),
            (_test_module, logging.WARNING,
             f'editform(): No record found when there should be name="{t_name}"')]
    projector_editform_mtdb.exec()
    projector_editform_mtdb.name_text.setText(t_name)
    projector_editform_mtdb.projector.name = t_name
    projector_editform_mtdb.new_projector = False

    # WHEN: Called
    caplog.clear()
    projector_editform_mtdb.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform_mtdb.mock_msg_box.warning.assert_called_once_with(None,
                                                                         Message.DatabaseError['title'],
                                                                         Message.DatabaseError['text']
                                                                         )


def test_name_NameDuplicate(projector_editform, caplog):
    """
    Test when name duplicate
    """
    # GIVEN: Test setup
    t_name = TEST1_DATA['name']
    # As long as the new record port number is different, we should be good
    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name'),
            (_test_module, logging.WARNING, f'editform(): Name "{t_name}" already in database')
            ]
    projector_editform.exec()
    projector_editform.name_text.setText(t_name)
    projector_editform.projector.name = t_name

    # WHEN: Called
    caplog.clear()
    projector_editform.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform.mock_msg_box.warning.assert_called_once_with(None,
                                                                    Message.NameDuplicate['title'],
                                                                    Message.NameDuplicate['text']
                                                                    )


def test_name_DatabaseMultiple(projector_editform, caplog):
    """
    Test when multiple database records have the same name
    """
    # GIVEN: Test setup
    # Save another instance of TEST1_DATA
    t_proj = Projector(**TEST1_DATA)
    t_proj.id = None
    projector_editform.projectordb.save_object(t_proj)

    # Test variables
    t_id1 = TEST1_DATA['id']
    # There should only be 3 records in the DB, TEST[1,2,3]_DATA
    # The above save_object() should have created record 4
    t_id2 = t_proj.id
    t_name = TEST1_DATA['name']
    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name'),
            (_test_module, logging.WARNING, f'editform(): Multiple records found for name "{t_name}"'),
            (_test_module, logging.WARNING, f'editform() Found record={t_id1} name="{t_name}"'),
            (_test_module, logging.WARNING, f'editform() Found record={t_id2} name="{t_name}"')
            ]
    projector_editform.exec()
    projector_editform.name_text.setText(t_name)

    # WHEN: Called
    caplog.clear()
    projector_editform.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform.mock_msg_box.warning.assert_called_once_with(None,
                                                                    Message.DatabaseMultiple['title'],
                                                                    Message.DatabaseMultiple['text']
                                                                    )


def test_ip_IPBlank(projector_editform_mtdb, caplog):
    """
    Test when IP field blank
    """
    # GIVEN: Test setup
    t_name = TEST1_DATA['name']
    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name')]
    projector_editform_mtdb.exec()
    projector_editform_mtdb.name_text.setText(t_name)
    projector_editform_mtdb.ip_text.setText('')

    # WHEN: Called
    caplog.clear()
    projector_editform_mtdb.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform_mtdb.mock_msg_box.warning.assert_called_once_with(None,
                                                                         Message.IPBlank['title'],
                                                                         Message.IPBlank['text']
                                                                         )


def test_ip_IPInvalid(projector_editform_mtdb, caplog):
    """
    Test when IP invalid
    """
    # GIVEN: Test setup
    t_name = TEST1_DATA['name']
    t_ip = 'a'
    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name')]
    projector_editform_mtdb.exec()
    projector_editform_mtdb.name_text.setText(t_name)
    projector_editform_mtdb.ip_text.setText(t_ip)

    # WHEN: Called
    caplog.clear()
    projector_editform_mtdb.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform_mtdb.mock_msg_box.warning.assert_called_once_with(None,
                                                                         Message.IPInvalid['title'],
                                                                         Message.IPInvalid['text']
                                                                         )


def test_port_PortBlank(projector_editform_mtdb, caplog):
    """
    Test when port field blank
    """
    # GIVEN: Test setup
    t_name = TEST1_DATA['name']
    t_ip = TEST1_DATA['ip']
    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name'),
            ]
    projector_editform_mtdb.exec()
    projector_editform_mtdb.name_text.setText(t_name)
    projector_editform_mtdb.ip_text.setText(t_ip)
    projector_editform_mtdb.port_text.setText('')

    # WHEN: Called
    caplog.clear()
    projector_editform_mtdb.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform_mtdb.mock_msg_box.warning.assert_called_once_with(None,
                                                                         Message.PortBlank['title'],
                                                                         Message.PortBlank['text']
                                                                         )


def test_port_PortInvalid_not_decimal(projector_editform_mtdb, caplog):
    """
    Test when port not a decimal digit
    """
    # GIVEN: Test setup
    t_name = TEST1_DATA['name']
    t_ip = TEST1_DATA['ip']
    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name'),
            ]
    projector_editform_mtdb.exec()
    projector_editform_mtdb.name_text.setText(t_name)
    projector_editform_mtdb.ip_text.setText(t_ip)
    projector_editform_mtdb.port_text.setText('a')

    # WHEN: Called
    caplog.clear()
    projector_editform_mtdb.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform_mtdb.mock_msg_box.warning.assert_called_once_with(None,
                                                                         Message.PortInvalid['title'],
                                                                         Message.PortInvalid['text']
                                                                         )


def test_port_PortInvalid_low(projector_editform_mtdb, caplog):
    """
    Test when port number less than PJLINK_VALID_PORTS lower value
    """
    # GIVEN: Test setup
    t_name = TEST1_DATA['name']
    t_ip = TEST1_DATA['ip']
    t_port = PJLINK_VALID_PORTS.start - 1
    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name'),
            ]
    projector_editform_mtdb.exec()
    projector_editform_mtdb.name_text.setText(t_name)
    projector_editform_mtdb.ip_text.setText(t_ip)
    projector_editform_mtdb.port_text.setText(str(t_port))

    # WHEN: Called
    caplog.clear()
    projector_editform_mtdb.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform_mtdb.mock_msg_box.warning.assert_called_once_with(None,
                                                                         Message.PortInvalid['title'],
                                                                         Message.PortInvalid['text']
                                                                         )


def test_port_PortInvalid_high(projector_editform_mtdb, caplog):
    """
    Test when port number greater than PJLINK_VALID_PORTS higher value
    """
    # GIVEN: Test setup
    t_name = TEST1_DATA['name']
    t_ip = TEST1_DATA['ip']
    t_port = PJLINK_VALID_PORTS.stop + 1
    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name'),
            ]
    projector_editform_mtdb.exec()
    projector_editform_mtdb.name_text.setText(t_name)
    projector_editform_mtdb.ip_text.setText(t_ip)
    projector_editform_mtdb.port_text.setText(str(t_port))

    # WHEN: Called
    caplog.clear()
    projector_editform_mtdb.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform_mtdb.mock_msg_box.warning.assert_called_once_with(None,
                                                                         Message.PortInvalid['title'],
                                                                         Message.PortInvalid['text']
                                                                         )


def test_adx_AddressDuplicate(projector_editform, caplog):
    """
    Test when IP:Port address duplicate
    """
    # GIVEN: Test setup
    t_ip = TEST1_DATA['ip']
    t_port = TEST1_DATA['port']

    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name'),
            (_test_module_db, logging.DEBUG, 'Filter by IP Port'),
            (_test_module, logging.WARNING, f'editform(): Address already in database {t_ip}:{t_port}')
            ]
    projector_editform.exec()
    projector_editform.name_text.setText('A Different Name Not In DB')
    projector_editform.ip_text.setText(t_ip)
    projector_editform.port_text.setText(str(t_port))

    # WHEN: Called
    caplog.clear()
    projector_editform.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform.mock_msg_box.warning.assert_called_once_with(None,
                                                                    Message.AddressDuplicate['title'],
                                                                    Message.AddressDuplicate['text']
                                                                    )


def test_adx_DatabaseMultiple(projector_editform, caplog):
    """
    Test when database has multiple same IP:Port records
    """
    # GIVEN: Test setup
    t_proj = Projector(**TEST1_DATA)
    t_proj.id = None
    projector_editform.projectordb.save_object(t_proj)
    t_id1 = TEST1_DATA['id']
    t_id2 = t_proj.id
    t_name = TEST1_DATA['name']
    t_ip = TEST1_DATA['ip']
    t_port = TEST1_DATA['port']

    caplog.set_level(logging.DEBUG)
    logs = [(_test_module, logging.DEBUG, 'accept_me() signal received'),
            (_test_module_db, logging.DEBUG, 'Filter by Name'),
            (_test_module_db, logging.DEBUG, 'Filter by IP Port'),
            (_test_module, logging.WARNING, f'editform(): Multiple records found for {t_ip}:{t_port}'),
            (_test_module, logging.WARNING, f'editform(): record={t_id1} name="{t_name}" adx={t_ip}:{t_port}'),
            (_test_module, logging.WARNING, f'editform(): record={t_id2} name="{t_name}" adx={t_ip}:{t_port}')
            ]
    projector_editform.exec()
    projector_editform.name_text.setText('A Different Name Not In DB')
    projector_editform.ip_text.setText(t_ip)
    projector_editform.port_text.setText(str(t_port))

    # WHEN: Called
    caplog.clear()
    projector_editform.accept_me()

    # THEN: Appropriate calls made
    assert caplog.record_tuples == logs, 'Invalid logs'
    projector_editform.mock_msg_box.warning.assert_called_once_with(None,
                                                                    Message.DatabaseMultiple['title'],
                                                                    Message.DatabaseMultiple['text']
                                                                    )


@patch.multiple(openlp.core.projectors.editform.ProjectorEditForm, updateProjectors=DEFAULT, close=DEFAULT)
@patch.object(openlp.core.projectors.db.ProjectorDB, 'add_projector')
def test_save_new(mock_add, projector_editform_mtdb, **kwargs):
    """
    Test editform saving new projector instance where db fails to save
    """
    # GIVEN: Test environment
    mock_update = kwargs['updateProjectors']
    mock_close = kwargs['close']
    mock_add.return_value = True

    t_proj = Projector(**TEST1_DATA)
    t_proj.id = None
    projector_editform_mtdb.new_projector = True
    projector_editform_mtdb.exec()
    projector_editform_mtdb.name_text.setText(t_proj.name)
    projector_editform_mtdb.ip_text.setText(t_proj.ip)
    projector_editform_mtdb.port_text.setText(str(t_proj.port))

    # WHEN: Called
    projector_editform_mtdb.accept_me()

    # THEN: appropriate message called
    projector_editform_mtdb.mock_msg_box.warning.assert_not_called()
    mock_update.emit.assert_called_once()
    mock_close.assert_called_once()


@patch.multiple(openlp.core.projectors.editform.ProjectorEditForm, updateProjectors=DEFAULT, close=DEFAULT)
@patch.object(openlp.core.projectors.db.ProjectorDB, 'add_projector')
def test_save_new_fail(mock_add, projector_editform_mtdb, caplog, **kwargs):
    """
    Test editform saving new projector instance where db fails to save
    """
    # GIVEN: Test environment
    mock_update = kwargs['updateProjectors']
    mock_close = kwargs['close']
    mock_add.return_value = False

    caplog.set_level(logging.DEBUG)
    t_proj = Projector(**TEST1_DATA)
    t_proj.id = None
    projector_editform_mtdb.new_projector = True
    projector_editform_mtdb.exec()
    projector_editform_mtdb.name_text.setText(t_proj.name)
    projector_editform_mtdb.ip_text.setText(t_proj.ip)
    projector_editform_mtdb.port_text.setText(str(t_proj.port))

    # WHEN: Called
    projector_editform_mtdb.accept_me()

    # THEN: appropriate message called
    mock_add.assert_called_once_with(projector_editform_mtdb.projector)
    projector_editform_mtdb.mock_msg_box.warning.assert_called_once_with(None,
                                                                         Message.DatabaseError['title'],
                                                                         Message.DatabaseError['text']
                                                                         )
    mock_update.assert_not_called()
    mock_close.assert_not_called()


@patch.multiple(openlp.core.projectors.editform.ProjectorEditForm, updateProjectors=DEFAULT, close=DEFAULT)
@patch.object(openlp.core.projectors.db.ProjectorDB, 'update_projector')
def test_save_update(mock_add, projector_editform, **kwargs):
    """
    Test editform update projector instance in database
    """
    # GIVEN: Test environment
    mock_update = kwargs['updateProjectors']
    mock_close = kwargs['close']
    mock_add.return_value = True

    t_proj = Projector(**TEST1_DATA)
    projector_editform.new_projector = True
    projector_editform.exec(projector=t_proj)
    projector_editform.name_text.setText(t_proj.name)
    projector_editform.ip_text.setText(t_proj.ip)
    projector_editform.port_text.setText(str(t_proj.port))

    # WHEN: Called
    projector_editform.accept_me()

    # THEN: appropriate message called
    projector_editform.mock_msg_box.warning.assert_not_called()
    mock_update.emit.assert_called_once()
    mock_close.assert_called_once()


@patch.multiple(openlp.core.projectors.editform.ProjectorEditForm, updateProjectors=DEFAULT, close=DEFAULT)
@patch.object(openlp.core.projectors.db.ProjectorDB, 'update_projector')
def test_save_update_fail(mock_add, projector_editform, caplog, **kwargs):
    """
    Test editform updating projector instance where db fails to save
    """
    # GIVEN: Test environment
    mock_update = kwargs['updateProjectors']
    mock_close = kwargs['close']
    mock_add.return_value = False

    caplog.set_level(logging.DEBUG)
    t_proj = Projector(**TEST1_DATA)
    projector_editform.exec(projector=t_proj)
    projector_editform.name_text.setText(t_proj.name)
    projector_editform.ip_text.setText(t_proj.ip)
    projector_editform.port_text.setText(str(t_proj.port))

    # WHEN: Called
    projector_editform.accept_me()

    # THEN: appropriate message called
    mock_add.assert_called_once_with(projector_editform.projector)
    projector_editform.mock_msg_box.warning.assert_called_once_with(None,
                                                                    Message.DatabaseError['title'],
                                                                    Message.DatabaseError['text']
                                                                    )
    mock_update.assert_not_called()
    mock_close.assert_not_called()
