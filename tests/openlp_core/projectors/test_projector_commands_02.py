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
Package to test the openlp.core.projectors.pjlink commands package.
"""
from unittest.mock import call, patch

import openlp.core.projectors.pjlink
from openlp.core.projectors.pjlinkcommands import process_command
from openlp.core.projectors.constants import PJLINK_POWR_STATUS, S_ON, S_STANDBY


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_inpt_good(mock_log, pjlink):
    """
    Test input source status shows current input
    """
    # GIVEN: Test object
    pjlink.source = '11'
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "INPT" with data "21"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for INPT'.format(ip=pjlink.name)),
                       call('({ip}) Setting current source to "21"'.format(ip=pjlink.name))]
    chk_source_available = ['11', '12', '21', '22', '31', '32']
    pjlink.source_available = chk_source_available

    # WHEN: Called with input source
    process_command(projector=pjlink, cmd='INPT', data='21')

    # THEN: Input selected should reflect current input
    assert '21' == pjlink.source, 'Input source should be set to "21"'
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_inpt_invalid(mock_log, pjlink):
    """
    Test input source returned not valid according to standard
    """
    # GIVEN: Test object
    log_warning_calls = [call('({ip}) Input source not listed as a PJLink valid source - '
                              'ignoring'.format(ip=pjlink.name))]
    log_debug_calls = [call('({ip}) Processing command "INPT" with data "91"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for INPT'.format(ip=pjlink.name))]
    pjlink.source = None
    pjlink.source_available = None

    # WHEN: Called with input source
    process_command(projector=pjlink, cmd='INPT', data='91')

    # THEN: Input selected should reflect current input
    assert not pjlink.source, 'Input source should not have changed'
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_inpt_not_in_list(mock_log, pjlink):
    """
    Test input source not listed in available sources
    """
    # GIVEN: Test object
    log_warning_calls = [call('({ip}) Input source not listed in available sources - '
                              'ignoring'.format(ip=pjlink.name))]
    log_debug_calls = [call('({ip}) Processing command "INPT" with data "25"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for INPT'.format(ip=pjlink.name))]
    pjlink.source = '11'
    chk_source_available = ['11', '12', '21', '22', '31', '32']
    pjlink.source_available = chk_source_available

    # WHEN: Called with input source
    process_command(projector=pjlink, cmd='INPT', data='25')

    # THEN: Input selected should reflect current input
    assert '11' == pjlink.source, 'Input source should not have changed'
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_inst_class_1(mock_log, pjlink):
    """
    Test saving video source available information
    """

    # GIVEN: Test object
    pjlink.source_available = []
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "INST" with data '
                            '"21 12 11 22 32 31"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for INST'.format(ip=pjlink.name)),
                       call('({ip}) Setting projector source_available to '
                            '"[\'11\', \'12\', \'21\', \'22\', \'31\', \'32\']"'.format(ip=pjlink.name))]

    chk_data = '21 12 11 22 32 31'  # Although they should already be sorted, use unsorted to check method
    chk_test = ['11', '12', '21', '22', '31', '32']

    # WHEN: process_inst called with test data
    process_command(projector=pjlink, cmd='INST', data=chk_data)

    # THEN: Data should have been sorted and saved properly
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
    assert pjlink.source_available == chk_test, "Sources should have been sorted and saved"


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_lamp_invalid_missing_data(mock_log, pjlink):
    """
    Test process lamp with 1 lamp reply hours only and no on/off status
    """
    # GIVEN: Test object
    log_warning_calls = [call('({ip}) process_lamp(): Invalid data "45" - '
                              'Missing data'.format(ip=pjlink.name))]
    log_debug_calls = [call('({ip}) Processing command "LAMP" with data "45"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for LAMP'.format(ip=pjlink.name))]
    pjlink.lamp = None

    # WHEN: Call process_command with 3 lamps
    process_command(projector=pjlink, cmd='LAMP', data='45')

    # THEN: Lamp should have been set with proper lamp status
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
    assert not pjlink.lamp, 'Projector lamp info should not have changed'


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_lamp_invalid_nan(mock_log, pjlink):
    """
    Test status multiple lamp on/off and hours
    """
    # GIVEN: Test object
    pjlink.lamp = [{'Hours': 00000, 'On': True},
                   {'Hours': 11111, 'On': False}]
    log_warning_calls = [call('({ip}) process_lamp(): Invalid data "11111 1 22222 0 '
                              '333A3 1"'.format(ip=pjlink.name))]
    log_debug_calls = [call('({ip}) Processing command "LAMP" with data "11111 1 22222 0 '
                            '333A3 1"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for LAMP'.format(ip=pjlink.name))]

    # WHEN: Call process_command with invalid lamp data
    process_command(projector=pjlink, cmd='LAMP', data='11111 1 22222 0 333A3 1')

    # THEN: lamps should not have changed
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
    assert 2 == len(pjlink.lamp), 'Projector lamp list should not have changed'
    assert pjlink.lamp[0]['On'], 'Lamp 1 power status should not have changed'
    assert 0 == pjlink.lamp[0]['Hours'], 'Lamp 1 hours should not have changed'
    assert not pjlink.lamp[1]['On'], 'Lamp 2 power status should not have changed'
    assert 11111 == pjlink.lamp[1]['Hours'], 'Lamp 2 hours should not have changed'


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_lamp_multiple(mock_log, pjlink):
    """
    Test status multiple lamp on/off and hours
    """
    # GIVEN: Test object
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "LAMP" with data "11111 1 22222 0 '
                            '33333 1"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for LAMP'.format(ip=pjlink.name))]
    pjlink.lamp = None

    # WHEN: Call process_command with 3 lamps
    process_command(projector=pjlink, cmd='LAMP', data='11111 1 22222 0 33333 1')

    # THEN: Lamp should have been set with proper lamp status
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
    assert 3 == len(pjlink.lamp), 'Projector should have 3 lamps specified'
    assert pjlink.lamp[0]['On'], 'Lamp 1 power status should have been set to TRUE'
    assert 11111 == pjlink.lamp[0]['Hours'], 'Lamp 1 hours should have been set to 11111'
    assert not pjlink.lamp[1]['On'], 'Lamp 2 power status should have been set to FALSE'
    assert 22222 == pjlink.lamp[1]['Hours'], 'Lamp 2 hours should have been set to 22222'
    assert pjlink.lamp[2]['On'], 'Lamp 3 power status should have been set to TRUE'
    assert 33333 == pjlink.lamp[2]['Hours'], 'Lamp 3 hours should have been set to 33333'


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_lamp_single(mock_log, pjlink):
    """
    Test status lamp on/off and hours
    """
    # GIVEN: Test object
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "LAMP" with data "11111 1"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for LAMP'.format(ip=pjlink.name))]
    pjlink.lamp = None

    # WHEN: Call process_command with 3 lamps
    process_command(projector=pjlink, cmd='LAMP', data='11111 1')

    # THEN: Lamp should have been set with proper lamp status
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
    assert 1 == len(pjlink.lamp), 'Projector should have 1 lamp specified'
    assert pjlink.lamp[0]['On'], 'Lamp 1 power status should have been set to TRUE'
    assert 11111 == pjlink.lamp[0]['Hours'], 'Lamp 1 hours should have been set to 11111'


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_name(mock_log, pjlink):
    """
    Test saving NAME data from projector
    """
    # GIVEN: Test object
    chk_data = "Some Name the End-User Set IN Projector"
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "NAME" with data '
                            '"Some Name the End-User Set IN Projector"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for NAME'.format(ip=pjlink.name)),
                       call('({ip}) Setting projector PJLink name to '
                            '"Some Name the End-User Set IN Projector"'.format(ip=pjlink.name))]

    # WHEN: process_name called with test data
    process_command(projector=pjlink, cmd='NAME', data=chk_data)

    # THEN: name should be set and logged
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
    assert pjlink.pjlink_name == chk_data, 'Name test data should have been saved'


@patch.object(openlp.core.projectors.pjlink.PJLink, 'send_command')
@patch.object(openlp.core.projectors.pjlink.PJLink, 'change_status')
@patch.object(openlp.core.projectors.pjlink.PJLink, 'projectorUpdateIcons')
@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_powr_invalid(mock_log, mock_UpdateIcons, mock_change_status, mock_send_command, pjlink):
    """
    Test process_powr invalid call
    """
    # GIVEN: Test object
    pjlink.power = S_STANDBY
    log_warning_calls = [call('({ip}) Unknown power response: "99"'.format(ip=pjlink.name))]
    log_debug_calls = [call('({ip}) Processing command "POWR" with data "99"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for POWR'.format(ip=pjlink.name)),
                       call('({ip}) Processing POWR command'.format(ip=pjlink.name))]

    # WHEN: process_command called with test data
    process_command(projector=pjlink, cmd='POWR', data='99')

    # THEN: Projector power should not have changed
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
    assert S_STANDBY == pjlink.power, 'Power should not have changed'
    mock_UpdateIcons.emit.assert_not_called()
    mock_change_status.assert_not_called()
    mock_send_command.assert_not_called()


@patch.object(openlp.core.projectors.pjlink.PJLink, 'send_command')
@patch.object(openlp.core.projectors.pjlink.PJLink, 'change_status')
@patch.object(openlp.core.projectors.pjlink.PJLink, 'projectorUpdateIcons')
@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_powr_off(mock_log, mock_UpdateIcons, mock_change_status, mock_send_command, pjlink):
    """
    Test status power to OFF
    """
    # GIVEN: Test object
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "POWR" with data "0"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for POWR'.format(ip=pjlink.name)),
                       call('({ip}) Processing POWR command'.format(ip=pjlink.name))]
    pjlink.power = S_ON

    # WHEN: process_name called with test data
    process_command(projector=pjlink, cmd='POWR', data=PJLINK_POWR_STATUS[S_STANDBY])

    # THEN: Power should be set to ON
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
    assert S_STANDBY == pjlink.power, 'Power should have been set to OFF'
    assert mock_UpdateIcons.emit.called, 'projectorUpdateIcons should have been called'
    assert not mock_send_command.called, 'send_command should not have been called'
    mock_change_status.assert_called_once_with(S_STANDBY)


@patch.object(openlp.core.projectors.pjlink.PJLink, 'send_command')
@patch.object(openlp.core.projectors.pjlink.PJLink, 'change_status')
@patch.object(openlp.core.projectors.pjlink.PJLink, 'projectorUpdateIcons')
@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_powr_on(mock_log, mock_UpdateIcons, mock_change_status, mock_send_command, pjlink):
    """
    Test status power to ON
    """
    # GIVEN: Test object
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "POWR" with data "1"'.format(ip=pjlink.name)),
                       call('({ip}) Calling function for POWR'.format(ip=pjlink.name)),
                       call('({ip}) Processing POWR command'.format(ip=pjlink.name))]
    pjlink.power = S_STANDBY

    # WHEN: process_name called with test data
    process_command(projector=pjlink, cmd='POWR', data=PJLINK_POWR_STATUS[S_ON])

    # THEN: Power should be set to ON
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
    assert S_ON == pjlink.power, 'Power should have been set to ON'
    assert mock_UpdateIcons.emit.called, 'projectorUpdateIcons should have been called'
    mock_send_command.assert_called_once_with('INST')
    mock_change_status.assert_called_once_with(S_ON)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_rfil_save(mock_log, pjlink):
    """
    Test saving filter type
    """
    # GIVEN: Test object
    new_data = 'Filter Type Test'
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "RFIL" with data '
                            '"{data}"'.format(ip=pjlink.name, data=new_data)),
                       call('({ip}) Calling function for RFIL'.format(ip=pjlink.name))]
    pjlink.model_filter = None

    # WHEN: Filter model is received
    process_command(projector=pjlink, cmd='RFIL', data=new_data)

    # THEN: Filter model number should be saved
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
    assert pjlink.model_filter == new_data, 'Filter model should have been saved'


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_rfil_nosave(mock_log, pjlink):
    """
    Test saving filter type previously saved
    """
    # GIVEN: Test object
    old_data = 'Old filter type'
    new_data = 'Filter Type Test'
    log_warning_calls = [call('({ip}) Filter model already set'.format(ip=pjlink.name)),
                         call('({ip}) Saved model: "{data}"'.format(ip=pjlink.name, data=old_data)),
                         call('({ip}) New model: "{data}"'.format(ip=pjlink.name, data=new_data))]
    log_debug_calls = [call('({ip}) Processing command "RFIL" with data '
                            '"{data}"'.format(ip=pjlink.name, data=new_data)),
                       call('({ip}) Calling function for RFIL'.format(ip=pjlink.name))]
    pjlink.model_filter = old_data

    # WHEN: Filter model is received
    process_command(projector=pjlink, cmd='RFIL', data=new_data)

    # THEN: Filter model number should be saved
    assert pjlink.model_filter != new_data, 'Filter model should NOT have been saved'
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_rlmp_save(mock_log, pjlink):
    """
    Test saving lamp type
    """
    # GIVEN: Test object
    new_data = 'Lamp Type Test'
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "RLMP" with data '
                            '"{data}"'.format(ip=pjlink.name, data=new_data)),
                       call('({ip}) Calling function for RLMP'.format(ip=pjlink.name))]
    pjlink.model_lamp = None

    # WHEN: Filter model is received
    process_command(projector=pjlink, cmd='RLMP', data=new_data)

    # THEN: Filter model number should be saved
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
    assert pjlink.model_lamp == new_data, 'Lamp model should have been saved'


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_rlmp_nosave(mock_log, pjlink):
    """
    Test saving lamp type previously saved
    """
    # GIVEN: Test object
    old_data = 'Old filter type'
    new_data = 'Filter Type Test'
    log_warning_calls = [call('({ip}) Lamp model already set'.format(ip=pjlink.name)),
                         call('({ip}) Saved lamp: "{data}"'.format(ip=pjlink.name, data=old_data)),
                         call('({ip}) New lamp: "{data}"'.format(ip=pjlink.name, data=new_data))]
    log_debug_calls = [call('({ip}) Processing command "RLMP" with data '
                            '"{data}"'.format(ip=pjlink.name, data=new_data)),
                       call('({ip}) Calling function for RLMP'.format(ip=pjlink.name))]
    pjlink.model_lamp = old_data

    # WHEN: Filter model is received
    process_command(projector=pjlink, cmd='RLMP', data=new_data)

    # THEN: Filter model number should be saved
    assert pjlink.model_lamp != new_data, 'Lamp model should NOT have been saved'
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_snum_different(mock_log, pjlink):
    """
    Test projector serial number different than saved serial number
    """
    # GIVEN: Test object
    new_data = 'Test Serial Number'
    old_data = 'Previous serial number'
    log_warning_calls = [call('({ip}) Projector serial number does not match '
                              'saved serial number'.format(ip=pjlink.name)),
                         call('({ip}) Saved:    "{data}"'.format(ip=pjlink.name, data=old_data)),
                         call('({ip}) Received: "{data}"'.format(ip=pjlink.name, data=new_data)),
                         call('({ip}) NOT saving serial number'.format(ip=pjlink.name))]

    log_debug_calls = [call('({ip}) Processing command "SNUM" with data '
                            '"{data}"'.format(ip=pjlink.name, data=new_data)),
                       call('({ip}) Calling function for SNUM'.format(ip=pjlink.name))]
    pjlink.serial_no = old_data

    # WHEN: No serial number is set and we receive serial number command
    process_command(projector=pjlink, cmd='SNUM', data=new_data)

    # THEN: Serial number should be set
    assert pjlink.serial_no != new_data, 'Projector serial number should NOT have been set'
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_snum_set(mock_log, pjlink):
    """
    Test saving serial number from projector
    """
    # GIVEN: Test object
    new_data = 'Test Serial Number'
    pjlink.serial_no = None
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "SNUM" with data "{data}"'.format(ip=pjlink.name,
                                                                                         data=new_data)),
                       call('({ip}) Calling function for SNUM'.format(ip=pjlink.name)),
                       call('({ip}) Setting projector serial number to '
                            '"{data}"'.format(ip=pjlink.name, data=new_data))]

    # WHEN: No serial number is set and we receive serial number command
    process_command(projector=pjlink, cmd='SNUM', data=new_data)

    # THEN: Serial number should be set
    assert pjlink.serial_no == new_data, 'Projector serial number should have been set'
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
