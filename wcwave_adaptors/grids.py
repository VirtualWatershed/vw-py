"""
Ingestion and access routines for working with the ISU gridding tools.

Author: Matthew Turner
Date: 9/30/2015
"""
import gdal
import glob
import os.path
import re
import warnings

from datetime import datetime
from numpy import array
from os import mkdir
from pandas import to_datetime
from uuid import uuid4

from zipfile import ZipFile

from .isnobal import AssertISNOBALInput, ncgen_from_template
from .netcdf import utm2latlon


def create_isnobal_dataset(tif_zip, unzip_dir=None, nc_out=None):
    """
    Public function to create an isnobal dataset from a tif zip file returned
    by the ISU Gridding Tool.

    Arguments:
        tif_zip (str): path to the geotiff zip file
        unzip_dir (str): where the tifs should go. if None, a temp dir is created

    Returns:
        (netCDF4.Dataset) loaded with input (init, precip, in) required to run
        iSNOBAL
    """
    # create temp directory if no unzip dir is specified
    if not unzip_dir:
        if not os.path.exists('.tmp'):
            mkdir('.tmp')

        unzip_dir = os.path.join('.tmp', str(uuid4()))

    _unzip_geotiffs(tif_zip, unzip_dir)

    return _create_isnobal_nc_from_dir(unzip_dir, nc_out=nc_out)


def _unzip_geotiffs(tif_zip, unzip_dir):
    """Private function to unzip all '*.tif' in tif_zip to unzip_dir
    """
    zf = ZipFile(tif_zip)

    for zi in zf.infolist():
        if os.path.splitext(zi.filename)[-1] == '.tif':
            zf.extract(zi, unzip_dir)

INIT_LOOKUP = dict(
    z_0='roughness_length',
    rho='snow_density',
    T_s_0='active_snow_layer_temperature',
    T_s='average_snow_cover_temperature',
    h2o_sat='H2O_saturation'
)

CLIMATE_LOOKUP = dict(
    # iSNOBAL 'in' non-precip variables
    I_lw='thermal_radiation',
    T_a='air_temperature',
    e_a='vapor_pressure',
    u='wind_speed',
    T_g='soil_temperature',
    S_n='solar_radiation',

    # precipitation
    m_pp='precipitation_mass',
    percent_snow='percent_snow',
    rho_snow='precipitation_snow_density',
    T_pp='dew_point_temperature'
)


def _create_isnobal_nc_from_dir(tif_dir, data_tstep=60, output_frequency=1,
                                dt=1, nc_out=None):
    """
    After the zip file has been unzipped, this function parses the filenames
    and data in the `tif_dir`. Each geotiff in the file corresponds to a
    specific variable and timestep. We construct an xray Dataset in four parts:
    1) initialize the space and time coordinates and variables
    2) insert data in the matching variable and timestep

    Ideally new memory doesn't have to be allotted every time a variable/time
    is inserted if the dataset is initialized with full dimensionality ahead
    of time.

    Arguments:
        tif_dir (str): path to directory where geotiffs are stored

    Returns:
        (xray.Dataset): NetCDF representation of isnobal inputs
    """
    # extract geo information from one raster; assume (TODO check) it matches
    tifs = glob.glob(os.path.join(tif_dir, '*'))
    tif0 = gdal.Open(tifs[0])

    # build easting and northing vectors
    n_northings = tif0.RasterXSize
    n_eastings = tif0.RasterYSize

    geotransform = tif0.GetGeoTransform()
    easting = geotransform[0]
    d_easting = geotransform[1]
    northing = geotransform[3]
    d_northing = geotransform[5]

    easting_vec = array([easting + d_easting*i for i in range(n_eastings)])
    northing_vec = array([northing + d_northing*i for i in range(n_northings)])

    # get a n_points x 2 array of lat/lon pairs at every point on the grid
    latlon_arr = utm2latlon(easting, northing, d_easting,
                            d_northing, n_eastings, n_northings)

    lat_vec = latlon_arr[:, 0].squeeze()
    lon_vec = latlon_arr[:, 1].squeeze()

    # build datetimes array using air temp, which is present for every input
    all_ta = glob.glob(os.path.join(tif_dir, 'air_temperature*'))

    time_index = to_datetime(map(_read_timestamp, all_ta)).order()
    n_timesteps = len(time_index)
    earliest_time = time_index[0]

    print n_timesteps

    # initialize netCDF
    template_args = dict(bline=easting, bsamp=northing, dline=d_easting,
                         dsamp=d_northing, nsamps=n_eastings,
                         nlines=n_northings, data_tstep=data_tstep,
                         nsteps=n_timesteps, output_frequency=output_frequency,
                         dt=dt,
                         year=earliest_time.year,
                         month=earliest_time.month,
                         day=earliest_time.day,
                         hour=earliest_time.hour)

    nc = ncgen_from_template(
        'ipw_in_template.cdl', nc_out, clobber=True, **template_args
    )

    # build coordinates
    nc['northing'][:] = northing_vec
    nc['easting'][:] = easting_vec
    nc['lat'][:] = lat_vec.reshape((n_northings, n_eastings))
    nc['lon'][:] = lon_vec.reshape((n_northings, n_eastings))

    # insert time-independent initialization bands
    # XXX set initial snow depth to zero
    nc['z_s'][:] = 0.0

    for k, v in INIT_LOOKUP.iteritems():

        f = glob.glob(tif_dir + '/*' + v + '*')
        # assert len(f) == 1, "there should be only one timestep of init vars" +\
        if len(f) != 1:
            warnings.warn("there should be only one timestep of init vars" +
                          "there are {} for variable {}".format(len(f), k))

        gdl_tif = gdal.Open(f.pop())
        rb = gdl_tif.GetRasterBand(1)
        arr = rb.ReadAsArray()
        nc[k][:] = arr

    # insert time-dependent non-precip input bands
    for k, v in CLIMATE_LOOKUP.iteritems():
        file_list = glob.glob(tif_dir + '/*' + v + '*')
        for f in file_list:
            # extract date from path and insert in proper output nc location
            dtime = _read_timestamp(f)
            i_nc = time_index.get_loc(dtime)

            gdl_tif = gdal.Open(f)
            rb = gdl_tif.GetRasterBand(1)
            nc[k][i_nc, :] = rb.ReadAsArray()

    AssertISNOBALInput(nc)

    return nc


DATE_REGEX = re.compile('[0-9]{8}_[0-9]{2}')


def _read_timestamp(tif_path):
    """
    Parse the ISU timestamp formatted as %Y%m%d_%H
    https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior

    Returns:
        (datetime.datetime)
    """
    tif_datestr = re.search(DATE_REGEX, tif_path).group()

    tif_datetime = datetime.strptime(tif_datestr, '%Y%m%d_%H')

    return tif_datetime
