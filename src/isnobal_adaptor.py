# Copyright (c) 2014, Matthew Turner (maturner01.gmail.com)
#
# For the Tri-state EPSCoR Program
"""
Tools for working with IPW binary data and running the iSNOBAL model
"""

import pandas as pd
from collections import namedtuple

#: Container for ISNOBAL Band information
Band = namedtuple("Band", \
                  'nBytes nBits binMin binMax floatMin floatMax'.split())

#: Container for ISNOBAL Global Band information
GlobalBand = namedtuple("GlobalBand", 'nLines nSamps nBands'.split())

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
    # parse global information from global header
    for i, l in headerLines[1:-1]:
        if l.split()[0] == "!<header>":
            toIndex = i
            break

    globalHeaderLines = headerLines[1:toIndex]

    for l in globalHeaderLines:
        exec(l)

    del byteorder

    globalBand = GlobalBand(nlines, nsamps, nbands)

    bands = []

    # create header groups for each band index number
    nBands = nbands

    return dict(zip(['global'] + range(nBands), globalBand + bands))

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
