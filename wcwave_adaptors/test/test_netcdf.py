"""Tests of NetCDF functionality including enforcement of CF standards,
   metadata gleaning, CF-Station data conversion, and maybe more, like opendap.
"""

import unittest

# from wcwave_adaptors.netcdf import *
from ..netcdf import isCF


class TestNetCDF(unittest.TestCase):
    """Unittests for NetCDF Adaptor Functionality
    """

    def setUp(self):
        pass

    def test_cf_enforcement(self):
        "Check CF standard breaking and meeting are properly detected"
        assert False

    def test_station_conversion(self):
        "Properly convert compliant weather station csv to NetCDF Dataset"
        assert False
