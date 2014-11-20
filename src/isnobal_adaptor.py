# Copyright (c) 2014, Matthew Turner (maturner01.gmail.com)
#
# For the Tri-state EPSCoR Program
"""
Tools for working with IPW binary data and running the iSNOBAL model
"""

import pandas as pd
from collections import namedtuple

from collections import defaultdict

import logging

#: IPW standard. assumed unchanging since they've been the same for 20 years
BAND_TYPE_LOC = 1
BAND_INDEX_LOC = 2


class Band:
    """
    Container for band information
    """
    def __init__(self, nBytes=None, nBits=None, intMin=None, intMax=None,
                 floatMin=None, floatMax=None):
        """
        Can either pass this information or create an all-None Band.
        """
        self.bytes_ = nBytes
        self.bits_ = nBits
        self.intMin = intMin
        self.intMax = intMax
        self.floatMin = floatMin
        self.floatMax = floatMax


def _calc_float_value(band, integerValue):
    """
    Calculate a floating point value for the integer int_ given the min/max int
    and min/max floats in the given bandObj

    Returns: Floating point value of the mapped int_
    """
    floatRange = band.floatMax - band.floatMin

    return (integerValue / float(band.intMax)) * floatRange + band.floatMin


#: Container for ISNOBAL Global Band information
GlobalBand = namedtuple("GlobalBand", 'nLines nSamps nBands')

#: ISNOBAL variable names to be looked up to make dataframes and write metadata
VARNAME_DICT = \
    {
        'in': ["I_lw", "T_a", "e_a", "u", "T_g", "S_n"],
        'em': [],
        'snow': []
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

        header = _parse_header_lines(ipwLines.headerLines)

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


def _build_ipw_dataframe(header, binaryData, colnames):
    """
    Build a pandas DataFrame using header info to assign column names
    """
    pass


def _make_header_dict(headerLines, varnames):
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
            globalBandDict[spl[0]] = int(spl[2])

    # these are the standard names in an ISNOBAL header file
    nLines = globalBandDict['nlines']
    nSamps = globalBandDict['nsamps']
    nBands = globalBandDict['nbands']

    # this will be put into the return dictionary at the return statement
    globalBand = GlobalBand(nLines, nSamps, nBands)

    # initialize a list of bands to put parsed information into
    bands = [Band() for i in range(nBands)]

    # bandDict = {'global': globalBand}

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


class IPWLines:
    """
    Data structure to wrap header and binary parts of an IPW file.

    Arguments: ipwFile -- file name pointing to an IPW file
    """
    def __init__(self, ipwFile):

        with open(ipwFile, 'rb') as f:
            lines = f.readlines

        self.headerLines = lines[:-1]

        self.binaryData  = lines[-1]
