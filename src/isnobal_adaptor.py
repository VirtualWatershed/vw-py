# Copyright (c) 2014, Matthew Turner (maturner01.gmail.com)
#
# For the Tri-state EPSCoR Program
"""
Tools for working with IPW binary data and running the iSNOBAL model
"""

import pandas as pd


def read_ipw(ipwPath):
    """
    Reads an IPW binary file into a `pandas DataFrame
    <http://pandas.pydata.org/pandas-docs/dev/generated/pandas.DataFrame.html>`_
    """
    # load data and separate header and
    with open(ipwPath, 'rb') as f:
        ipwLines = f.readlines()

    headerLines = ipwLines[:-1]

    binData = ipwLines[-1]

    # get colnames and number of bytes per value

    # assign column names

    # use header info to parse binary data

    return pd.DataFrame()


class IPW(pd.DataFrame):
    """
    Represents an IPW file. Headers are stored as "metadata" entries of the
    individual
    """
    def __init__(self, ipwLines, colnames=None):

        header = _parse_header_lines(ipwLines.headerLines)

        df = _build_ipw_dataframe(header, ipwLines.binaryData)

        self.header = header
        self.dataFrame = df

    @classmethod
    def from_lines(self, lines, colnames=None):
        """
        Build an IPW DataFrame using lines from an IPW file
        """
        ipwLines = IPWLines(lines)
        self.__init__(ipwLines, colnames)

    @classmethod
    def from_file(self, dataFile, colnames=None):
        """
        Build an IPW DataFrame starting from file
        """
        ipwLines = _ipw_lines(dataFile)
        self.__init__(ipwLines)

    @property
    def header(self):
        """
        Get the header associated with this IPW file
        """
        return self.header


def _build_ipw_dataframe(header, binaryData, colnames=None):
    """
    Build a pandas DataFrame using header info to assign
    """
    pass


def _parse_header_lines(headerLines):
    """
    Parse header lines and return a Header object
    """
    pass


class Header:
    """
    Parse header, store information
    """
    @property
    def global(self):
        """
        byteorder, nlines, nsamps, nbands
        """
        pass

    @property
    def quantization(self):
        """
        Units, bytes, value maps
        """
        pass

    @property
    def geo(self):
        """
        Geographic info for bands
        """
        pass




def _ipw_lines(ipwFile):
    """
    Get lines from ipw file
    """
    with open(ipwFile, 'rb') as f:
        lines = f.readlines

    return IPWLines(lines)


class IPWLines:
    """
    Data structure to wrap header and binary parts of an IPW file
    """
    def __init__(self, ipwLines):

        self.headerLines = ipwLines[:-1]

        self.binaryData  = ipwLines[-1]
