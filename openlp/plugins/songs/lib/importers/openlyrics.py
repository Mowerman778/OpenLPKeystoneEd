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
The :mod:`openlyrics` module provides the functionality for importing
songs which are saved as OpenLyrics files.
"""
import logging

from lxml import etree

from openlp.core.widgets.wizard import WizardStrings
from openlp.plugins.songs.lib.db import Song
from openlp.plugins.songs.lib.importers.songimport import SongImport
from openlp.plugins.songs.lib.openlyricsxml import OpenLyrics, OpenLyricsError
from openlp.plugins.songs.lib.ui import SongStrings


log = logging.getLogger(__name__)


class OpenLyricsImport(SongImport):
    """
    This provides the Openlyrics import.
    """
    def __init__(self, manager, **kwargs):
        """
        Initialise the Open Lyrics importer.
        """
        log.debug('initialise OpenLyricsImport')
        super(OpenLyricsImport, self).__init__(manager, **kwargs)
        self.open_lyrics = OpenLyrics(self.manager)

    def do_import(self):
        """
        Imports the songs.
        """
        self.import_wizard.progress_bar.setMaximum(len(self.import_source))
        parser = etree.XMLParser(remove_blank_text=True, remove_pis=True)
        for file_path in self.import_source:
            if self.stop_import_flag:
                return
            self.import_wizard.increment_progress_bar(WizardStrings.ImportingType.format(source=file_path.name))
            try:
                # Pass a file object, because lxml does not cope with some
                # special characters in the path (see lp:757673 and lp:744337).
                parsed_file = etree.parse(file_path.open('rb'), parser)

                # Remove whitespaces from <lines> tags and its descendants
                root = parsed_file.getroot()
                for elem in root.iter('{*}lines'):
                    self._strip_whitespace(elem)
                    for subelem in elem.iter('{*}br'):
                        next_subelem = subelem.getnext()
                        self._strip_whitespace(subelem, next_subelem)
                xml = etree.tostring(root).decode()
                song = self.open_lyrics.xml_to_song(xml)
                if song is None:
                    # Not a valid OpenLyrics file (e.g. no <properties> element). This is commonly a song saved
                    # in a different XML-based format, such as OpenSong, so fall back to trying that before
                    # giving up - otherwise the file is silently skipped with no feedback at all. The fallback
                    # logs its own error if it also fails to make sense of the file.
                    self._try_import_as_opensong(file_path)
            except etree.XMLSyntaxError:
                log.exception('XML syntax error in file {path}'.format(path=file_path))
                self.log_error(file_path, SongStrings().XMLSyntaxError)
            except OpenLyricsError as exception:
                log.exception('OpenLyricsException {error:d} in file {name}: {text}'.format(error=exception.type,
                                                                                            name=file_path,
                                                                                            text=exception.log_message))
                self.log_error(file_path, exception.display_message)

    def _try_import_as_opensong(self, file_path):
        """
        Attempt to import a file that isn't valid OpenLyrics as an OpenSong song instead.

        Both formats commonly use a bare ``<song>`` root tag, so a file exported from OpenSong (or a similar
        tool) can easily end up here if the user leaves the wizard on its default "OpenLyrics" format.

        :param file_path: The file that failed to parse as OpenLyrics.
        :return: ``True`` if the file was successfully imported as OpenSong, ``False`` otherwise.
        """
        # Imported here to avoid a module-level circular import between the two importers.
        from openlp.plugins.songs.lib.importers.opensong import OpenSongImport
        songs_before = len(self.manager.get_all_objects(Song))
        try:
            with file_path.open('rb') as opensong_file:
                # OpenSongImport.do_import_file() only relies on attributes/methods defined on the common
                # SongImport base class, so it can be called against this OpenLyricsImport instance directly.
                # It calls self.log_error() itself if the fallback also fails to parse.
                OpenSongImport.do_import_file(self, opensong_file)
        except (etree.Error, etree.LxmlError):
            return False
        return len(self.manager.get_all_objects(Song)) > songs_before

    def _strip_whitespace(self, elem, next_subelem=None):
        """
        Remove leading and trailing whitespace from the 'text' and 'tail' attributes of an etree._Element object
        """
        if next_subelem is not None:
            # Trimming whitespaces after br tags.
            # We can't trim the spaces before 'chord' tags
            is_chord_after_tail = False
            if next_subelem.tag.endswith('chord'):
                is_chord_after_tail = True
            if elem.text is not None:
                elem.text = elem.text.strip()
            if elem.tail is not None and not is_chord_after_tail:
                elem.tail = elem.tail.strip()
            if elem.tail is not None and elem.tail.startswith('\n'):
                elem.tail = elem.tail.lstrip()
        else:
            has_children = bool(elem.getchildren())
            if elem.text is not None:
                if has_children:
                    # Can only strip on left as there's children inside
                    elem.text = elem.text.lstrip()
                else:
                    elem.text = elem.text.strip()
            if elem.tail is not None:
                if has_children:
                    # Can only strip on right as there's children inside
                    elem.tail = elem.tail.rstrip()
                else:
                    elem.tail = elem.tail.strip()
            elif has_children:
                # Can only strip on right as it's the last tag and there's no tail
                last_elem = elem.getchildren()[-1]
                if last_elem.tail is not None:
                    last_elem.tail = last_elem.tail.rstrip()
