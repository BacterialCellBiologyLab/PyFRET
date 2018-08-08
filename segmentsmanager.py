import numpy as np
from scipy import ndimage
from skimage.feature import peak_local_max
from skimage.morphology import watershed


class SegmentsManager(object):

    def __init__(self):
        self.features = None
        self.labels = None
        self.phase_w_features = None

    @staticmethod
    def compute_distance_peaks(mask, params):
        """Method used when the selected algorithm for the feature computation
        is the Distance Peaks.
        Returns a list of the centers of the different identified regions,
        which should be used in the compute_features method"""

        distance = ndimage.morphology.distance_transform_edt(1 - mask)

        mindist = params.peak_min_distance
        minmargin = params.peak_min_distance_from_edge

        centers = peak_local_max(distance, min_distance=mindist,
                                 threshold_abs=params.peak_min_height,
                                 exclude_border=True,
                                 num_peaks=params.max_peaks,
                                 indices=True)

        placedmask = np.ones(distance.shape)
        lx, ly = distance.shape
        result = []
        rad = 5
        heights = []
        circles = []

        for c in centers:
            x, y = c

            if x >= minmargin and y >= minmargin and x <= lx - minmargin \
               and y <= ly - minmargin and placedmask[x, y]:
                placedmask[x - mindist:x + mindist +
                           1, y - mindist:y + mindist + 1] = 0
                s = distance[x, y]
                circles.append((x, y, rad, s))
                heights.append(s)

        ixs = np.argsort(heights)
        for ix in ixs:
            result.append(circles[ix])

        return result

    def compute_features(self, params, image_manager):
        """Method used to compute the features of an image using the mask.
        requires a mask and an instance of the imageprocessingparams
        if the selected algorithm used is Distance Peak, used the method
        compute_distance_peaks to compute the features"""

        mask = image_manager.mask
        features = np.zeros(mask.shape)

        if params.peak_min_distance_from_edge < 1:
            params.peak_min_distance_from_edge = 1

        circles = self.compute_distance_peaks(mask, params)

        for ix, c in enumerate(circles):
            x, y, dum1, dum2 = c
            for f in range(3):
                features[x - 1 + f, y] = ix + 1
                features[x, y - 1 + f] = ix + 1

        self.features = features

    def overlay_phase_w_features(self, image_manager):
        """Method used to produce an image with an overlay of the features on
        the phase image requires a phase image, the features and the clip
        values to overlay the images returns a image matrix which can be saved
        using the save_image method from EHooke or directly using the imsave
        from skimage.io"""

        x1, y1, x2, y2 = image_manager.clip
        clipped_phase = np.copy(image_manager.phase_image)

        places = self.features > 0.5
        clipped_phase[places] = 1
        self.phase_w_features = clipped_phase

    def compute_labels(self, params, image_manager):
        """Computes the labels for each region phased on the previous computed
        features. Requires the mask, th phase mask, the features and an
        instance of the imageprocessingparams"""

        markers = self.features
        inverted_mask = 1 - image_manager.mask
        distance = -ndimage.morphology.distance_transform_edt(inverted_mask)

        mindist = np.min(distance)
        markpoints = markers > 0
        distance[markpoints] = mindist
        labels = watershed(distance, markers, mask=inverted_mask)

        self.labels = labels

    def compute_segments(self, params, image_manager):
        """Calls the different methods of the module in the right order.
        Can be used as the interface of this module in the main module of the
        software"""
        self.compute_features(params, image_manager)
        self.overlay_phase_w_features(image_manager)
        self.compute_labels(params, image_manager)
