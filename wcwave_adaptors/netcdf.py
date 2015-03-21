"""

"""
import utm
import numpy as np
import netCDF4 as nc


def ipwfile2netcdf(ipw_filename, ipw_type=None, netcdf=None):
    """Convert or append an
       `IPW iSNOBAL file <http://cgiss.boisestate.edu/~hpm/software/IPW/man1/isnobal.html>`_
       to a NetCDF file.

       Args:
        ipw_filename (str) name of IPW file to convert to netcdf
        ipw_type (str) one of init, mask, dem, ppt, in, em, or snow. Corresponds
            to the iSNOBAL types of file inputs
        netcdf (netCDF4.Dataset)

    """
    if not netcdf:
        netcdf = _from_ipw_init()

    # else:
        # validate_ipw_netcdf(netcdf)

    ipw = IPW(ipw_filename)

    if not ipw_type:
        ipw_type = 'in'

    for var_label in VARNAME_DICT[ipw_type]:
        # dem and mask images are time-independent
        if ipw_type in ['dem', 'mask']:
            var = netcdf.createVariable(var_label, np.float32, ('lat', 'lon'))
            var[:] = ipw[var_label]

        else:
            var = netcdf.createVariable(var_label, np.float32,
                                        ('time', 'lat', 'lon'))

            var[:, :, :] = np.reshape(ipw[var_label],
                                      (1, (ipw.nsamps, ipw.nlines)))


def _from_ipw_init(start_time='2012-10-01 00:00:00', nc_filename=None, latlon_coords=None):
    """Create a NetCDF that is CF-compliant and has all necessary dimensions for
       ingesting an IPW file.

        Returns:
            (netCDF4.Dataset) Dataset initialized with time, lat, and lon
                              variables. Lat and lon filled in using
    """
    nc_filename = nc_filename or 'new.nc'

    netcdf = nc.Dataset(nc_filename, mode='wr', format='NETCDF4')

    # time
    time_dim = netcdf.createDimension('time', None)
    time = ncfile.createVariable('time', np.float64, ('time',))
    time.units = 'hours since ' + start_time
    time.long_name = 'time'

    lat_dim = netcdf.createDimension('lat', len(latlon_coords))
    lon_dim = netcdf.createDimension('lon', len(latlon_coords))

    lat = netcdf.createVariable('lat', np.float32, ('lat',))
    lon = netcdf.createVariable('lon', np.float32, ('lon',))

    if latlon_coords:
        assert type(latlon_coords) is np.ndarray, \
            "latlon_coords must be an np.ndarray"

        lat[:] = latlon_coords[:, 0]
        lon[:] = latlon_coords[:, 1]

    return netcdf


def append_ipw_dem(ipw_dem, netcdf):
    """Append an IPW dem to an existing netcdf file. Overwrites if one is
       already present.

    """
    alt = netcdf.createDimension('alt', np.float32, ('lat', 'lon'))
    alt.standard_name = 'height'
    alt.long_name = 'vertical distance above the surface'
    alt.units = 'm'
    alt.positive = 'up'
    alt.axis = 'Z'



def make_latlon(bsamp=None, bline=None, dsamp=None, dline=None,
                nsamp=None, nline=None):
    """
    Create latitude and longitude variables based on the bline and bsamp
    variables given.

        Returns:
            2 x (nline * nsamp) array of lat/lon coordinates
    """
    lines = [bline + dline*i for i in range(nline)]
    samps = [bsamp + dsamp*i for i in range(nsamp)]

    latlon_arr = [utm.to_latlon(s, l, 11, 'U') for s in samps for l in lines]

    return np.array(latlon_arr)

