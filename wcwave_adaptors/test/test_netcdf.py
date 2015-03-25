"""Tests of NetCDF functionality including enforcement of CF standards,
   metadata gleaning, CF-Station data conversion, and maybe more, like opendap.
"""

import os
import unittest
from nose.tools import raises

from wcwave_adaptors.netcdf import utm2latlon, ncgen_from_template
# include tests for isnobal2netcdf in this module
from wcwave_adaptors.isnobal import isnobal2netcdf


class TestIsnobalNetCDF(unittest.TestCase):
    """Unittests for NetCDF Adaptor Functionality
    """
    def setUp(self):
        test_dir = os.path.join(os.path.dirname(__file__), 'data')

        input_data_sources = ['inputs', 'ppt_desc', 'init.ipw',
                              'tl2p5_dem.ipw', 'tl2p5mask.ipw']

        self.input_data_sources = map(lambda x: os.path.join(test_dir, x),
                                      input_data_sources)

        self.output_data_source = os.path.join(test_dir, 'outputs')

    @raises(AssertionError)
    def test_isnobal_inputs_or_outputs(self):
        "isnobal2netcdf raises error if the isnobal type is not 'input' or 'output'"
        assert True

    def test_isnobal2netcdf_inputs(self):
        "Check that a sample NetCDF is properly built from a series of inputs"

        assert False

    def test_isnobal2netcdf_outputs(self):
        "Check that a sample NetCDF is properly built from a series of outputs"
        assert False


class TestNetCDF(unittest.TestCase):
    """Unittests for NetCDF Adaptor Functionality
    """

    def setUp(self):
        self.cdl_build_path = 'wcwave_adaptors/test/test_cdl_path.cdl'
        self.nc_out_path = 'wcwave_adaptors/test/test_nc_from_template.nc'

    def test_utm_latlon_conversion(self):
        "check utm to latlon conversion of Dry Creek actually maps there"
        # bbox corners from upper left clockwise around
        east0 = 569029.6
        east1 = 569452.1
        north0 = 4842544.9
        north1 = 4842177.4

        utm_zone = 11
        utm_letter = 'T'

        latlons = utm2latlon(bsamp=east0, bline=north0, dsamp=east1-east0,
                             dline=north1-north0, nsamp=2, nline=2,
                             utm_zone=utm_zone, utm_letter=utm_letter)

        from utm import to_latlon
        ll0 = to_latlon(east0, north0, utm_zone, utm_letter)
        ll1 = to_latlon(east1, north0, utm_zone, utm_letter)
        ll2 = to_latlon(east1, north1, utm_zone, utm_letter)
        ll3 = to_latlon(east0, north1, utm_zone, utm_letter)

        assert (ll0 == latlons[0]).all
        assert (ll1 == latlons[1]).all
        assert (ll2 == latlons[2]).all
        assert (ll3 == latlons[3]).all

    def test_ncgen(self):
        "CDL is generated from template and arguments and can build a valid NetCDF using `ncgen`"

        # ncgen for iSNOBAL
        template_path = 'ipw_in_template.cdl'

        template_args = dict(bline=100, bsamp=10, dline=1.0, dsamp=-1.0,
                             nlines=50, nsamps=10, dt=1, year=2010, month=10,
                             day="01")

        nc = ncgen_from_template(template_path, self.nc_out_path,
                                 cdl_output_filename=self.cdl_build_path,
                                 **template_args)

        assert os.path.exists(self.cdl_build_path), \
            "CDL template did not get built!"

        assert os.path.exists(self.cdl_build_path), \
            "NetCDF did not get built!"

        assert nc, "NetCDF Python Dataset representation is None!"

    def tearDown(self):
        if os.path.exists(self.cdl_build_path):
            os.remove(self.cdl_build_path)

        if os.path.exists(self.nc_out_path):
            os.remove(self.nc_out_path)
