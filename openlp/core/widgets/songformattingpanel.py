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
The :mod:`songformattingpanel` module provides a collapsible panel of rich text formatting controls (font,
size, colour, highlight, bold/italic/underline and emoji) that can be attached to a :class:`SpellTextEdit`
(or any other ``QPlainTextEdit``/``QTextEdit``) used to edit song verses or custom slides.

The formatting is applied to the current text selection using the existing Formatting Tags mechanism (the
same one used by ``{r}red text{/r}`` style tags), so slides using it render correctly without any changes to
the rendering/display pipeline. Rather than requiring the user to pre-define a tag for every colour/font
combination via the "Configure Formatting Tags" dialog, a matching tag is found or created automatically.
"""
from PyQt5 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.lib.formattingtags import FormattingTags
from openlp.core.lib.richtext import TAG_NAME_PROPERTY, char_format_from_html
from openlp.core.ui.icons import UiIcons
from openlp.core.widgets.buttons import ColorButton


# A small, deliberately short list of commonly used emoji, grouped loosely by theme.
EMOJI_CHOICES = [
    '😀', '😊', '😢', '😍', '🙏', '👏', '🙌', '👍',
    '❤️', '✝️', '🕊️', '🔥', '⭐', '☀️', '🌙', '🎵',
    '🎶', '📖', '✨', '🎉',
]


class SongFormattingPanel(QtWidgets.QWidget):
    """
    A collapsible "Song Formatting Panel" of rich text controls that apply formatting to the current
    selection of an attached text editor.
    """
    def __init__(self, parent, text_edit):
        """
        :param parent: The parent widget.
        :param text_edit: The text edit widget (e.g. a ``SpellTextEdit``) that formatting is applied to.
        """
        super().__init__(parent)
        self.text_edit = text_edit
        self.setObjectName('song_formatting_panel')
        self._setup_ui()

    def _setup_ui(self):
        self.outer_layout = QtWidgets.QHBoxLayout(self)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setObjectName('song_formatting_panel_outer_layout')
        # Collapse/expand toggle - kept outside the collapsible body so it's always reachable.
        self.collapse_button = QtWidgets.QToolButton(self)
        self.collapse_button.setObjectName('song_formatting_collapse_button')
        self.collapse_button.setCheckable(True)
        self.collapse_button.setChecked(False)
        self.collapse_button.setIcon(UiIcons().arrow_right)
        self.collapse_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.collapse_button.toggled.connect(self.on_collapse_button_toggled)
        self.outer_layout.addWidget(self.collapse_button)
        # The collapsible body containing all the actual formatting controls.
        self.body_widget = QtWidgets.QWidget(self)
        self.body_widget.setObjectName('song_formatting_panel_body')
        self.outer_layout.addWidget(self.body_widget)
        self.body_layout = QtWidgets.QFormLayout(self.body_widget)
        self.body_layout.setObjectName('song_formatting_panel_body_layout')
        self.title_label = QtWidgets.QLabel(self.body_widget)
        self.title_label.setObjectName('song_formatting_title_label')
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)
        self.body_layout.addRow(self.title_label)
        # Font family/size
        self.font_label = QtWidgets.QLabel(self.body_widget)
        self.font_combo_box = QtWidgets.QFontComboBox(self.body_widget)
        self.font_combo_box.setObjectName('song_formatting_font_combo_box')
        self.body_layout.addRow(self.font_label, self.font_combo_box)
        self.size_label = QtWidgets.QLabel(self.body_widget)
        self.size_spin_box = QtWidgets.QSpinBox(self.body_widget)
        self.size_spin_box.setObjectName('song_formatting_size_spin_box')
        self.size_spin_box.setRange(6, 200)
        self.size_spin_box.setValue(24)
        self.body_layout.addRow(self.size_label, self.size_spin_box)
        # Colour / highlight
        self.color_label = QtWidgets.QLabel(self.body_widget)
        self.color_button = ColorButton(self.body_widget)
        self.color_button.setObjectName('song_formatting_color_button')
        self.color_button.change_color('#ffffff')
        self.body_layout.addRow(self.color_label, self.color_button)
        self.highlight_layout = QtWidgets.QHBoxLayout()
        self.highlight_check_box = QtWidgets.QCheckBox(self.body_widget)
        self.highlight_check_box.setObjectName('song_formatting_highlight_check_box')
        self.highlight_layout.addWidget(self.highlight_check_box)
        self.highlight_button = ColorButton(self.body_widget)
        self.highlight_button.setObjectName('song_formatting_highlight_button')
        self.highlight_button.change_color('#ffff00')
        self.highlight_button.setEnabled(False)
        self.highlight_layout.addWidget(self.highlight_button)
        self.highlight_check_box.toggled.connect(self.highlight_button.setEnabled)
        self.highlight_label = QtWidgets.QLabel(self.body_widget)
        self.body_layout.addRow(self.highlight_label, self.highlight_layout)
        # Bold / Italic / Underline
        self.style_layout = QtWidgets.QHBoxLayout()
        self.bold_button = QtWidgets.QToolButton(self.body_widget)
        self.bold_button.setObjectName('song_formatting_bold_button')
        self.bold_button.setCheckable(True)
        bold_font = QtGui.QFont()
        bold_font.setBold(True)
        self.bold_button.setFont(bold_font)
        self.bold_button.setText('B')
        self.style_layout.addWidget(self.bold_button)
        self.italic_button = QtWidgets.QToolButton(self.body_widget)
        self.italic_button.setObjectName('song_formatting_italic_button')
        self.italic_button.setCheckable(True)
        italic_font = QtGui.QFont()
        italic_font.setItalic(True)
        self.italic_button.setFont(italic_font)
        self.italic_button.setText('I')
        self.style_layout.addWidget(self.italic_button)
        self.underline_button = QtWidgets.QToolButton(self.body_widget)
        self.underline_button.setObjectName('song_formatting_underline_button')
        self.underline_button.setCheckable(True)
        underline_font = QtGui.QFont()
        underline_font.setUnderline(True)
        self.underline_button.setFont(underline_font)
        self.underline_button.setText('U')
        self.style_layout.addWidget(self.underline_button)
        self.style_layout.addStretch()
        self.body_layout.addRow(self.style_layout)
        # Apply button
        self.apply_button = QtWidgets.QPushButton(self.body_widget)
        self.apply_button.setObjectName('song_formatting_apply_button')
        self.apply_button.clicked.connect(self.apply_to_selection)
        self.body_layout.addRow(self.apply_button)
        # Emoji picker
        self.emoji_button = QtWidgets.QToolButton(self.body_widget)
        self.emoji_button.setObjectName('song_formatting_emoji_button')
        self.emoji_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.emoji_menu = QtWidgets.QMenu(self.emoji_button)
        for emoji in EMOJI_CHOICES:
            action = self.emoji_menu.addAction(emoji)
            action.triggered.connect(lambda checked=False, emoji=emoji: self.insert_emoji(emoji))
        self.emoji_button.setMenu(self.emoji_menu)
        self.body_layout.addRow(self.emoji_button)
        self.retranslate_ui()

    def retranslate_ui(self):
        self.collapse_button.setToolTip(translate('OpenLP.SongFormattingPanel', 'Show/hide the formatting panel'))
        self.title_label.setText(translate('OpenLP.SongFormattingPanel', 'Song Formatting'))
        self.font_label.setText(translate('OpenLP.SongFormattingPanel', 'Font:'))
        self.size_label.setText(translate('OpenLP.SongFormattingPanel', 'Size:'))
        self.color_label.setText(translate('OpenLP.SongFormattingPanel', 'Text colour:'))
        self.highlight_label.setText(translate('OpenLP.SongFormattingPanel', 'Highlight:'))
        self.highlight_check_box.setToolTip(translate('OpenLP.SongFormattingPanel', 'Enable text highlighting'))
        self.bold_button.setToolTip(translate('OpenLP.SongFormattingPanel', 'Bold'))
        self.italic_button.setToolTip(translate('OpenLP.SongFormattingPanel', 'Italic'))
        self.underline_button.setToolTip(translate('OpenLP.SongFormattingPanel', 'Underline'))
        self.apply_button.setText(translate('OpenLP.SongFormattingPanel', 'Apply to Selection'))
        self.emoji_button.setText(translate('OpenLP.SongFormattingPanel', 'Insert Emoji...'))

    def on_collapse_button_toggled(self, checked):
        """
        Collapse the panel's body to give more space to the editor(s)/preview, leaving just the toggle button.
        """
        self.body_widget.setVisible(not checked)
        self.collapse_button.setIcon(UiIcons().arrow_left if checked else UiIcons().arrow_right)

    def build_style(self):
        """
        Build the CSS ``style`` attribute content for the currently selected formatting options.

        :rtype: str
        """
        declarations = [
            'font-family:{family}'.format(family=self.font_combo_box.currentFont().family()),
            'font-size:{size}pt'.format(size=self.size_spin_box.value()),
            '-webkit-text-fill-color:{color}'.format(color=self.color_button.color),
        ]
        if self.highlight_check_box.isChecked():
            declarations.append('background-color:{color}'.format(color=self.highlight_button.color))
        if self.bold_button.isChecked():
            declarations.append('font-weight:bold')
        if self.italic_button.isChecked():
            declarations.append('font-style:italic')
        if self.underline_button.isChecked():
            declarations.append('text-decoration:underline')
        return ';'.join(declarations)

    def apply_to_selection(self):
        """
        Apply the panel's current settings to the text edit's selection.

        On a rich text edit the formatting is applied to the text itself and the run remembers which tag it
        came from, so it still saves as ordinary formatting-tag markup. On a plain text edit there is nothing
        to show formatting with, so the markup is inserted instead.
        """
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            return
        style = self.build_style()
        tag_name = FormattingTags.get_or_create_custom_tag(style)
        if hasattr(self.text_edit, 'set_tagged_text'):
            char_format = char_format_from_html('<span style="{style}">'.format(style=style))
            # The panel describes the whole appearance of the run, so this tag replaces any it already had.
            char_format.setProperty(TAG_NAME_PROPERTY, tag_name)
            cursor.mergeCharFormat(char_format)
            self.text_edit.setFocus()
            return
        # QTextCursor uses U+2029 (paragraph separator) for line breaks within a selection, rather than '\n'.
        selected_text = cursor.selectedText().replace(' ', '\n')
        cursor.insertText('{{{tag}}}{text}{{/{tag}}}'.format(tag=tag_name, text=selected_text))

    def insert_emoji(self, emoji):
        """
        Insert an emoji character at the current cursor position (no selection required).

        :param emoji: The emoji character to insert.
        """
        self.text_edit.insertPlainText(emoji)
        self.text_edit.setFocus()
