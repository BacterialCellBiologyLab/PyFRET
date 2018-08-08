import numpy as np
import tkFileDialog
from scipy import ndimage
from skimage.color import rgb2gray
from skimage.exposure import rescale_intensity
from skimage.filters import threshold_adaptive, threshold_isodata
from skimage.morphology import closing, erosion
from skimage.io import imread
from skimage.util import img_as_float


class ImageManager(object):

    def __init__(self):

        self.phase_image = None
        self.clip = None
        self.mask = None
        self.align_values = None
        self.donor_image = None
        self.acceptor_image = None
        self.fret_image = None

    def load_phase_image(self, path=None, border=10):

        if path is None:
            image_path = tkFileDialog.askopenfilename(title="Load Phase Image")
        else:
            image_path = path

        img = imread(image_path)
        img = rgb2gray(img)
        img = img_as_float(img)
        img = rescale_intensity(img)

        self.clip = (border, border, img.shape[0]-border, img.shape[1]-border)

        x0, y0, x1, y1 = self.clip

        self.phase_image = img[x0:x1, y0:y1]

    def compute_mask(self, params):

        base_mask = np.copy(self.phase_image)

        if params.mask_algorithm == "Isodata":
            isodata_threshold = threshold_isodata(base_mask)
            base_mask = img_as_float(base_mask <= isodata_threshold)

        elif params.mask_algorithm == "Local Average":
            # need to invert because threshold_adaptive sets dark parts to 0
            block_size = params.mask_blocksize

            if block_size % 2 == 0:
                block_size += 1

            base_mask = 1.0 - threshold_adaptive(base_mask,
                                                 block_size,
                                                 offset=params.mask_offset)

        else:
            print "Not a valid mask algorithm"

        base_mask = 1 - base_mask

        mask = np.copy(base_mask)
        closing_matrix = np.ones((int(params.mask_closing),
                                  int(params.mask_closing)))

        if params.mask_closing > 0:
            # removes small dark spots and then small white spots
            mask = img_as_float(closing(mask, closing_matrix))
            mask = 1 - \
                img_as_float(closing(1 - mask, closing_matrix))

        for f in range(params.mask_dilation):
            mask = erosion(mask, np.ones((3, 3)))

        if params.mask_fill_holes:
            # mask is inverted
            mask = 1 - img_as_float(ndimage.binary_fill_holes(1.0 - mask))

        self.mask = mask

    def align_image(self, img, params):

        inverted_mask = 1 - self.mask

        best = (0, 0)
        x0, y0, x1, y1 = self.clip

        if params.auto_align:
            minscore = 0
            width = params.border
            for dx in range(-width, width):
                for dy in range(-width, width):
                    tot = -np.sum(np.multiply(inverted_mask,
                                              img[x0 + dx:x1 + dx,
                                                  y0 + dy:y1 + dy]))

                    if tot < minscore:
                        minscore = tot
                        best = (dx, dy)

        else:
            best = (params.x_align, params.y_align)

        return best

    def load_fluor_image(self, channel, params, path=None):

        x0, y0, x1, y1 = self.clip

        if path is None:
            image_path = tkFileDialog.askopenfilename(title="Load " + channel + " Image")
        else:
            image_path = path

        img = imread(image_path)
        img = rgb2gray(img)

        dx, dy = self.align_image(img, params)

        if channel == "Donor":
            self.donor_image = img[x0 + dx:x1 + dx, y0 + dy:y1 + dy]

        elif channel == "Acceptor":
            self.acceptor_image = img[x0 + dx:x1 + dx, y0 + dy:y1 + dy]

        elif channel == "FRET":
            self.fret_image = img[x0 + dx:x1 + dx, y0 + dy:y1 + dy]

        else:
            print "Not a valid channel name"
