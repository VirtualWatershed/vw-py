"""
Tests for posting/ingetsting dflow and casimir data to each respective model
to/from the virtual watershed.
"""
import unittest

from nose.tools import eq_

from wcwave_adaptors.dflow_casimir import Ascii, asc_veg_to_nvals


class TestDflow(unittest.TestCase):
    """
    Functions for working with DFLOW inputs and outputs
    """
    def setUp(self):
        self.ascii_veg = 'wcwave_adaptors/test/data/ascii_veg.asc'
        self.excel_veg_to_nval = \
            'wcwave_adaptors/test/data/excel_veg_to_nval.xls'
        pass

    def test_asc_veg_to_nvals(self):
        "Properly build nvals ESRI .asc from vegetation code .asc and lookup table"
        ascii_nvals = asc_veg_to_nvals(self.ascii_veg, self.excel_veg_to_nval)
        expected_ascii_nvals = \
            Ascii('wcwave_adaptors/test/data/expected_ascii_nvals.asc')

        eq_(ascii_nvals, expected_ascii_nvals)

    def test_unstruc_mesh_to_ascii(self):
        assert False
