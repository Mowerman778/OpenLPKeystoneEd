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
Test converting between formatting-tag markup and a Qt rich text document
"""
import pytest
from PyQt5 import QtGui

from openlp.core.lib.formattingtags import FormattingTags
from openlp.core.lib.richtext import (TAG_NAME_PROPERTY, char_format_from_html, document_to_tags,
                                      tags_to_document)


@pytest.fixture()
def tags(settings):
    """
    Load the standard formatting tags
    """
    FormattingTags.load_tags()
    yield
    FormattingTags.html_expands = []


def round_trip(text):
    """
    Convert text to a document and straight back again
    """
    document = QtGui.QTextDocument()
    tags_to_document(text, document)
    return document_to_tags(document)


@pytest.mark.parametrize('text', [
    '',
    'Amazing grace, how sweet the sound',
    '{r}Amazing grace{/r}',
    'Amazing {r}grace{/r}, how sweet the sound',
    '{r}{st}Amazing grace{/st}{/r}',
    '{r}Amazing{/r} grace {bl}how sweet{/bl}',
    'Line one\nLine two',
    '{r}Line one\nLine two{/r}',
    'Verse with a {su}1{/su} superscript',
    # A tag that closes at the end of a line: the closing tag must land before the newline, not after it.
    '---[Verse:1]---\n{r}Amazing grace{/r}\n---[Chorus:1]---\nHow sweet',
    '{r}Verse one{/r}\n\n{bl}Verse two{/bl}',
    '{r}red{/r}{bl}blue{/bl}',
    '{st}---[Verse:1]---\nAmazing grace{/st}',
    '[---]\n{r}Amazing{/r}\n[--}{--]\ngrace',
    '[=G]Am[G]azing {r}gr[G/B]ace{/r}, how sw[C]eet',
])
def test_round_trip_is_lossless(tags, text):
    """
    Test that converting stored text to a document and back leaves it byte-identical.

    This is the guarantee the whole module rests on: opening a song and saving it without editing it must
    not rewrite the user's library.
    """
    assert round_trip(text) == text


def test_unknown_tags_are_left_alone(tags):
    """
    Test that a tag this module does not know about survives untouched
    """
    # GIVEN: Text containing a tag that is not a registered formatting tag
    text = 'Some {notatag}text{/notatag} here'

    # WHEN/THEN: It should come back exactly as it went in
    assert round_trip(text) == text


def test_endless_tags_are_left_alone(tags):
    """
    Test that a tag with no closing tag, such as {br}, is kept as literal text
    """
    # GIVEN: Text with a line break tag, which marks a point rather than a run
    text = 'First line{br}Second line'

    # WHEN/THEN: It should be preserved rather than swallowed
    assert round_trip(text) == text


def test_unpaired_closing_tag_is_left_alone(tags):
    """
    Test that a stray closing tag is not guessed at
    """
    # GIVEN: Text with a closing tag that was never opened
    text = 'Amazing grace{/r} how sweet'

    # WHEN/THEN: It should be preserved
    assert round_trip(text) == text


def test_tags_become_real_formatting(tags):
    """
    Test that a colour tag actually colours the text in the document, rather than showing the markup
    """
    # GIVEN: Text with a red tag in it
    document = QtGui.QTextDocument()

    # WHEN: It is converted to a document
    tags_to_document('Amazing {r}grace{/r}', document)

    # THEN: The markup should be gone from the visible text, and the word should be red
    assert document.toPlainText() == 'Amazing grace'
    cursor = QtGui.QTextCursor(document)
    cursor.setPosition(len('Amazing ') + 1)
    assert cursor.charFormat().foreground().color().name() == QtGui.QColor('red').name()


def test_formatted_run_remembers_its_tag(tags):
    """
    Test that a converted run records which tag it came from
    """
    # GIVEN: Text with a red tag in it
    document = QtGui.QTextDocument()

    # WHEN: It is converted to a document
    tags_to_document('Amazing {r}grace{/r}', document)

    # THEN: The formatted run should carry the tag name, so it can be written back out exactly
    cursor = QtGui.QTextCursor(document)
    cursor.setPosition(len('Amazing ') + 1)
    assert cursor.charFormat().property(TAG_NAME_PROPERTY) == 'r'


def test_char_format_from_html_reads_colour():
    """
    Test that the colour used by OpenLP's own tags is understood
    """
    # GIVEN/WHEN: The red tag's HTML is converted
    char_format = char_format_from_html('<span style="-webkit-text-fill-color:red">')

    # THEN: The format should be red
    assert char_format.foreground().color().name() == QtGui.QColor('red').name()


def test_char_format_from_html_reads_bold_and_italic():
    """
    Test that both the element form and the CSS form of bold/italic are understood
    """
    # GIVEN/WHEN: The two ways OpenLP expresses bold and italic are converted
    from_element = char_format_from_html('<strong>')
    from_css = char_format_from_html('<span style="font-weight:bold;font-style:italic">')

    # THEN: Both should be recognised
    assert from_element.fontWeight() == QtGui.QFont.Bold
    assert from_css.fontWeight() == QtGui.QFont.Bold
    assert from_css.fontItalic() is True


def test_char_format_from_html_ignores_what_it_cannot_read():
    """
    Test that unrecognised HTML produces an empty format rather than an error
    """
    # GIVEN/WHEN: A tag whose HTML means nothing to this module
    char_format = char_format_from_html('<span style="text-transform: uppercase;">')

    # THEN: Nothing should have been set, and nothing should have blown up
    assert char_format.fontWeight() == QtGui.QFont.Normal
    assert char_format.fontItalic() is False


def test_rich_text_edit_round_trips_through_the_widget(tags, settings):
    """
    Test that the editor widget itself loads and saves tagged text without changing it.

    This is the end-to-end version of the round-trip guarantee: it goes through the real widget the song and
    custom slide editors now use, not just the converter functions.
    """
    # GIVEN: A rich text edit and a verse with formatting in it
    from openlp.core.widgets.edits import SpellRichTextEdit
    text = '---[Verse:1]---\n{r}Amazing grace{/r}, how {st}sweet{/st} the sound'
    edit = SpellRichTextEdit()

    # WHEN: The verse is loaded and read straight back
    edit.set_tagged_text(text)

    # THEN: The markup should be hidden from the user but preserved exactly on the way out
    assert '{r}' not in edit.toPlainText()
    assert edit.toPlainText() == '---[Verse:1]---\nAmazing grace, how sweet the sound'
    assert edit.tagged_text() == text
