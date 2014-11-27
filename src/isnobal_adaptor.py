#
# Copyright (c) 2014, Matthew Turner (maturner01.gmail.com)
#
# For the Tri-state EPSCoR Track II WC-WAVE Project
#
"""
Tools for working with IPW binary data and running the iSNOBAL model
"""

import os
import logging
import pandas as pd
import numpy as np
import subprocess
import struct

from collections import namedtuple, defaultdict

#: IPW standard. assumed unchanging since they've been the same for 20 years
BAND_TYPE_LOC = 1
BAND_INDEX_LOC = 2

#: Container for ISNOBAL Global Band information
GlobalBand = namedtuple("GlobalBand", 'byteorder nLines nSamps nBands')

#: Check if a header is starting
IsHeaderStart = lambda headerLine: headerLine.split()[0] == "!<header>"

#: ISNOBAL variable names to be looked up to make dataframes and write metadata
VARNAME_DICT = \
    {
        'in': ["I_lw", "T_a", "e_a", "u", "T_g", "S_n"],
        'em': ["R_n", "H", "L_v_E", "G", "M", "delta_Q", "E_s", "melt",
               "ro_predict", "cc_s"],
        'snow': ["z_s", "rho", "m_s", "h2o", "T_s_0", "T_s_l", "T_s",
                 "z_s_l", "h2o_sat"]
    }

#: Convert number of bytes to struct package code for unsigned integer type
PACK_DICT = \
    {
        1: 'B',
        2: 'H',
        4: 'I'
    }


def isnobal(data_tstep=60, nsteps=8758, init_img="data/init.ipw",
            precip_file="data/ppt_desc", mask_file="data/tl2p5mask.ipw",
            input_prefix="data/inputs/in", output_frequency=1,
            em_prefix="data/outputs/em", snow_prefix="data/outputs/snow"):
    """
    Wrapper for running the ISNOBAL
    (http://cgiss.boisestate.edu/~hpm/software/IPW/man1/isnobal.html) model.
    """
    isnobalcmd = "".join(["isnobal ",
                          " -t " + str(data_tstep),
                          " -n " + str(nsteps),
                          " -I " + init_img,
                          " -p " + precip_file,
                          " -m " + mask_file,
                          " -i " + input_prefix,
                          " -O " + str(output_frequency),
                          " -e " + em_prefix,
                          " -s " + snow_prefix])
    logging.debug("ISNOBAL shell command: " + isnobalcmd)

    output = subprocess.check_output(isnobalcmd, shell=True)

    logging.debug("ISNOBAL process output: " + output)


class IPW:
    """
    Represents an IPW file. Provides a dataFrame attribute to access the
    variables and their floating point representation as a dataframe. The
    dataframe can be modified, the headers recalculated with
    recalculateHeaders, and then written back to IPW binary with
    writeBinary.

    >>> ipw = IPW().from_file("in.0000")
    >>> ipw.dataFrame.T_a = ipw.dataFrame.T_a + 1.0 # add 1 deg C to each temp
    >>> ipw.writeBinary("in.plusOne.000")

    """
    def __init__(self, dataFile):

        ipwLines = IPWLines(dataFile)
        fileType = os.path.basename(dataFile).split('.')[0]

        # _make_bands
        headerDict = _make_bands(ipwLines.headerLines, VARNAME_DICT[fileType])
        geoLines = _parse_geo_header(ipwLines.headerLines)

        bands = [band for band in headerDict.values()]
        nonglobalBands =\
            sorted([band for varname, band in headerDict.iteritems()
                    if varname != 'global'],
                   key=lambda b: b.bandIdx)

        df = _build_ipw_dataframe(nonglobalBands, ipwLines.binaryData)

        self.fileType = fileType
        self.headerDict = headerDict
        self.geoLines = geoLines
        self.bands = bands
        self.nonglobalBands = nonglobalBands
        self.dataFrame = df

    def recalculate_header(self):
        """
        Recalculate header values
        """
        _recalculate_headers(self.nonglobalBands, self.dataFrame)

    def write(self, fileName):
        """
        Write the IPW data to file
        """
        lastLine = "!<header> image -1 $Revision: 1.5 $"

        with open(fileName, 'wb') as f:
            for l in _bands_to_header_lines(self.headerDict):
                f.write(l + '\n')
            for l in self.geoLines:
                # geoLines have not been altered; still have line ends
                f.write(l)

            f.write(lastLine + '\n')

            f.write(_floatdf_to_binstring(self.nonglobalBands, self.dataFrame))

        return None


def _build_ipw_dataframe(nonglobalBands, binaryData):
    """
    Build a pandas DataFrame using header info to assign column names
    """
    colnames = [b.varname for b in nonglobalBands]

    dtype = _bands_to_dtype(nonglobalBands)



    intData = np.fromstring(binaryData, dtype=dtype)

    df = pd.DataFrame(intData, columns=colnames)

    for b in nonglobalBands:
        df[b.varname] = _calc_float_value(b, df[b.varname])

    return df


def _make_bands(headerLines, varnames):
    """
    Make a header dictionary that points to Band objects for each variable
    name.

    Returns: dict
    """
    # parse global information from global header
    for i, l in enumerate(headerLines[1:-1]):
        if IsHeaderStart(l):
            globalEndIdx = i
            break

    globalHeaderLines = headerLines[1:globalEndIdx+1]

    # tried a prettier dictionary comprehension, but wouldn't fly
    globalBandDict = defaultdict(int)
    for l in globalHeaderLines:
        if l:
            spl = l.strip().split()
            if spl[0] == 'byteorder':
                globalBandDict[spl[0]] = spl[2]
            else:
                globalBandDict[spl[0]] = int(spl[2])

    # these are the standard names in an ISNOBAL header file
    byteorder = globalBandDict['byteorder']
    nLines = globalBandDict['nlines']
    nSamps = globalBandDict['nsamps']
    nBands = globalBandDict['nbands']

    # this will be put into the return dictionary at the return statement
    globalBand = GlobalBand(byteorder, nLines, nSamps, nBands)

    # initialize a list of bands to put parsed information into
    bands = [Band() for i in range(nBands)]

    # bandDict = {'global': globalBand}
    for i, b in enumerate(bands):
        b.varname = varnames[i]
        b.bandIdx = i

    bandType = None
    bandIdx = None
    for l in headerLines[globalEndIdx:]:

        spl = l.strip().split()

        if IsHeaderStart(l):

            bandType = spl[BAND_TYPE_LOC]
            bandIdx = int(spl[BAND_INDEX_LOC])

            lqCounter = 0

        elif bandType == 'basic_image':
            # assign byte and bits info that's stored here
            if spl[0] in ['bits', 'bytes']:
                setattr(bands[bandIdx], spl[0] + "_", int(spl[2]))

        elif bandType == 'lq':
            # assign integer and float min and max. ignore non-"map" fields
            if spl[0] == "map":
                # minimum values are listed first
                if lqCounter == 0:
                    bands[bandIdx].intMin = float(spl[2])
                    bands[bandIdx].floatMin = float(spl[3])
                    lqCounter += 1

                elif lqCounter == 1:
                    bands[bandIdx].intMax = float(spl[2])
                    bands[bandIdx].floatMax = float(spl[3])

    return dict(zip(['global']+varnames[:nBands], [globalBand]+bands))


def _parse_geo_header(headerLines):
    """
    For now, just returns all the geographic lines within the header lines.

    Returns: list of geographic header lines ONLY. not the last header line
    """
    firstGeoIdx = 0
    for idx, line in enumerate(headerLines):
        if IsHeaderStart(line) and line.split()[1] == 'geo':
            firstGeoIdx = idx
            break

    # exclude last line because it's just !<header> image -1 $Revision: 1.5 $
    return headerLines[firstGeoIdx:-1]


def _calc_float_value(band, integerValue):
    """
    Calculate a floating point value for the integer int_ given the min/max int
    and min/max floats in the given bandObj

    Returns: Floating point value of the mapped int_
    """
    # TODO create Band.floatRange
    floatRange = band.floatMax - band.floatMin

    # TODO create Band.scaleMult = floatRange/band.intMax
    return integerValue * (floatRange / band.intMax) + band.floatMin


def _bands_to_dtype(bands):
    """
    Given a list of Bands, convert them to a numpy.dtype for use in creating
    the IPW dataframe.
    """
    return np.dtype([(b.varname, 'uint' + str(b.bytes_ * 8)) for b in bands])


def _bands_to_header_lines(bandsDict):
    """
    Convert the bands to a new header assuming the float ranges are up to date
    for the current dataframe, df.
    """
    firstLine = "!<header> basic_image_i -1 $Revision: 1.11 $"

    global_ = bandsDict['global']

    firstLines = [firstLine,
                  "byteorder = {0} ".format(global_.byteorder),
                  "nlines = {0} ".format(global_.nLines),
                  "nsamps = {0} ".format(global_.nSamps),
                  "nbands = {0} ".format(global_.nBands)]

    otherLines = []
    bands = [b for varname, b in bandsDict.iteritems() if varname != 'global']

    bands = sorted(bands, key=lambda b: b.bandIdx)

    # for some reason IPW has a space at the end of data lines
    for i, b in enumerate(bands):
        otherLines += ["!<header> basic_image {0} $Revision: 1.11 $".format(i),
                       "bytes = {0} ".format(b.bytes_),
                       "bits = {0} ".format(b.bits_)]

    for i, b in enumerate(bands):
        # IPW writes integer floats without even a dec point, so strip decimal
        intMin = int(b.intMin)
        intMax = int(b.intMax)
        floatMin = (b.floatMin, int(b.floatMin))[b.floatMin == int(b.floatMin)]
        floatMax = (b.floatMax, int(b.floatMax))[b.floatMax == int(b.floatMax)]
        otherLines += ["!<header> lq {0} $Revision: 1.6 $".format(i),
                       "map = {0} {1} ".format(intMin, floatMin),
                       "map = {0} {1} ".format(intMax, floatMax)]

    return firstLines + otherLines


def _floatdf_to_binstring(bands, df):
    """
    Convert the dataframe floating point data to a binary string.
    """
    # first convert df to an integer dataframe
    intDf = pd.DataFrame(dtype='uint64')

    for b in bands:
        # check that bands are appropriately made, that b.Max/Min really are
        assert (b.floatMax >= df[b.varname]).all(), \
            "Bad band: max not really max.\nb.floatMax = %s\n \
            df[b.varname].max()  = %s" % (b.floatMax, df[b.varname].max())
        assert (b.floatMin <= df[b.varname]).all(), \
            "Bad band: min not really min.\nb.floatMin = %s\n \
            df[b.varname].min()  = %s" % (b.floatMin, df[b.varname].min())

        # no need to include b.intMin, it's always zero
        mapFn = lambda x: \
            np.round(((x - b.floatMin) * b.intMax)/(b.floatMax - b.floatMin))

        intDf[b.varname] = mapFn(df[b.varname])

    packStr = "=" + "".join([PACK_DICT[b.bytes_] for b in bands])

    return b''.join([struct.pack(packStr, *r[1]) for r in intDf.iterrows()])


# TODO: rename this to _recalculate_header
def _recalculate_headers(bands, dataframe):
    """
    Recalculate the minimum and maximum of each band in bands given a dataframe
    that contains data for each band.

    Returns: None
    """
    assert list(dataframe.columns) == [b.varname for b in bands], \
        "DataFrame column names do not match bands' variable names!"

    for band in bands:
        band.floatMin = dataframe[band.varname].min()
        band.floatMax = dataframe[band.varname].max()

        if band.floatMin == band.floatMax:
            band.floatMax = band.floatMin + 1.0

    return None


class Band(object):
    """
    Container for band information
    """
    def __init__(self, varname="", bandIdx=0, nBytes=0, nBits=0, intMin=0.0,
                 intMax=0.0, floatMin=0.0, floatMax=0.0):
        """
        Can either pass this information or create an all-None Band.
        """
        self.varname = varname

        self.bandIdx = bandIdx

        self.bytes_ = nBytes
        self.bits_ = nBits

        self.intMin = float(intMin)
        self.intMax = float(intMax)
        self.floatMin = float(floatMin)
        self.floatMax = float(floatMax)


class IPWLines:
    """
    Data structure to wrap header and binary parts of an IPW file.

    Arguments: ipwFile -- file name pointing to an IPW file
    """
    def __init__(self, ipwFile):

        with open(ipwFile, 'rb') as f:
            lines = f.readlines()

        lastHeaderIdx = [(i, l) for i, l in enumerate(lines) if "" in l][0][0]
        splitIdx = lastHeaderIdx + 1

        self.headerLines = lines[:splitIdx]

        self.binaryData = "".join(lines[splitIdx:])
