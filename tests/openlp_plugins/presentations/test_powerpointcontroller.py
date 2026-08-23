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
Functional tests to test the PowerPointController class and related methods.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from openlp.core.common.platform import is_win
from openlp.core.common.registry import Registry
from openlp.plugins.presentations.lib.powerpointcontroller import PowerpointController, PowerpointDocument, \
    _get_text_from_shapes
from tests.utils.constants import RESOURCE_PATH

if is_win():
    import pywintypes


@pytest.fixture()
def get_thumbnail_folder(settings):
    gtf = patch('openlp.plugins.presentations.lib.powerpointcontroller.PresentationDocument._setup')
    yield gtf.start()
    gtf.stop()


def test_constructor(settings, mock_plugin):
    """
    Test the Constructor from the PowerpointController
    """
    # GIVEN: No presentation controller
    controller = None

    # WHEN: The presentation controller object is created
    controller = PowerpointController(plugin=mock_plugin)

    # THEN: The name of the presentation controller should be correct
    assert 'Powerpoint' == controller.name, 'The name of the presentation controller should be correct'


def test_show_error_msg(get_thumbnail_folder):
    """
    Test the PowerpointDocument.show_error_msg() method gets called on com exception
    """
    if is_win():
        # GIVEN: A PowerpointDocument with mocked controller and presentation
        with patch('openlp.plugins.presentations.lib.powerpointcontroller.critical_error_message_box') as \
                mocked_critical_error_message_box:
            instance = PowerpointDocument(MagicMock(), MagicMock())
            instance.presentation = MagicMock()
            instance.presentation.SlideShowWindow.View.GotoSlide = MagicMock(side_effect=pywintypes.com_error('1'))
            instance.index_map[42] = 42

            # WHEN: Calling goto_slide which will throw an exception
            instance.goto_slide(42)

            # THEN: mocked_critical_error_message_box should have been called
            mocked_critical_error_message_box.assert_called_with('Error', 'An error occurred in the PowerPoint '
                                                                 'integration and the presentation will be stopped.'
                                                                 ' Restart the presentation if you wish to '
                                                                 'present it.')


def test_create_titles_and_notes(get_thumbnail_folder):
    """
    Test creating the titles from PowerPoint
    """
    # GIVEN: mocked save_titles_and_notes, _get_text_from_shapes and two mocked slides
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.get_slide_count = MagicMock()
    doc.get_slide_count.return_value = 2
    doc.index_map = {1: 1, 2: 2}
    doc.save_titles_and_notes = MagicMock()
    doc._PowerpointDocument__get_text_from_shapes = MagicMock()
    slide = MagicMock()
    slide.Shapes.Title.TextFrame.TextRange.Text = 'SlideText'
    pres = MagicMock()
    pres.Slides = MagicMock(side_effect=[slide, slide])
    doc.presentation = pres

    # WHEN reading the titles and notes
    doc.create_titles_and_notes()

    # THEN the save should have been called exactly once with 2 titles and 2 notes
    doc.save_titles_and_notes.assert_called_once_with(['SlideText', 'SlideText'], [' ', ' '])


def test_create_titles_and_notes_with_no_slides(get_thumbnail_folder):
    """
    Test creating the titles from PowerPoint when it returns no slides
    """
    # GIVEN: mocked save_titles_and_notes, _get_text_from_shapes and two mocked slides
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.save_titles_and_notes = MagicMock()
    doc._PowerpointDocument__get_text_from_shapes = MagicMock()
    pres = MagicMock()
    pres.Slides = []
    doc.presentation = pres

    # WHEN reading the titles and notes
    doc.create_titles_and_notes()

    # THEN the save should have been called exactly once with empty titles and notes
    doc.save_titles_and_notes.assert_called_once_with([], [])


def test_get_text_from_shapes():
    """
    Test getting text from powerpoint shapes
    """
    # GIVEN: mocked shapes
    shape = MagicMock()
    shape.PlaceholderFormat.Type = 2
    shape.HasTextFrame = shape.TextFrame.HasText = True
    shape.TextFrame.TextRange.Text = 'slideText'
    shapes = [shape, shape]

    # WHEN: getting the text
    result = _get_text_from_shapes(shapes)

    # THEN: it should return the text
    assert result == 'slideText\nslideText\n', 'result should match \'slideText\nslideText\n\''


def test_get_text_from_shapes_with_no_shapes():
    """
    Test getting text from powerpoint shapes with no shapes
    """
    # GIVEN: empty shapes array
    shapes = []

    # WHEN: getting the text
    result = _get_text_from_shapes(shapes)

    # THEN: it should not fail but return empty string
    assert result == '', 'result should be empty'


def test_goto_slide(get_thumbnail_folder):
    """
    Test that goto_slide goes to next effect if the slide is already displayed
    """
    # GIVEN: A Document with mocked controller, presentation, and mocked functions get_slide_number and next_step
    Registry().get('settings').setValue('presentations/powerpoint slide click advance', True)
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.presentation = MagicMock()
    doc.presentation.SlideShowWindow.View.GetClickIndex.return_value = 1
    doc.presentation.SlideShowWindow.View.GetClickCount.return_value = 2
    doc.get_slide_number = MagicMock()
    doc.get_slide_number.return_value = 1
    doc.next_step = MagicMock()
    doc.index_map[1] = 1

    # WHEN: Calling goto_slide
    doc.goto_slide(1)

    # THEN: next_step() should be call to try to advance to the next effect.
    assert doc.next_step.called is True, 'next_step() should have been called!'


def test_blank_screen(get_thumbnail_folder):
    """
    Test that blank_screen works as expected
    """
    # GIVEN: A Document with mocked controller, presentation, and mocked function get_slide_number
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.presentation = MagicMock()
    doc.presentation.SlideShowWindow.View.GetClickIndex.return_value = 3
    doc.presentation.Application.Version = 14.0
    doc.get_slide_number = MagicMock()
    doc.get_slide_number.return_value = 2

    # WHEN: Calling goto_slide
    doc.blank_screen()

    # THEN: The view state, doc.blank_slide and doc.blank_click should have new values
    assert doc.presentation.SlideShowWindow.View.State == 3, 'The View State should be 3'
    assert doc.blank_slide == 2, 'doc.blank_slide should be 2 because of the PowerPoint version'
    assert doc.blank_click == 3, 'doc.blank_click should be 3 because of the PowerPoint version'


def test_unblank_screen(get_thumbnail_folder):
    """
    Test that unblank_screen works as expected
    """
    # GIVEN: A Document with mocked controller, presentation, ScreenList, and mocked function get_slide_number
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList') as mocked_screen_list:
        mocked_screen_list_ret = MagicMock()
        mocked_screen_list_ret.screen_list = [1]
        mocked_screen_list.return_value = mocked_screen_list_ret
        doc = PowerpointDocument(MagicMock(), MagicMock())
        doc.presentation = MagicMock()
        doc.presentation.SlideShowWindow.View.GetClickIndex.return_value = 3
        doc.presentation.Application.Version = 14.0
        doc.get_slide_number = MagicMock()
        doc.get_slide_number.return_value = 2
        doc.index_map[1] = 1
        doc.blank_slide = 1
        doc.blank_click = 1

        # WHEN: Calling goto_slide
        doc.unblank_screen()

        # THEN: The view state have new value, and several function should have been called
        assert doc.presentation.SlideShowWindow.View.State == 1, 'The View State should be 1'
        assert doc.presentation.SlideShowWindow.Activate.called is True, \
            'SlideShowWindow.Activate should have been called'
        assert doc.presentation.SlideShowWindow.View.GotoSlide.called is True, \
            'View.GotoSlide should have been called because of the PowerPoint version'
        assert doc.presentation.SlideShowWindow.View.GotoClick.called is True, \
            'View.GotoClick should have been called because of the PowerPoint version'


@pytest.mark.parametrize('file_path, expected_is_in_cloud, expected_same_file_name', [
    (RESOURCE_PATH / 'presentations' / 'test.pptx', False, True),
    (Path('test.pptx'), True, False)
])
def test_presentation_is_in_cloud(file_path, expected_is_in_cloud, expected_same_file_name,
                                  registry, settings):
    """
    Test that a presentation from a cloud drive is being detected.
    """
    # GIVEN: A Document with mocked controller and presentation.
    mocked_plugin = MagicMock()
    mocked_plugin.settings_section = 'presentations'
    ppc = PowerpointController(mocked_plugin)
    doc = PowerpointDocument(ppc, file_path)
    doc.presentation = MagicMock(FullName=file_path)
    if expected_is_in_cloud:
        doc.presentation = MagicMock(FullName='https://' + str(file_path))
    else:
        doc.presentation = MagicMock(FullName=str(file_path))
    assert doc.is_in_cloud == expected_is_in_cloud, \
        'is_in_cloud should be false because this file is locally stored'
    assert (doc.presentation_file == doc.presentation_controller_file) == expected_same_file_name, \
        'presentation_file should have the same value as presentation_controller_file'
