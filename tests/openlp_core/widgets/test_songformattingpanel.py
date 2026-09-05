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
This module contains tests for the SongFormattingPanel widget.
"""
from PyQt5 import QtGui

from openlp.core.lib.formattingtags import FormattingTags
from openlp.core.widgets.edits import SpellTextEdit
from openlp.core.widgets.songformattingpanel import SongFormattingPanel


def test_apply_to_selection_wraps_selected_text_with_a_tag(registry, settings):
    """
    Test that applying formatting to a selection wraps it with a formatting tag matching the panel's settings
    """
    # GIVEN: A text edit with some selected text, and a formatting panel attached to it
    FormattingTags.load_tags()
    text_edit = SpellTextEdit()
    text_edit.setPlainText('Amazing grace, how sweet the sound')
    cursor = text_edit.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(len('Amazing grace'), QtGui.QTextCursor.MoveMode.KeepAnchor)
    text_edit.setTextCursor(cursor)
    panel = SongFormattingPanel(None, text_edit)
    panel.color_button.change_color('#ff0000')
    panel.bold_button.setChecked(True)

    # WHEN: The formatting is applied to the selection
    panel.apply_to_selection()

    # THEN: The selected text should be wrapped in a tag whose style matches the panel's settings, and the
    # rest of the text should be untouched
    result = text_edit.toPlainText()
    assert result.endswith(', how sweet the sound')
    assert result.startswith('{')
    tag_name = result[1:result.index('}')]
    matching = [tag for tag in FormattingTags.get_html_tags() if tag['start tag'] == '{{{name}}}'.format(name=tag_name)]
    assert len(matching) == 1
    assert 'font-weight:bold' in matching[0]['start html']
    assert '-webkit-text-fill-color:#ff0000' in matching[0]['start html']
    assert result == '{{{tag}}}Amazing grace{{/{tag}}}, how sweet the sound'.format(tag=tag_name)


def test_apply_to_selection_does_nothing_without_a_selection(registry, settings):
    """
    Test that applying formatting without a selection is a no-op
    """
    # GIVEN: A text edit with no selection
    text_edit = SpellTextEdit()
    text_edit.setPlainText('Amazing grace')
    text_edit.moveCursor(QtGui.QTextCursor.MoveOperation.Start)
    panel = SongFormattingPanel(None, text_edit)

    # WHEN: apply_to_selection() is called
    panel.apply_to_selection()

    # THEN: The text should be unchanged
    assert text_edit.toPlainText() == 'Amazing grace'


def test_insert_emoji_inserts_at_cursor(registry, settings):
    """
    Test that insert_emoji() inserts the emoji at the current cursor position without needing a selection
    """
    # GIVEN: A text edit with the cursor at the end
    text_edit = SpellTextEdit()
    text_edit.setPlainText('Hallelujah')
    text_edit.moveCursor(QtGui.QTextCursor.MoveOperation.End)
    panel = SongFormattingPanel(None, text_edit)

    # WHEN: An emoji is inserted
    panel.insert_emoji('🙌')

    # THEN: It should be appended
    assert text_edit.toPlainText() == 'Hallelujah🙌'


def test_collapse_button_hides_and_shows_the_body(registry, settings):
    """
    Test that toggling the collapse button hides/shows the panel's controls
    """
    # GIVEN: A formatting panel, initially expanded
    text_edit = SpellTextEdit()
    panel = SongFormattingPanel(None, text_edit)
    assert panel.body_widget.isHidden() is False

    # WHEN: The collapse button is toggled on
    panel.collapse_button.setChecked(True)

    # THEN: The body should be hidden
    assert panel.body_widget.isHidden() is True

    # WHEN: The collapse button is toggled back off
    panel.collapse_button.setChecked(False)

    # THEN: The body should be shown again
    assert panel.body_widget.isHidden() is False


def test_build_style_reuses_existing_tag_for_identical_settings(registry, settings):
    """
    Test that applying the exact same formatting twice reuses one tag rather than creating duplicates
    """
    # GIVEN: A text edit with two selections and a formatting panel with fixed settings
    FormattingTags.load_tags()
    text_edit = SpellTextEdit()
    text_edit.setPlainText('one two')
    panel = SongFormattingPanel(None, text_edit)
    panel.color_button.change_color('#00ff00')

    cursor = text_edit.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(3, QtGui.QTextCursor.MoveMode.KeepAnchor)
    text_edit.setTextCursor(cursor)

    # WHEN: The same style is applied to two different selections
    panel.apply_to_selection()
    text = text_edit.toPlainText()
    cursor = text_edit.textCursor()
    cursor.setPosition(len(text) - 3)
    cursor.setPosition(len(text), QtGui.QTextCursor.MoveMode.KeepAnchor)
    text_edit.setTextCursor(cursor)
    panel.apply_to_selection()

    # THEN: Only one custom tag should have been created for that style
    custom_tags = [tag for tag in FormattingTags.get_html_tags() if not tag.get('protected')]
    assert len(custom_tags) == 1
