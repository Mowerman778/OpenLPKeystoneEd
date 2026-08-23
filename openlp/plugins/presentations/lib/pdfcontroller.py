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

from openlp.core.display.screens import ScreenList
from openlp.plugins.presentations.lib.presentationcontroller import PresentationController, PresentationDocument


try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz_old as fitz
        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False

log = logging.getLogger(__name__)

PDF_CONTROLLER_FILETYPES = ['pdf', 'xps', 'oxps', 'epub', 'cbz', 'fb2']


class PdfController(PresentationController):
    """
    Class to control PDF presentations
    """
    log.info('PdfController loaded')

    def __init__(self, plugin):
        """
        Initialise the class

        :param plugin: The plugin that creates the controller.
        """
        log.debug('Initialising')
        super(PdfController, self).__init__(plugin, 'Pdf', PdfDocument)
        self.process = None
        self.supports = ['pdf']
        self.also_supports = ['xps', 'oxps', 'epub', 'cbz', 'fb2']

    def check_available(self):
        """
        PdfController is able to run on this machine.

        :return: True if PyMuPDF is installed, otherwise False.
        """
        log.debug('check_available Pdf')
        return PYMUPDF_AVAILABLE

    def kill(self):
        """
        Called at system exit to clean up any running presentations
        """
        log.debug('Kill pdfviewer')
        while self.docs:
            self.docs[0].close_presentation()


class PdfDocument(PresentationDocument):
    """
    Class which holds information of a single presentation.
    This class is not actually used to present the PDF, instead we convert to
    image-serviceitem on the fly and present as such. Therefore some of the 'playback'
    functions is not implemented.
    """
    def __init__(self, controller, document_path):
        """
        Constructor, store information about the file and initialise.

        :param pathlib.Path document_path: Path to the document to load
        :rtype: None
        """
        log.debug('Init Presentation Pdf')
        super().__init__(controller, document_path)
        self.presentation = None
        self.blanked = False
        self.hidden = False
        self.image_files = []
        self.num_pages = -1

    def load_presentation(self):
        """
        Called when a presentation is added to the SlideController. It generates images from the PDF.

        :return: True is loading succeeded, otherwise False.
        """
        log.debug('load_presentation pdf')
        temp_dir_path = self.get_temp_folder()
        # Check if the images has already been created, and if yes load them
        if (temp_dir_path / 'mainslide001.png').is_file():
            created_files = sorted(temp_dir_path.glob('*'))
            for image_path in created_files:
                if image_path.is_file():
                    self.image_files.append(image_path)
            self.num_pages = len(self.image_files)
            return True
        size = ScreenList().current.display_geometry
        # Generate images from PDF that will fit the frame.
        runlog = ''
        if not temp_dir_path.is_dir():
            temp_dir_path.mkdir(parents=True)
        try:
            log.debug('loading presentation using PyMuPDF')
            pdf = fitz.open(str(self.file_path))
            for i, page in enumerate(pdf, start=1):
                src_size = page.bound().round()
                # keep aspect ratio
                scale = min(size.width() / src_size.width, size.height() / src_size.height)
                matrix = fitz.Matrix(scale, scale)
                pngpath = str(temp_dir_path / 'mainslide{:03d}.png'.format(i))
                try:
                    page.get_pixmap(matrix=matrix, alpha=False).save(pngpath)
                except AttributeError:
                    # old function names
                    page.getPixmap(matrix=matrix, alpha=False).writeImage(pngpath)
            pdf.close()
            created_files = sorted(temp_dir_path.glob('*'))
            for image_path in created_files:
                if image_path.is_file():
                    self.image_files.append(image_path)
        except Exception:
            log.exception(runlog)
            return False
        self.num_pages = len(self.image_files)
        # Create thumbnails
        self.create_thumbnails()
        return True

    def create_thumbnails(self):
        """
        Generates thumbnails
        """
        log.debug('create_thumbnails pdf')
        if self.check_thumbnails():
            return
        # use builtin function to create thumbnails from generated images
        index = 1
        for image in self.image_files:
            self.convert_thumbnail(image, index)
            index += 1

    def close_presentation(self):
        """
        Close presentation and clean up objects. Triggered by new object being added to SlideController or OpenLP being
        shut down.
        """
        log.debug('close_presentation pdf')
        self.controller.remove_doc(self)

    def is_loaded(self):
        """
        Returns true if a presentation is loaded.

        :return: True if loaded, False if not.
        """
        log.debug('is_loaded pdf')
        if self.num_pages < 0:
            return False
        return True

    def is_active(self):
        """
        Returns true if a presentation is currently active.

        :return: True if active, False if not.
        """
        log.debug('is_active pdf')
        return self.is_loaded() and not self.hidden

    def get_slide_count(self):
        """
        Returns total number of slides

        :return: The number of pages in the presentation..
        """
        return self.num_pages
