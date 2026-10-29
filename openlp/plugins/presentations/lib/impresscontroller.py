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

# OOo API documentation:
# http://api.openoffice.org/docs/common/ref/com/sun/star/presentation/XSlideShowController.html
# http://wiki.services.openoffice.org/wiki/Documentation/DevGuide/ProUNO/Basic
#                          /Getting_Information_about_UNO_Objects#Inspecting_interfaces_during_debugging
# http://docs.go-oo.org/sd/html/classsd_1_1SlideShow.html
# http://www.oooforum.org/forum/viewtopic.phtml?t=5252
# http://wiki.services.openoffice.org/wiki/Documentation/DevGuide/Working_with_Presentations
# http://mail.python.org/pipermail/python-win32/2008-January/006676.html
# http://www.linuxjournal.com/content/starting-stopping-and-connecting-openoffice-python
# http://nxsy.org/comparing-documents-with-openoffice-and-python

import logging
import posixpath
import subprocess
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from PyQt5 import QtCore

from openlp.core.common import delete_file, get_uno_command, get_uno_instance, trace_error_handler
from openlp.core.common.platform import is_win
from openlp.core.common.registry import Registry
from openlp.core.display.screens import ScreenList
from openlp.plugins.presentations.lib.presentationcontroller import PresentationController, PresentationDocument, \
    TextType

# Declare the XSlideShowListener class so we can inherit from it below, won't really use in on windows.
if is_win():
    import winreg
    from win32com.client import Dispatch
    import pywintypes
    uno_available = False

    class SlideShowListenerImport:
        pass

    # Declare an empty exception to match the exception imported from UNO
    class ErrorCodeIOException(Exception):
        pass
else:
    # Load the XSlideShowListener class so we can inherit from it below
    try:
        import uno
        import unohelper
        from com.sun.star.beans import PropertyValue
        from com.sun.star.task import ErrorCodeIOException
        from com.sun.star.presentation import XSlideShowListener

        class SlideShowListenerImport(unohelper.Base, XSlideShowListener):
            pass

        uno_available = True
    except ImportError:
        uno_available = False

        class SlideShowListenerImport:
            pass

log = logging.getLogger(__name__)


def get_com_soffice_path():
    """
    Find soffice.exe from the COM registration of the LibreOffice/OpenOffice service manager.

    :return: The path to soffice.exe, or None if it is not registered or no longer exists
    :rtype: Path | None
    """
    try:
        clsid = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, r'com.sun.star.ServiceManager\CLSID')
        command = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, r'CLSID\{clsid}\LocalServer32'.format(clsid=clsid))
    except OSError:
        return None
    # The value is the exe followed by arguments, e.g. "C:\Program Files\LibreOffice\program\soffice.exe --nologo"
    command = command.strip()
    if command.startswith('"'):
        exe = command[1:].split('"', 1)[0]
    else:
        exe = command.split(' --', 1)[0].split(' -', 1)[0]
    path = Path(exe)
    return path if path.is_file() else None


PACKAGE_RELS_NS = '{http://schemas.openxmlformats.org/package/2006/relationships}'
PPTX_MAIN_NS = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
PPTX_RELS_ID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
ODF_DRAW_NS = '{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}'
ODF_PRESENTATION_NS = '{urn:oasis:names:tc:opendocument:xmlns:presentation:1.0}'
ODF_XLINK_HREF = '{http://www.w3.org/1999/xlink}href'


def _read_pptx_rels(package, part_name):
    """
    :return: {relationship id: (type, target)} for a part of a .pptx, with targets resolved inside the package
    """
    folder, name = posixpath.split(part_name)
    try:
        root = ElementTree.fromstring(package.read(posixpath.join(folder, '_rels', name + '.rels')))
    except KeyError:
        return {}
    rels = {}
    for rel in root.iter(PACKAGE_RELS_NS + 'Relationship'):
        target = rel.get('Target', '')
        if rel.get('TargetMode') != 'External':
            target = posixpath.normpath(posixpath.join(folder, target))
        rels[rel.get('Id')] = (rel.get('Type', ''), target)
    return rels


def _get_pptx_slides_with_video(package):
    presentation_rels = _read_pptx_rels(package, 'ppt/presentation.xml')
    slide_list = ElementTree.fromstring(package.read('ppt/presentation.xml')).find(PPTX_MAIN_NS + 'sldIdLst')
    slides = []
    for number, slide_id in enumerate(slide_list if slide_list is not None else [], 1):
        slide_part = presentation_rels.get(slide_id.get(PPTX_RELS_ID), ('', ''))[1]
        if any(rel_type.endswith('/video') for rel_type, _ in _read_pptx_rels(package, slide_part).values()):
            slides.append(number)
    return slides


def _get_odp_slides_with_video(package):
    from openlp.core.ui.media import VIDEO_EXT
    video_suffixes = {ext[1:] for ext in VIDEO_EXT}
    slides = []
    for number, page in enumerate(ElementTree.fromstring(package.read('content.xml')).iter(ODF_DRAW_NS + 'page'), 1):
        # Media in the speaker notes is never played
        notes = page.find(ODF_PRESENTATION_NS + 'notes')
        notes_plugins = set(notes.iter(ODF_DRAW_NS + 'plugin')) if notes is not None else set()
        for plugin in page.iter(ODF_DRAW_NS + 'plugin'):
            if plugin in notes_plugins:
                continue
            if plugin.get(ODF_DRAW_NS + 'mime-type', '').startswith('video/') or \
                    Path(plugin.get(ODF_XLINK_HREF, '')).suffix.lower() in video_suffixes:
                slides.append(number)
                break
    return slides


def get_slides_with_video(file_path):
    """
    Find the slides of a .pptx or .odp file that hold a video, embedded or linked. LibreOffice can crash or garble the
    picture when it plays them, so the videos should be attached to the slides in OpenLP instead.

    :param Path file_path: The presentation
    :return: The slide numbers, counting from 1. Empty for other file types or files that cannot be read.
    :rtype: list[int]
    """
    try:
        with zipfile.ZipFile(file_path) as package:
            if file_path.suffix.lower() in ('.pptx', '.pptm', '.ppsx', '.ppsm'):
                return _get_pptx_slides_with_video(package)
            if file_path.suffix.lower() in ('.odp', '.otp'):
                return _get_odp_slides_with_video(package)
    except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError):
        log.exception('Could not look for videos in {path}'.format(path=file_path))
    return []


class ImpressController(PresentationController):
    """
    Class to control interactions with Impress presentations. It creates the runtime environment, loads and closes the
    presentation as well as triggering the correct activities based on the users input.
    """
    log.info('ImpressController loaded')

    def __init__(self, plugin):
        """
        Initialise the class
        """
        log.debug('Initialising')
        super(ImpressController, self).__init__(plugin, 'Impress', ImpressDocument)
        self.supports = ['odp']
        self.also_supports = ['ppt', 'pps', 'pptx', 'ppsx', 'pptm']
        self.process = None
        self.desktop = None
        self.manager = None
        self.conf_provider = None
        self.presenter_screen_disabled_by_openlp = False
        self.office_started = False

    def check_available(self):
        """
        Impress is able to run on this machine.
        """
        log.debug('check_available')
        if is_win():
            return self.get_com_servicemanager() is not None
        return uno_available

    def start_process(self):
        """
        Loads a running version of OpenOffice in the background. It is not displayed to the user but is available to the
        UNO interface when required.
        """
        log.debug('start process Openoffice')
        if is_win():
            self.manager = self.get_com_servicemanager()
            if self.manager is None:
                return
            self.manager._FlagAsMethod('Bridge_GetStruct')
            self.manager._FlagAsMethod('Bridge_GetValueObject')
        else:
            # -headless
            cmd = get_uno_command()
            self.process = QtCore.QProcess()
            self.process.startDetached(cmd)

    def get_uno_desktop(self):
        """
        On non-Windows platforms, use Uno. Get the OpenOffice desktop which will be used to manage impress.
        """
        log.debug('get UNO Desktop Openoffice')
        uno_instance = None
        loop = 0
        log.debug('get UNO Desktop Openoffice - getComponentContext')
        context = uno.getComponentContext()
        log.debug('get UNO Desktop Openoffice - createInstaneWithContext - UnoUrlResolver')
        resolver = context.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', context)
        while uno_instance is None and loop < 3:
            try:
                uno_instance = get_uno_instance(resolver)
            except Exception:
                log.warning('Unable to find running instance ')
                self.start_process()
                loop += 1
        try:
            self.manager = uno_instance.ServiceManager
            log.debug('get UNO Desktop Openoffice - createInstanceWithContext - Desktop')
            desktop = self.manager.createInstanceWithContext("com.sun.star.frame.Desktop", uno_instance)
            self.toggle_presentation_screen(False)
            return desktop
        except Exception:
            log.exception('Failed to get UNO desktop')
            return None

    def get_com_desktop(self):
        """
        On Windows platforms, use COM. Return the desktop object which will be used to manage Impress.
        """
        log.debug('get COM Desktop OpenOffice')
        if not self.manager:
            return None
        desktop = None
        try:
            desktop = self.manager.createInstance('com.sun.star.frame.Desktop')
        except (AttributeError, pywintypes.com_error):
            log.warning('Failure to find desktop - Impress may have closed')
        if not desktop:
            # LibreOffice closed or crashed, so the old connection is dead: let it be started again with --norestore
            self.office_started = False
            self.conf_provider = None
            return None
        self.toggle_presentation_screen(False)
        return desktop

    def get_com_servicemanager(self):
        """
        Return the OOo service manager for windows.
        """
        log.debug('get_com_servicemanager openoffice')
        self.start_office_without_restore()
        try:
            return Dispatch('com.sun.star.ServiceManager')
        except pywintypes.com_error:
            log.warning('Failed to get COM service manager. Impress Controller has been disabled')
            return None

    def start_office_without_restore(self):
        """
        On Windows, COM starts LibreOffice by itself, and after a crash LibreOffice then opens its Document Recovery
        dialog. That dialog is hidden behind OpenLP and blocks every COM call, so start LibreOffice ourselves with
        --norestore before COM connects. If it is already running, the arguments are handed to that instance.
        """
        if self.office_started:
            return
        self.office_started = True
        soffice = get_com_soffice_path()
        if not soffice:
            return
        try:
            subprocess.Popen([str(soffice), '--norestore', '--nologo', '--nodefault'],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            log.exception('Failed to start {path}'.format(path=soffice))
            return
        # Give it time to register with COM, otherwise COM starts a second copy that may show Document Recovery
        time.sleep(3)

    def kill(self):
        """
        Called at system exit to clean up any running presentations.
        """
        log.debug('Kill OpenOffice')
        # LibreOffice may have crashed or been closed, so nothing here may stop OpenLP from shutting down
        if self.presenter_screen_disabled_by_openlp:
            try:
                self.toggle_presentation_screen(True)
            except Exception:
                log.warning('Failed to re-enable the Presenter Screen - Impress may have closed')
        while self.docs:
            self.docs[0].close_presentation()
        desktop = None
        try:
            if not is_win():
                desktop = self.get_uno_desktop()
            else:
                desktop = self.get_com_desktop()
        except Exception:
            log.warning('Failed to find an OpenOffice desktop to terminate')
        if not desktop:
            return
        cnt = 0
        try:
            docs = desktop.getComponents()
            if docs.hasElements():
                list_elements = docs.createEnumeration()
                while list_elements.hasMoreElements():
                    doc = list_elements.nextElement()
                    if doc.getImplementationName() != 'com.sun.star.comp.framework.BackingComp':
                        cnt += 1
        except Exception:
            log.warning('Failed to list OpenOffice documents - Impress may have closed')
            return
        if cnt > 0:
            log.debug('OpenOffice not terminated as docs are still open')
        else:
            try:
                desktop.terminate()
                log.debug('OpenOffice killed')
            except Exception:
                log.warning('Failed to terminate OpenOffice')

    def toggle_presentation_screen(self, set_visible):
        """
        Enable or disable the Presentation Screen/Console

        :param bool set_visible: Should the presentation screen/console be set to be visible.
        :rtype: None
        """
        # Create Instance of ConfigurationProvider
        if not self.conf_provider:
            if is_win():
                self.conf_provider = self.manager.createInstance('com.sun.star.configuration.ConfigurationProvider')
            else:
                self.conf_provider = self.manager.createInstanceWithContext(
                    'com.sun.star.configuration.ConfigurationProvider', uno.getComponentContext())
        # Setup lookup properties to get Impress settings
        properties = (self.create_property('nodepath', 'org.openoffice.Office.Impress'),)
        try:
            # Get an updateable configuration view
            impress_conf_props = self.conf_provider.createInstanceWithArguments(
                'com.sun.star.configuration.ConfigurationUpdateAccess', properties)
            try:
                # Get the specific setting for presentation screen
                # For libre office this is 'EnablePresenterScreen' but for open office 'PresenterScreen'
                # So we try the libre office first, and this raises an exception if it doesn't exist
                presenter_screen_enabled = impress_conf_props.getHierarchicalPropertyValue(
                    'Misc/Start/EnablePresenterScreen')
                # If the presentation screen is enabled we disable it
                if presenter_screen_enabled != set_visible:
                    impress_conf_props.setHierarchicalPropertyValue('Misc/Start/EnablePresenterScreen', set_visible)
                    impress_conf_props.commitChanges()
                    # if set_visible is False this is an attempt to disable the Presenter Screen
                    # so we make a note that it has been disabled, so it can be enabled again on close.
                    if set_visible is False:
                        self.presenter_screen_disabled_by_openlp = True
            except Exception as e:
                # same code as above, except using 'PresenterScreen' which is the open office equivalent
                if 'UnknownPropertyException' in str(e):
                    presenter_screen_enabled = impress_conf_props.getHierarchicalPropertyValue(
                        'Misc/Start/PresenterScreen')
                    if presenter_screen_enabled != set_visible:
                        impress_conf_props.setHierarchicalPropertyValue('Misc/Start/PresenterScreen', set_visible)
                        impress_conf_props.commitChanges()
                        if set_visible is False:
                            self.presenter_screen_disabled_by_openlp = True
                else:
                    raise
        except Exception as e:
            log.exception(e)
            trace_error_handler(log)

    def create_property(self, name, value):
        """
        Create an OOo style property object which are passed into some Uno methods.

        :param str name: The name of the property
        :param str value: The value of the property
        :rtype: com.sun.star.beans.PropertyValue
        """
        log.debug('create property OpenOffice')
        if is_win():
            property_object = self.manager.Bridge_GetStruct('com.sun.star.beans.PropertyValue')
        else:
            property_object = PropertyValue()
        property_object.Name = name
        property_object.Value = value
        return property_object


class ImpressDocument(PresentationDocument):
    """
    Class which holds information and controls a single presentation.
    """

    def __init__(self, controller, document_path):
        """
        Constructor, store information about the file and initialise.

        :param pathlib.Path document_path: File path for the document to load
        :rtype: None
        """
        log.debug('Init Presentation OpenOffice')
        super().__init__(controller, document_path)
        self.document = None
        self.presentation = None
        self.control = None
        self.slide_ended = False
        self.slide_ended_reverse = False

    def load_presentation(self):
        """
        Called when a presentation is added to the SlideController. It builds the environment, starts communcations with
        the background OpenOffice task started earlier. If OpenOffice is not present is is started. Once the environment
        is available the presentation is loaded and started.
        """
        log.debug('Load Presentation OpenOffice')
        if is_win():
            desktop = self.controller.get_com_desktop()
            if desktop is None:
                self.controller.start_process()
                desktop = self.controller.get_com_desktop()
        else:
            desktop = self.controller.get_uno_desktop()
        url = self.file_path.as_uri()
        if desktop is None:
            return False
        self.desktop = desktop
        # UpdateDocMode FULL_UPDATE (3): without it, linked videos/sounds are blocked when loading through the API
        properties = (self.controller.create_property('Hidden', True),
                      self.controller.create_property('UpdateDocMode', 3))
        try:
            self.document = desktop.loadComponentFromURL(url, '_blank', 0, properties)
        except Exception:
            log.warning('Failed to load presentation {url}'.format(url=url))
            return False
        if self.document is None:
            log.warning('Presentation {url} could not be loaded'.format(url=url))
            return False
        self.presentation = self.document.getPresentation()
        # OpenOffice uses a screen numbering scheme where the primary display is 1 and the external monitor 2
        # but OpenLP sets screen numbers based on screen coordinates (geometry)
        # so we work out what OpenOffice display to use based on which of the openlp screens is primary
        # unless the user has defined in Settings to use the impress Slide Show setting for presentation display
        if not self.settings.value('presentations/impress use display setting'):
            public_display_screen_number = ScreenList().current.number
            screens = list(ScreenList())
            if screens[public_display_screen_number].is_primary:
                self.presentation.Display = 1
            else:
                self.presentation.Display = 2
        self.control = None
        self.create_thumbnails()
        self.create_titles_and_notes()
        return True

    def create_thumbnails(self):
        """
        Create thumbnail images for presentation.
        """
        log.debug('create thumbnails OpenOffice')
        if self.check_thumbnails():
            return
        temp_folder_path = self.get_temp_folder()
        thumb_dir_url = temp_folder_path.as_uri()
        properties = (self.controller.create_property('FilterName', 'impress_png_Export'),)
        doc = self.document
        pages = doc.getDrawPages()
        if not pages:
            return
        if not temp_folder_path.is_dir():
            temp_folder_path.mkdir(parents=True)
        for index in range(pages.getCount()):
            page = pages.getByIndex(index)
            doc.getCurrentController().setCurrentPage(page)
            url_path = '{path}/{name:d}.png'.format(path=thumb_dir_url, name=index + 1)
            path = temp_folder_path / '{number:d}.png'.format(number=index + 1)
            try:
                doc.storeToURL(url_path, properties)
                self.convert_thumbnail(path, index + 1)
                delete_file(path)
            except ErrorCodeIOException as exception:
                log.exception('ERROR! ErrorCodeIOException {error:d}'.format(error=exception.ErrCode))
            except Exception:
                log.exception('{path} - Unable to store openoffice preview'.format(path=path))
        # Return to the first page, otherwise the slide show starts on the last page exported
        doc.getCurrentController().setCurrentPage(pages.getByIndex(0))

    def close_presentation(self):
        """
        Close presentation and clean up objects. Triggered by new object being added to SlideController or OpenLP being
        shutdown.
        """
        log.debug('close Presentation OpenOffice')
        if self.document:
            if self.presentation:
                try:
                    self.presentation.end()
                    self.presentation = None
                    self.document.dispose()
                except Exception:
                    log.warning("Closing presentation failed")
            self.document = None
        self.controller.remove_doc(self)

    def is_loaded(self):
        """
        Returns true if a presentation is loaded.
        """
        log.debug('is loaded OpenOffice')
        if self.presentation is None or self.document is None:
            log.debug("is_loaded: no presentation or document")
            return False
        try:
            if self.document.getPresentation() is None:
                log.debug("getPresentation failed to find a presentation")
                return False
        except Exception:
            log.warning("getPresentation failed to find a presentation")
            return False
        return True

    def is_active(self):
        """
        Returns true if a presentation is active and running.
        """
        log.debug('is active OpenOffice')
        if not self.is_loaded():
            return False
        return self.is_control_running()

    def is_control_running(self):
        """
        Returns true if the slide show is running. LibreOffice may have crashed (e.g. playing a video), so a dead
        connection means it is not running.
        """
        if not self.control:
            return False
        try:
            return self.control.isRunning()
        except Exception:
            log.warning('Slide show is not answering - Impress may have closed')
            self.control = None
            return False

    def unblank_screen(self):
        """
        Unblanks the screen.
        """
        log.debug('unblank screen OpenOffice')
        return self.control.resume()

    def blank_screen(self):
        """
        Blanks the screen.
        """
        log.debug('blank screen OpenOffice')
        self.control.blankScreen(0)

    def is_blank(self):
        """
        Returns true if screen is blank.
        """
        log.debug('is blank OpenOffice')
        if self.is_control_running():
            return self.control.isPaused()
        return False

    def stop_presentation(self):
        """
        Stop the presentation, remove from screen.
        """
        log.debug('stop presentation OpenOffice')
        self.presentation.end()
        self.control = None

    def start_presentation(self):
        """
        Start the presentation from the beginning.
        """
        log.debug('start presentation OpenOffice')
        if not self.is_control_running():
            window = self.document.getCurrentController().getFrame().getContainerWindow()
            window.setVisible(True)
            self.presentation.start()
            self.control = self.presentation.getController()
            # start() returns before the Component is ready. Try for 15 seconds.
            sleep_count = 1
            while not self.control and sleep_count < 150:
                time.sleep(0.1)
                sleep_count += 1
                self.control = self.presentation.getController()
            window.setVisible(False)
            if not is_win():
                listener = SlideShowListener(self)
                self.control.getSlideShow().addSlideShowListener(listener)
        else:
            self.control.activate()
            self.goto_slide(1)
        # Make sure impress doesn't steal focus, unless we're on a single screen setup
        if len(ScreenList()) > 1:
            Registry().get('main_window').activateWindow()

    def get_slide_number(self):
        """
        Return the current slide number on the screen, from 1.
        """
        return self.control.getCurrentSlideIndex() + 1

    def get_slide_count(self):
        """
        Return the total number of slides.
        """
        return self.document.getDrawPages().getCount()

    def goto_slide(self, slide_no):
        """
        Go to a specific slide (from 1).

        :param slide_no: The slide the text is required for, starting at 1
        """
        self.control.gotoSlideIndex(slide_no - 1)

    def next_step(self):
        """
        Triggers the next effect of slide on the running presentation.
        """
        # if we are at the presentations end don't go further, just return True
        if self.slide_ended and self.get_slide_count() == self.get_slide_number():
            return True
        self.slide_ended = False
        self.slide_ended_reverse = False
        past_end = False
        is_paused = self.control.isPaused()
        self.control.gotoNextEffect()
        time.sleep(0.1)
        # If for some reason the presentation end was not detected above, this will catch it.
        # The presentation is set to paused when going past the end.
        if not is_paused and self.control.isPaused():
            self.control.gotoPreviousEffect()
            past_end = True
        return past_end

    def previous_step(self):
        """
        Triggers the previous slide on the running presentation.
        """
        # if we are at the presentations start don't go further back, just return True
        if self.slide_ended_reverse and self.get_slide_number() == 1:
            return True
        self.slide_ended = False
        self.slide_ended_reverse = False
        self.control.gotoPreviousEffect()
        return False

    def get_slide_text(self, slide_no):
        """
        Returns the text on the slide.

        :param slide_no: The slide the text is required for, starting at 1
        """
        return self.__get_text_from_page(slide_no)

    def get_slide_notes(self, slide_no):
        """
        Returns the text in the slide notes.

        :param slide_no: The slide the notes are required for, starting at 1
        """
        return self.__get_text_from_page(slide_no, TextType.Notes)

    def __get_text_from_page(self, slide_no, text_type=TextType.SlideText):
        """
        Return any text extracted from the presentation page.

        :param slide_no: The slide the notes are required for, starting at 1
        :param notes: A boolean. If set the method searches the notes of the slide.
        :param text_type: A TextType. Enumeration of the types of supported text.
        """
        text = ''
        if TextType.Title <= text_type <= TextType.Notes:
            pages = self.document.getDrawPages()
            if 0 < slide_no <= pages.getCount():
                page = pages.getByIndex(slide_no - 1)
                if text_type == TextType.Notes:
                    page = page.getNotesPage()
                for index in range(page.getCount()):
                    shape = page.getByIndex(index)
                    shape_type = shape.getShapeType()
                    if shape.supportsService("com.sun.star.drawing.Text"):
                        # if they requested title, make sure it is the title
                        if text_type == TextType.Title and shape_type != "com.sun.star.presentation.TitleTextShape":
                            continue
                        # notes pages also hold slide number/header/footer placeholders, so skip those
                        if text_type == TextType.Notes and shape_type != "com.sun.star.presentation.NotesShape":
                            continue
                        text += shape.getString() + '\n'
        return text

    def create_titles_and_notes(self):
        """
        Writes the list of titles (one per slide) to 'titles.txt' and the notes to 'slideNotes[x].txt'
        in the thumbnails directory
        """
        titles = []
        notes = []
        pages = self.document.getDrawPages()
        for slide_no in range(1, pages.getCount() + 1):
            titles.append(self.__get_text_from_page(slide_no, TextType.Title).replace('\r\n', ' ')
                                                                             .replace('\n', ' ').strip())
            note = self.__get_text_from_page(slide_no, TextType.Notes)
            if len(note) == 0:
                note = ' '
            notes.append(note)
        self.save_titles_and_notes(titles, notes)


class SlideShowListener(SlideShowListenerImport):
    """
    Listener interface to receive global slide show events.
    """

    def __init__(self, document):
        """
        Constructor

        :param document: The ImpressDocument being presented
        """
        self.document = document

    def paused(self):
        """
        Notify that the slide show is paused
        """
        log.debug('LibreOffice SlideShowListener event: paused')

    def resumed(self):
        """
        Notify that the slide show is resumed from a paused state
        """
        log.debug('LibreOffice SlideShowListener event: resumed')

    def slideTransitionStarted(self):
        """
        Notify that a new slide starts to become visible.
        """
        log.debug('LibreOffice SlideShowListener event: slideTransitionStarted')

    def slideTransitionEnded(self):
        """
        Notify that the slide transtion of the current slide ended.
        """
        log.debug('LibreOffice SlideShowListener event: slideTransitionEnded')

    def slideAnimationsEnded(self):
        """
        Notify that the last animation from the main sequence of the current slide has ended.
        """
        log.debug('LibreOffice SlideShowListener event: slideAnimationsEnded')
        if not Registry().get('main_window').isActiveWindow():
            log.debug('main window is not in focus - should update slidecontroller')
            Registry().execute('slidecontroller_live_change', self.document.control.getCurrentSlideIndex() + 1)

    def slideEnded(self, reverse):
        """
        Notify that the current slide has ended, e.g. the user has clicked on the slide. Calling displaySlide()
        twice will not issue this event.

        :param bool reverse: Whether or not the direction of the "slide movement" is reversed/backwards.
        :rtype: None
        """
        log.debug('LibreOffice SlideShowListener event: slideEnded %d' % reverse)
        if reverse:
            self.document.slide_ended = False
            self.document.slide_ended_reverse = True
        else:
            self.document.slide_ended = True
            self.document.slide_ended_reverse = False

    def hyperLinkClicked(self, hyperLink):
        """
        Notifies that a hyperlink has been clicked.
        """
        log.debug('LibreOffice SlideShowListener event: hyperLinkClicked %s' % hyperLink)

    def disposing(self, source):
        """
        gets called when the broadcaster is about to be disposed.
        :param source:
        """
        log.debug('LibreOffice SlideShowListener event: disposing')

    def beginEvent(self, node):
        """
        This event is raised when the element local timeline begins to play.
        :param node:
        """
        log.debug('LibreOffice SlideShowListener event: beginEvent')

    def endEvent(self, node):
        """
        This event is raised at the active end of the element.
        :param node:
        """
        log.debug('LibreOffice SlideShowListener event: endEvent')

    def repeat(self, node):
        """
        This event is raised when the element local timeline repeats.
        :param node:
        """
        log.debug('LibreOffice SlideShowListener event: repeat')
