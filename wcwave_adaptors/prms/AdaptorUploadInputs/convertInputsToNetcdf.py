__author__ = 'jerickson'

import os
import dataToNetcdf
import parameterToNetcdf

def convertDataToNetcdf(data_in):
    basename = os.path.basename(data_in)
    filename, file_extension = os.path.splitext(basename)
    print file_extension
    if file_extension == '.data':
        outname = filename + '_data.nc'
        dataToNetcdf.data_to_netcdf(data_in, outname)
        return 0

    return -1


def convertParamsToNetcdf(param_in, nrows, ncols, dataloc, nhru):
    basename = os.path.basename(param_in)
    filename, file_extension = os.path.splitext(basename)
    print file_extension
    if file_extension == '.param':
        outname = filename + '_param.nc'
        parameterToNetcdf.parameter_to_netcdf(param_in, dataloc, nhru, nrows, ncols, outname)
        return 0

    return -1

if __name__ == '__main__':
    if convertDataToNetcdf("../Input Files/LC.data") == 0:
        print "Data File converted successfully"
    else:
        print "Data File failed to convert"
    if convertParamsToNetcdf("../Input Files/LC.param", 49, 96, "../XY.DAT", 4704 ) == 0:
        print "Param File converted successfully"
    else:
        print "Param File failed to convert"