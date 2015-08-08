"""
Ingestion and access routines for working with the ISU gridding tools.

Author: Matthew Turner
Date: 8/7/2015
"""
import gdal
import os.path

from numpy import array
from os import mkdir
from uuid import uuid4
from xray import Dataset
from zipfile import ZipFile


def extract_band(tif_path):
    """
    Convert a tif on disk to a numpy array.

    Arguments:
        tif_path (str): path to geotiff

    Returns:
        (numpy.array) With shape equal to raster shape
    """
    tif = gdal.Open(tif_path)
    return array(tif.GetRasterBand(1).ReadAsArray())


def _insert_band(band_name, band_array, dataset):
    """
    insert a band into xray dataset
    """
    pass


PLACEHOLDER_LAT = 40.5
PLACEHOLDER_DLAT = 0.25
PLACEHOLDER_LON = -120.0
PLACEHOLDER_DLON = 0.5


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
            os.mkdir('.tmp')

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

    Arguments:
        tif_dir (str): path to directory where geotiffs are stored

    Returns:
        (xray.Dataset): NetCDF representation of isnobal inputs
    """
    # ## get date range of geotiffs contained in tif_dir
    # # read all dates into set from directory
    # datetimes = _get_date_set(tif_dir)

    # # get max/min of those array dates
    # max_datetime = datetimes.max()
    # min_datetime = datetimes.min()

    # # initialize dataset dimensions
    # dataset = _initialize_isnobal_dataset(tif_dir)

    # _insert_in_rasters(dataset)

    # _insert_init_rasters(dataset)

    # _insert_precip_rasters(dataset)

    # # confirm netcdf is an isnobal-ready netcdf (TODO in isnobal check,
    # # also check for empty variables)
    # AssertISNOBALInput(dataset)

    # return dataset
    pass

def _initialize_isnobal_dataset(tif_dir):
    """
    Initialize an input netcdf that's ready for netcdf variables
    """
    pass

def _insert_in_rasters(dataset):
    """

    """
    pass

def _insert_init_rasters(dataset):
    """

    """
    pass

def _insert_precip_rasters(dataset):
    """

    """
    pass

def _get_date_set(tif_dir):
    """
    Return a set of dates that the geotiffs cover
    """
    pass
