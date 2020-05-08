"""Helper functions/classes for outputting data generated by the simulation."""
import numpy as np
import os
import sys
import time

import daetools.pyDAE as dae
from daetools.pyDAE.data_reporters import daeMatlabMATFileDataReporter
import scipy.io as sio


class MyMATDataReporter(daeMatlabMATFileDataReporter):
    """See source code for pyDataReporting.daeMatlabMATFileDataReporter"""
    def WriteDataToFile(self):
        mdict = {}
        for var in self.Process.Variables:
            # Remove the model name part of the output key for
            # brevity.
            dkeybase = var.Name[var.Name.index(".")+1:]
            # Remove dots from variable keys. This enables the mat
            # file to be read by, e.g., MATLAB.
            dkeybase = dkeybase.replace(".", "_")
            mdict[dkeybase] = var.Values 
            #if we are not in a continuation directory
            mdict[dkeybase + '_times'] = var.TimeValues

            #if we are in a directory that has continued simulations (maccor reader)
            if os.path.isfile(self.ConnectionString + ".mat"):
                if os.stat(self.ConnectionString + ".mat").st_size != 0:
                    mat_dat = sio.loadmat(self.ConnectionString + ".mat")
                    #increment time by the previous end time of the last simulation
                    tend = mat_dat[dkeybase + '_times'][0, -1]
                    #get previous values from old output_mat
                    mdict[dkeybase + '_times'] = (var.TimeValues + tend).T
                    #may flatten array, so we specify axis
                    if mat_dat[dkeybase].shape[0] == 1:
                        mat_dat[dkeybase] = mat_dat[dkeybase].T
                        mdict[dkeybase] = mdict[dkeybase].reshape(-1, 1)
                    #data output does weird arrays where its (n, 2) but (1, n) if only one row
                    mdict[dkeybase] = np.append(mat_dat[dkeybase], mdict[dkeybase], axis = 0)
                    mdict[dkeybase + '_times'] = np.append(mat_dat[dkeybase + '_times'],  mdict[dkeybase + '_times'])

        sio.savemat(self.ConnectionString + ".mat",
                    mdict, appendmat=False, format='5',
                    long_field_names=False, do_compression=False,
                    oned_as='row')


def setup_data_reporters(simulation, outdir):
    """Create daeDelegateDataReporter and add data reporter."""
    datareporter = dae.daeDelegateDataReporter()
    simulation.dr = MyMATDataReporter()
    datareporter.AddDataReporter(simulation.dr)
    # Connect data reporters
    simName = simulation.m.Name + time.strftime(" [%d.%m.%Y %H:%M:%S]",
                                                time.localtime())
    #we name it another name so it doesn't overwrite our output data file
    matDataName = "output_data"
    matfilename = os.path.join(outdir, matDataName)
    if not simulation.dr.Connect(matfilename, simName):
        sys.exit()
    # a hack to make compatible with pre/post r526 daetools
    try:
        simulation.dr.ConnectionString = simulation.dr.ConnectString
    except AttributeError:
        pass
    return datareporter
