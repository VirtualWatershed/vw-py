"""
Tools for working with IPW binary data and running the iSNOBAL model.
"""
#
# Copyright (c) 2014, Matthew Turner (maturner01.gmail.com)
#
# For the Tri-state EPSCoR Track II WC-WAVE Project
#

# Acknowledgements to Robert Lew for inspiration in the design of the IPW
# class (see https://github.com/rogerlew/RL_GIS_Sandbox/tree/master/isnobal).
#
import datetime
import logging
import numpy as np
import os
import pandas as pd
import subprocess
import struct

from nose.tools import set_trace

from collections import namedtuple, defaultdict
from copy import deepcopy
from netCDF4 import Dataset

from wcwave_adaptors.watershed import get_config, make_fgdc_metadata, make_watershed_metadata
from wcwave_adaptors.netcdf import ncgen_from_template

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
                 "z_s_l", "h2o_sat"],
        'init': ["z", "z_o", "z_s", "rho", "T_s_0", "T_s", "h2o_sat"],
        'precip': ["m_pp", "pct_snow", "rho_snow", "T_pp"],
        'mask': ["mask"],
        'dem': ["dem"]
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


class IPW(object):
    """
    Represents an IPW file. Provides a data_frame attribute to access the
    variables and their floating point representation as a dataframe. The
    dataframe can be modified, the headers recalculated with
    recalculateHeaders, and then written back to IPW binary with
    writeBinary.

    >>> ipw = IPW("in.0000")
    >>> ipw.data_frame.T_a = ipw.data_frame.T_a + 1.0 # add 1 dg C to each temp
    >>> ipw.writeBinary("in.plusOne.000")

    """
    def __init__(self, input_file=None, config_file=None, dt=None,
                 file_type=None):

        assert dt is None or issubclass(type(dt), datetime.timedelta)

        if input_file is not None:

            ipw_lines = IPWLines(input_file)
            input_split = os.path.basename(input_file).split('.')

            file_type = file_type or input_split[0]

            # _make_bands
            try:
                header_dict = \
                    _make_bands(ipw_lines.header_lines,
                                VARNAME_DICT[file_type])

            except (KeyError):
                raise IPWFileError("Provide explicit file type for file %s" %
                                   input_file)

            # extract just bands from the header dictionary
            bands = [band for band in header_dict.values()]

            # get the nonglobal_bands in a list, ordered by band index
            nonglobal_bands =\
                sorted([band for varname, band in header_dict.iteritems()
                        if varname != 'global'],
                       key=lambda b: b.band_idx)

            # the default configuration is used if no config file is given
            if config_file is None:
                config_file = \
                    os.path.join(os.path.dirname(__file__), '../default.conf')

            # helper function get_config uses ConfigParser to parse config file
            config = get_config(config_file)

            if file_type in ['in', 'em', 'snow']:

                # get the water year
                water_year_start = int(config['Common']['water_year'])

                # note that we have not generalized for non-hour timestep data
                if dt is None:
                    dt = pd.Timedelta('1 hour')

                # the iSNOBAL file naming scheme puts the integer time step
                # after the dot, really as the extension
                # TODO as Roger pointed out, really this is for
                # a single point in time, so this timing thing is not right
                start_dt = dt * int(input_split[-1])

                start_datetime = \
                    datetime.datetime(water_year_start, 10, 01) + start_dt

                end_datetime = start_datetime + dt

            else:

                start_datetime = None
                end_datetime = None

            # initialized when called for below
            self._data_frame = None

            self.input_file = input_file
            self.file_type = file_type
            self.header_dict = header_dict
            self.binary_data = ipw_lines.binary_data
            self.bands = bands
            self.nonglobal_bands = nonglobal_bands

            # use geo information in band0; all bands have equiv geo info
            band0 = nonglobal_bands[0]
            self.geotransform = [band0.bsamp - band0.dsamp / 2.0,
                                 band0.dsamp,
                                 0.0,
                                 band0.bline - band0.dline / 2.0,
                                 0.0,
                                 band0.dline]

            self.config_file = config_file

            self.start_datetime = start_datetime
            self.end_datetime = end_datetime

        else:

            self._data_frame = None
            self.input_file = None
            self.file_type = None
            self.header_dict = None
            self.binary_data = None
            self.bands = None
            self.nonglobal_bands = None
            self.geotransform = None
            self.start_datetime = None
            self.end_datetime = None

    def recalculate_header(self):
        """
        Recalculate header values
        """
        _recalculate_header(self.nonglobal_bands, self.data_frame())
        for band in self.nonglobal_bands:
            self.header_dict[band.varname] = band

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

            f.write(last_line + '\n')

            f.write(
                _floatdf_to_binstring(self.nonglobal_bands, self._data_frame))

            return None


def isnobal2netcdf(netcdf_path, ipw_source, isnobal_type=None,
                   dt='hours', year=2010, month=10, day='01'):
    """Use the utilities from netcdf.py to convert either set of input or output
        IPW to NetCDF format, saving to netcdf_path

        Arguments:
            netcdf_path (str): Path to save the NetCDF to
            ipw_source (str or [str]): path to either file or directory

        Returns:
            (netCDF4.Dataset) Representation of the data
    """
    # sanity check isnobal_type and set CDL path based on isnobal_type
    assert isnobal_type in ['inputs', 'outputs'],\
        "isnobal_type must be 'inputs' or 'outputs', not %s" % isnobal_type

    template_path = os.path.join(os.path.dirname(__file__), 'cdl',
                                 'ipw_template_')

    template_path += '_in.cdl' if isnobal_type == 'inputs' else '_out.cdl'

    # for the iSNOBAL input or output parameters, provide some header info
    if type(ipw_source) is str:
        ipw_source = [ipw_source]

    ipw0 = ipw_source[0]
    gt = ipw0.geotransform
    gb = ipw0.bands[1]  # TODO no good--need some names on these bands.

    template_parameters = dict(bline=gt[3], bsamp=gt[0], dline=gt[5],
                               dsamp=gt[1], nsamps=gb.nSamps,
                               nlines=gb.nLines, dt=dt, year=year,
                               month=month, day=day)

    nc = ncgen_from_template(template_path, netcdf_path,
                             **template_parameters)

    # insert the IPW data to the NetCDF; mapping file type to nc group/var
    # done by _ncinsert_ipw
    for f in ipw_source:

        _ncinsert_ipw(nc, IPW(f))

    nc = netcdf_path

    ipw_source.append(nc)

    return ipw_source


def _ncinsert_ipw(dataset, ipw, tstep, nlines, nsamps):
    """Put IPW data into dataset based on file naming conventions

        Args:
            dataset (NetCDF4.Dataset): Dataset to be populated
            ipw (wcwave_adaptors.isnobal.IPW): source data in IPW format
            tstep (int): Positive integer indicating the current time step
            nlines (int): number of 'lines' in IPW file, aka n_northings
            nsamps (int): number of 'samps' in IPW file, aka n_eastings

        Returns:
            None. `dataset` is populated in-place.
    """
    file_type = ipw.file_type

    df = ipw.data_frame()

    if file_type == 'dem':
        # dem only has 'alt' information, stored in root group
        dataset.variables['alt'][:, :] = df.altitude

    elif file_type == 'in':
        gvars = dataset.groups['Input'].variables
        for var in gvars:
            # can't just assign b/c if sun is 'down' var is absent from df
            if var in df.columns:
                gvars[var][tstep, :, :] = np.reshape(df[var],
                                                     (nlines, nsamps))
            else:
                gvars[var][tstep, :, :] = np.zeros((nlines, nsamps))

    elif file_type == 'precip':
        # get the list of precip files from 'ppt_desc'
        pass

    elif file_type == 'mask':
        pass

    elif file_type == 'init':
        pass

    else:
        raise Exception('File type %s not recognized!' % file_type)


def metadata_from_ipw(ipw, output_file, parent_model_run_uuid, model_run_uuid,
                      description, model_set=None):
    """
    Create the metadata for the IPW object, even if it doesn't existed as
    a file on disk.

    WARNING: Does not check that output_file exists. Should be used when, e.g.,
    a re-sampled IPW file or geotiff is being created and saved, and the
    metadata also needs to be created and either saved or sent to the
    waterhsed.

    Returns: None
    """
    fgdc_metadata = make_fgdc_metadata(output_file,
                                     ipw.config, model_run_uuid)

    input_prefix = output_file.split('.')[0]

    if model_set is None:
        model_set = ("outputs", "inputs")[input_prefix == "in"]

    return make_watershed_metadata(output_file,
                                 ipw.config,
                                 parent_model_run_uuid,
                                 model_run_uuid,
                                 model_set,
                                 description,
                                 ipw.model_vars,
                                 fgdc_metadata,
                                 ipw.start_datetime,
                                 ipw.end_datetime)


def reaggregate_ipws(ipws, fun=np.sum, freq='H', rule='D'):
    """
    Resample IPWs using the function fun, but only sum is supported.
    `freq` corresponds to the actual frequency of the ipws; rule corresponds to
    one of the resampling 'rules' given here:
    http://pandas.pydata.org/pandas-docs/dev/timeseries.html#time-date-components
    """
    assert fun is np.sum, "Cannot use " + fun.func_name + \
        ", only np.sum has been implemented"

    assert _is_consecutive(ipws)

    ipw0 = ipws[0]
    start_datetime = ipw0.start_datetime

    idx = pd.date_range(start=start_datetime, periods=len(ipws), freq=freq)

    series = pd.Series(map(lambda ipw: ipw.data_frame(), ipws), index=idx)

    resampled = series.resample(rule, how=np.sum)
    resampled_idx = resampled.index

    resampled_dt = resampled_idx[1] - resampled_idx[0]

    resampled_ipws = [IPW() for el in resampled]

    header_dict = deepcopy(ipw0.header_dict)
    file_type = ipw0.file_type
    # bands = deepcopy(ipw0.bands)
    bands = ipw0.bands
    # nonglobal_bands = deepcopy(ipw0.nonglobal_bands)
    nonglobal_bands = ipw0.nonglobal_bands
    geotransform = ipw0.geotransform
    for ipw_idx, ipw in enumerate(resampled_ipws):

        ipw._data_frame = resampled[ipw_idx]
        ipw.start_datetime = resampled_idx[ipw_idx]
        ipw.end_datetime = resampled_idx[ipw_idx] + resampled_dt
        ipw.header_dict = deepcopy(header_dict)
        ipw.file_type = file_type
        ipw.bands = deepcopy(bands)
        ipw.nonglobal_bands = deepcopy(nonglobal_bands)
        ipw.geotransform = geotransform

        ipw.recalculate_header()

    return resampled_ipws


def _is_consecutive(ipws):
    """
    Check that a list of ipws is consecutive
    """
    ret = True
    ipw_prev = ipws[0]
    for ipw in ipws[1:]:
        ret &= ipw_prev.end_datetime == ipw.start_datetime
        ipw_prev = ipw

    return ret


def _build_ipw_dataframe(nonglobal_bands, binary_data):
    """
    Build a pandas DataFrame using header info to assign column names
    """
    colnames = [b.varname for b in nonglobal_bands]

    dtype = _bands_to_dtype(nonglobal_bands)

    # print len(binary_data)
    # print dtype

    # print nonglobal_bands

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
    globalEndIdx = 0
    # parse global information from global header
    for i, l in enumerate(header_lines[1:-1]):
        if IsHeaderStart(l):
            globalEndIdx = i
            break

    global_header_lines = header_lines[1:globalEndIdx+1]

    # tried a prettier dictionary comprehension, but wouldn't fly
    global_band_dict = defaultdict(int)
    for l in global_header_lines:
        if l:
            spl = l.strip().split()
            if spl[0] == 'byteorder':
                global_band_dict[spl[0]] = spl[2]
            else:
                global_band_dict[spl[0]] = int(spl[2])

    # these are the standard names in an ISNOBAL header file
    byteorder = global_band_dict['byteorder']
    nLines = global_band_dict['nlines']
    nSamps = global_band_dict['nsamps']
    nBands = global_band_dict['nbands']

    # this will be put into the return dictionary at the return statement
    globalBand = GlobalBand(byteorder, nLines, nSamps, nBands)

    # initialize a list of bands to put parsed information into
    bands = [Band() for i in range(nBands)]

    # bandDict = {'global': globalBand}
    for i, b in enumerate(bands):
        b.varname = varnames[i]
        b.band_idx = i

    band_type = None
    band_idx = None
    geo_parsed = False
    ref_band = Band()
    geo_count = 0
    for line in header_lines[globalEndIdx:]:

        spl = line.strip().split()
        attr = spl[0]

        if IsHeaderStart(line):

            band_type = spl[BAND_TYPE_LOC]
            band_idx = int(spl[BAND_INDEX_LOC])

            lqCounter = 0

            if band_type == 'geo':
                geo_count += 1
                if geo_count == 2:
                    geo_parsed = True

        elif band_type == 'basic_image':
            # assign byte and bits info that's stored here
            if attr in ['bits', 'bytes']:
                setattr(bands[band_idx], attr + "_", int(spl[2]))

        elif band_type == 'lq':
            # assign integer and float min and max. ignore non-"map" fields
            if attr == "map":
                # minimum values are listed first by IPW
                if lqCounter == 0:
                    bands[band_idx].int_min = float(spl[2])
                    bands[band_idx].float_min = float(spl[3])
                    lqCounter += 1

                elif lqCounter == 1:
                    bands[band_idx].int_max = float(spl[2])
                    bands[band_idx].float_max = float(spl[3])

        elif band_type == 'geo':
            # Not all bands have geo information. The ones that do are
            # expected to be redundant. Check that all available are equal
            # and for any that don't have geo information, set them to the
            # geo information
            if not geo_parsed:

                if attr in ["bline", "bsamp", "dline", "dsamp"]:
                    setattr(ref_band, attr, float(spl[2]))
                    # setattr(bands[band_idx], attr, float(spl[2]))

                elif attr in ["units", "coord_sys_ID"]:
                    if attr == "units":
                        attr = "geo_units"
                    setattr(ref_band, attr, spl[2])
                    # setattr(bands[band_idx], attr, spl[2])
                else:
                    raise Exception(
                        "'geo' attribute %s from IPW file not recognized!" %
                        attr)

            else:
                if attr == "units":
                    attr = "geo_units"

                assert\
                    getattr(ref_band, attr) == getattr(bands[band_idx], attr)

        # now set all bands to the reference band
        for band in bands:

            band.bline = ref_band.bline
            band.bsamp = ref_band.bsamp
            band.dline = ref_band.dline
            band.dsamp = ref_band.dsamp
            band.geo_units = ref_band.geo_units
            band.coord_sys_ID = ref_band.coord_sys_ID

    return dict(zip(['global']+varnames[:nBands], [globalBand]+bands))


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


def _bands_to_header_lines(bands_dict):
    """
    Convert the bands to a new header assuming the float ranges are up to date
    for the current dataframe, df.
    """
    firstLine = "!<header> basic_image_i -1 $Revision: 1.11 $"

    global_ = bands_dict['global']

    firstLines = [firstLine,
                  "byteorder = {0} ".format(global_.byteorder),
                  "nlines = {0} ".format(global_.nLines),
                  "nsamps = {0} ".format(global_.nSamps),
                  "nbands = {0} ".format(global_.nBands)]

    other_lines = []
    bands = [b for varname, b in bands_dict.iteritems() if varname != 'global']

    bands = sorted(bands, key=lambda b: b.band_idx)

    # for some reason IPW has a space at the end of data lines
    for i, b in enumerate(bands):
        other_lines += ["!<header> basic_image {0} $Revision: 1.11 $".format(i),
                       "bytes = {0} ".format(b.bytes_),
                       "bits = {0} ".format(b.bits_)]

    # build the linear quantization (lq) headers
    for i, b in enumerate(bands):
        int_min = int(b.int_min)
        int_max = int(b.int_max)

        # IPW writes integer floats without a dec point, so remove if necessary
        float_min = \
            (b.float_min, int(b.float_min))[b.float_min == int(b.float_min)]
        float_max = \
            (b.float_max, int(b.float_max))[b.float_max == int(b.float_max)]
        other_lines += ["!<header> lq {0} $Revision: 1.6 $".format(i),
                       "map = {0} {1} ".format(int_min, float_min),
                       "map = {0} {1} ".format(int_max, float_max)]

    # build the geographic header
    for i, b in enumerate(bands):
        bline = b.bline
        bsamp = b.bsamp
        dline = b.dline
        dsamp = b.dsamp
        units = b.geo_units
        coord_sys_ID = b.coord_sys_ID

        other_lines += ["!<header> geo {0} $Revision: 1.7 $".format(i),
                        "bline = {0} ".format(bline),
                        "bsamp = {0} ".format(bsamp),
                        "dline = {0} ".format(dline),
                        "dsamp = {0} ".format(dsamp),
                        "units = {0} ".format(units),
                        "coord_sys_ID = {0} ".format(coord_sys_ID)]

    return firstLines + other_lines


def _floatdf_to_binstring(bands, df):
    """
    Convert the dataframe floating point data to a binary string.
    """
    # first convert df to an integer dataframe
    int_df = pd.DataFrame(dtype='uint64')

    for b in bands:
        # check that bands are appropriately made, that b.Max/Min really are
        assert df[b.varname].le(b.float_max).all(), \
            "Bad band: max not really max.\nb.float_max = %2.10f\n \
            df[b.varname].max()  = %s" % (b.float_max, df[b.varname].max())

        assert df[b.varname].ge(b.float_min).all(), \
            "Bad band: min not really min.\nb.float_min = %s\n \
            df[b.varname].min()  = %2.10f" % (b.float_min, df[b.varname].min())

        # no need to include b.int_min, it's always zero
        map_fn = lambda x: \
            np.round(
                ((x - b.float_min) * b.int_max)/(b.float_max - b.float_min))

        int_df[b.varname] = map_fn(df[b.varname])

    # use the struct package to pack ints to bytes; use '=' to prevent padding
    # that causes problems with the IPW scheme
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
    def __init__(self, varname="", band_idx=0, nBytes=0, nBits=0, int_min=0.0,
                 int_max=0.0, float_min=0.0, float_max=0.0,
                 bline=0.0, bsamp=0.0, dline=0.0, dsamp=0.0,
                 units="meters", coord_sys_ID="UTM"):
        """
        Can either pass this information or create an all-None Band.
        """
        self.varname = varname

        self.band_idx = band_idx

        self.bytes_ = nBytes
        self.bits_ = nBits

        self.int_min = float(int_min)
        self.int_max = float(int_max)
        self.float_min = float(float_min)
        self.float_max = float(float_max)

        self.bline = float(bline)
        self.bsamp = float(bsamp)
        self.dline = float(dline)
        self.dsamp = float(dsamp)

        assert type(units) is str
        self.geo_units = units

        assert type(coord_sys_ID) is str
        self.coord_sys_ID = coord_sys_ID

    def __str__(self):
        return "-- " + self.varname + " --\n" +\
            "".join([attr + ": " + str(value) + "\n"
                     for attr, value in
                     self.__dict__.iteritems()])


class IPWLines(object):
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


class IPWFileError(Exception):
    pass
