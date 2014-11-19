# Copyright (c) 2014, Matthew Turner (maturner01.gmail.com)
#
# For the Tri-state EPSCoR Program
"""
Tools for working with IPW binary data and running the iSNOBAL model
"""

import pandas as pd

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
    Represents an IPW file.
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


def _make_header_dict(


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
