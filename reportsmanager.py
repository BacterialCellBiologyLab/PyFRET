import cellprocessing as cp
import tkFileDialog
import os
from skimage.util import img_as_float, img_as_int
from skimage.io import imsave


class ReportsManager(object):

    def __init__(self, parameters):
        self.keys = cp.stats_format(parameters.cellprocessingparams)

    def generate_report_experiment(self, image_manager, cells_manager, fret_manager, path):
        cells = cells_manager.cells

        g_value = fret_manager.fret_G
        cell_e = fret_manager.cell_E
        membrane_e = fret_manager.membrane_E
        cyto_e = fret_manager.cyto_E
        membsept_e = fret_manager.membsept_E
        septum_e = fret_manager.septum_E

        auto_d = fret_manager.autofluorescence_donor
        auto_a = fret_manager.autofluorescence_acceptor
        auto_f = fret_manager.autofluorescence_fret

        cf_a = fret_manager.fret_a
        cf_b = fret_manager.fret_b
        cf_c = fret_manager.fret_c
        cf_d = fret_manager.fret_d

        HTML_HEADER = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
                        "http://www.w3.org/TR/html4/strict.dtd">
                    <html lang="en">
                      <head>
                        <meta http-equiv="content-type" content="text/html; charset=utf-8">
                        <title>title</title>
                        <link rel="stylesheet" type="text/css" href="style.css">
                        <script type="text/javascript" src="script.js"></script>
                      </head>
                      <body>\n"""

        report = [HTML_HEADER]

        g_report = "<h2>Average G value: " + str(g_value) + "</h2>"
        report.extend(g_report)
        cell_e_report = "<h2>Average Cell E value: " + str(cell_e) + "</h2>"
        report.extend(cell_e_report)
        membrane_e_report = "<h2>Average Membrane E value: " + str(membrane_e) + "</h2>"
        report.extend(membrane_e_report)
        cyto_e_report = "<h2>Average Cytoplasm E value: " + str(cyto_e) + "</h2>"
        report.extend(cyto_e_report)
        septum_e_report = "<h2>Average Septum E value: " + str(septum_e) + "</h2>"
        report.extend(septum_e_report)
        membsept_e_report = "<h2>Average MembSept E value: " + str(membsept_e) + "</h2>"
        report.extend(membsept_e_report)

        auto_d_report = "<h2>Average Donor Autofluorescence value: " + str(auto_d) + "</h2>"
        report.extend(auto_d_report)
        auto_a_report = "<h2>Average Acceptor Autofluorescence value: " + str(auto_a) + "</h2>"
        report.extend(auto_a_report)
        auto_f_report = "<h2>Average FRET Autofluorescence value: " + str(auto_f) + "</h2>"
        report.extend(auto_f_report)

        cf_a_report = "<h2>Average a value: " + str(cf_a) + "</h2>"
        report.extend(cf_a_report)
        cf_b_report = "<h2>Average b value: " + str(cf_b) + "</h2>"
        report.extend(cf_b_report)
        cf_c_report = "<h2>Average c value: " + str(cf_c) + "</h2>"
        report.extend(cf_c_report)
        cf_d_report = "<h2>Average d value: " + str(cf_d) + "</h2>"
        report.extend(cf_d_report)

        if len(cells) > 0:
            header = '<table border=1>\n<th>Cell ID</th><th>Images'
            for k in self.keys:
                label, digits = k
                header = header + '</th><th>' + label
            header += '</th>\n'
            fret = ['\n<h1>FRET cells:</h1>\n' + header + '\n']
            donor = ['\n<h1>Donor cells:</h1>\n' + header + '\n']
            acceptor = ['\n<h1>Acceptor Cells:</h1>\n' + header + '\n']
            control = ['\n<h1>Control Cells:</h1>\n' + header + '\n']
            wt = ['\n<h1>wt Cells:</h1>\n' + header + '\n']
            discarded = ['\n<h1>Discarded Cells:</h1>\n' + header + '\n']

            sorted_keys = []
            for k in sorted(cells.keys()):
                sorted_keys.append(int(k))

            sorted_keys = sorted(sorted_keys)

            for k in sorted_keys:
                cell = cells[str(k)]

                if cell.channel == "both":
                    cellid = str(int(cell.label))
                    img = img_as_float(cell.image[:, 0:1+cell.image.shape[1]/2])
                    imsave(path + "/_fret_images" +
                           os.sep + cellid + '.png', img)
                    lin = '<tr><td>' + cellid + '</td><td><img src="./' + '_fret_images/' + \
                          cellid + '.png" alt="pic" width="200"/></td>'

                    for stat in self.keys:
                        lbl, digits = stat
                        lin = lin + '</td><td>' + \
                            ("{0:." + str(digits) +
                             "f}").format(cell.stats[lbl])

                    lin += '</td></tr>\n'
                    fret.append(lin)

                elif cell.channel == "donor":
                    cellid = str(int(cell.label))
                    img = img_as_float(cell.image[:, 0:1+cell.image.shape[1]/2])
                    imsave(path + "/_donor_images" +
                           os.sep + cellid + '.png', img)
                    lin = '<tr><td>' + cellid + '</td><td><img src="./' + '_donor_images/' + \
                          cellid + '.png" alt="pic" width="200"/></td>'

                    for stat in self.keys:
                        lbl, digits = stat
                        lin = lin + '</td><td>' + \
                            ("{0:." + str(digits) +
                             "f}").format(cell.stats[lbl])

                    lin += '</td></tr>\n'
                    donor.append(lin)

                elif cell.channel == "acceptor":
                    cellid = str(int(cell.label))
                    img = img_as_float(cell.image[:, 0:1+cell.image.shape[1]/2])
                    imsave(path + "/_acceptor_images" +
                           os.sep + cellid + '.png', img)
                    lin = '<tr><td>' + cellid + '</td><td><img src="./' + '_acceptor_images/' + \
                          cellid + '.png" alt="pic" width="200"/></td>'

                    for stat in self.keys:
                        lbl, digits = stat
                        lin = lin + '</td><td>' + \
                            ("{0:." + str(digits) +
                             "f}").format(cell.stats[lbl])

                    lin += '</td></tr>\n'
                    acceptor.append(lin)

                elif cell.channel == "control":
                    cellid = str(int(cell.label))
                    img = img_as_float(cell.image[:, 0:1+cell.image.shape[1]/2])
                    imsave(path + "/_control_images" +
                           os.sep + cellid + '.png', img)
                    lin = '<tr><td>' + cellid + '</td><td><img src="./' + '_control_images/' + \
                          cellid + '.png" alt="pic" width="200"/></td>'

                    for stat in self.keys:
                        lbl, digits = stat
                        lin = lin + '</td><td>' + \
                            ("{0:." + str(digits) +
                             "f}").format(cell.stats[lbl])

                    lin += '</td></tr>\n'
                    control.append(lin)

                elif cell.channel == "wt":
                    cellid = str(int(cell.label))
                    img = img_as_float(cell.image[:, 0:1+cell.image.shape[1]/2])
                    imsave(path + "/_wt_images" +
                           os.sep + cellid + '.png', img)
                    lin = '<tr><td>' + cellid + '</td><td><img src="./' + '_wt_images/' + \
                          cellid + '.png" alt="pic" width="200"/></td>'

                    for stat in self.keys:
                        lbl, digits = stat
                        lin = lin + '</td><td>' + \
                            ("{0:." + str(digits) +
                             "f}").format(cell.stats[lbl])

                    lin += '</td></tr>\n'
                    wt.append(lin)

                elif cell.channel == "discard":
                    cellid = str(int(cell.label))
                    img = img_as_float(cell.image[:, 0:1+cell.image.shape[1]/2])
                    imsave(path + "/_discarded_images" +
                           os.sep + cellid + '.png', img)
                    lin = '<tr><td>' + cellid + '</td><td><img src="./' + '_discarded_images/' + \
                          cellid + '.png" alt="pic" width="200"/></td>'

                    for stat in self.keys:
                        lbl, digits = stat
                        lin = lin + '</td><td>' + \
                            ("{0:." + str(digits) +
                             "f}").format(cell.stats[lbl])

                    lin += '</td></tr>\n'
                    discarded.append(lin)

            if len(fret) > 1:
                report.extend(fret)
                report.append("</table>\n")
            if len(donor) > 1:
                report.extend(donor)
                report.append("</table>\n")
            if len(acceptor) > 1:
                report.extend(acceptor)
                report.append("</table>\n")
            if len(control) > 1:
                report.extend(control)
                report.append("</table>\n")
            if len(wt) > 1:
                report.extend(wt)
                report.append("</table>\n")
            if len(discarded) > 1:
                report.extend(discarded)
                report.append("</table>\n")

            report.append('</body>\n</html>')

        open(path + os.sep + "html_report.html", "w").writelines(report)

    def generate_report(self, image_manager, cells_manager, fret_manager, path=None):

        if path is None:
            path = tkFileDialog.askdirectory()

        path = path + os.sep + "Report Experiment"
        if not os.path.exists(path + os.sep + "_fret_images"):
            os.makedirs(path + os.sep + "_fret_images")
        if not os.path.exists(path + os.sep + "_donor_images"):
            os.makedirs(path + os.sep + "_donor_images")
        if not os.path.exists(path + os.sep + "_acceptor_images"):
            os.makedirs(path + os.sep + "_acceptor_images")
        if not os.path.exists(path + os.sep + "_control_images"):
            os.makedirs(path + os.sep + "_control_images")
        if not os.path.exists(path + os.sep + "_wt_images"):
            os.makedirs(path + os.sep + "_wt_images")
        if not os.path.exists(path + os.sep + "_discarded_images"):
            os.makedirs(path + os.sep + "_discarded_images")
        self.generate_report_experiment(image_manager, cells_manager, fret_manager, path)
        imsave(path + os.sep + "heatmap.png", img_as_int(fret_manager.fret_heatmap))
