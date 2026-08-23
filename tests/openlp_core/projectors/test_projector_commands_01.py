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
from openlp.core.projectors.constants import E_ERROR, E_WARN, PJLINK_ERST_DATA, PJLINK_ERST_STATUS, S_OK


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_ackn(mock_log, pjlink):
    """
    Test ackn command (empty test)
    """
    # GIVEN: Test setup
    log_debug_text = [call('({ip}) Processing command "ACKN" with data "0"'.format(ip=pjlink.name)),
                      call('({ip}) Calling function for ACKN'.format(ip=pjlink.name))]

    # WHEN: Called with setting shutter closed and mute on
    process_command(projector=pjlink, cmd='ACKN', data='0')

    # THEN: Shutter should be closed and mute should be True
    mock_log.debug.assert_has_calls(log_debug_text)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_erst_all_error(mock_log, pjlink):
    """
    Test test_projector_process_erst_all_error
    """
    # GIVEN: Test object
    chk_data = '{fan}{lamp}{temp}{cover}{filt}{other}'.format(fan=PJLINK_ERST_STATUS[E_ERROR],
                                                              lamp=PJLINK_ERST_STATUS[E_ERROR],
                                                              temp=PJLINK_ERST_STATUS[E_ERROR],
                                                              cover=PJLINK_ERST_STATUS[E_ERROR],
                                                              filt=PJLINK_ERST_STATUS[E_ERROR],
                                                              other=PJLINK_ERST_STATUS[E_ERROR])
    chk_test = {'Fan': E_ERROR,
                'Lamp': E_ERROR,
                'Temperature': E_ERROR,
                'Cover': E_ERROR,
                'Filter': E_ERROR,
                'Other': E_ERROR}
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "ERST" with data "{chk}"'.format(ip=pjlink.name,
                                                                                        chk=chk_data)),
                       call('({ip}) Calling function for ERST'.format(ip=pjlink.name))]
    pjlink.projector_errors = None

    # WHEN: process_erst with status set to WARN
    process_command(projector=pjlink, cmd='ERST', data=chk_data)

    # THEN: PJLink instance errors should match chk_value
    assert pjlink.projector_errors == chk_test, 'Projector errors should be all E_ERROR'
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_erst_all_ok(mock_log, pjlink):
    """
    Test to verify pjlink.projector_errors is set to None when no errors
    """
    # GIVEN: Test object
    chk_data = '0' * PJLINK_ERST_DATA['DATA_LENGTH']
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "ERST" with data "{chk}"'.format(ip=pjlink.name,
                                                                                        chk=chk_data)),
                       call('({ip}) Calling function for ERST'.format(ip=pjlink.name))]

    # WHEN: process_erst with no errors
    process_command(projector=pjlink, cmd='ERST', data=chk_data)

    # THEN: PJLink instance errors should be None
    assert pjlink.projector_errors is None, 'projector_errors should have been set to None'
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_erst_all_warn(mock_log, pjlink):
    """
    Test test_projector_process_erst_all_error
    """
    # GIVEN: Test object
    chk_data = '{fan}{lamp}{temp}{cover}{filt}{other}'.format(fan=PJLINK_ERST_STATUS[E_WARN],
                                                              lamp=PJLINK_ERST_STATUS[E_WARN],
                                                              temp=PJLINK_ERST_STATUS[E_WARN],
                                                              cover=PJLINK_ERST_STATUS[E_WARN],
                                                              filt=PJLINK_ERST_STATUS[E_WARN],
                                                              other=PJLINK_ERST_STATUS[E_WARN])
    chk_test = {'Fan': E_WARN,
                'Lamp': E_WARN,
                'Temperature': E_WARN,
                'Cover': E_WARN,
                'Filter': E_WARN,
                'Other': E_WARN}
    log_warning_calls = []
    log_debug_calls = [call('({ip}) Processing command "ERST" with data "{chk}"'.format(ip=pjlink.name,
                                                                                        chk=chk_data)),
                       call('({ip}) Calling function for ERST'.format(ip=pjlink.name))]
    pjlink.projector_errors = None

    # WHEN: process_erst with status set to WARN
    process_command(projector=pjlink, cmd='ERST', data=chk_data)

    # THEN: PJLink instance errors should match chk_value
    assert pjlink.projector_errors == chk_test, 'Projector errors should be all E_WARN'
    mock_log.warning.assert_has_calls(log_warning_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_erst_data_invalid_length(mock_log, pjlink):
    """
    Test test_projector_process_erst_data_invalid_length
    """
    # GIVEN: Test object
    chk_data = '0' * (PJLINK_ERST_DATA['DATA_LENGTH'] + 1)
    log_warn_calls = [call('({ip}) Invalid error status response "{data}": '
                           'length != {chk}'.format(ip=pjlink.name,
                                                    data=chk_data, chk=PJLINK_ERST_DATA['DATA_LENGTH']))]
    log_debug_calls = [call('({ip}) Processing command "ERST" with data "{data}"'.format(ip=pjlink.name,
                                                                                         data=chk_data)),
                       call('({ip}) Calling function for ERST'.format(ip=pjlink.name))]
    pjlink.projector_errors = None

    # WHEN: process_erst called with invalid data (too many values
    process_command(pjlink, cmd='ERST', data=chk_data)

    # THEN: pjlink.projector_errors should be empty and warning logged
    assert not pjlink.projector_errors, 'There should be no errors'
    mock_log.warning.assert_has_calls(log_warn_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_erst_data_invalid_nan(mock_log, pjlink):
    """
    Test ERST called with invalid data
    """
    # GIVEN: Test object
    chk_data = 'Z' + ('0' * (PJLINK_ERST_DATA['DATA_LENGTH'] - 1))
    log_warn_calls = [call('({ip}) Invalid error status response "{data}"'.format(ip=pjlink.name,
                                                                                  data=chk_data))]
    log_debug_calls = [call('({ip}) Processing command "ERST" with data "{data}"'.format(ip=pjlink.name,
                                                                                         data=chk_data)),
                       call('({ip}) Calling function for ERST'.format(ip=pjlink.name))]
    pjlink.projector_errors = None

    # WHEN: process_erst called with invalid data (too many values
    process_command(pjlink, cmd='ERST', data=chk_data)

    # THEN: pjlink.projector_errors should be empty and warning logged
    assert not pjlink.projector_errors, 'There should be no errors'
    mock_log.warning.assert_has_calls(log_warn_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_erst_warn_cover_only(mock_log, pjlink):
    """
    Test test_projector_process_erst_warn_cover_only
    """
    # GIVEN: Test object
    chk_data = '{fan}{lamp}{temp}{cover}{filt}{other}'.format(fan=PJLINK_ERST_STATUS[S_OK],
                                                              lamp=PJLINK_ERST_STATUS[S_OK],
                                                              temp=PJLINK_ERST_STATUS[S_OK],
                                                              cover=PJLINK_ERST_STATUS[E_WARN],
                                                              filt=PJLINK_ERST_STATUS[S_OK],
                                                              other=PJLINK_ERST_STATUS[S_OK])
    chk_test = {'Cover': E_WARN}
    log_warn_calls = []
    log_debug_calls = [call('({ip}) Processing command "ERST" with data "{data}"'.format(ip=pjlink.name,
                                                                                         data=chk_data)),
                       call('({ip}) Calling function for ERST'.format(ip=pjlink.name))]
    pjlink.projector_errors = None

    # WHEN: process_erst with status set to WARN
    process_command(projector=pjlink, cmd='ERST', data=chk_data)

    # THEN: PJLink instance errors should match only cover warning
    assert 1 == len(pjlink.projector_errors), 'There should only be 1 error listed in projector_errors'
    assert 'Cover' in pjlink.projector_errors, '"Cover" should be the only error listed'
    assert pjlink.projector_errors['Cover'] == E_WARN, '"Cover" should have E_WARN listed as error'
    assert chk_test == pjlink.projector_errors, 'projector_errors should match test errors'
    mock_log.warning.assert_has_calls(log_warn_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_inf1(mock_log, pjlink):
    """
    Test saving INF1 data (manufacturer)
    """
    # GIVEN: Test object
    chk_data = 'TEst INformation MultiCase'
    log_warn_calls = []
    log_debug_calls = [call('({ip}) Processing command "INF1" with data "{data}"'.format(ip=pjlink.name,
                                                                                         data=chk_data)),
                       call('({ip}) Calling function for INF1'.format(ip=pjlink.name)),
                       call('({ip}) Setting projector manufacturer data to '
                            '"{data}"'.format(ip=pjlink.name, data=chk_data))]
    pjlink.manufacturer = None

    # WHEN: process_inf called with test data
    process_command(projector=pjlink, cmd='INF1', data=chk_data)

    # THEN: Data should be saved
    assert pjlink.manufacturer == chk_data, 'Test data should have been saved'
    mock_log.warning.assert_has_calls(log_warn_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_inf2(mock_log, pjlink):
    """
    Test saving INF2 data (model)
    """
    # GIVEN: Test object
    chk_data = 'TEst moDEl MultiCase'
    log_warn_calls = []
    log_debug_calls = [call('({ip}) Processing command "INF2" with data "{data}"'.format(ip=pjlink.name,
                                                                                         data=chk_data)),
                       call('({ip}) Calling function for INF2'.format(ip=pjlink.name)),
                       call('({ip}) Setting projector model to "{data}"'.format(ip=pjlink.name,
                                                                                data=chk_data))]
    pjlink.model = None

    # WHEN: process_inf called with test data
    process_command(projector=pjlink, cmd='INF2', data=chk_data)

    # THEN: Data should be saved
    assert pjlink.model == chk_data, 'Test data should have been saved'
    mock_log.warning.assert_has_calls(log_warn_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)


@patch.object(openlp.core.projectors.pjlinkcommands, 'log')
def test_projector_info(mock_log, pjlink):
    """
    Test saving INF2 data (model)
    """
    # GIVEN: Test object
    chk_data = 'TEst ExtrANEous MultiCase INformatoin that MFGR might Set'
    log_warn_calls = []
    log_debug_calls = [call('({ip}) Processing command "INFO" with data "{data}"'.format(ip=pjlink.name,
                                                                                         data=chk_data)),
                       call('({ip}) Calling function for INFO'.format(ip=pjlink.name)),
                       call('({ip}) Setting projector other_info to "{data}"'.format(ip=pjlink.name,
                                                                                     data=chk_data))]
    pjlink.other_info = None

    # WHEN: process_inf called with test data
    process_command(projector=pjlink, cmd='INFO', data=chk_data)

    # THEN: Data should be saved
    assert pjlink.other_info == chk_data, 'Test data should have been saved'
    mock_log.warning.assert_has_calls(log_warn_calls)
    mock_log.debug.assert_has_calls(log_debug_calls)
