import tkFileDialog
from imagemanager import ImageManager
from segmentsmanager import SegmentsManager
from cellsmanager import CellsManager
from fretmanager import FRETManager
from parameters import ParametersManager
from reportsmanager import ReportsManager


class SetManager(object):

    def __init__(self):
        self.parameters = ParametersManager()
        self.image_manager = ImageManager()
        self.segments_manager = SegmentsManager()
        self.cells_manager = None
        self.fret_manager = FRETManager()
        self.reports_manager = ReportsManager(self.parameters)
        self.control_params = None
        self.working_dir = None

    def load_phase_image(self, filename=None):
        if filename is None:
            filename = tkFileDialog.askopenfilename(initialdir=self.working_dir)

        self.working_dir = "/".join(filename.split("/")[:len(filename.split("/"))-1])

        self.image_manager.load_phase_image(filename,
                                            self.parameters.imageloaderparams.border)

        print "Phase Image Loaded"

    def compute_mask(self):
        """Calls the compute_mask method from image_manager."""

        self.image_manager.compute_mask(self.parameters.imageloaderparams)

        print "Mask Computation Finished"

    def load_fluor_image(self, channel, filename=None):
        """Calls the load_fluor_image method from the ImageManager
        Can be called without a filename or by passing one as an arg
        (filename=...)"""
        if filename is None:
            filename = tkFileDialog.askopenfilename(initialdir=self.working_dir)

        self.image_manager.load_fluor_image(channel,
                                            self.parameters.imageloaderparams,
                                            filename)

        print "Fluor Image Loaded"

    def compute_segments(self):
        """Calls the compute_segments method from Segments.
        Requires the prior loading of both the phase and fluor images and
        the computation of the mask"""

        self.segments_manager = SegmentsManager()
        self.segments_manager.compute_segments(self.parameters.
                                               imageprocessingparams,
                                               self.image_manager)

        print "Segments Computation Finished"

    def compute_cells(self):
        """Creates an instance of the CellManager class and uses the
        compute_cells_method to create a list of cells based on the labels
        computed by the SegmentsManager instance."""
        self.cells_manager = CellsManager(self.parameters)
        self.cells_manager.compute_cells(self.parameters.cellprocessingparams,
                                         self.image_manager,
                                         self.segments_manager)

        print "Cells Computation Finished"

    def merge_cells(self, label_c1, label_c2):
        """Merges two cells using the merge_cells method from the cell_manager
        instance and the compute_merged_cells to create a new list of cells,
        containing a cell corresponding to the merge of the previous two."""
        self.cells_manager.merge_cells(label_c1, label_c2,
                                       self.parameters.cellprocessingparams,
                                       self.segments_manager,
                                       self.image_manager)
        self.cells_manager.overlay_cells(self.image_manager)

        print "Merge Finished"

    def split_cells(self, label_c1):
        """Splits a previously merged cell, requires the label of cell to be
        splitted.
        Calls the split_cells method from the cell_manager instance"""
        self.cells_manager.split_cells(int(label_c1),
                                       self.parameters.cellprocessingparams,
                                       self.segments_manager,
                                       self.image_manager)
        self.cells_manager.overlay_cells(self.image_manager)

        print "Split Finished"

    def define_as_noise(self, label_c1, noise):
        """Method used to change the state of a cell to noise or to undo it"""
        self.cells_manager.mark_cell_as_noise(label_c1, self.image_manager,
                                              noise)

    def process_cells(self):
        self.cells_manager.process_cells(self.parameters.cellprocessingparams, self.image_manager)

        print "Cells Processing Finished"

    def pick_channel(self):
        self.fret_manager.start_channel_picker(self.image_manager, self.cells_manager)

    def compute_autofluorescence(self):
        self.fret_manager.compute_autofluorescence(self.image_manager, self.cells_manager)

    def compute_correction_factors(self):
        self.fret_manager.compute_correction_factors(self.image_manager, self.cells_manager)

    def compute_g(self):
        self.fret_manager.compute_g(self.image_manager, self.cells_manager)

    def compute_fret_efficiency(self):
        self.fret_manager.compute_fret_efficiency(self.image_manager, self.cells_manager)

    def generate_report(self):
        self.reports_manager.generate_report(self.image_manager, self.cells_manager, self.fret_manager)
