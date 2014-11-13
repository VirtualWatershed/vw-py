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


class Header:
    """
    Parse and wrap header info.
    """
    def __init__(self, headerLines):
        """
        Parse header lines to find variables
        """


class HeaderVarInfo:
    """
    Wrap the header info: variable name, units, float max/min, quantization
    resolution (no. of bytes used per variable).
    """
    def __init__(self, headerChunk):
        """
        ``headerChunk`` is the chunk of TODO: 3? lines of header for each
        variable.
        """


def chunk_header(headerLines):
    """
    Create header "chunks" or sets of header lines corresponding to a single
    variable.

    Returns list of HeaderVarInfo
    """
    newVar = False
    for line in headerLines:
        while not newVar:
            if line[0] == "====":
                newVar = True

    return []
