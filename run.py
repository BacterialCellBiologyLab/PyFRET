from setmanager import SetManager

app = SetManager()

app.load_phase_image()
app.compute_mask()
app.load_fluor_image("Donor")
app.load_fluor_image("FRET")
app.load_fluor_image("Acceptor")

app.compute_segments()
app.compute_cells()
app.process_cells()

app.pick_channel()
app.compute_autofluorescence()
print "Autofluorescence Donor: ", app.fret_manager.autofluorescence_donor
print "Autofluorescence Acceptor: ", app.fret_manager.autofluorescence_acceptor
print "Autofluorescence FRET: ", app.fret_manager.autofluorescence_fret

app.compute_correction_factors()
print "a: ", app.fret_manager.fret_a
print "b: ", app.fret_manager.fret_b
print "c: ", app.fret_manager.fret_c
print "d: ", app.fret_manager.fret_d

app.compute_g()
print "G: ", app.fret_manager.fret_G

app.compute_fret_efficiency()
print "E: ", app.fret_manager.fret_E

app.generate_report()
