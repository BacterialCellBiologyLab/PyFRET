import numpy as np
import Tkinter as tk
from matplotlib import cm
from skimage.util import img_as_float
from skimage.color import gray2rgb
from cellpicker import CellPicker


# READ: correction factors are calculated from membrane and septum (if it exists)
# these corrections factors are used for every calculation
# autofluorescence and G from cyto_mask
# E from every possible mask

class FRETManager(object):

    def __init__(self):
        self.control_cells = []
        self.wt_cells = []
        self.donor_cells = []
        self.acceptor_cells = []
        self.both_cells = []

        self.autofluorescence_donor = None
        self.autofluorescence_acceptor = None
        self.autofluorescence_fret = None

        self.fret_a = None
        self.fret_b = None
        self.fret_c = None
        self.fret_d = None

        self.fret_E = None
        self.fret_G = None

        self.cell_E = None
        self.membrane_E = None
        self.cyto_E = None
        self.septum_E = None
        self.membsept_E = None

        self.fret_heatmap = None

    def start_channel_picker(self, image_manager, cells_manager):
        picker = CellPicker()
        picker.start_picker(image_manager, cells_manager)

        for key in cells_manager.cells.keys():
            if cells_manager.cells[key].channel == "donor":
                self.donor_cells.append(key)
            elif cells_manager.cells[key].channel == "wt":
                self.wt_cells.append(key)
            elif cells_manager.cells[key].channel == "acceptor":
                self.acceptor_cells.append(key)
            elif cells_manager.cells[key].channel == "both":
                self.both_cells.append(key)
            elif cells_manager.cells[key].channel == "control":
                self.control_cells.append(key)

    def compute_autofluorescence(self, image_manager, cells_manager):

        print "Computing Autofluorescense"

        cell_average_donor = []
        cell_average_acceptor = []
        cell_average_fret = []

        for key in self.wt_cells:
            x0, y0, x1, y1 = cells_manager.cells[key].box
            cell_mask = cells_manager.cells[key].cyto_mask

            donor_values = (image_manager.donor_image[x0:x1+1, y0:y1+1] - cells_manager.cells[key].stats["Baseline Donor"]) * cell_mask
            donor_values = donor_values[np.nonzero(donor_values)]
            cell_average_donor.append(np.average(donor_values))

            acceptor_values = (image_manager.acceptor_image[x0:x1+1, y0:y1+1] - cells_manager.cells[key].stats["Baseline Acceptor"]) * cell_mask
            acceptor_values = acceptor_values[np.nonzero(acceptor_values)]
            cell_average_acceptor.append(np.average(acceptor_values))

            fret_values = (image_manager.fret_image[x0:x1+1, y0:y1+1] - cells_manager.cells[key].stats["Baseline FRET"]) * cell_mask
            fret_values = fret_values[np.nonzero(fret_values)]
            cell_average_fret.append(np.average(fret_values))

        self.autofluorescence_donor = np.median(cell_average_donor)
        self.autofluorescence_acceptor = np.median(cell_average_acceptor)
        self.autofluorescence_fret = np.median(cell_average_fret)

    def compute_ab(self, image_manager, cells_manager):
        cell_average_a = []
        cell_average_b = []

        for key in self.acceptor_cells:
            x0, y0, x1, y1 = cells_manager.cells[key].box
            cell_mask = cells_manager.cells[key].perim_mask

            donor_cell_image = image_manager.donor_image[x0:x1+1, y0:y1+1] * cell_mask
            donor_cell_image = donor_cell_image - self.autofluorescence_donor - cells_manager.cells[key].stats["Baseline Donor"]
            donor_cell_image = donor_cell_image * (donor_cell_image > 0)
            nonzero_donor = np.nonzero(donor_cell_image)

            acceptor_cell_image = image_manager.acceptor_image[x0:x1+1, y0:y1+1] * cell_mask
            acceptor_cell_image = acceptor_cell_image - self.autofluorescence_acceptor - cells_manager.cells[key].stats["Baseline Acceptor"]
            acceptor_cell_image = acceptor_cell_image * (acceptor_cell_image > 0)
            nonzero_acceptor = np.nonzero(acceptor_cell_image)

            fret_cell_image = image_manager.fret_image[x0:x1+1, y0:y1+1] * cell_mask
            fret_cell_image = fret_cell_image - self.autofluorescence_fret - cells_manager.cells[key].stats["Baseline FRET"]
            fret_cell_image = fret_cell_image * (fret_cell_image > 0)
            nonzero_fret = np.nonzero(fret_cell_image)

            a_ix = list(set(zip(list(nonzero_fret[0]), list(nonzero_fret[1]))).intersection(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))))

            a_values = []
            for ix in a_ix:
                a_values.append(fret_cell_image[ix]/acceptor_cell_image[ix])

            b_ix = list(set(zip(list(nonzero_donor[0]), list(nonzero_donor[1]))).intersection(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))))

            b_values = []
            for ix in b_ix:
                b_values.append(donor_cell_image[ix]/acceptor_cell_image[ix])

            if cells_manager.cells[key].has_septum:
                x0, y0, x1, y1 = cells_manager.cells[key].box
                cell_mask = cells_manager.cells[key].sept_mask

                donor_cell_image = image_manager.donor_image[x0:x1+1, y0:y1+1] * cell_mask
                donor_cell_image = donor_cell_image - self.autofluorescence_donor - cells_manager.cells[key].stats["Baseline Donor"]
                donor_cell_image = donor_cell_image * (donor_cell_image > 0)
                nonzero_donor = np.nonzero(donor_cell_image)

                acceptor_cell_image = image_manager.acceptor_image[x0:x1+1, y0:y1+1] * cell_mask
                acceptor_cell_image = acceptor_cell_image - self.autofluorescence_acceptor - cells_manager.cells[key].stats["Baseline Acceptor"]
                acceptor_cell_image = acceptor_cell_image * (acceptor_cell_image > 0)
                nonzero_acceptor = np.nonzero(acceptor_cell_image)

                fret_cell_image = image_manager.fret_image[x0:x1+1, y0:y1+1] * cell_mask
                fret_cell_image = fret_cell_image - self.autofluorescence_fret - cells_manager.cells[key].stats["Baseline FRET"]
                fret_cell_image = fret_cell_image * (fret_cell_image > 0)
                nonzero_fret = np.nonzero(fret_cell_image)

                a_ix = list(set(zip(list(nonzero_fret[0]), list(nonzero_fret[1]))).intersection(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))))

                for ix in a_ix:
                    a_values.append(fret_cell_image[ix]/acceptor_cell_image[ix])

                b_ix = list(set(zip(list(nonzero_donor[0]), list(nonzero_donor[1]))).intersection(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))))

                for ix in b_ix:
                    b_values.append(donor_cell_image[ix]/acceptor_cell_image[ix])

            if len(a_values) > 0:
                cell_average_a.append(np.average(a_values))
            if len(b_values) > 0:
                cell_average_b.append(np.average(b_values))

        self.fret_a = np.median(cell_average_a)
        self.fret_b = np.median(cell_average_b)

    def compute_cd(self, image_manager, cells_manager):
        cell_average_c = []
        cell_average_d = []

        for key in self.donor_cells:
            x0, y0, x1, y1 = cells_manager.cells[key].box
            cell_mask = cells_manager.cells[key].perim_mask

            donor_cell_image = image_manager.donor_image[x0:x1+1, y0:y1+1] * cell_mask
            donor_cell_image = donor_cell_image - self.autofluorescence_donor - cells_manager.cells[key].stats["Baseline Donor"]
            donor_cell_image = donor_cell_image * (donor_cell_image > 0)
            nonzero_donor = np.nonzero(donor_cell_image)

            acceptor_cell_image = image_manager.acceptor_image[x0:x1+1, y0:y1+1] * cell_mask
            acceptor_cell_image = acceptor_cell_image - self.autofluorescence_acceptor - cells_manager.cells[key].stats["Baseline Acceptor"]
            acceptor_cell_image = acceptor_cell_image * (acceptor_cell_image > 0)
            nonzero_acceptor = np.nonzero(acceptor_cell_image)

            fret_cell_image = image_manager.fret_image[x0:x1+1, y0:y1+1] * cell_mask
            fret_cell_image = fret_cell_image - self.autofluorescence_fret - cells_manager.cells[key].stats["Baseline FRET"]
            fret_cell_image = fret_cell_image * (fret_cell_image > 0)
            nonzero_fret = np.nonzero(fret_cell_image)

            c_ix = list(set(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))).intersection(zip(list(nonzero_donor[0]), list(nonzero_donor[1]))))

            c_values = []
            for ix in c_ix:
                c_values.append(acceptor_cell_image[ix]/donor_cell_image[ix])

            d_ix = list(set(zip(list(nonzero_fret[0]), list(nonzero_fret[1]))).intersection(zip(list(nonzero_donor[0]), list(nonzero_donor[1]))))

            d_values = []
            for ix in d_ix:
                d_values.append(fret_cell_image[ix]/donor_cell_image[ix])

            if cells_manager.cells[key].has_septum:
                x0, y0, x1, y1 = cells_manager.cells[key].box
                cell_mask = cells_manager.cells[key].sept_mask

                donor_cell_image = image_manager.donor_image[x0:x1+1, y0:y1+1] * cell_mask
                donor_cell_image = donor_cell_image - self.autofluorescence_donor - cells_manager.cells[key].stats["Baseline Donor"]
                donor_cell_image = donor_cell_image * (donor_cell_image > 0)
                nonzero_donor = np.nonzero(donor_cell_image)

                acceptor_cell_image = image_manager.acceptor_image[x0:x1+1, y0:y1+1] * cell_mask
                acceptor_cell_image = acceptor_cell_image - self.autofluorescence_acceptor - cells_manager.cells[key].stats["Baseline Acceptor"]
                acceptor_cell_image = acceptor_cell_image * (acceptor_cell_image > 0)
                nonzero_acceptor = np.nonzero(acceptor_cell_image)

                fret_cell_image = image_manager.fret_image[x0:x1+1, y0:y1+1] * cell_mask
                fret_cell_image = fret_cell_image - self.autofluorescence_fret - cells_manager.cells[key].stats["Baseline FRET"]
                fret_cell_image = fret_cell_image * (fret_cell_image > 0)
                nonzero_fret = np.nonzero(fret_cell_image)

                c_ix = list(set(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))).intersection(zip(list(nonzero_donor[0]), list(nonzero_donor[1]))))

                for ix in c_ix:
                    c_values.append(acceptor_cell_image[ix]/donor_cell_image[ix])

                d_ix = list(set(zip(list(nonzero_fret[0]), list(nonzero_fret[1]))).intersection(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))))

                for ix in d_ix:
                    d_values.append(fret_cell_image[ix]/donor_cell_image[ix])

            if len(c_values) > 0:
                cell_average_c.append(np.average(c_values))
            if len(d_values) > 0:
                cell_average_d.append(np.average(d_values))

        self.fret_c = np.median(cell_average_c)
        self.fret_d = np.median(cell_average_d)

    def compute_correction_factors(self, image_manager, cells_manager):
        """autofluorescence is removed px by px using the previous computed average.
        if the subtracted value is less than zero, the px is assumed to have no signal and is not computed"""

        print "Computing Corrections Factors a,b,c,d"

        self.compute_ab(image_manager, cells_manager)
        self.compute_cd(image_manager, cells_manager)

    def close_input_e(self, window_object, input_object):

        self.fret_E = float(input_object.get())
        window_object.quit()
        window_object.destroy()

    def get_E_value(self):
        print "Choose E value"
        window = tk.Tk()

        e_label = tk.Label(text="Enter E value:")
        e_label.pack(side="top")
        e_input = tk.Entry()
        e_input.pack(side="top")
        submit_button = tk.Button(text="Submit", command=lambda: self.close_input_e(window, e_input))
        submit_button.pack()

        window.mainloop()

    def compute_g(self, image_manager, cells_manager):
        if self.fret_E is None:
            self.get_E_value()

        cell_average_g = []

        print "Computing G"

        for key in self.control_cells:
            x0, y0, x1, y1 = cells_manager.cells[key].box
            cell_mask = cells_manager.cells[key].cyto_mask

            donor_cell_image = image_manager.donor_image[x0:x1+1, y0:y1+1] * cell_mask
            donor_cell_image = donor_cell_image - self.autofluorescence_donor - cells_manager.cells[key].stats["Baseline Donor"]
            donor_cell_image = donor_cell_image * (donor_cell_image > 0)
            nonzero_donor = np.nonzero(donor_cell_image)

            acceptor_cell_image = image_manager.acceptor_image[x0:x1+1, y0:y1+1] * cell_mask
            acceptor_cell_image = acceptor_cell_image - self.autofluorescence_acceptor - cells_manager.cells[key].stats["Baseline Acceptor"]
            acceptor_cell_image = acceptor_cell_image * (acceptor_cell_image > 0)
            nonzero_acceptor = np.nonzero(acceptor_cell_image)

            fret_cell_image = image_manager.fret_image[x0:x1+1, y0:y1+1] * cell_mask
            fret_cell_image = fret_cell_image - self.autofluorescence_fret - cells_manager.cells[key].stats["Baseline FRET"]
            fret_cell_image = fret_cell_image * (fret_cell_image > 0)
            nonzero_fret = np.nonzero(fret_cell_image)

            # TODO discuss if we shoudld use these pixels anyway
            nonzero_ix = list(set(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))).intersection(zip(list(nonzero_donor[0]), list(nonzero_donor[1]))).intersection(zip(list(nonzero_fret[0]), list(nonzero_fret[1]))))

            g_values = []
            for ix in nonzero_ix:
                Iaa = (self.fret_d * acceptor_cell_image[ix] - self.fret_c * fret_cell_image[ix]) / (self.fret_d - self.fret_c * self.fret_a)
                Idd = (self.fret_a * donor_cell_image[ix] - self.fret_b * fret_cell_image[ix]) / (self.fret_a - self.fret_b * self.fret_d)
                Fc = fret_cell_image[ix] - self.fret_a * Iaa - self.fret_d * Idd
                g_value = ((1-self.fret_E)*Fc)/(self.fret_E*Idd)
                g_values.append(g_value)

            if len(g_values) > 0:
                average = np.average(g_values)
                cell_average_g.append(average)
                cells_manager.cells[key].stats["G"] = average
            else:
                cells_manager.cells[key].stats["G"] = 0

        self.fret_G = np.median(cell_average_g)

    def compute_fret_efficiency(self, image_manager, cells_manager):

        heatmap = np.zeros(image_manager.phase_image.shape)

        print "computing FRET Efficiency"

        cell_average_E = []
        cyto_average_E = []
        membrane_average_E = []
        septum_average_E = []
        membsept_average_E = []

        for key in self.both_cells:
            ###################################################################
            # Whole Cell Calculations
            x0, y0, x1, y1 = cells_manager.cells[key].box
            cell_mask = cells_manager.cells[key].cell_mask

            donor_cell_image = image_manager.donor_image[x0:x1+1, y0:y1+1] * cell_mask
            donor_cell_image = donor_cell_image - self.autofluorescence_donor - cells_manager.cells[key].stats["Baseline Donor"]
            donor_cell_image = donor_cell_image * (donor_cell_image > 0)
            nonzero_donor = np.nonzero(donor_cell_image)

            acceptor_cell_image = image_manager.acceptor_image[x0:x1+1, y0:y1+1] * cell_mask
            acceptor_cell_image = acceptor_cell_image - self.autofluorescence_acceptor - cells_manager.cells[key].stats["Baseline Acceptor"]
            acceptor_cell_image = acceptor_cell_image * (acceptor_cell_image > 0)
            nonzero_acceptor = np.nonzero(acceptor_cell_image)

            fret_cell_image = image_manager.fret_image[x0:x1+1, y0:y1+1] * cell_mask
            fret_cell_image = fret_cell_image - self.autofluorescence_fret - cells_manager.cells[key].stats["Baseline FRET"]
            fret_cell_image = fret_cell_image * (fret_cell_image > 0)
            nonzero_fret = np.nonzero(fret_cell_image)

            # TODO discuss if we shoudld use this pixels anyway
            cell_nonzero_ix = list(set(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))).intersection(zip(list(nonzero_donor[0]), list(nonzero_donor[1]))).intersection(zip(list(nonzero_fret[0]), list(nonzero_fret[1]))))

            e_values = []
            for ix in cell_nonzero_ix:
                Iaa = (self.fret_d * acceptor_cell_image[ix] - self.fret_c * fret_cell_image[ix]) / (self.fret_d - self.fret_c * self.fret_a)
                Idd = (self.fret_a * donor_cell_image[ix] - self.fret_b * fret_cell_image[ix]) / (self.fret_a - self.fret_b * self.fret_d)
                Fc = fret_cell_image[ix] - self.fret_a * Iaa - self.fret_d * Idd

                e = (Fc/self.fret_G) / (Idd+(Fc/self.fret_G))
                e_values.append(e)
                x, y = ix
                heatmap[x0+x, y0+y] = e

            if len(e_values) > 0:
                average = np.average(e_values)
                cell_average_E.append(average)
                cells_manager.cells[key].stats["Cell E"] = average
            else:
                cells_manager.cells[key].stats["Cell E"] = 0

            ###################################################################
            # Membrane Calculations
            cell_mask = cells_manager.cells[key].perim_mask

            donor_cell_image = image_manager.donor_image[x0:x1+1, y0:y1+1] * cell_mask
            donor_cell_image = donor_cell_image - self.autofluorescence_donor - cells_manager.cells[key].stats["Baseline Donor"]
            donor_cell_image = donor_cell_image * (donor_cell_image > 0)
            nonzero_donor = np.nonzero(donor_cell_image)

            acceptor_cell_image = image_manager.acceptor_image[x0:x1+1, y0:y1+1] * cell_mask
            acceptor_cell_image = acceptor_cell_image - self.autofluorescence_acceptor - cells_manager.cells[key].stats["Baseline Acceptor"]
            acceptor_cell_image = acceptor_cell_image * (acceptor_cell_image > 0)
            nonzero_acceptor = np.nonzero(acceptor_cell_image)

            fret_cell_image = image_manager.fret_image[x0:x1+1, y0:y1+1] * cell_mask
            fret_cell_image = fret_cell_image - self.autofluorescence_fret - cells_manager.cells[key].stats["Baseline FRET"]
            fret_cell_image = fret_cell_image * (fret_cell_image > 0)
            nonzero_fret = np.nonzero(fret_cell_image)

            # TODO discuss if we shoudld use this pixels anyway
            membrane_nonzero_ix = list(set(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))).intersection(zip(list(nonzero_donor[0]), list(nonzero_donor[1]))).intersection(zip(list(nonzero_fret[0]), list(nonzero_fret[1]))))

            membrane_e_values = []
            for ix in membrane_nonzero_ix:
                Iaa = (self.fret_d * acceptor_cell_image[ix] - self.fret_c * fret_cell_image[ix]) / (self.fret_d - self.fret_c * self.fret_a)
                Idd = (self.fret_a * donor_cell_image[ix] - self.fret_b * fret_cell_image[ix]) / (self.fret_a - self.fret_b * self.fret_d)
                Fc = fret_cell_image[ix] - self.fret_a * Iaa - self.fret_d * Idd

                e = (Fc/self.fret_G) / (Idd+(Fc/self.fret_G))
                membrane_e_values.append(e)
                x, y = ix

            if len(membrane_e_values) > 0:
                average = np.average(membrane_e_values)
                membrane_average_E.append(average)
                cells_manager.cells[key].stats["Membrane E"] = average
            else:
                cells_manager.cells[key].stats["Membrane E"] = 0

            ###################################################################
            # Cytoplasm Calculations
            cell_mask = cells_manager.cells[key].cyto_mask

            donor_cell_image = image_manager.donor_image[x0:x1+1, y0:y1+1] * cell_mask
            donor_cell_image = donor_cell_image - self.autofluorescence_donor - cells_manager.cells[key].stats["Baseline Donor"]
            donor_cell_image = donor_cell_image * (donor_cell_image > 0)
            nonzero_donor = np.nonzero(donor_cell_image)

            acceptor_cell_image = image_manager.acceptor_image[x0:x1+1, y0:y1+1] * cell_mask
            acceptor_cell_image = acceptor_cell_image - self.autofluorescence_acceptor - cells_manager.cells[key].stats["Baseline Acceptor"]
            acceptor_cell_image = acceptor_cell_image * (acceptor_cell_image > 0)
            nonzero_acceptor = np.nonzero(acceptor_cell_image)

            fret_cell_image = image_manager.fret_image[x0:x1+1, y0:y1+1] * cell_mask
            fret_cell_image = fret_cell_image - self.autofluorescence_fret - cells_manager.cells[key].stats["Baseline FRET"]
            fret_cell_image = fret_cell_image * (fret_cell_image > 0)
            nonzero_fret = np.nonzero(fret_cell_image)

            # TODO discuss if we shoudld use this pixels anyway
            cyto_nonzero_ix = list(set(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))).intersection(zip(list(nonzero_donor[0]), list(nonzero_donor[1]))).intersection(zip(list(nonzero_fret[0]), list(nonzero_fret[1]))))

            cyto_e_values = []
            for ix in cyto_nonzero_ix:
                Iaa = (self.fret_d * acceptor_cell_image[ix] - self.fret_c * fret_cell_image[ix]) / (self.fret_d - self.fret_c * self.fret_a)
                Idd = (self.fret_a * donor_cell_image[ix] - self.fret_b * fret_cell_image[ix]) / (self.fret_a - self.fret_b * self.fret_d)
                Fc = fret_cell_image[ix] - self.fret_a * Iaa - self.fret_d * Idd

                e = (Fc/self.fret_G) / (Idd+(Fc/self.fret_G))
                cyto_e_values.append(e)
                x, y = ix

            if len(cyto_e_values) > 0:
                average = np.average(cyto_e_values)
                cyto_average_E.append(average)
                cells_manager.cells[key].stats["Cytoplasm E"] = average
            else:
                cells_manager.cells[key].stats["Cytoplasm E"] = 0

            ###################################################################
            # Septum Calculations
            if cells_manager.cells[key].has_septum:
                x0, y0, x1, y1 = cells_manager.cells[key].box
                sept_mask = cells_manager.cells[key].sept_mask

                donor_cell_image = image_manager.donor_image[x0:x1+1, y0:y1+1] * sept_mask
                donor_cell_image = donor_cell_image - self.autofluorescence_donor - cells_manager.cells[key].stats["Baseline Donor"]
                donor_cell_image = donor_cell_image * (donor_cell_image > 0)
                nonzero_donor = np.nonzero(donor_cell_image)

                acceptor_cell_image = image_manager.acceptor_image[x0:x1+1, y0:y1+1] * sept_mask
                acceptor_cell_image = acceptor_cell_image - self.autofluorescence_acceptor - cells_manager.cells[key].stats["Baseline Acceptor"]
                acceptor_cell_image = acceptor_cell_image * (acceptor_cell_image > 0)
                nonzero_acceptor = np.nonzero(acceptor_cell_image)

                fret_cell_image = image_manager.fret_image[x0:x1+1, y0:y1+1] * sept_mask
                fret_cell_image = fret_cell_image - self.autofluorescence_fret - cells_manager.cells[key].stats["Baseline FRET"]
                fret_cell_image = fret_cell_image * (fret_cell_image > 0)
                nonzero_fret = np.nonzero(fret_cell_image)

                # TODO discuss if we shoudld use this pixels anyway
                septum_nonzero_ix = list(set(zip(list(nonzero_acceptor[0]), list(nonzero_acceptor[1]))).intersection(zip(list(nonzero_donor[0]), list(nonzero_donor[1]))).intersection(zip(list(nonzero_fret[0]), list(nonzero_fret[1]))))

                septum_e_values = []
                for ix in septum_nonzero_ix:
                    Iaa = (self.fret_d * acceptor_cell_image[ix] - self.fret_c * fret_cell_image[ix]) / (self.fret_d - self.fret_c * self.fret_a)
                    Idd = (self.fret_a * donor_cell_image[ix] - self.fret_b * fret_cell_image[ix]) / (self.fret_a - self.fret_b * self.fret_d)
                    Fc = fret_cell_image[ix] - self.fret_a * Iaa - self.fret_d * Idd

                    e = (Fc/self.fret_G) / (Idd+(Fc/self.fret_G))
                    septum_e_values.append(e)

                if len(septum_e_values) > 0:
                    average = np.average(septum_e_values)
                    septum_average_E.append(average)
                    cells_manager.cells[key].stats["Septum E"] = average
                else:
                    cells_manager.cells[key].stats["Septum E"] = 0

                ###################################################################
                # MembSept Calculations

                membsept_e_values = []
                membsept_e_values.extend(membrane_e_values)
                membsept_e_values.extend(septum_e_values)

                if len(membsept_e_values) > 0:
                    average = np.average(membsept_e_values)
                    membsept_average_E.append(average)
                    cells_manager.cells[key].stats["MembSept E"] = average
                else:
                    cells_manager.cells[key].stats["MembSept E"] = 0

            else:
                cells_manager.cells[key].stats["MembSept E"] = 0

            phase_img = image_manager.phase_image
            phase_img = img_as_float(gray2rgb(phase_img))

            ht_ix = np.nonzero(heatmap > 0)
            ht_ix = zip(list(ht_ix[0]), list(ht_ix[1]))
            min_val = 0
            max_val = 100

            for ix in ht_ix:
                cm_ix = int(((heatmap[ix] + np.sqrt(min_val*min_val))*256) / (max_val + np.sqrt(min_val*min_val)))
                color = np.array(cm.bwr(cm_ix)[:3])
                phase_img[ix] = color

        self.cell_E = np.median(cell_average_E)
        self.cyto_E = np.median(cyto_average_E)
        self.membrane_E = np.median(membrane_average_E)
        self.membsept_E = np.median(membsept_average_E)
        self.septum_E = np.median(septum_average_E)
        self.fret_heatmap = phase_img
