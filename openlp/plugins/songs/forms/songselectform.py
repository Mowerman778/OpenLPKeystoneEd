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
The :mod:`~openlp.plugins.songs.forms.songselectform` module contains the GUI for the SongSelect importer
"""
import logging
import re
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets, QtWebEngineWidgets
from sqlalchemy.sql import and_
from tempfile import TemporaryDirectory

from openlp.core.common.i18n import translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.platform import is_linux, is_macosx
from openlp.core.widgets.dialogs import FileDialog
from openlp.plugins.songs.forms.songselectdialog import Ui_SongSelectDialog
from openlp.plugins.songs.lib.db import Song
from openlp.plugins.songs.lib.songselect import LOGIN_PAGE, SEARCH_URL, SongSelectImport, Pages
from openlp.plugins.songs.lib.importers.chordpro import ChordProImport
from openlp.plugins.songs.lib.importers.cclifile import CCLIFileImport


CHROME_USER_AGENT = 'Mozilla/5.0 ({os_info}) AppleWebKit/537.36 ' \
                    '(KHTML, like Gecko) Chrome/{version} Safari/537.36'
WIN_OS_USER_AGENT = 'Windows NT 10.0; Win64; x64'
MAC_OS_USER_AGENT = 'Macintosh; Intel Mac OS X 13_5_2'
LINUX_OS_USER_AGENT = 'X11; Linux x86_64'

REPLACE_ALL_JS = """
// Based on: https://vanillajstoolkit.com/polyfills/stringreplaceall/
if (!String.prototype.replaceAll) {
    String.prototype.replaceAll = function(str, newStr){
        // If a regex pattern
        if (Object.prototype.toString.call(str).toLowerCase() === '[object regexp]') {
            return this.replace(str, newStr);
        }
        // If a string
        return this.split(str).join(newStr);
    };
}
"""

log = logging.getLogger(__name__)

SONGSELECT_FILE_SUFFIXES = ('.txt', '.chordpro', '.cho', '.chopro', '.pro')
# Give the browser a moment to finish writing a download before it is read
AUTO_IMPORT_DELAY_MS = 1000


def get_downloads_folder():
    """
    Get the user's Downloads folder (which Windows lets the user move), falling back to their home folder.

    :rtype: pathlib.Path
    """
    location = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DownloadLocation)
    downloads = Path(location) if location else Path.home() / 'Downloads'
    return downloads if downloads.is_dir() else Path.home()


def is_songselect_file(file_path):
    """
    Check whether a downloaded file looks like a SongSelect lyrics or ChordPro file, so that unrelated downloads
    landing in the same folder are left alone.

    :param pathlib.Path file_path: The file to check
    :rtype: bool
    """
    if file_path.suffix.lower() not in SONGSELECT_FILE_SUFFIXES or not file_path.is_file():
        return False
    try:
        with file_path.open('rt', encoding='utf-8-sig', errors='replace') as song_file:
            return 'ccli' in song_file.read(100000).lower()
    except OSError:
        return False


class SongSelectForm(QtWidgets.QDialog, Ui_SongSelectDialog, RegistryProperties):
    """
    The :class:`SongSelectForm` class is the SongSelect dialog.
    """

    def __init__(self, parent=None, plugin=None, db_manager=None):
        QtWidgets.QDialog.__init__(self, parent, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint |
                                   QtCore.Qt.WindowCloseButtonHint)
        self.plugin = plugin
        self.db_manager = db_manager
        self.setup_ui(self)
        self.current_download_item = None
        self.tmp_folder = TemporaryDirectory(prefix='openlp_songselect_', ignore_cleanup_errors=True)
        self.downloads_watcher = None
        self.downloads_folder = None
        self.seen_downloads = set()

    def initialise(self):
        """
        Initialise the SongSelectForm
        """
        self.song = None
        self.song_select_importer = SongSelectImport(self.db_manager, self.webview)
        self.url_bar.returnPressed.connect(self.on_url_bar_return_pressed)
        self.back_button.clicked.connect(self.on_back_button_clicked)
        self.close_button.clicked.connect(self.done)
        self.browser_button.clicked.connect(self.on_browser_button_clicked)
        self.search_button.clicked.connect(self.on_search_button_clicked)
        self.search_edit.returnPressed.connect(self.on_search_button_clicked)
        self.import_files_button.clicked.connect(self.on_import_files_button_clicked)
        # We need to set the user agent to an up to date browser version do to the pyqtwebengine package
        # from pypi has not been updated in ages...
        # TODO: get the latest version number from somewhere
        chrome_version = '117.0.5938.48'
        if is_linux():
            user_agent = CHROME_USER_AGENT.format(os_info=LINUX_OS_USER_AGENT, version=chrome_version)
        elif is_macosx():
            user_agent = CHROME_USER_AGENT.format(os_info=MAC_OS_USER_AGENT, version=chrome_version)
        else:
            user_agent = CHROME_USER_AGENT.format(os_info=WIN_OS_USER_AGENT, version=chrome_version)
        self.webview.page().profile().setHttpUserAgent(user_agent)
        self.webview.page().loadStarted.connect(self.page_load_started)
        self.webview.page().loadFinished.connect(self.page_loaded)
        self.webview.page().profile().downloadRequested.connect(self.on_download_requested)
        self.webview.urlChanged.connect(self.update_url)
        self.inject_js_str_replaceall()

    def inject_js_str_replaceall(self):
        """
        Inject an implementation of string replaceAll which are missing in pre 5.15.3 QWebEngine
        """
        script = QtWebEngineWidgets.QWebEngineScript()
        script.setInjectionPoint(QtWebEngineWidgets.QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setSourceCode(REPLACE_ALL_JS)
        script.setWorldId(QtWebEngineWidgets.QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(True)
        script.setName('string_replaceall')
        self.webview.page().scripts().insert(script)

    def update_url(self, new_url):
        self.url_bar.setText(new_url.toString())

    def download_finished(self):
        """
        Callback for when download has finished
        """
        if self.current_download_item:
            if self.current_download_item.state() == QtWebEngineWidgets.QWebEngineDownloadItem.DownloadCompleted:
                self.song_progress_bar.setValue(2)
                song_filename = self.current_download_item.downloadDirectory() + '/' \
                    + self.current_download_item.downloadFileName()
                if self.import_song_file(Path(song_filename)):
                    self.song_progress_bar.setValue(3)
                    QtWidgets.QMessageBox.information(self, translate('SongsPlugin.SongSelectForm', 'Song Imported'),
                                                      translate('SongsPlugin.SongSelectForm',
                                                                'Your song has been imported'))
                self.song_progress_bar.setVisible(False)
            self.url_bar.setVisible(True)
            self.webview.setEnabled(True)

    def import_song_file(self, file_path):
        """
        Import a song file downloaded from SongSelect (simple lyrics .txt or ChordPro).

        :param pathlib.Path file_path: The downloaded file
        :return: True if the song was imported, False if the user skipped it as a duplicate
        """
        # SongSelect downloads are UTF-8, sometimes with a byte order mark
        with file_path.open('rt', encoding='utf-8-sig') as song_file:
            song_content = song_file.read()
            song_file.seek(0)
            if not self.check_for_duplicate(song_content):
                return False
            # if a chordpro title tag is in the file, assume it is chordpro format
            if '{title:' in song_content:
                chordpro_importer = ChordProImport(self.plugin.manager, file_path=file_path)
                chordpro_importer.do_import_file(song_file)
            else:
                # assume it is a simple lyrics
                cccli_lyrics_importer = CCLIFileImport(self.plugin.manager, file_path=file_path)
                if not cccli_lyrics_importer.do_import_txt_file(song_file.readlines()):
                    raise ValueError('Not a valid SongSelect lyrics file: {name}'.format(name=file_path.name))
        return True

    def on_browser_button_clicked(self):
        """
        Open the SongSelect sign-in page in the user's normal web browser
        """
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(LOGIN_PAGE))

    def on_import_files_button_clicked(self):
        """
        Let the user pick songs they downloaded from SongSelect in their browser, and import them
        """
        file_paths, _ = FileDialog.getOpenFileNames(
            self, translate('SongsPlugin.SongSelectForm', 'Select songs downloaded from SongSelect'),
            get_downloads_folder(),
            translate('SongsPlugin.SongSelectForm', 'SongSelect files (*.txt *.chordpro *.cho *.chopro *.pro);;'
                                                    'All files (*)'))
        imported = 0
        failed = []
        for file_path in file_paths:
            try:
                if self.import_song_file(file_path):
                    imported += 1
            except Exception:
                log.exception('Failed to import SongSelect file {path}'.format(path=file_path))
                failed.append(file_path.name)
        if not file_paths:
            return
        message = translate('SongsPlugin.SongSelectForm', '{count} song(s) imported.').format(count=imported)
        if failed:
            message += '\n\n' + translate('SongsPlugin.SongSelectForm', 'These files could not be imported:') + \
                '\n' + '\n'.join(failed)
        QtWidgets.QMessageBox.information(self, translate('SongsPlugin.SongSelectForm', 'Import Finished'), message)

    @QtCore.pyqtSlot(QtWebEngineWidgets.QWebEngineDownloadItem)
    def on_download_requested(self, download_item):
        """
        Called when download is started
        """
        # only import from txt is supported
        if download_item.suggestedFileName().endswith('.txt'):
            self.song_progress_bar.setMaximum(3)
            self.song_progress_bar.setValue(1)
            self.song_progress_bar.setVisible(True)
            self.webview.setEnabled(False)
            download_item.setDownloadDirectory(self.tmp_folder.name)
            download_item.accept()
            self.current_download_item = download_item
            self.current_download_item.finished.connect(self.download_finished)
        else:
            download_item.cancel()
            QtWidgets.QMessageBox.information(self, translate('SongsPlugin.SongSelectForm', 'Unsupported format'),
                                              translate('SongsPlugin.SongSelectForm',
                                                        'OpenLP can only import simple lyrics or ChordPro'))

    def exec(self):
        """
        Execute the dialog. This method sets everything back to its initial
        values.
        """
        self.song_select_importer.reset_webview()
        self.back_button.setEnabled(False)
        self.stacked_widget.setCurrentIndex(0)
        self.start_downloads_watcher()
        self.search_edit.setFocus()
        return QtWidgets.QDialog.exec(self)

    def done(self, result_code):
        """
        Log out of SongSelect.

        :param result_code: The result of the dialog.
        """
        self.stop_downloads_watcher()
        return QtWidgets.QDialog.done(self, result_code)

    def start_downloads_watcher(self):
        """
        Watch the Downloads folder while this window is open, so songs downloaded from SongSelect in the user's
        browser are imported automatically. Files already there are ignored.
        """
        self.stop_downloads_watcher()
        self.downloads_folder = get_downloads_folder()
        self.seen_downloads = set(self.downloads_folder.iterdir())
        self.downloads_watcher = QtCore.QFileSystemWatcher([str(self.downloads_folder)], self)
        self.downloads_watcher.directoryChanged.connect(self.on_downloads_folder_changed)

    def stop_downloads_watcher(self):
        """
        Stop watching the Downloads folder
        """
        if self.downloads_watcher:
            self.downloads_watcher.directoryChanged.disconnect(self.on_downloads_folder_changed)
            self.downloads_watcher.deleteLater()
            self.downloads_watcher = None

    def on_downloads_folder_changed(self, folder):
        """
        Something changed in the Downloads folder: queue any new SongSelect-type files for import. Browsers write to a
        temporary name (.crdownload, .part) and rename when finished, so the real name only appears once complete.
        """
        try:
            current_files = set(self.downloads_folder.iterdir())
        except OSError:
            log.exception('Could not read the Downloads folder')
            return
        new_files = current_files - self.seen_downloads
        self.seen_downloads = current_files
        for file_path in sorted(new_files):
            if file_path.suffix.lower() in SONGSELECT_FILE_SUFFIXES:
                QtCore.QTimer.singleShot(AUTO_IMPORT_DELAY_MS, lambda path=file_path: self.auto_import_file(path))

    def auto_import_file(self, file_path):
        """
        Import a file that just appeared in the Downloads folder, if it is a SongSelect song

        :param pathlib.Path file_path: The new file
        """
        if not is_songselect_file(file_path):
            log.debug('Ignoring download that is not a SongSelect song: {path}'.format(path=file_path))
            return
        try:
            imported = self.import_song_file(file_path)
        except Exception:
            log.exception('Failed to auto-import SongSelect file {path}'.format(path=file_path))
            self.message_area.setText(translate('SongsPlugin.SongSelectForm',
                                                'Could not import {name}').format(name=file_path.name))
            return
        if imported:
            self.message_area.setText(translate('SongsPlugin.SongSelectForm',
                                                'Imported: {name}').format(name=file_path.stem))
            if self.plugin.media_item:
                self.plugin.media_item.on_search_text_button_clicked()

    def on_search_button_clicked(self):
        """
        Open the SongSelect search results for the text in the search box, in the user's web browser
        """
        search_text = self.search_edit.text().strip()
        if not search_text:
            self.on_browser_button_clicked()
            return
        url = QtCore.QUrl(SEARCH_URL)
        query = QtCore.QUrlQuery()
        query.addQueryItem('search', search_text)
        url.setQuery(query)
        QtGui.QDesktopServices.openUrl(url)
        self.message_area.setText(translate('SongsPlugin.SongSelectForm',
                                            'Click "Download" on the song in your browser. It will be imported here '
                                            'automatically.'))

    def page_load_started(self):
        self.back_button.setEnabled(False)
        self.url_bar.setCursorPosition(0)
        self.url_bar.setVisible(True)
        self.message_area.setText(translate('SongsPlugin.SongSelectForm',
                                            'Type a song above and click "Search SongSelect". In your browser, click '
                                            '"Download" on the Lyrics tab - the song is imported here automatically.'))

    def page_loaded(self, successful):
        self.song = None
        page_type = self.song_select_importer.get_page_type()
        if page_type == Pages.Login:
            self.signin_page_loaded()
        else:
            self.back_button.setEnabled(True)

    def signin_page_loaded(self):
        username = self.settings.value('songs/songselect username')
        password = self.settings.value('songs/songselect password')
        self.song_select_importer.set_login_fields(username, password)

    def _view_song(self):
        """
        Load a song into the song view.
        """
        if not self.song:
            QtWidgets.QMessageBox.critical(
                self, translate('SongsPlugin.SongSelectForm', 'Incomplete song'),
                translate('SongsPlugin.SongSelectForm', 'This song is missing some information, like the lyrics, '
                                                        'and cannot be imported.'),
                QtWidgets.QMessageBox.StandardButtons(QtWidgets.QMessageBox.Ok), QtWidgets.QMessageBox.Ok)
            return
        # Clear up the UI
        self.author_list_widget.clear()
        self.lyrics_table_widget.clear()
        self.lyrics_table_widget.setRowCount(0)
        # Update the UI
        self.title_edit.setText(self.song['title'])
        self.copyright_edit.setText(self.song['copyright'])
        self.ccli_edit.setText(self.song['ccli_number'])
        for author in self.song['authors']:
            self.author_list_widget.addItem(QtWidgets.QListWidgetItem(author, self.author_list_widget))
        for counter, verse in enumerate(self.song['verses']):
            self.lyrics_table_widget.setRowCount(self.lyrics_table_widget.rowCount() + 1)
            item = QtWidgets.QTableWidgetItem(verse['lyrics'])
            item.setData(QtCore.Qt.UserRole, verse['label'])
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.lyrics_table_widget.setItem(counter, 0, item)
        self.lyrics_table_widget.setVerticalHeaderLabels([verse['label'] for verse in self.song['verses']])
        self.lyrics_table_widget.resizeRowsToContents()
        self.lyrics_table_widget.scrollToTop()
        self.stacked_widget.setCurrentIndex(1)

    def on_url_bar_return_pressed(self):
        """
        Go to the url in the url bar
        """
        url = self.url_bar.text()
        self.song_select_importer.set_page(url)

    def on_back_button_clicked(self, force_return_to_home=False):
        """
        Go back to the search page or just to the webview if on the preview screen
        """
        if (self.stacked_widget.currentIndex() == 0 or force_return_to_home):
            self.song_select_importer.set_home_page()
        else:
            self.url_bar.setEnabled(True)
        self.stacked_widget.setCurrentIndex(0)

    def check_for_duplicate(self, song_content):
        """
        Warn user if a song exists in the database with the same ccli_number
        """
        # First extract the CCLI number of the song
        match = re.search(r'\nCCLI.+?#\s*(\d+)', song_content)
        if match:
            self.ccli_number = match.group(1)
        else:
            return True
        songs_with_same_ccli_number = self.plugin.manager.get_all_objects(
            Song, and_(Song.ccli_number.like(self.ccli_number), Song.ccli_number != ''))
        if len(songs_with_same_ccli_number) > 0:
            continue_import = QtWidgets.QMessageBox.question(self,
                                                             translate('SongsPlugin.SongSelectForm',
                                                                       'Song Duplicate Warning'),
                                                             translate('SongsPlugin.SongSelectForm',
                                                                       'A song with the same CCLI number is already in '
                                                                       'your database.\n\n'
                                                                       'Are you sure you want to import this song?'),
                                                             defaultButton=QtWidgets.QMessageBox.No)
            if continue_import == QtWidgets.QMessageBox.No:
                return False
        return True
