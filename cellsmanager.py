import cellprocessing as cp
import numpy as np
import matplotlib as plt
from collections import OrderedDict
from copy import deepcopy
from skimage.color import gray2rgb, rgb2gray
from skimage.draw import line
from skimage.exposure import rescale_intensity
from skimage.measure import label
from skimage.morphology import binary_dilation, binary_erosion
from skimage.filters import threshold_isodata
from skimage.util import img_as_float, img_as_int, img_as_uint
from skimage.segmentation import mark_boundaries


class Cell(object):
    """Template for each cell object."""

    def __init__(self, cell_id):
        self.label = cell_id
        self.merged_with = "No"
        self.merged_list = []
        self.marked_as_noise = "No"
        self.box = None
        self.box_margin = 20
        self.lines = []
        self.outline = []
        self.neighbours = {}
        self.color_i = -1
        self.long_axis = []
        self.short_axis = []

        self.cell_mask = None
        self.perim_mask = None
        self.sept_mask = None
        self.cyto_mask = None
        self.membsept_mask = None

        self.septum_from = None
        self.channel = None
        self.has_septum = None

        self.fluor = None
        self.image = None
        self.donacc_image = None

        self.stats = OrderedDict([("Area", 0),
                                  ("Perimeter", 0),
                                  ("Length", 0),
                                  ("Width", 0),
                                  ("Eccentricity", 0),
                                  ("Irregularity", 0),
                                  ("Neighbours", 0),
                                  ("Baseline Donor", 0),
                                  ("Baseline Acceptor", 0),
                                  ("Baseline FRET", 0),
                                  ("G", 0),
                                  ("Cell E", 0),
                                  ("Septum E", 0),
                                  ("Membrane E", 0),
                                  ("Cytoplasm E", 0),
                                  ("MembSept E", 0),
                                  ("Has Septum", False)])

        self.selection_state = 1

    def clean_cell(self):
        """Resets the cell to an empty instance.
        Can be used to mark the cell to discard"""
        self.label = cell_id
        self.merged_with = "No"
        self.merged_list = []
        self.marked_as_noise = "No"
        self.box = None
        self.box_margin = 20
        self.lines = []
        self.outline = []
        self.neighbours = {}
        self.color_i = -1
        self.long_axis = []
        self.short_axis = []

        self.cell_mask = None
        self.perim_mask = None
        self.sept_mask = None
        self.cyto_mask = None
        self.membsept_mask = None

        self.septum_from = None
        self.channel = None
        self.has_septum = None

        self.fluor = None
        self.image = None
        self.donacc_image = None

        self.stats = OrderedDict([("Area", 0),
                                  ("Perimeter", 0),
                                  ("Length", 0),
                                  ("Width", 0),
                                  ("Eccentricity", 0),
                                  ("Irregularity", 0),
                                  ("Neighbours", 0),
                                  ("Baseline Donor", 0),
                                  ("Baseline Acceptor", 0),
                                  ("Baseline FRET", 0),
                                  ("G", 0),
                                  ("Cell E", 0),
                                  ("Membrane E", 0),
                                  ("Cytoplasm E", 0),
                                  ("Septum E", 0),
                                  ("MembSept E", 0),
                                  ("Has Septum", False)])

        self.selection_state = 1

    def add_line(self, y, x1, x2):
        """
        Adds a line to the cell region and updates area
        """

        self.lines.append((y, x1, x2))
        self.stats["Area"] = self.stats["Area"] + x2 - x1 + 1

    def add_frontier_point(self, x, y, neighs):
        """
        Adds an external point. Neighs is the neighbourhood labels
        """
        # check if any neighbour not in labels
        # nlabels=np.unique(neighs[neighs <> self.label])

        nlabels = []
        notzero = []
        for line in neighs:
            for p in line:
                if p != self.label and not p in nlabels:
                    nlabels.append(p)
                    if p > 0:
                        notzero.append(p)

        if nlabels != []:
            self.outline.append((x, y))

        if notzero != []:
            for l in notzero:
                if l in self.neighbours.keys():
                    count = self.neighbours[l]
                else:
                    count = 0
                self.neighbours[l] = count + 1

    def compute_box(self, maskshape):
        """ computes the box
        """

        points = np.asarray(self.outline)  # in two columns, x, y
        bm = self.box_margin
        w, h = maskshape
        self.box = (max(min(points[:, 0]) - bm, 0),
                    max(min(points[:, 1]) - bm, 0),
                    min(max(points[:, 0]) + bm, w - 1),
                    min(max(points[:, 1]) + bm, h - 1))

    def axes_from_rotation(self, x0, y0, x1, y1, rotation):
        """ sets the cell axes from the box and the rotation
        """

        # midpoints
        mx = (x1 + x0) / 2
        my = (y1 + y0) / 2

        # assumes long is X. This duplicates rotations but simplifies
        # using different algorithms such as brightness
        self.long_axis = [[x0, my], [x1, my]]
        self.short_axis = [[mx, y0], [mx, y1]]
        self.short_axis = \
            np.asarray(np.dot(self.short_axis, rotation.T), dtype=np.int32)
        self.long_axis = \
            np.asarray(np.dot(self.long_axis, rotation.T), dtype=np.int32)

        # check if axis fall outside area due to rounding errors
        bx0, by0, bx1, by1 = self.box
        self.short_axis[0] = \
            cp.bounded_point(bx0, bx1, by0, by1, self.short_axis[0])
        self.short_axis[1] = \
            cp.bounded_point(bx0, bx1, by0, by1, self.short_axis[1])
        self.long_axis[0] = \
            cp.bounded_point(bx0, bx1, by0, by1, self.long_axis[0])
        self.long_axis[1] = \
            cp.bounded_point(bx0, bx1, by0, by1, self.long_axis[1])

        self.stats["Length"] = \
            np.linalg.norm(self.long_axis[1] - self.long_axis[0])
        self.stats["Width"] = \
            np.linalg.norm(self.short_axis[1] - self.short_axis[0])

    def compute_axes(self, rotations, maskshape):
        """ scans rotation matrices for the narrowest rectangle
        stores the result in self.long_axis and self.short_axis, each a 2,2
        array with one point per line (coords axes in columns)

        also computes the box for masks and images
        WARNING: Rotations cannot be empty and must include a null rotation
        """

        self.compute_box(maskshape)
        points = np.asarray(self.outline)  # in two columns, x, y
        width = len(points) + 1

        # no need to do more rotations, due to symmetry
        for rix in range(len(rotations) / 2 + 1):
            r = rotations[rix]
            nx0, ny0, nx1, ny1, nwidth = cp.bound_rectangle(
                np.asarray(np.dot(points, r)))

            if nwidth < width:
                width = nwidth
                x0 = nx0
                x1 = nx1
                y0 = ny0
                y1 = ny1
                angle = rix

        self.axes_from_rotation(x0, y0, x1, y1, rotations[angle])

        if self.stats["Length"] < self.stats["Width"]:
            dum = self.stats["Length"]
            self.stats["Length"] = self.stats["Width"]
            self.stats["Width"] = dum
            dum = self.short_axis
            self.short_axis = self.long_axis
            self.long_axis = dum

        self.stats["Eccentricity"] = \
            ((self.stats["Length"] - self.stats["Width"]) / (self.stats["Length"] +
                                                             self.stats["Width"]))
        self.stats["Irregularity"] = \
            (len(self.outline) / (self.stats["Area"] ** 0.5))

    def fluor_box(self, image_manager):
        """ returns box of flurescence from fluor image """

        x0, y0, x1, y1 = self.box

        return [image_manager.donor_image[x0:x1 + 1, y0:y1 + 1],
                image_manager.acceptor_image[x0:x1 + 1, y0:y1 + 1]]

    def compute_cell_mask(self):
        x0, y0, x1, y1 = self.box
        mask = np.zeros((x1 - x0 + 1, y1 - y0 + 1))
        for lin in self.lines:
            y, st, en = lin
            mask[st - x0:en - x0 + 1, y - y0] = 1.0
        return mask

    def compute_perim_mask(self, mask, thick):
        """returns mask for perimeter
        needs cell mask
        """
        # create mask

        eroded = binary_erosion(mask, np.ones(
            (thick * 2 - 1, thick - 1))).astype(float)
        perim = mask - eroded

        return perim

    def compute_sept_mask(self, mask, thick, algorithm):
        """ returns mask for axis.
        needs cell mask
        """

        if algorithm == "Isodata":
            return self.compute_sept_isodata(mask, thick)

        elif algorithm == "Box":
            return self.compute_sept_box(mask, thick)

        else:
            print "Not a a valid algorithm"

    def compute_sept_isodata(self, mask, thick):
        """Method used to create the cell sept_mask using the threshold_isodata
        to separate the cytoplasm from the septum"""
        cell_mask = mask

        septum_masks = []

        for img in self.fluor:
            fluor_box = img
            perim_mask = self.compute_perim_mask(cell_mask, thick)
            inner_mask = cell_mask - perim_mask
            inner_fluor = (inner_mask > 0) * fluor_box

            threshold = threshold_isodata(inner_fluor[inner_fluor > 0])
            interest_matrix = inner_mask * (inner_fluor > threshold)

            label_matrix = label(interest_matrix, connectivity=2)
            interest_label = 0
            interest_label_sum = 0

            for l in range(np.max(label_matrix)):
                if np.sum(img_as_float(label_matrix == l + 1)) > interest_label_sum:
                    interest_label = l + 1
                    interest_label_sum = np.sum(
                        img_as_float(label_matrix == l + 1))

            septum_masks.append(img_as_float(label_matrix == interest_label))

        donor_values = septum_masks[0] * self.fluor[0]
        donor_values = np.sort(donor_values, axis=None)[::-1]
        donor_values = donor_values[np.nonzero(donor_values)]
        donor_values = donor_values[:int(len(donor_values) * 0.25)]
        donor_fluor = np.median(donor_values)

        acceptor_values = septum_masks[1] * self.fluor[1]
        acceptor_values = np.sort(acceptor_values, axis=None)[::-1]
        acceptor_values = acceptor_values[np.nonzero(acceptor_values)]
        acceptor_values = acceptor_values[:int(len(acceptor_values) * 0.25)]
        acceptor_fluor = np.median(acceptor_values)

        if donor_fluor > acceptor_fluor:
            self.septum_from = "Donor"
            return septum_masks[0]
        else:
            self.septum_from = "Acceptor"
            return septum_masks[1]

    def compute_sept_box(self, mask, thick):
        """Method used to create a mask of the septum based on creating a box
        around the cell and then defining the septum as being the dilated short
        axis of the box."""
        x0, y0, x1, y1 = self.box
        lx0, ly0 = self.short_axis[0]
        lx1, ly1 = self.short_axis[1]
        x, y = line(lx0 - x0, ly0 - y0, lx1 - x0, ly1 - y0)

        linmask = np.zeros((x1 - x0 + 1, y1 - y0 + 1))
        linmask[x, y] = 1
        linmask = binary_dilation(
            linmask, np.ones((thick, thick))).astype(float)

        if mask is not None:
            linmask = mask * linmask

        return linmask

    def get_outline_points(self, data):
        """Method used to obtain the outline pixels of the septum"""
        outline = []
        for x in range(0, len(data)):
            for y in range(0, len(data[x])):
                if data[x, y] == 1:
                    if x == 0 and y == 0:
                        neighs_sum = data[x, y] + data[x + 1, y] + \
                            data[x + 1, y + 1] + data[x, y + 1]
                    elif x == len(data) - 1 and y == len(data[x]) - 1:
                        neighs_sum = data[x, y] + data[x, y - 1] + \
                            data[x - 1, y - 1] + data[x - 1, y]
                    elif x == 0 and y == len(data[x]) - 1:
                        neighs_sum = data[x, y] + data[x, y - 1] + \
                            data[x + 1, y - 1] + data[x + 1, y]
                    elif x == len(data) - 1 and y == 0:
                        neighs_sum = data[x, y] + data[x - 1, y] + \
                            data[x - 1, y + 1] + data[x, y + 1]
                    elif x == 0:
                        neighs_sum = data[x, y] + data[x, y - 1] + data[x, y + 1] + \
                            data[x + 1, y - 1] + \
                            data[x + 1, y] + data[x + 1, y + 1]
                    elif x == len(data) - 1:
                        neighs_sum = data[x, y] + data[x, y - 1] + data[x, y + 1] + \
                            data[x - 1, y - 1] + \
                            data[x - 1, y] + data[x - 1, y + 1]
                    elif y == 0:
                        neighs_sum = data[x, y] + data[x - 1, y] + data[x + 1, y] + \
                            data[x - 1, y + 1] + \
                            data[x, y + 1] + data[x + 1, y + 1]
                    elif y == len(data[x]) - 1:
                        neighs_sum = data[x, y] + data[x - 1, y] + data[x + 1, y] + \
                            data[x - 1, y - 1] + \
                            data[x, y - 1] + data[x + 1, y - 1]
                    else:
                        neighs_sum = data[x, y] + data[x - 1, y] + data[x + 1, y] + data[x - 1, y - 1] + data[
                            x, y - 1] + data[x + 1, y - 1] + data[x - 1, y + 1] + data[x, y + 1] + data[x + 1, y + 1]
                    if neighs_sum != 9:
                        outline.append((x, y))
        return outline

    def compute_sept_box_fix(self, outline, maskshape):
        """Method used to create a box aroung the septum, so that the short
        axis of this box can be used to choose the pixels of the membrane
        mask that need to be removed"""
        points = np.asarray(outline)  # in two columns, x, y
        bm = self.box_margin
        w, h = maskshape
        box = (max(min(points[:, 0]) - bm, 0),
               max(min(points[:, 1]) - bm, 0),
               min(max(points[:, 0]) + bm, w - 1),
               min(max(points[:, 1]) + bm, h - 1))

        return box

    def remove_sept_from_membrane(self, maskshape):
        """Method used to remove the pixels of the septum that were still in
        the membrane"""

        # get outline points of septum mask
        septum_outline = []
        septum_mask = self.sept_mask
        septum_outline = self.get_outline_points(septum_mask)

        # compute box of the septum
        septum_box = self.compute_sept_box_fix(septum_outline, maskshape)

        # compute axis of the septum
        rotations = cp.rotation_matrices(5)
        points = np.asarray(septum_outline)  # in two columns, x, y
        width = len(points) + 1

        # no need to do more rotations, due to symmetry
        for rix in range(len(rotations) / 2 + 1):
            r = rotations[rix]
            nx0, ny0, nx1, ny1, nwidth = cp.bound_rectangle(
                np.asarray(np.dot(points, r)))

            if nwidth < width:
                width = nwidth
                x0 = nx0
                x1 = nx1
                y0 = ny0
                y1 = ny1
                angle = rix

        rotation = rotations[angle]

        # midpoints
        mx = (x1 + x0) / 2
        my = (y1 + y0) / 2

        # assumes long is X. This duplicates rotations but simplifies
        # using different algorithms such as brightness
        long = [[x0, my], [x1, my]]
        short = [[mx, y0], [mx, y1]]
        short = np.asarray(np.dot(short, rotation.T), dtype=np.int32)
        long = np.asarray(np.dot(long, rotation.T), dtype=np.int32)

        # check if axis fall outside area due to rounding errors
        bx0, by0, bx1, by1 = septum_box
        short[0] = cp.bounded_point(bx0, bx1, by0, by1, short[0])
        short[1] = cp.bounded_point(bx0, bx1, by0, by1, short[1])
        long[0] = cp.bounded_point(bx0, bx1, by0, by1, long[0])
        long[1] = cp.bounded_point(bx0, bx1, by0, by1, long[1])

        length = np.linalg.norm(long[1] - long[0])
        width = np.linalg.norm(short[1] - short[0])

        if length < width:
            dum = length
            length = width
            width = dum
            dum = short
            short = long
            long = dum

        # expand long axis to create a linmask
        bx0, by0 = long[0]
        bx1, by1 = long[1]

        h, w = self.sept_mask.shape
        linmask = np.zeros((h, w))

        h, w = self.sept_mask.shape[0] - 2, self.sept_mask.shape[1] - 2
        bin_factor = int(width)

        if bx1 - bx0 == 0:
            x, y = line(bx0, 0, bx0, w)
            linmask[x, y] = 1
            try:
                linmask = binary_dilation(
                    linmask, np.ones((bin_factor, bin_factor))).astype(float)
            except RuntimeError:
                bin_factor = 4
                linmask = binary_dilation(
                    linmask, np.ones((bin_factor, bin_factor))).astype(float)

        else:
            m = ((by1 - by0) / (bx1 - bx0))
            b = by0 - m * bx0

            if b < 0:
                l_y0 = 0
                l_x0 = int(-b / m)

                if h * m + b > w:
                    l_y1 = w
                    l_x1 = int((w - b) / m)

                else:
                    l_x1 = h
                    l_y1 = int(h * m + b)

            elif b > w:
                l_y0 = w
                l_x0 = int((w - b) / m)

                if h * m + b < 0:
                    l_y1 = 0
                    l_x1 = int(-b / m)

                else:
                    l_x1 = h
                    l_y1 = int((h - b) / m)

            else:
                l_x0 = 0
                l_y0 = int(b)

                if m > 0:
                    if h * m + b > w:
                        l_y1 = w
                        l_x1 = int((w - b) / m)
                    else:
                        l_x1 = h
                        l_y1 = int(h * m + b)

                elif m < 0:
                    if h * m + b < 0:
                        l_y1 = 0
                        l_x1 = int(-b / m)
                    else:
                        l_x1 = h
                        l_y1 = int(h * m + b)

                else:
                    l_x1 = h
                    l_y1 = int(b)

            x, y = line(l_x0, l_y0, l_x1, l_y1)
            linmask[x, y] = 1
            try:
                linmask = binary_dilation(
                    linmask, np.ones((bin_factor, bin_factor))).astype(float)
            except RuntimeError:
                bin_factor = 4
                linmask = binary_dilation(
                    linmask, np.ones((bin_factor, bin_factor))).astype(float)
        return img_as_float(linmask)

    def recursive_compute_sept(self, cell_mask, inner_mask_thickness, algorithm):
        try:
            self.sept_mask = self.compute_sept_mask(cell_mask,
                                                    inner_mask_thickness,
                                                    algorithm)
        except IndexError:
            try:
                self.recursive_compute_sept(cell_mask, inner_mask_thickness - 1, algorithm)
            except RuntimeError:
                self.recursive_compute_sept(cell_mask, inner_mask_thickness - 1, "Box")

    def compute_regions(self, params, image_manager):
        """Computes each different region of the cell (whole cell, membrane,
        septum, cytoplasm) and creates their respectives masks."""

        self.fluor = self.fluor_box(image_manager)

        self.cell_mask = self.compute_cell_mask()

        if params.find_septum:
            self.recursive_compute_sept(self.cell_mask,
                                        params.inner_mask_thickness,
                                        params.septum_algorithm)

            if params.septum_algorithm == "Isodata":
                self.perim_mask = self.compute_perim_mask(self.cell_mask,
                                                          params.inner_mask_thickness)

                self.membsept_mask = (self.perim_mask + self.sept_mask) > 0
                linmask = self.remove_sept_from_membrane(
                    image_manager.mask.shape)

                self.cyto_mask = (self.cell_mask - self.perim_mask - self.sept_mask) > 0
                
                # different from ehooke, these values are not added to the cytoplasm
                if linmask is not None:
                    old_membrane = self.perim_mask
                    self.perim_mask = (old_membrane - linmask) > 0
                    

                else:
                    self.cyto_mask = (
                        self.cell_mask - self.perim_mask - self.sept_mask) > 0
            else:
                self.perim_mask = (self.compute_perim_mask(self.cell_mask,
                                                           params.inner_mask_thickness) -
                                   self.sept_mask) > 0
                self.membsept_mask = (self.perim_mask + self.sept_mask) > 0
                self.cyto_mask = (self.cell_mask - self.perim_mask -
                                  self.sept_mask) > 0
        else:
            self.sept_mask = None
            self.perim_mask = self.compute_perim_mask(self.cell_mask,
                                                      params.inner_mask_thickness)
            self.cyto_mask = (self.cell_mask - self.perim_mask) > 0

    def set_image(self, params, images):
        """ creates a strip with the cell in different images
            images is a list of rgb images
            background is a grayscale image to use for the masks
        """

        x0, y0, x1, y1 = self.box
        img = gray2rgb(
            np.zeros((x1 - x0 + 1, (len(images) + 4) * (y1 - y0 + 1))))
        bx0 = 0
        bx1 = x1 - x0 + 1
        by0 = 0
        by1 = y1 - y0 + 1

        for im in images:
            img[bx0:bx1, by0:by1] = im[x0:x1 + 1, y0:y1 + 1]
            by0 = by0 + y1 - y0 + 1
            by1 = by1 + y1 - y0 + 1

        self.image = img_as_int(img)

    def recompute_outline(self, labels):
        ids = self.merged_list
        ids.append(self.label)
        new_outline = []

        for px in self.outline:
            y, x = px
            neigh_pixels = labels[y-1:y+2, x-1:x+2].flatten()

            outline_check = False

            for val in neigh_pixels:
                if val in ids:
                    pass
                else:
                    outline_check = True
            if outline_check:
                new_outline.append(px)

        self.outline = new_outline

    def compute_fluor_baseline(self, mask, fluor, margin, channel):
        """mask and fluor are the global images
           NOTE: mask is 0 (black) at cells and 1 (white) outside
        """

        x0, y0, x1, y1 = self.box
        wid, hei = mask.shape
        x0 = max(x0 - margin, 0)
        y0 = max(y0 - margin, 0)
        x1 = min(x1 + margin, wid - 1)
        y1 = min(y1 + margin, hei - 1)
        mask_box = mask[x0:x1, y0:y1]

        count = 0

        inverted_mask_box = 1 - mask_box

        while count < 5:
            inverted_mask_box = binary_dilation(inverted_mask_box)
            count += 1

        mask_box = 1 - inverted_mask_box

        fluor_box = fluor[x0:x1, y0:y1]
        self.stats["Baseline " + channel] = np.median(
            mask_box[mask_box > 0] * fluor_box[mask_box > 0])
    
    def create_image(self, image_manager):

        x0, y0, x1, y1 = self.box

        phase_img = image_manager.phase_image[x0:x1+1, y0:y1+1]
        phase_img = gray2rgb(img_as_float(phase_img))
        donor_img = rescale_intensity(image_manager.donor_image[x0:x1+1, y0:y1+1])
        donor_img = gray2rgb(img_as_float(donor_img))
        acceptor_img = rescale_intensity(image_manager.acceptor_image[x0:x1+1, y0:y1+1])
        acceptor_img = gray2rgb(img_as_float(acceptor_img))

        cell_masks = np.concatenate((self.cell_mask, self.cell_mask, self.cell_mask), axis=1)
        septum_masks = np.concatenate((self.sept_mask, self.sept_mask, self.sept_mask), axis=1)

        no_mask = np.concatenate((phase_img, donor_img, acceptor_img), axis=1)
        with_masks = mark_boundaries(no_mask, img_as_uint(cell_masks), color=(0, 0, 1), outline_color=None)
        with_masks = mark_boundaries(with_masks, img_as_uint(septum_masks), color=(1, 0, 0), outline_color=None)
        img = np.concatenate((no_mask, with_masks), axis=0)

        self.donacc_image = img


class CellsManager(object):
    """Main class of the module. Should be used to interact with the rest of
    the modules."""

    def __init__(self, params):
        self.cells = {}
        self.original_cells = {}
        self.merged_cells = []
        self.merged_labels = None

        spmap = plt.cm.get_cmap("hsv", params.cellprocessingparams.cell_colors)
        self.cell_colors = spmap(np.arange(
            params.cellprocessingparams.cell_colors))

        self.phase_w_cells = None
        self.donor_w_cells = None
        self.acceptor_w_cells = None
        self.fret_w_cells = None

    def clean_empty_cells(self):
        """Removes empty cell objects from the cells dict"""
        newcells = {}
        for k in self.cells.keys():
            if self.cells[k].stats["Area"] > 0:
                newcells[k] = self.cells[k]

        self.cells = newcells

    def cell_regions_from_labels(self, labels):
        """creates a list of N cells assuming self.labels has consecutive
        values from 1 to N create cell regions, frontiers and neighbours from
        labeled regions presumes that cell list is created and has enough
        elements for all different labels. Each cell is at index label-1
        """

        difLabels = []
        for line in labels:
            difLabels.extend(set(line))
        difLabels = sorted(set(difLabels))[1:]

        cells = {}

        for f in difLabels:
            cells[str(int(f))] = Cell(f)

        for y in range(1, len(labels[0, :]) - 1):
            old_label = 0
            x1 = -1
            x2 = -1

            for x in range(1, len(labels[:, 0]) - 1):
                l = int(labels[x, y])

                # check if line began or ended, add line
                if l != old_label:
                    if x1 > 0:
                        x2 = x - 1
                        cells[str(old_label)].add_line(y, x1, x2)
                        x1 = -1
                    if l > 0:
                        x1 = x
                    old_label = l

                # check neighbours
                if l > 0:
                    square = labels[x - 1:x + 2, y - 1:y + 2]
                    cells[str(l)].add_frontier_point(x, y, square)

        for key in cells.keys():
            cells[key].stats["Perimeter"] = len(cells[key].outline)
            cells[key].stats["Neighbours"] = len(cells[key].neighbours)

        self.cells = cells

    def overlay_cells_w_image(self, image):
        """Creates an overlay of the cells over the base image.
        Besides the base image this method also requires the clipping
        coordinates for the image"""

        img = rgb2gray(img_as_float(image))
        img = rescale_intensity(img)

        return cp.overlay_cells(self.cells, img, self.cell_colors)

    def overlay_cells(self, image_manager):
        """Calls the methods used to create an overlay of the cells
        over the base and fluor images"""
        labels = np.zeros(image_manager.donor_image.shape)

        for k in self.cells.keys():
            c = self.cells[k]
            labels = cp.paint_cell(c, labels, c.label)

        self.merged_labels = labels
        self.phase_w_cells = self.overlay_cells_w_image(image_manager.phase_image)
        self.donor_w_cells = self.overlay_cells_w_image(image_manager.donor_image)
        self.acceptor_w_cells = self.overlay_cells_w_image(image_manager.acceptor_image)
        self.fret_w_cells = self.overlay_cells_w_image(image_manager.fret_image)

    def compute_box_axes(self, rotations, maskshape):
        for k in self.cells.keys():
            if self.cells[k].stats["Area"] > 0:
                self.cells[k].compute_axes(rotations, maskshape)

    def compute_cells(self, params, image_manager, segments_manager):
        """Creates a cell list that is stored on self.cells as a dict, where
        each cell id is a key of the dict.
        Also creates an overlay of the cells edges over both the base and
        fluor image.
        Requires the loading of the images and the computation of the
        segments"""

        self.cell_regions_from_labels(segments_manager.labels)
        rotations = cp.rotation_matrices(params.axial_step)

        self.compute_box_axes(rotations, image_manager.mask.shape)

        self.original_cells = deepcopy(self.cells)

        for k in self.cells.keys():
            try:
                c = self.cells[k]
                if len(c.neighbours) > 0:

                    bestneigh = max(c.neighbours.iterkeys(),
                                    key=(lambda key: c.neighbours[key]))
                    bestinterface = c.neighbours[bestneigh]
                    cn = self.cells[str(int(bestneigh))]

                    if cp.check_merge(c, cn, rotations, bestinterface,
                                      image_manager.mask, params):
                        self.merge_cells(c.label, cn.label, params, segments_manager, image_manager)
            except KeyError:
                pass

        for k in self.cells.keys():
            cp.assign_cell_color(self.cells[k], self.cells,
                                 self.cell_colors)

        self.overlay_cells(image_manager)

    def merge_cells(self, label_c1, label_c2, params, segments_manager, image_manager):
        """merges two cells"""
        label_c1 = int(label_c1)
        label_c2 = int(label_c2)
        self.cells[str(label_c2)].stats["Area"] = self.cells[str(label_c2)].stats[
            "Area"] + self.cells[str(label_c1)].stats["Area"]

        self.cells[str(label_c2)].lines.extend(self.cells[str(label_c1)].lines)

        self.cells[str(label_c2)].merged_list.append(label_c1)

        self.cells[str(label_c2)].outline.extend(self.cells[str(label_c1)].outline)

        self.cells[str(label_c2)].stats["Neighbours"] = self.cells[str(label_c2)].stats["Neighbours"] + self.cells[str(label_c1)].stats["Neighbours"] - 2

        del self.cells[str(label_c1)]

        rotations = cp.rotation_matrices(params.axial_step)
        self.cells[str(label_c2)].compute_axes(rotations, image_manager.mask.shape)

        self.cells[str(label_c2)].recompute_outline(segments_manager.labels)

        if len(self.cells[str(label_c2)].merged_list) > 0:
            self.cells[str(label_c2)].merged_with = "Yes"

    def split_cells(self, label_c1, params, segments_manager, image_manager):
        """Splits a previously merged cell."""
        merged_cells = self.cells[str(label_c1)].merged_list
        merged_cells.append(label_c1)
        del self.cells[str(label_c1)]

        rotations = cp.rotation_matrices(params.axial_step)
        for id in merged_cells:
            id = int(id)
            self.cells[str(id)] = deepcopy(self.original_cells[str(id)])
            self.cells[str(id)].compute_axes(rotations, image_manager.mask.shape)
            self.cells[str(id)].recompute_outline(segments_manager.labels)
            if len(self.cells[str(id)].merged_list) == 0:
                self.cells[str(id)].merged_with = "No"

        for k in self.cells.keys():
            cp.assign_cell_color(self.cells[k], self.cells,
                                 self.cell_colors)

    def mark_cell_as_noise(self, label_c1, image_manager, is_noise):
        """Used to change the selection_state of a cell to 0 (noise)
        or to revert that change if the optional param "is_noise" is marked as
        false."""
        if is_noise:
            self.cells[str(label_c1)].selection_state = 0
            self.cells[str(label_c1)].marked_as_noise = "Yes"
        else:
            self.cells[str(label_c1)].selection_state = 1
            self.cells[str(label_c1)].marked_as_noise = "No"

        self.overlay_cells(image_manager)

    def process_cells(self, params, image_manager):
        """Method used to compute the individual regions of each cell and the
        computation of the stats related to the fluorescence"""
        for k in self.cells.keys():
            """try:"""
            self.cells[k].compute_regions(params, image_manager)
            """except TypeError:
                del self.cells[k]"""

        if params.remove_background:
            for k in self.cells.keys():
                self.cells[k].set_image(params, [self.donor_w_cells, self.acceptor_w_cells, self.fret_w_cells])
                self.cells[k].compute_fluor_baseline(image_manager.mask,
                                                     image_manager.donor_image,
                                                     params.baseline_margin,
                                                     "Donor")
                self.cells[k].compute_fluor_baseline(image_manager.mask,
                                                     image_manager.acceptor_image,
                                                     params.baseline_margin,
                                                     "Acceptor")
                self.cells[k].compute_fluor_baseline(image_manager.mask,
                                                     image_manager.fret_image,
                                                     params.baseline_margin,
                                                     "FRET")
                self.cells[k].create_image(image_manager)
        else:
            for k in self.cells.keys():
                self.cells[k].set_image(params, [self.donor_w_cells, self.acceptor_w_cells, self.fret_w_cells])
                self.cells[k].create_image(image_manager)

        self.overlay_cells(image_manager)

    def filter_cells(self, params, image_manager):
        """Gets the list of filters on the parameters [("Stat", min, max)].
        Compares each cell to the filter and only select the ones that pass the filter"""
        for k in self.cells.keys():
            if self.cells[k].selection_state != 0:
                if cp.blocked_by_filter(self.cells[k], params.cell_filters):
                    self.cells[k].selection_state = -1
                else:
                    self.cells[k].selection_state = 1

        self.overlay_cells(image_manager)
