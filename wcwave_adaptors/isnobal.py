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
import subprocess
import struct

from collections import namedtuple, defaultdict
from copy import deepcopy
from netCDF4 import Dataset
from numpy import (arange, array, zeros, ravel, reshape, fromstring, dtype,
                   floor, log10)
from numpy import sum as npsum
from numpy import round as npround
from numpy.ma.core import MaskedArray
from os import mkdir, listdir
from os.path import exists, dirname, basename
from os.path import join as osjoin
from pandas import date_range, DataFrame, Series, Timedelta
from progressbar import ProgressBar
from shutil import rmtree

from .watershed import (_get_config, make_fgdc_metadata,
                        make_watershed_metadata)

from .netcdf import ncgen_from_template, utm2latlon


#: IPW standard. assumed unchanging since they've been the same for 20 years
BAND_TYPE_LOC = 1
BAND_INDEX_LOC = 2

#: For converting NetCDF to iSNOBAL, use 2 bytes for all variables except mask
NC_NBYTES = 2
NC_NBITS = 16
NC_MAXINT = pow(2, NC_NBITS) - 1

#: Container for ISNOBAL Global Band information
GlobalBand = namedtuple("GlobalBand", 'byteorder nLines nSamps nBands')

#: Check if a header is starting
IsHeaderStart = lambda headerLine: headerLine.split()[0] == "!<header>"


def AssertISNOBALInput(nc):
    """Check if a NetCDF conforms to iSNOBAL requirements for running that
       model. Throw a ISNOBALNetcdfError if not

    """
    nca = nc.ncattrs()
    valid = ('data_tstep' in nca and 'nsteps' in nca and
             'output_frequency' in nca)

    if not valid:
        raise ISNOBALNetcdfError("Attributes 'data_tstep', 'nsteps', " +
                                 "'output_frequency', 'bline', 'bsamp', " +
                                 "'dline', and 'dsamp' not all in NetCDF")

    ncv = nc.variables
    valid = ('alt' in ncv and 'mask' in ncv and 'time' in ncv and
             'easting' in ncv and 'northing' in ncv and 'lat' in ncv and
             'lon' in ncv)

    if not valid:
        raise ISNOBALNetcdfError("Variables 'alt', 'mask', 'time', 'easting', \
                'northing', 'lat' and 'lon' not all present in NetCDF")

    ncg = nc.groups
    valid = ('Initial' in ncg and 'Precipitation' in ncg and 'Input' in ncg)

    if not valid:
        raise ISNOBALNetcdfError("'Initial', 'Precipitation', and 'Input' \
                groups not present in NetCDF")

    gvars = ncg['Input'].variables
    valid = ('I_lw' in gvars and 'T_a' in gvars and 'e_a' in gvars and
             'u' in gvars and 'T_g' in gvars and 'S_n' in gvars)

    if not valid:
        raise ISNOBALNetcdfError("All required variables not present in inputs\
                group of NetCDF")

    gvars = ncg['Initial'].variables
    valid = ('z' in gvars and 'z_0' in gvars and 'z_s' in gvars and
             'rho' in gvars and 'T_s_0' in gvars and 'T_s' in gvars and
             'h2o_sat' in gvars)

    if not valid:
        raise ISNOBALNetcdfError("All required variables not present in \
                initialization group of NetCDF")

    gvars = ncg['Precipitation'].variables
    valid = ('m_pp' in gvars and 'percent_snow' in gvars and
             'rho_snow' in gvars)

    if not valid:
        raise ISNOBALNetcdfError("All precipitation variables are not present \
                in NetCDF")


#: ISNOBAL variable names to be looked up to make dataframes and write metadata
VARNAME_DICT = \
    {
        'in': ["I_lw", "T_a", "e_a", "u", "T_g", "S_n"],
        'em': ["R_n", "H", "L_v_E", "G", "M", "delta_Q", "E_s", "melt",
               "ro_predict", "cc_s"],
        'snow': ["z_s", "rho", "m_s", "h2o", "T_s_0", "T_s_l", "T_s",
                 "z_s_l", "h2o_sat"],
        'init': ["z", "z_0", "z_s", "rho", "T_s_0", "T_s", "h2o_sat"],
        'precip': ["m_pp", "percent_snow", "rho_snow", "T_pp"],
        'mask': ["mask"],
        'dem': ["alt"]
    }

#: Convert number of bytes to struct package code for unsigned integer type
PACK_DICT = \
    {
        1: 'B',
        2: 'H',
        4: 'I'
    }


def isnobal(nc_in=None, nc_out_fname=None, data_tstep=60, nsteps=8758,
            init_img="data/init.ipw", precip_file="data/ppt_desc",
            mask_file="data/tl2p5mask.ipw", input_prefix="data/inputs/in",
            output_frequency=1, em_prefix="data/outputs/em",
            snow_prefix="data/outputs/snow", dt='hours', year=2010,
            month=10, day='01'):
    """ Wrapper for running the ISNOBAL
        (http://cgiss.boisestate.edu/~hpm/software/IPW/man1/isnobal.html)
        model.

        Arguments:
            nc_in (netCDF4.Dataset) Input NetCDF4 dataset. See
                AssertISNOBALInput for requirements.
            nc_out_fname (str) Name of NetCDF file to write to, if desired

            For explanations the rest, see the link above.

        Returns:
            (netCDF4.Dataset) NetCDF Dataset object of the outputs
    """
    if not nc_in:

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

        # TODO sanitize this isnobalcmd or better yet, avoid shell=True
        output = subprocess.check_output(isnobalcmd, shell=True)
        logging.debug("ISNOBAL process output: " + output)

        # create a NetCDF of the outputs and return it
        nc_out = \
            generate_standard_nc(dirname(em_prefix), nc_out_fname,
                                 data_tstep=data_tstep,
                                 output_frequency=output_frequency, dt=dt,
                                 year=year, month=month, day=day)

        return nc_out

    else:

        AssertISNOBALInput(nc_in)

        # these are guaranteed to be present by the above assertion
        data_tstep = nc_in.data_tstep
        nsteps = nc_in.nsteps
        output_frequency = nc_in.output_frequency

        # create standard IPW data in tmpdir; creates tmpdir
        tmpdir = '/tmp/isnobalrun' + \
            str(datetime.datetime.now()).replace(' ', '')

        nc_to_standard_ipw(nc_in, tmpdir)

        mkdir(osjoin(tmpdir, 'outputs'))

        # nc_to_standard_ipw is well tested, we know these will be present
        init_img = osjoin(tmpdir, 'init.ipw')
        precip_file = osjoin(tmpdir, 'ppt_desc')
        mask_file = osjoin(tmpdir, 'mask.ipw')
        input_prefix = osjoin(tmpdir, 'inputs/in')
        em_prefix = osjoin(tmpdir, 'outputs/em')
        snow_prefix = osjoin(tmpdir, 'outputs/snow')

        # recursively run isnobal with nc_in=None
        nc_out = isnobal(data_tstep=data_tstep, nsteps=nsteps,
                         init_img=init_img, precip_file=precip_file,
                         mask_file=mask_file, input_prefix=input_prefix,
                         output_frequency=output_frequency,
                         em_prefix=em_prefix, snow_prefix=snow_prefix)

        rmtree(tmpdir)

        return nc_out


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
    def __init__(self, input_file=None, config_file=None,
                 water_year=None, dt=None, file_type=None):

        assert dt is None or issubclass(type(dt), datetime.timedelta)

        if input_file is not None:

            ipw_lines = IPWLines(input_file)
            input_split = basename(input_file).split('.')

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
                    osjoin(dirname(__file__), '../default.conf')

            # helper function _get_config uses ConfigParser to parse config file
            config = _get_config(config_file)

            if file_type in ['in', 'em', 'snow']:

                # set the water year to default if not given
                if not water_year:
                    water_year = 2010

                # note that we have not generalized for non-hour timestep data
                if dt is None:
                    dt = Timedelta('1 hour')

                # the iSNOBAL file naming scheme puts the integer time step
                # after the dot, really as the extension
                # TODO as Roger pointed out, really this is for
                # a single point in time, so this timing thing is not right
                start_dt = dt * int(input_split[-1])

                start_datetime = \
                    datetime.datetime(water_year, 10, 01) + start_dt

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

        return None

    def recalculate_header(self):
        """
            Recalculate header values
        """
        _recalculate_header(self.nonglobal_bands, self.data_frame())
        for band in self.nonglobal_bands:
            self.header_dict[band.varname] = band

    @classmethod
    def precip_tuple(self, precip_file, sepchar='\t'):
        """Create list of two-lists where each element's elements are the time
           index of the time step when the precipitation happened and an IPW
           of the precipitation data.
        """
        pptlist = map(lambda l: l.strip().split(sepchar),
                      open(precip_file, 'r').readlines())

        return map(lambda l: (l[0], IPW(l[1], file_type='precip')), pptlist)

    @classmethod
    def from_nc(cls, nc_in, tstep=None, group=None, variable=None,
                distance_units='m', coord_sys_ID='UTM'):
        """
        Generate an IPW object from a NetCDF file.

        >>> ipw = IPW.from_nc('dataset.nc', tstep='1', group='Inputs')
        >>> ipw = IPW.from_nc(nc_in)

        If your data uses units of distance other than meters, set that
        with kwarg `distance_units`. Simliar

       Arguments:
            nc_in (str or NetCDF4.Dataset) NetCDF to convert to IPW
            tstep (int) The time step in whatever units are being used
            group (str) Group of NetCDF variable, e.g. 'Precipitation'
            variable (str or list) One or many variable names to be
                incorporated into IPW file
            distance_units (str) If you use a measure of distance other
                than meters, put the units here
            coord_sys_ID (str) Coordinate system being used

        Returns:
            (IPW) IPW instance built from NetCDF inputs
        """
        if type(nc_in) is str:
            nc_in = Dataset(nc_in, 'r')
        # check and get variables from netcdf
        if group is None and variable is None:
            raise Exception("group and variable both 'None': no data to convert!")

        # initialize the IPW and set its some global attributes
        ipw = IPW()

        if group is None:
            if variable == 'alt':
                ipw.file_type = 'dem'
            elif variable == 'mask':
                ipw.file_type = variable

            # this allows same lookup to be used for init or dem/mask
            nc_vars = {variable: nc_in.variables[variable]}

        else:
            nc_vars = nc_in.groups[group].variables  # throw if key `group` dne

            if group == 'Input':
                ipw.file_type = 'in'
            elif group == 'Precipitation':
                ipw.file_type = 'precip'
            elif group == 'Initial':
                ipw.file_type = 'init'

        # read header info from nc and generate/assign to new IPW
        # build global dict
        ipw.byteorder = '0123'  # TODO read from file
        ipw.nlines = len(nc_in.dimensions['northing'])
        ipw.nsamps = len(nc_in.dimensions['easting'])

        # if the bands are not part of a group, they are handled individually
        if group:
            ipw.nbands = len(nc_vars)
        else:
            ipw.nbands = 1

        globalBand = GlobalBand(ipw.byteorder, ipw.nlines,
                                ipw.nsamps, ipw.nbands)

        # build non-global band(s). Can use recalculate_header so no min/max
        # need be set.
        # setting all values common to all bands
        # use 2 bytes/16 bits for floating point values
        bytes_ = NC_NBYTES
        bits_ = NC_NBITS

        bline = nc_in.bline
        dline = nc_in.dline
        bsamp = nc_in.bsamp
        dsamp = nc_in.dsamp

        geo_units = distance_units
        coord_sys_ID = coord_sys_ID

        # iterate over each item in VARNAME_DICT for the filetype, creating
        # a "Band" for each and corresponding entry in the poorly named
        # header_dict
        varnames = VARNAME_DICT[ipw.file_type]
        header_dict = dict(zip(varnames,
                               [Band() for i in range(len(varnames) + 1)]))

        # create a dataframe with nrows = nlines*nsamps and variable colnames
        df_shape = (ipw.nlines*ipw.nsamps, len(varnames))
        df = DataFrame(zeros(df_shape), columns=varnames)
        for idx, var in enumerate(varnames):

            header_dict[var] = Band(varname=var, band_idx=idx, nBytes=bytes_,
                nBits=bits_, int_max=NC_MAXINT, bline=bline, dline=dline,
                bsamp=bsamp, dsamp=dsamp, units=geo_units,
                coord_sys_ID=coord_sys_ID)

            # insert data to each df column
            if tstep is not None:
                data = ravel(nc_vars[var][tstep])
            else:
                data = ravel(nc_vars[var])

            df[var] = data

        ipw._data_frame = df

        ipw.nonglobal_bands = header_dict.values()

        # include global band in header dictionary
        header_dict.update({'global': globalBand})

        ipw.geotransform = [bsamp - dsamp / 2.0,
                            dsamp,
                            0.0,
                            bline - dline / 2.0,
                            0.0,
                            dline]

        ipw.bands = header_dict.values()

        ipw.header_dict = header_dict

        # recalculate headers
        ipw.recalculate_header()

        return ipw

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


def generate_standard_nc(base_dir, nc_out=None, data_tstep=60,
                         output_frequency=1, dt='hours', year=2010, month=10,
                         day='01'):
    """Use the utilities from netcdf.py to convert standard set of either input
       or output files to a NetCDF4 file. A standard set of files means

        for inputs:
            - inputs/ dir with 5/6-band input files named like in.0000, in.0001
            - ppt_desc file with time index of precip file and path to ppt file
            - ppt_images_dist directory with the 4-band files from ppt_desc
            - tl2p5mask.ipw and tl2p5_dem.ipw for mask and DEM images
            - init.ipw 7-band initialization file

        for outputs:
            - an output/ directory with 9-band energy-mass (em) outputs and
              snow outputs in time steps named like em.0000 and snow.0000

        Arguments:
            base_dir (str): base directory of the data
            nc_out (str): path to write data to

        Returns:
            (netCDF4.Dataset) Representation of the data
    """
    if 'outputs' in base_dir.split('/')[-1]:
        ipw_type = 'outputs'

    elif 'inputs' in listdir(base_dir):
        ipw_type = 'inputs'

    else:
        raise IPWFileError("%s does not meet standards" % base_dir)

    if ipw_type == 'inputs':
        input_files = [osjoin(base_dir, 'inputs', el) for el in
                       listdir(osjoin(base_dir, 'inputs'))]

        ipw0 = IPW(input_files[0])
        gt = ipw0.geotransform
        gb = [x for x in ipw0.bands if type(x) is GlobalBand][0]

        # in iSNOBAL speak, literally the number of steps, not number of
        # time index entries
        nsteps = len(input_files) - 1

        template_args = dict(bline=gt[3], bsamp=gt[0], dline=gt[5],
                             dsamp=gt[1], nsamps=gb.nSamps, nlines=gb.nLines,
                             data_tstep=data_tstep, nsteps=nsteps,
                             output_frequency=output_frequency, dt=dt,
                             year=year, month=month, day=day)

        # initialize the nc file
        nc = ncgen_from_template('ipw_in_template.cdl', nc_out, clobber=True,
                                 **template_args)

        # first take care of non-precip files
        print "Inserting 'Input' data"
        with ProgressBar(maxval=len(input_files)) as progress:
            for i, f in enumerate(input_files):
                ipw = IPW(f)
                tstep = int(basename(ipw.input_file).split('.')[-1])
                _nc_insert_ipw(nc, ipw, tstep, gb.nLines, gb.nSamps)

                progress.update(i)

        dem = IPW(osjoin(base_dir, 'tl2p5_dem.ipw'), file_type='dem')
        mask = IPW(osjoin(base_dir, 'tl2p5mask.ipw'), file_type='mask')
        init = IPW(osjoin(base_dir, 'init.ipw'))

        for el in [mask, dem, init]:
            _nc_insert_ipw(nc, el, None, gb.nLines, gb.nSamps)

        # read ppt_desc file and insert to nc with appropriate time step
        ppt_pairs = [ppt_line.strip().split('\t')
                     for ppt_line in
                     open(osjoin(base_dir, 'ppt_desc'), 'r').readlines()]

        print "Inserting Precip Data"
        with ProgressBar(maxval=len(ppt_pairs)) as progress:
            for i, ppt_pair in enumerate(ppt_pairs):
                tstep = int(ppt_pair[0])
                el = IPW(ppt_pair[1], file_type='precip')

                _nc_insert_ipw(nc, el, tstep, gb.nLines, gb.nSamps)

                progress.update(i)

    else:

        output_files = [osjoin(base_dir, el) for el in listdir(base_dir)]
        ipw0 = IPW(output_files[0])
        gt = ipw0.geotransform
        gb = [x for x in ipw0.bands if type(x) is GlobalBand][0]

        nsteps = len(output_files)

        template_args = dict(bline=gt[3], bsamp=gt[0], dline=gt[5],
                             dsamp=gt[1], nsamps=gb.nSamps, nlines=gb.nLines,
                             data_tstep=data_tstep, nsteps=nsteps,
                             output_frequency=output_frequency, dt=dt,
                             year=year, month=month, day=day)

        # initialize nc file
        nc = ncgen_from_template('ipw_out_template.cdl', nc_out, clobber=True,
                                 **template_args)

        print "Inserting Output Data"
        with ProgressBar(maxval=len(output_files)) as progress:
            for i, f in enumerate(output_files):
                ipw = IPW(f)
                tstep = int(basename(ipw.input_file).split('.')[-1])
                _nc_insert_ipw(nc, ipw, tstep, gb.nLines, gb.nSamps)

                progress.update(i)

    # import ipdb; ipdb.set_trace()
    # whether inputs or outputs, we need to include the dimensional values
    t = nc.variables['time']
    t[:] = arange(len(t))

    e = nc.variables['easting']
    # eastings are "samples" in IPW
    nsamps = len(e)
    e[:] = array([nc.bsamp + nc.dsamp*i for i in range(nsamps)])

    n = nc.variables['northing']
    # northings are "lines" in IPW
    nlines = len(n)
    n[:] = array([nc.bline + nc.dline*i for i in range(nlines)])

    # get a n_points x 2 array of lat/lon pairs at every point on the grid
    latlon_arr = utm2latlon(nc.bsamp, nc.bline, nc.dsamp,
                            nc.dline, nsamps, nlines)

    # break this out into lat and lon separately at each point on the grid
    lat = nc.variables['lat']
    lat[:] = reshape(latlon_arr[:, 0], (nlines, nsamps))

    # break this out into lat and lon separately at each point on the grid
    lon = nc.variables['lon']
    lon[:] = reshape(latlon_arr[:, 1], (nlines, nsamps))

    # finish setting attributes
    nc.data_tstep = data_tstep

    nc.nsteps = len(t)

    nc.sync()

    return nc


def _nc_insert_ipw(dataset, ipw, tstep, nlines, nsamps):
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
        dataset.variables['alt'][:, :] = reshape(df['alt'],
                                                    (nlines, nsamps))

    elif file_type == 'in':
        gvars = dataset.groups['Input'].variables
        for var in gvars:
            # can't just assign b/c if sun is 'down' var is absent from df
            if var in df.columns:
                gvars[var][tstep, :, :] = reshape(df[var],
                                                     (nlines, nsamps))
            else:
                gvars[var][tstep, :, :] = zeros((nlines, nsamps))

    elif file_type == 'precip':
        gvars = dataset.groups['Precipitation'].variables

        for var in gvars:
            gvars[var][tstep, :, :] = reshape(df[var], (nlines, nsamps))

    elif file_type == 'mask':
        # mask is binary and one-banded; store in root group
        dataset.variables['mask'][:, :] = reshape(df['mask'],
                                                     (nlines, nsamps))

    elif file_type == 'init':
        gvars = dataset.groups['Initial'].variables

        for var in gvars:
            gvars[var][:, :] = reshape(df[var], (nlines, nsamps))

    elif file_type == 'em':
        gvars = dataset.groups['em'].variables

        for var in gvars:
            gvars[var][tstep, :, :] = reshape(df[var], (nlines, nsamps))

    elif file_type == 'snow':
        gvars = dataset.groups['snow'].variables

        for var in gvars:
            gvars[var][tstep, :, :] = reshape(df[var], (nlines, nsamps))

    # TODO file_type == "em" and "snow" for outputs

    else:
        raise Exception('File type %s not recognized!' % file_type)


def nc_to_standard_ipw(nc_in, ipw_base_dir, clobber=True):
    """Convert an iSNOBAL NetCDF file to an iSNOBAL standard directory structure
       in IPW format. This means that for

        input nc: all inputs are all in {ipw_base_dir}/inputs and all precip
            files are in {ipw_base_dir}/ppt_images_dist. There is a precip
            description file {ipw_base_dir}/ppt_desc describing what time index
            each precipitation file corresponsds to and the path to the precip
            file in ppt_images_dist. There are three more files, the mask, init,
            and DEM files at {ipw_base_dir}/ tl2p5mask.ipw, tl2p5_dem.ipw, and
            init.ipw

        output nc: files get output to {ipw_base_dir}/outputs to allow for
            building a directory of both inputs and outputs. Files are like
            em.0000 and snow.0000 for energy-mass and snow outputs, respectively.

        Arguments:
            nc_in (str) path to input NetCDF file to break out
            ipw_base_dir

        Returns:
            None
    """
    if type(nc_in) is str:
        nc_in = Dataset(nc_in, 'r')
    else:
        assert isinstance(nc_in, Dataset)

    nc_groups = nc_in.groups.keys()
    if 'Input' in nc_groups:
        type_ = 'inputs'
    elif 'Output' in nc_groups:
        type_ = 'outputs'
    else:
        raise IPWFileError("NetCDF %s is not a valid iSNOBAL representation"
                           % nc_in)

    assert set(nc_in.groups.keys()) == \
        set([u'Initial', u'Precipitation', u'Input']), \
        "%s not a valid input iSNOBAL NetCDF" % nc_in.filepath()

    assert set(nc_in.variables.keys()) == \
        set([u'time', u'easting', u'northing', u'lat', u'lon',
             u'alt', u'mask']), \
        "%s not a valid input iSNOBAL NetCDF" % nc_in.filepath()

    if clobber and exists(ipw_base_dir):
        rmtree(ipw_base_dir)
    elif exists(ipw_base_dir):
        raise IPWFileError("clobber=False and %s exists" % ipw_base_dir)
    mkdir(ipw_base_dir)

    time_index = range(len(nc_in.variables['time']))

    if type_ == 'inputs':

        # for each time step create an IPW file
        group = 'Input'
        inputs_dir = osjoin(ipw_base_dir, 'inputs')
        mkdir(inputs_dir)

        tsteps = len(time_index)

        zeropad_factor = floor(log10(tsteps))

        print "Writing 'Input' Data to IPW files"
        with ProgressBar(maxval=time_index[-1]) as progress:
            for i, idx in enumerate(time_index):
                if idx < 10:
                    idxstr = "0"*zeropad_factor + str(idx)
                elif idx < 100:
                    idxstr = "0"*(zeropad_factor - 1) + str(idx)
                elif idx < 1000:
                    idxstr = "0"*(zeropad_factor - 2) + str(idx)
                else:
                    idxstr = str(idx)

                IPW.from_nc(nc_in, tstep=idx, group=group
                            ).write(osjoin(inputs_dir, 'in.' + idxstr))

                progress.update(i)

        group = 'Initial'
        IPW.from_nc(nc_in, group=group
                    ).write(osjoin(ipw_base_dir, 'init.ipw'))

        IPW.from_nc(nc_in, variable='alt'
                    ).write(osjoin(ipw_base_dir, 'dem.ipw'))

        IPW.from_nc(nc_in, variable='mask'
                    ).write(osjoin(ipw_base_dir, 'mask.ipw'))

        # precip is weird. for no precip tsteps, no IPW exists
        # list of tsteps that had precip and associated
        # files stored in ppt_desc
        group = 'Precipitation'
        ppt_images_dir = osjoin(ipw_base_dir, 'ppt_images_dist')
        mkdir(ppt_images_dir)

        # can use just one variable (precip mass) to see which
        mpp = nc_in.groups[group].variables['m_pp']

        # if no precip at a tstep, variable type is numpy.ma.core.MaskedArray
        time_indexes = [i for i, el in enumerate(mpp)
                        if not isinstance(el, MaskedArray)]

        # this should be mostly right except for ppt_desc and ppt data dir
        print "Writing 'Precipitation' Data to IPW files"
        with open(osjoin(ipw_base_dir, 'ppt_desc'), 'w') as ppt_desc:

            with ProgressBar(maxval=len(time_indexes)) as progress:

                for i, idx in enumerate(time_indexes):
                    ppt_desc.write("%s\t%s\n" % (idx,
                                   osjoin(ppt_images_dir,
                                          'ppt_' + str(idx) + '.ipw')))

                    ipw = IPW.from_nc(nc_in, tstep=idx, group=group)

                    ipw.write(osjoin(ppt_images_dir,
                                     'ppt_' + str(idx) + '.ipw'))

                    progress.update(i)

    else:
        raise Exception("NetCDF to IPW converter not implemented for type %s" %
                        type_)


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


def reaggregate_ipws(ipws, fun=npsum, freq='H', rule='D'):
    """
    Resample IPWs using the function fun, but only sum is supported.
    `freq` corresponds to the actual frequency of the ipws; rule corresponds to
    one of the resampling 'rules' given here:
    http://pandas.pydata.org/pandas-docs/dev/timeseries.html#time-date-components
    """
    assert fun is npsum, "Cannot use " + fun.func_name + \
        ", only sum has been implemented"

    assert _is_consecutive(ipws)

    ipw0 = ipws[0]
    start_datetime = ipw0.start_datetime

    idx = date_range(start=start_datetime, periods=len(ipws), freq=freq)

    series = Series(map(lambda ipw: ipw.data_frame(), ipws), index=idx)

    resampled = series.resample(rule, how=npsum)
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

    intData = fromstring(binary_data, dtype=dtype)

    df = DataFrame(intData, columns=colnames)

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
    floatRange = band.float_max - band.float_min

    return integerValue * (floatRange / band.int_max) + band.float_min


def _bands_to_dtype(bands):
    """
    Given a list of Bands, convert them to a numpy.dtype for use in creating
    the IPW dataframe.
    """
    return dtype([(b.varname, 'uint' + str(b.bytes_ * 8)) for b in bands])


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
    int_df = DataFrame(dtype='uint64')

    for b in sorted(bands, key=lambda b: b.band_idx):
        # check that bands are appropriately made, that b.Max/Min really are
        assert df[b.varname].le(b.float_max).all(), \
            "Bad band: max not really max.\nb.float_max = %2.10f\n \
            df[b.varname].max()  = %s" % (b.float_max, df[b.varname].max())

        assert df[b.varname].ge(b.float_min).all(), \
            "Bad band: min not really min.\nb.float_min = %s\n \
            df[b.varname].min()  = %2.10f" % (b.float_min, df[b.varname].min())

        # no need to include b.int_min, it's always zero
        map_fn = lambda x: \
            floor(npround(
                ((x - b.float_min) * b.int_max)/(b.float_max - b.float_min)))

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
    assert set(list(dataframe.columns)) == set([b.varname for b in bands]), \
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


class ISNOBALNetcdfError(Exception):
    pass
