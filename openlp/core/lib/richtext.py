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
Convert between OpenLP's formatting-tag markup and a Qt rich text document.

Songs and custom slides are stored as plain text with formatting tags in it, e.g. ``{r}bold and red{/r}``.
That storage format is shared with the renderer, the OpenLyrics import/export and every other song importer,
so this module deliberately does *not* change it. Instead it lets an editor show the formatting rather than
the markup, by converting the stored text to a :class:`~PyQt5.QtGui.QTextDocument` on the way in and back to
the same markup on the way out.

The guarantee that matters is round-tripping: loading a verse and saving it again without editing it must
produce byte-identical text, because anything else silently rewrites the user's song library. Two rules keep
that true:

* Every formatted run remembers the tag it came from, in :data:`TAG_NAME_PROPERTY`. Serialising emits that
  exact tag rather than trying to reconstruct one from the character format, so a tag whose HTML this module
  does not fully understand still survives untouched.
* Anything that cannot be represented as a character format at all - an "endless" tag such as ``{br}``, an
  unknown tag, or a tag whose partner is missing - is left in the document as literal text.
"""
import re

from PyQt5 import QtGui

from openlp.core.lib.formattingtags import FormattingTags


# Remembers which formatting tag produced a run of text, so it can be written back out unchanged.
TAG_NAME_PROPERTY = QtGui.QTextFormat.UserProperty + 1

TAG_PATTERN = re.compile(r'\{(/)?([a-zA-Z0-9_]+)\}')

COLOR_PATTERN = re.compile(r'(?:^|[;\s"\'])(?:-webkit-text-fill-color|color)\s*:\s*([^;"]+)')
BACKGROUND_PATTERN = re.compile(r'(?:^|[;\s"\'])background(?:-color)?\s*:\s*([^;"]+)')
FONT_FAMILY_PATTERN = re.compile(r'(?:^|[;\s"\'])font-family\s*:\s*([^;"]+)')
FONT_SIZE_PATTERN = re.compile(r'(?:^|[;\s])font-size\s*:\s*([0-9.]+)pt')
BOLD_PATTERN = re.compile(r'font-weight\s*:\s*bold')
ITALIC_PATTERN = re.compile(r'font-style\s*:\s*italic')
UNDERLINE_PATTERN = re.compile(r'text-decoration\s*:[^;"]*underline')


def char_format_from_html(start_html):
    """
    Build a :class:`~PyQt5.QtGui.QTextCharFormat` describing a formatting tag's opening HTML.

    Only the subset of HTML/CSS that OpenLP's own tags use is understood. Anything else simply contributes
    nothing to the format - the run is still tagged, so it will be written back out correctly either way.

    :param start_html: The tag's ``start html``, e.g. ``'<span style="-webkit-text-fill-color:red">'``.
    :return: A character format, which may be empty if nothing in the HTML was recognised.
    """
    char_format = QtGui.QTextCharFormat()
    if not start_html:
        return char_format
    html = start_html.strip()
    lowered = html.lower()
    if '<strong' in lowered or '<b>' in lowered or BOLD_PATTERN.search(lowered):
        char_format.setFontWeight(QtGui.QFont.Bold)
    if '<em' in lowered or '<i>' in lowered or ITALIC_PATTERN.search(lowered):
        char_format.setFontItalic(True)
    if '<u>' in lowered or UNDERLINE_PATTERN.search(lowered):
        char_format.setFontUnderline(True)
    if '<sup' in lowered:
        char_format.setVerticalAlignment(QtGui.QTextCharFormat.AlignSuperScript)
    if '<sub' in lowered:
        char_format.setVerticalAlignment(QtGui.QTextCharFormat.AlignSubScript)
    color_match = COLOR_PATTERN.search(html)
    if color_match:
        color = QtGui.QColor(color_match.group(1).strip())
        if color.isValid():
            char_format.setForeground(color)
    background_match = BACKGROUND_PATTERN.search(html)
    if background_match:
        color = QtGui.QColor(background_match.group(1).strip())
        if color.isValid():
            char_format.setBackground(color)
    family_match = FONT_FAMILY_PATTERN.search(html)
    if family_match:
        char_format.setFontFamily(family_match.group(1).strip().strip('\'"'))
    size_match = FONT_SIZE_PATTERN.search(html)
    if size_match:
        char_format.setFontPointSize(float(size_match.group(1)))
    return char_format


def _tag_lookup():
    """
    Map each usable tag name to its character format.

    "Endless" tags - ones with no closing tag, such as ``{br}`` - are excluded, because they mark a point
    rather than a run and so cannot be represented as a character format.

    :return: A dict of tag name to :class:`~PyQt5.QtGui.QTextCharFormat`.
    """
    formats = {}
    for tag in FormattingTags.get_html_tags():
        start_tag = tag.get('start tag') or ''
        end_tag = tag.get('end tag') or ''
        if not start_tag.startswith('{') or not end_tag:
            continue
        formats[start_tag[1:-1]] = char_format_from_html(tag.get('start html'))
    return formats


def tags_to_document(text, document):
    """
    Fill a text document with ``text``, showing its formatting tags as actual formatting.

    :param text: The stored text, with formatting tags in it.
    :param document: The :class:`~PyQt5.QtGui.QTextDocument` to populate. It is cleared first.
    """
    known_formats = _tag_lookup()
    document.clear()
    cursor = QtGui.QTextCursor(document)
    open_tags = []
    position = 0
    for match in TAG_PATTERN.finditer(text or ''):
        name = match.group(2)
        is_close = match.group(1) is not None
        if name not in known_formats:
            # Unknown or endless tag - leave it in the text exactly as it was found.
            continue
        if is_close and name not in open_tags:
            # A stray closing tag; keep it literal rather than guessing what it belonged to.
            continue
        cursor.insertText(text[position:match.start()], _merged_format(known_formats, open_tags))
        position = match.end()
        if is_close:
            open_tags.remove(name)
        else:
            open_tags.append(name)
    cursor.insertText(text[position:], _merged_format(known_formats, open_tags))


def _merged_format(known_formats, open_tags):
    """
    Combine the formats of every currently open tag, so nested tags both apply.

    :param known_formats: The tag name to character format mapping.
    :param open_tags: The tag names that are open, outermost first.
    :return: The combined character format.
    """
    merged = QtGui.QTextCharFormat()
    for name in open_tags:
        merged.merge(known_formats[name])
    if open_tags:
        # Remember the innermost tag so the run can be written back out as exactly that tag.
        merged.setProperty(TAG_NAME_PROPERTY, ','.join(open_tags))
    return merged


def document_to_tags(document):
    """
    Serialise a text document back to stored text with formatting tags.

    :param document: The :class:`~PyQt5.QtGui.QTextDocument` to read.
    :return: The text, with formatting tags restored.
    """
    blocks = [[(fragment.text(), _tags_of(fragment.charFormat())) for fragment in _fragments(block)]
              for block in _blocks(document)]
    runs = []
    for index, fragments in enumerate(blocks):
        if index:
            # A newline sits inside whichever tags carry on across it, and outside the ones that do not, so
            # that "{r}one\ntwo{/r}" and "{r}one{/r}\ntwo" both come back exactly as they went in.
            previous = blocks[index - 1][-1][1] if blocks[index - 1] else []
            following = fragments[0][1] if fragments else []
            runs.append(('\n', previous[:_common_length(previous, following)]))
        runs.extend(fragments)
    parts = []
    open_tags = []
    for text, wanted in runs:
        common = _common_length(open_tags, wanted)
        for name in reversed(open_tags[common:]):
            parts.append('{{/{name}}}'.format(name=name))
        for name in wanted[common:]:
            parts.append('{{{name}}}'.format(name=name))
        open_tags = wanted
        parts.append(text)
    for name in reversed(open_tags):
        parts.append('{{/{name}}}'.format(name=name))
    return ''.join(parts)


def _common_length(first, second):
    """
    Count how many tags two runs have open in common, from the outermost inwards.

    :param first: The first list of tag names.
    :param second: The second list of tag names.
    :return: The length of their common prefix.
    """
    length = 0
    while length < len(first) and length < len(second) and first[length] == second[length]:
        length += 1
    return length


def _tags_of(char_format):
    """
    Read the tag names recorded on a character format.

    :param char_format: The :class:`~PyQt5.QtGui.QTextCharFormat` to read.
    :return: A list of tag names, outermost first.
    """
    names = char_format.property(TAG_NAME_PROPERTY)
    return names.split(',') if names else []


def _blocks(document):
    """
    Yield each block in a document.

    :param document: The :class:`~PyQt5.QtGui.QTextDocument` to walk.
    """
    block = document.begin()
    while block.isValid():
        yield block
        block = block.next()


def _fragments(block):
    """
    Yield each text fragment in a block.

    :param block: The :class:`~PyQt5.QtGui.QTextBlock` to walk.
    """
    iterator = block.begin()
    while not iterator.atEnd():
        fragment = iterator.fragment()
        if fragment.isValid():
            yield fragment
        iterator += 1
