# Copyright (c) 2014, Matthew Turner (maturner01.gmail.com)
#
# For the Tri-state EPSCoR Program
"""
Tools for working with IPW binary data and running the iSNOBAL model
"""

import pandas as pd
import numpy as np
import logging

import struct
from collections import namedtuple, defaultdict

#: IPW standard. assumed unchanging since they've been the same for 20 years
BAND_TYPE_LOC = 1
BAND_INDEX_LOC = 2


#: Container for ISNOBAL Global Band information
GlobalBand = namedtuple("GlobalBand", 'byteorder nLines nSamps nBands')

#: ISNOBAL variable names to be looked up to make dataframes and write metadata
VARNAME_DICT = \
    {
        'in': ["I_lw", "T_a", "e_a", "u", "T_g", "S_n"],
        'em': [],
        'snow': []
    }

#: Convert number of bytes to struct package code for unsigned integer type
PACK_DICT = \
    {
        1: 'B',
        2: 'H',
        4: 'I'
    }


def get_varnames(fileType):
    """
    Access variable names associated with the fileType via VARNAME_DICT.

    Valid fileTypes: 'in', 'em', and 'snow'.

    Returns: list of variable names
    """
    if fileType in ('em', 'snow'):
        print "Not yet implemented for filetype " + fileType
        return None

    return VARNAME_DICT[fileType]


class IPW(pd.DataFrame):
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
    def __init__(self, ipwLines, fileType):

        header = _make_header_dict(ipwLines.headerLines)

        df = _build_ipw_dataframe(header, ipwLines.binaryData)

        self.fileType = fileType
        self.header = header
        self.dataFrame = df

    @classmethod
    def from_lines(self, lines, fileType):
        """
        Build an IPW DataFrame using lines from an IPW file
        """
        ipwLines = IPWLines(lines)
        self.__init__(ipwLines, colnames)

    @classmethod
    def from_file(self, dataFile):
        """
        Build an IPW DataFrame starting from file
        """
        ipwLines = _ipw_lines(dataFile)

        fileType = os.path.basename(dataFile).split('.')[0]
        self.__init__(ipwLines, fileType)

    @property
    def header(self):
        """
        Get the header associated with this IPW file
        """
        return self.header


def _build_ipw_dataframe(bands, binaryData):
    """
    Build a pandas DataFrame using header info to assign column names
    """
    colnames = [b.varname for b in bands]

    dtype = _bands_to_dtype(bands)

    intData = np.fromstring(binaryData, dtype=dtype)

    df = pd.DataFrame(intData, columns=colnames)

    for b in bands:
        df[b.varname] = _calc_float_value(b, df[b.varname])

    return df


def _make_bands(headerLines, varnames):
    """
    Make a header dictionary that points to Band objects for each variable
    name.

    Returns: dict
    """
    # use this to check if a line in the header is a header start announcement
    isHeaderStart = lambda headerLine: headerLine.split()[0] == "!<header>"

    # parse global information from global header
    for i, l in enumerate(headerLines[1:-1]):
        if isHeaderStart(l):
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

        if isHeaderStart(l):

            bandType = spl[BAND_TYPE_LOC]
            bandIdx = int(spl[BAND_INDEX_LOC])

            lqCounter = 0

        elif bandType == 'basic_image':
            # assign byte and bits info that's stored here
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
    return np.dtype([(b.varname, 'uint' + str(b.bits_)) for b in bands])


def _bands_to_header(bandsDict):
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
                       "nbytes = {0} ".format(b.bytes_),
                       "nbits = {0} ".format(b.bits_)]

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
        assert (b.floatMax > df[b.varname]).all(), \
            "Bad band: max not really max"
        assert (b.floatMin < df[b.varname]).all(), \
            "Bad band: min not really min"

        # no need to include b.intMin, it's always zero
        mapFn = lambda x: \
            np.floor(((x - b.floatMin) * b.intMax)/(b.floatMax - b.floatMin))

        intDf[b.varname] = mapFn(df[b.varname])

    packStr = "".join([PACK_DICT[b.bytes_] for b in bands])

    logging.debug("packStr: " + packStr)

    logging.debug("intDf: " + str(intDf))

    return "".join([struct.pack(packStr, *r[1]) for r in intDf.iterrows()])


class Band:
    """
    Container for band information
    """
    def __init__(self, varname="", bandIdx=0, nBytes=0, nBits=0, intMin=0,
                 intMax=0, floatMin=0.0, floatMax=0.0):
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

        self.headerLines = lines[:-1]

        self.binaryData = lines[-1]
