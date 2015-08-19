"""
Ingestion and access routines for working with the ISU gridding tools.

Author: Matthew Turner
Date: 8/7/2015
"""
import gdal
import glob
import os.path

from numpy import array, full, ones
from numpy.random import randn
from os import mkdir
from pandas import to_datetime
from uuid import uuid4
from xray import Dataset
from zipfile import ZipFile

from .isnobal import AssertISNOBALInput, VARNAME_BY_FILETYPE
from .netcdf import utm2latlon

def create_isnobal_dataset(tif_zip, unzip_dir=None):
    """
    Public function to create an isnobal dataset from a tif zip file returned
    by the ISU Gridding Tool.

    Arguments:
        tif_zip (str): path to the geotiff zip file
        unzip_dir (str): where the tifs should go. if None, a temp dir is created

    Returns:
        (xray.Dataset) loaded with input (init, precip, in) required to run
        iSNOBAL
    """
    # create temp directory if no unzip dir is specified
    if not unzip_dir:
        if not os.path.exists('.tmp'):
            mkdir('.tmp')

        unzip_dir = os.path.join('.tmp', str(uuid4()))

    _unzip_geotiffs(tif_zip, unzip_dir)

    return _create_isnobal_nc_from_dir(unzip_dir)


def _unzip_geotiffs(tif_zip, unzip_dir):
    """Private function to unzip all '*.tif' in tif_zip to unzip_dir
    """
    zf = ZipFile(tif_zip)

    for zi in zf.infolist():
        if os.path.splitext(zi.filename)[-1] == '.tif':
            zf.extract(zi, unzip_dir)


def _create_isnobal_nc_from_dir(tif_dir):
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
    # XXX temporary fix until ISU fixes varied gridding size
    n_northings = 1689
    n_eastings = 1120
    # n_northings = tif0.RasterXSize
    # n_eastings = tif0.RasterYSize

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

    # build datetimes array; t_a is present for every input; use that
    all_ta = glob.glob(os.path.join(tif_dir, 'T_a*'))

    _get_timestamp = \
        lambda tif_path: tif_path.split('_')[-1].replace('.tif', '')

    time_index = to_datetime(map(_get_timestamp, all_ta)).order()
    n_timesteps = len(time_index)

    vardict = VARNAME_BY_FILETYPE

    coords = {'easting': easting_vec, 'northing': northing_vec,
              'time': time_index, 'reference_time': time_index[0]}

    dataset = Dataset(coords=coords)

    # add some additional stuff
    # XXX fake elevation until ISU gives me elevation
    alt = 1000 + randn(n_eastings, n_northings)*50

    # all points are being used, so all mask values are 1
    mask = ones((n_eastings, n_northings))

    # insert lon, lat, alt
    lon = lon_vec.reshape((n_eastings, n_northings))
    lat = lat_vec.reshape((n_eastings, n_northings))
    dataset.update(Dataset(
        {
            'lon': (['easting', 'northing'], lon),
            'lat': (['easting', 'northing'], lat),
            'mask': (['easting', 'northing'], mask),
            'alt': (['easting', 'northing'], alt)
        }, coords=coords))

    # initialize 3D input and precipitation variables
    for varname in (vardict['in'] + vardict['precip']):

        # initialize the variable
        data = full((n_timesteps, n_eastings, n_northings), -9999.)

        # glob on that variable name
        glb = glob.glob(os.path.join(tif_dir, varname + '*'))

        for g in glb:
            # use extract timestamp off end of file
            timestamp = g.split('_')[-1].replace('.tif', '')
            # get index of the tif based on date lookup
            tif_idx = time_index.get_loc(timestamp)

            tif = gdal.Open(g)

            # XXX remove this once Joel fixes the grid size issue
            cur_n_northings = tif.RasterXSize
            cur_n_eastings = tif.RasterYSize

            tif_array = tif.GetRasterBand(1).ReadAsArray()
            tif_array[tif_array < -1e30] = 0.0
            # XXX when bug in grid size is fixed,
            data[tif_idx, :cur_n_eastings, :cur_n_northings] = tif_array
            # data[tif_idx] = tif.GetRasterBand(1).ReadAsArray()

            dataset.update(Dataset({varname: (['time', 'easting', 'northing'],
                                              data)},
                           coords=coords))

    # XXX generate fake random wind speeds until ISU provides
    wind_speed = abs(10*randn(n_timesteps, n_eastings, n_northings))

    dataset.update(Dataset({'u': (['time', 'easting', 'northing'],
                                  wind_speed)},
                           coords=coords)
                   )

    # initialize 2D init image
    init_varnames = vardict['init']
    for varname in init_varnames:

        min_datetime = time_index[0]
        min_timestamp = min_datetime.isoformat()

        # glob on that variable name
        glob_path = os.path.join(tif_dir,
                                 varname + '_' + min_timestamp + '.tif')

        glb = glob.glob(glob_path)

        assert len(glb) == 1, \
            "There are more than one timestep's worth of init data " \
            "in the zip file:\nvariable:{}\nglob:{}".format(varname, glb)

        # initialize the variable
        data = full((n_eastings, n_northings), -9999.)

        tif = gdal.Open(glb[0])

        # XXX remove this once Joel fixes the grid size issue
        cur_n_northings = tif.RasterXSize
        cur_n_eastings = tif.RasterYSize

        tif_array = tif.GetRasterBand(1).ReadAsArray()
        tif_array[tif_array < -1e30] = 0.0

        data[:cur_n_eastings, :cur_n_northings] = tif_array

        dataset.update(Dataset({varname: (['easting', 'northing'], data)},
                       coords=coords))

    dataset.attrs.update({
        'nsteps': n_timesteps,
        'data_tstep': 60,  # time interval between inputs in _minutes_
        'output_frequency': 1,
        'bline': northing,
        'bsamp': easting,
        'dline': d_northing,
        'dsamp': d_easting
    })

    AssertISNOBALInput(dataset)

    return dataset
