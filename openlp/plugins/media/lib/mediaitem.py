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

import logging
import os
from pathlib import Path

from PyQt5 import QtCore, QtWidgets
from sqlalchemy.sql.expression import or_

from openlp.core.common import delete_file
from openlp.core.common.applocation import AppLocation
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.path import create_paths
from openlp.core.common.registry import Registry
from openlp.core.lib import MediaType, ServiceItemContext
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.core.lib.ui import create_action, create_widget_action, critical_error_message_box
from openlp.core.state import State
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.library import FolderLibraryItem
from openlp.core.ui.media import parse_optical_path, parse_stream_path, format_milliseconds, AUDIO_EXT, VIDEO_EXT
from openlp.core.ui.media.vlcplayer import get_vlc

from openlp.plugins.media.lib.db import Folder, Item

if get_vlc() is not None:
    from openlp.plugins.media.forms.mediaclipselectorform import MediaClipSelectorForm
    from openlp.plugins.media.forms.streamselectorform import StreamSelectorForm
    from openlp.plugins.media.forms.networkstreamselectorform import NetworkStreamSelectorForm


log = logging.getLogger(__name__)


class MediaMediaItem(FolderLibraryItem):
    """
    This is the custom media manager item for Media Slides.
    """
    media_go_live = QtCore.pyqtSignal(list)
    media_add_to_service = QtCore.pyqtSignal(list)
    log.info('{name} MediaMediaItem loaded'.format(name=__name__))

    def __init__(self, parent, plugin):
        self.setup()
        super(MediaMediaItem, self).__init__(parent, plugin, Folder, Item)

    def retranslate_ui(self):
        """
        This method is called automatically to provide OpenLP with the opportunity to translate the ``MediaManagerItem``
        to another language.
        """
        super().retranslate_ui()
        self.on_new_prompt = translate('MediaPlugin.MediaItem', 'Select Media')

    def setup_item(self):
        """
        Do some additional setup.
        """
        self.media_go_live.connect(self.go_live_remote)
        self.media_add_to_service.connect(self.add_to_service_remote)
        self.single_service_item = False
        self.has_search = True
        self.media_object = None
        Registry().register_function('mediaitem_media_rebuild', self.rebuild_players)
        # Allow DnD from the desktop
        self.list_view.activateDnD()

    def setup(self):
        """
        Allow early setup to be mocked.
        """
        self.icon_path = 'images/image'
        self.background = False
        self.automatic = ''
        self.error_icon = UiIcons().delete
        self.clapperboard = UiIcons().clapperboard

    def required_icons(self):
        """
        Set which icons the media manager tab should show
        """
        super().required_icons()
        self.has_file_icon = True
        self.has_new_icon = False
        self.has_edit_icon = False
        if not State().check_preconditions('media'):
            self.can_preview = False
            self.can_make_live = False
            self.can_add_to_service = False
        if State().check_preconditions('media_live'):
            self.can_make_live = True
        else:
            self.can_preview = False
            self.can_make_live = False
            self.can_add_to_service = False

    def initialise(self):
        """
        Initialize media item.
        """
        self.log_debug('Initialise')
        self.list_view.clear()
        self.list_view.setIndentation(self.list_view.default_indentation)
        self.list_view.allow_internal_dnd = True
        self.service_path = AppLocation.get_section_data_path(self.settings_section) / 'thumbnails'
        create_paths(self.service_path)
        # Load images from the database
        self.load_list(self.manager.get_all_objects(Item, order_by_ref=Item.file_path), is_initial_load=True)
        self.service_path = AppLocation.get_section_data_path('media') / 'thumbnails'
        self.rebuild_players()

    def add_custom_context_actions(self):
        """
        Add custom actions to the context menu.
        """
        create_widget_action(self.list_view, separator=True)
        create_widget_action(
            self.list_view,
            text=UiStrings().AddFolder, icon=UiIcons().folder, triggers=self.on_add_folder_click)
        create_widget_action(
            self.list_view,
            text=translate('MediaPlugin', 'Add new media'),
            icon=UiIcons().open, triggers=self.on_file_click)
        create_widget_action(self.list_view, separator=True)

    def setup_ui(self):
        """
        Re-implement to add a dropdown menu to the load icon
        """
        super().setup_ui()
        if State().check_preconditions('media'):
            optical_button_text = translate('MediaPlugin.MediaItem', 'Load CD/DVD')
            optical_button_tooltip = translate('MediaPlugin.MediaItem', 'Load CD/DVD')
            self.load_optical = create_action(self, 'load_optical',
                                              icon=UiIcons().optical,
                                              text=optical_button_text,
                                              tooltip=optical_button_tooltip,
                                              triggers=self.on_load_optical)
            device_stream_button_text = translate('MediaPlugin.MediaItem', 'Open device stream')
            device_stream_button_tooltip = translate('MediaPlugin.MediaItem', 'Open device stream')
            self.open_stream = create_action(self, 'open_device_stream',
                                             icon=UiIcons().device_stream,
                                             text=device_stream_button_text,
                                             tooltip=device_stream_button_tooltip,
                                             triggers=self.on_open_device_stream)
            network_stream_button_text = translate('MediaPlugin.MediaItem', 'Open network stream')
            network_stream_button_tooltip = translate('MediaPlugin.MediaItem', 'Open network stream')
            self.open_network_stream = create_action(self, 'open_network_stream',
                                                     icon=UiIcons().network_stream,
                                                     text=network_stream_button_text,
                                                     tooltip=network_stream_button_tooltip,
                                                     triggers=self.on_open_network_stream)
            self.load_menu = QtWidgets.QMenu(self.toolbar)
            self.load_menu.setObjectName('load_menu')
            self.load_menu.addAction(self.load_optical)
            self.load_menu.addAction(self.open_stream)
            self.load_menu.addAction(self.open_network_stream)
            self.toolbar.actions['mediaLoadAction'].setMenu(self.load_menu)
            button = self.toolbar.widgetForAction(self.toolbar.actions['mediaLoadAction'])
            button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)

    def generate_slide_data(self, service_item, *, item=None, remote=False, context=ServiceItemContext.Service,
                            **kwargs):
        """
        Generate the slide data. Needs to be implemented by the plugin.

        :param service_item: The service item to be built on
        :param item: The Song item to be used
        :param remote: Triggered from remote
        :param context: Why is it being generated
        :param kwargs: Consume other unused args specified by the base implementation, but not use by this one.
        """
        if item is None:
            item = self.list_view.currentItem()
            if item is None:
                return False
        if isinstance(item, QtCore.QModelIndex):
            item = self.list_view.itemFromIndex(item)
        media_item = item.data(0, QtCore.Qt.UserRole)
        if not isinstance(media_item, Item):
            return False
        filename = media_item.file_path
        # Special handling if the filename is a optical clip
        if filename.startswith('optical:'):
            (name, title, audio_track, subtitle_track, start, end, clip_name) = parse_optical_path(filename)
            if not os.path.exists(name):
                if not remote:
                    # Optical disc is no longer present
                    critical_error_message_box(
                        translate('MediaPlugin.MediaItem', 'Missing Media File'),
                        translate('MediaPlugin.MediaItem',
                                  'The optical disc {name} is no longer available.').format(name=name))
                return False
            service_item.processor = 'vlc'
            service_item.add_capability(ItemCapabilities.IsOptical)
            service_item.add_from_command(filename, name, self.clapperboard)
            service_item.title = clip_name
            # Set the length
            service_item.set_media_length(end - start)
            service_item.start_time = start
            service_item.end_time = end
        elif filename.startswith('devicestream:') or filename.startswith('networkstream:'):
            # Special handling if the filename is a devicestream
            (name, mrl, options) = parse_stream_path(filename)
            service_item.processor = 'vlc'
            service_item.add_capability(ItemCapabilities.CanStream)
            service_item.add_from_command(filename, name, self.clapperboard)
            service_item.title = name
        else:
            if not os.path.exists(filename):
                if not remote:
                    # File is no longer present
                    critical_error_message_box(
                        translate('MediaPlugin.MediaItem', 'Missing Media File'),
                        translate('MediaPlugin.MediaItem', 'The file {name} no longer exists.').format(name=filename))
                return False
            (path, name) = os.path.split(filename)
            service_item.title = name
            service_item.processor = 'vlc'
            service_item.add_from_command(path, name, self.clapperboard)
            # Only get start and end times if going to a service
            service_item.set_media_length(self.media_controller.media_length(filename))
        service_item.add_capability(ItemCapabilities.CanAutoStartForLive)
        service_item.add_capability(ItemCapabilities.CanEditTitle)
        service_item.add_capability(ItemCapabilities.RequiresMedia)
        # force a non-existent theme
        service_item.theme = -1
        # validate the item after all capabilities has been added
        service_item.validate_item()
        return True

    def rebuild_players(self):
        """
        Rebuild the tab in the media manager when changes are made in the settings.
        """
        # self.populate_display_types()
        self.on_new_file_masks = translate('MediaPlugin.MediaItem',
                                           'Videos ({video});;Audio ({audio});;{files} '
                                           '(*)').format(video=' '.join(VIDEO_EXT),
                                                         audio=' '.join(AUDIO_EXT),
                                                         files=UiStrings().AllFiles)

    def file_to_item(self, filename):
        """
        Override the inherited file_to_item() method to handle various tracks
        """
        if isinstance(filename, Path):
            name = filename.name
            filename = str(filename)
        elif filename.startswith('optical:'):
            # Handle optical based item
            _, _, _, _, _, _, name = parse_optical_path(filename)
        elif filename.startswith('devicestream:') or filename.startswith('networkstream:'):
            name, _, _ = parse_stream_path(filename)
        else:
            name = os.path.basename(filename)
        item = self.item_class(name=name, file_path=filename)
        self.manager.save_object(item)
        return item

    def load_item(self, item, is_initial_load=False):
        """
        Given an item object, return a QTreeWidgetItem
        """
        track_str = str(item.file_path)
        track_info = QtCore.QFileInfo(track_str)
        tree_item = None
        if track_str.startswith('optical:'):
            # Handle optical based item
            (file_name, title, audio_track, subtitle_track, start, end, clip_name) = parse_optical_path(track_str)
            tree_item = QtWidgets.QTreeWidgetItem([clip_name])
            tree_item.setText(0, clip_name)
            tree_item.setIcon(0, UiIcons().optical)
            tree_item.setToolTip(0, '{name}@{start}-{end}'.format(name=file_name,
                                                                  start=format_milliseconds(start),
                                                                  end=format_milliseconds(end)))
        elif track_str.startswith('devicestream:') or track_str.startswith('networkstream:'):
            (name, mrl, options) = parse_stream_path(track_str)
            tree_item = QtWidgets.QTreeWidgetItem([name])
            tree_item.setText(0, name)
            if track_str.startswith('devicestream:'):
                tree_item.setIcon(0, UiIcons().device_stream)
            else:
                tree_item.setIcon(0, UiIcons().network_stream)
            tree_item.setToolTip(0, mrl)
        elif not Path(item.file_path).exists():
            # File doesn't exist, mark as error.
            file_name = Path(item.file_path).name
            tree_item = QtWidgets.QTreeWidgetItem([file_name])
            tree_item.setText(0, file_name)
            tree_item.setIcon(0, UiIcons().error)
            tree_item.setToolTip(0, track_str)
        elif track_info.isFile():
            # Normal media file handling.
            file_name = Path(item.file_path).name
            tree_item = QtWidgets.QTreeWidgetItem([file_name])
            tree_item.setText(0, file_name)
            search = "*." + file_name.split('.')[-1].lower()
            if search in AUDIO_EXT:
                tree_item.setIcon(0, UiIcons().audio)
            else:
                tree_item.setIcon(0, UiIcons().video)
            tree_item.setToolTip(0, track_str)
        if tree_item:
            tree_item.setData(0, QtCore.Qt.UserRole, item)
        return tree_item

    def delete_item(self, item):
        """
        Delete any and all thumbnails and things associated with this media item
        """
        delete_file(self.service_path / Path(item.file_path).name)

    def format_search_result(self, item):
        """
        Format an item for the search results

        :param Item item: An Item to be formatted
        :return list[str, str]: A list of two items containing the full path and a pretty name
        """
        if Path(item.file_path).exists():
            return [item.file_path, Path(item.file_path).name]
        elif item.file_path.startswith('device'):
            (name, _, _) = parse_stream_path(item.file_path)
            return [item.file_path, name]
        else:
            return super().format_search_result(item)

    def get_list(self, media_type=MediaType.Audio):
        """
        Get the list of media, optional select media type.

        :param media_type: Type to get, defaults to audio.
        :return: The media list
        """
        if media_type == MediaType.Audio:
            extensions = AUDIO_EXT
        else:
            extensions = VIDEO_EXT
        clauses = []
        for extension in extensions:
            # Drop the initial * and add to the list of clauses
            clauses.append(Item.file_path.endswith(extension[1:]))
        items = self.manager.get_all_objects(Item, or_(*clauses))
        return [Path(item.file_path) for item in items]

    def on_load_optical(self):
        """
        When the load optical button is clicked, open the clip selector window.
        """
        if get_vlc():
            media_clip_selector_form = MediaClipSelectorForm(self, self.main_window, None)
            media_clip_selector_form.exec()
            del media_clip_selector_form
        else:
            critical_error_message_box(translate('MediaPlugin.MediaItem', 'VLC is not available'),
                                       translate('MediaPlugin.MediaItem', 'Optical device support requires VLC.'))

    def add_optical_clip(self, optical):
        """
        Add a optical based clip to the mediamanager, called from media_clip_selector_form.

        :param optical: The clip to add.
        """
        self.validate_and_load([str(optical)])

    def on_open_device_stream(self):
        """
        When the open device stream button is clicked, open the stream selector window.
        """
        if get_vlc():
            stream_selector_form = StreamSelectorForm(self.main_window, self.add_device_stream)
            stream_selector_form.exec()
            del stream_selector_form
        else:
            critical_error_message_box(translate('MediaPlugin.MediaItem', 'VLC is not available'),
                                       translate('MediaPlugin.MediaItem', 'Device streaming support requires VLC.'))

    def add_device_stream(self, stream):
        """
        Add a device stream based clip to the mediamanager, called from stream_selector_form.

        :param stream: The clip to add.
        """
        self.validate_and_load([str(stream)])

    def on_open_network_stream(self):
        """
        When the open network stream button is clicked, open the stream selector window.
        """
        if get_vlc():
            stream_selector_form = NetworkStreamSelectorForm(self.main_window, self.add_network_stream)
            stream_selector_form.exec()
            del stream_selector_form
        else:
            critical_error_message_box(translate('MediaPlugin.MediaItem', 'VLC is not available'),
                                       translate('MediaPlugin.MediaItem', 'Network streaming support requires VLC.'))

    def add_network_stream(self, stream):
        """
        Add a network stream based clip to the mediamanager, called from stream_selector_form.

        :param stream: The clip to add.
        """
        self.validate_and_load([str(stream)])
