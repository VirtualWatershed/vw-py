__author__ = 'jerickson'

import os
import animationToNetcdf
import statvarToNetcdf
import prmsoutToNetcdf

def convertAnimationToNetcdf(anim_in, modelname, nrows, ncols, dataloc, nhru):
    outname = modelname + '_animation.nc'
    animationToNetcdf.animation_to_netcdf(anim_in, dataloc, nhru, nrows, ncols, outname)

def convertStatvarToNetcdf(statvar_in, modelname):
    outname = modelname + '_statvar.nc'
    statvarToNetcdf.statvar_to_netcdf(statvar_in, outname)

def convertPRMSOutToNetcdf(prmsout_in, modelname):
    outname = modelname + '_prmsout.nc'
    prmsoutToNetcdf.prmsout_to_netcdf(prmsout_in, outname)

if __name__ == '__main__':
    convertAnimationToNetcdf("./output/animation.out.nhru", "LC", 49, 96, "./XY.DAT", 4704)
    convertStatvarToNetcdf("./output/statvar.dat", "LC")
    convertPRMSOutToNetcdf("./output/prms.out", "LC")