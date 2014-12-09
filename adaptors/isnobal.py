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
    isnobalcmd = " ".join(["isnobal",
                           "-t " + str(data_tstep),
                           "-n " + str(nsteps),
                           "-I " + init_img,
                           "-p " + precip_file,
                           "-m " + mask_file,
                           "-i " + input_prefix,
                           "-O " + str(output_frequency),
                           "-e " + em_prefix,
                           "-s " + snow_prefix])

    output = subprocess.check_output(isnobalcmd, shell=True)

    logging.debug("ISNOBAL process output: " + output)


class IPW:
    """
    Represents an IPW file. Provides a data_frame attribute to access the
    variables and their floating point representation as a dataframe. The
    dataframe can be modified, the headers recalculated with
    recalculateHeaders, and then written back to IPW binary with
    writeBinary.

    >>> ipw = IPW().from_file("in.0000")
    >>> ipw.data_frame.T_a = ipw.data_frame.T_a + 1.0 # add 1 dg C to each temp
    >>> ipw.writeBinary("in.plusOne.000")

    """
    def __init__(self, dataFile):

        ipw_lines = IPWLines(dataFile)
        file_type = os.path.basename(dataFile).split('.')[0]

        # _make_bands
        header_dict = \
            _make_bands(ipw_lines.header_lines, VARNAME_DICT[file_type])
        geo_lines = _parse_geo_header(ipw_lines.header_lines)

        bands = [band for band in header_dict.values()]
        nonglobal_bands =\
            sorted([band for varname, band in header_dict.iteritems()
                    if varname != 'global'],
                   key=lambda b: b.bandIdx)

        # initialized when called for below
        self._data_frame = None

        self.file_type = file_type
        self.header_dict = header_dict
        self.geo_lines = geo_lines
        self.binary_data = ipw_lines.binary_data
        self.bands = bands
        self.nonglobal_bands = nonglobal_bands

    def recalculate_header(self):
        """
        Recalculate header values
        """
        _recalculate_header(self.nonglobal_bands, self.data_frame())

    def data_frame(self):
        """
        Get the Pandas DataFrame representation of the IPW file
        """
        if self._data_frame is None:
            self._data_frame = \
                _build_ipw_dataframe(self.nonglobal_bands,
                                     self.binary_data)
        return self._data_frame

    def write(self, fileName):
        """
        Write the IPW data to file
        """
        last_line = "!<header> image -1 $Revision: 1.5 $"

        with open(fileName, 'wb') as f:
            for l in _bands_to_header_lines(self.header_dict):
                f.write(l + '\n')
            for l in self.geo_lines:
                # geo_lines have not been altered; still have line ends
                f.write(l)

            f.write(last_line + '\n')

            f.write(
                _floatdf_to_binstring(self.nonglobal_bands, self._data_frame))

        return None


def _build_ipw_dataframe(nonglobal_bands, binary_data):
    """
    Build a pandas DataFrame using header info to assign column names
    """
    colnames = [b.varname for b in nonglobal_bands]

    dtype = _bands_to_dtype(nonglobal_bands)

    intData = np.fromstring(binary_data, dtype=dtype)

    df = pd.DataFrame(intData, columns=colnames)

    for b in nonglobal_bands:
        df[b.varname] = _calc_float_value(b, df[b.varname])

    return df


def _make_bands(header_lines, varnames):
    """
    Make a header dictionary that points to Band objects for each variable
    name.

    Returns: dict
    """
    # parse global information from global header
    for i, l in enumerate(header_lines[1:-1]):
        if IsHeaderStart(l):
            globalEndIdx = i
            break

    globalHeaderLines = header_lines[1:globalEndIdx+1]

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
    for line in header_lines[globalEndIdx:]:

        spl = line.strip().split()

        if IsHeaderStart(line):

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
                # minimum values are listed first by IPW
                if lqCounter == 0:
                    bands[bandIdx].int_min = float(spl[2])
                    bands[bandIdx].float_min = float(spl[3])
                    lqCounter += 1

                elif lqCounter == 1:
                    bands[bandIdx].int_max = float(spl[2])
                    bands[bandIdx].float_max = float(spl[3])

    return dict(zip(['global']+varnames[:nBands], [globalBand]+bands))


def _parse_geo_header(header_lines):
    """
    For now, just returns all the geographic lines within the header lines.

    Returns: list of geographic header lines ONLY. not the last header line
    """
    first_geo_idx = 0
    for idx, line in enumerate(header_lines):
        if IsHeaderStart(line) and line.split()[1] == 'geo':
            first_geo_idx = idx
            break

    # exclude last line because it's just !<header> image -1 $Revision: 1.5 $
    return header_lines[first_geo_idx:-1]


def _calc_float_value(band, integerValue):
    """
    Calculate a floating point value for the integer int_ given the min/max int
    and min/max floats in the given bandObj

    Returns: Floating point value of the mapped int_
    """
    # TODO create Band.floatRange
    floatRange = band.float_max - band.float_min

    # TODO create Band.scaleMult = floatRange/band.int_max
    return integerValue * (floatRange / band.int_max) + band.float_min


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
        int_min = int(b.int_min)
        int_max = int(b.int_max)
        float_min = \
            (b.float_min, int(b.float_min))[b.float_min == int(b.float_min)]
        float_max = \
            (b.float_max, int(b.float_max))[b.float_max == int(b.float_max)]
        otherLines += ["!<header> lq {0} $Revision: 1.6 $".format(i),
                       "map = {0} {1} ".format(int_min, float_min),
                       "map = {0} {1} ".format(int_max, float_max)]

    return firstLines + otherLines


def _floatdf_to_binstring(bands, df):
    """
    Convert the dataframe floating point data to a binary string.
    """
    # first convert df to an integer dataframe
    int_df = pd.DataFrame(dtype='uint64')

    for b in bands:
        # check that bands are appropriately made, that b.Max/Min really are
        assert len(df[b.float_max < df[b.varname]]) == 0, \
            "Bad band: max not really max.\nb.float_max = %2.10f\n \
            df[b.varname].max()  = %s" % (b.float_max, df[b.varname].max())

        assert (b.float_min <= df[b.varname]).all(), \
            "Bad band: min not really min.\nb.float_min = %s\n \
            df[b.varname].min()  = %2.10f" % (b.float_min, df[b.varname].min())

        # no need to include b.int_min, it's always zero
        map_fn = lambda x: \
            np.round(
                ((x - b.float_min) * b.int_max)/(b.float_max - b.float_min))

        int_df[b.varname] = map_fn(df[b.varname])

    pack_str = "=" + "".join([PACK_DICT[b.bytes_] for b in bands])

    return b''.join([struct.pack(pack_str, *r[1]) for r in int_df.iterrows()])


def _recalculate_header(bands, dataframe):
    """
    Recalculate the minimum and maximum of each band in bands given a dataframe
    that contains data for each band.

    Returns: None
    """
    assert list(dataframe.columns) == [b.varname for b in bands], \
        "DataFrame column names do not match bands' variable names!"

    for band in bands:
        band.float_min = dataframe[band.varname].min()
        band.float_max = dataframe[band.varname].max()

        if band.float_min == band.float_max:
            band.float_max = band.float_min + 1.0

    return None


class Band(object):
    """
    Container for band information
    """
    def __init__(self, varname="", bandIdx=0, nBytes=0, nBits=0, int_min=0.0,
                 int_max=0.0, float_min=0.0, float_max=0.0):
        """
        Can either pass this information or create an all-None Band.
        """
        self.varname = varname

        self.bandIdx = bandIdx

        self.bytes_ = nBytes
        self.bits_ = nBits

        self.int_min = float(int_min)
        self.int_max = float(int_max)
        self.float_min = float(float_min)
        self.float_max = float(float_max)

    def __str__(self):
        return "-- " + self.varname + " --\n" +\
            "".join([attr + ": " + str(value) + "\n"
                     for attr, value in
                     self.__dict__.iteritems()])


class IPWLines:
    """
    Data structure to wrap header and binary parts of an IPW file.

    Arguments: ipwFile -- file name pointing to an IPW file
    """
    def __init__(self, ipw_file):

        with open(ipw_file, 'rb') as f:
            lines = f.readlines()

        last_header_idx = \
            [(i, l) for i, l in enumerate(lines) if "" in l][0][0]
        split_idx = last_header_idx + 1

        self.header_lines = lines[:split_idx]

        self.binary_data = "".join(lines[split_idx:])
