"""
Tests for the isnobal_adaptor module
"""

import unittest

import numpy.testing as npt
import numpy as np

from adaptors.src.isnobal_adaptor import VARNAME_DICT, _make_bands, \
    GlobalBand, Band, _calc_float_value, _bands_to_dtype


class TestHeaderParser(unittest.TestCase):
    """
    Test the creation of the header dictionary to be used as a member of the
    IPW class.
    """
    def setUp(self):

        # mirrors what is done in class IPWLines
        # there are five bands in this one, so we'll get to test handling of
        # the "sun-down" number of bands. There is one more in daylight hours
        with open('src/test/data/in.00', 'rb') as f:
            lines = f.readlines()

        self.headerLines = lines[:-1]

        self.headerDict = \
            _make_bands(self.headerLines, VARNAME_DICT['in'])

    def test_header_dict(self):
        """
        Check that header lines are properly built into a dictionary
        """
        expectedHeaderDict = \
            {
                'global': GlobalBand(148, 170, 5),
                'I_lw': Band('I_lw', 1, 8, 0, 255, 0, 500),
                'T_a': Band('T_a', 1, 8, 0, 255, 22.39999962, 23.39999962),
                'e_a': Band('e_a', 2, 16, 0, 65535, 468.7428284, 469.7428284),
                'u': Band('u', 2, 16, 0, 65535, 0.8422899842, 1.842289925),
                'T_g': Band('T_g', 1, 8, 0, 255, 0, 1)
            }

        headerDict =\
            self.headerDict

        i = 0
        for variable, expectedBand in expectedHeaderDict.iteritems():

            genBand = headerDict[variable]

            if variable == 'global':
                assert genBand.nLines is not None
                assert genBand.nSamps is not None
                assert genBand.nBands is not None

                assert genBand.nLines == expectedBand.nLines
                assert genBand.nSamps == expectedBand.nSamps
                assert genBand.nBands == expectedBand.nBands

            else:
                assert genBand.varname is not None
                assert genBand.bytes_ is not None
                assert genBand.bits_ is not None
                assert genBand.intMin is not None
                assert genBand.intMax is not None
                assert genBand.floatMin is not None
                assert genBand.floatMax is not None

                assert genBand.varname == expectedBand.varname
                assert genBand.bytes_ == expectedBand.bytes_
                assert genBand.bits_ == expectedBand.bits_
                assert genBand.intMin == expectedBand.intMin
                assert genBand.intMax == expectedBand.intMax
                assert genBand.floatMin == expectedBand.floatMin
                assert genBand.floatMax == expectedBand.floatMax

            i += 1

        assert i == 6, "Not enough variables were iterated through, test fail."

    def test_create_dtype(self):
        """
        Check that _bands_to_dtype works as expected
        """
        bands = [Band('I_lw', 1, 8, 0, 255, 0, 500),
                 Band('T_a', 1, 8, 0, 255, 22.39999962, 23.39999962),
                 Band('e_a', 2, 16, 0, 65535, 468.7428284, 469.7428284),
                 Band('u', 2, 16, 0, 65535, 0.8422899842, 1.842289925),
                 Band('T_g', 1, 8, 0, 255, 0, 1)]

        expectedDt = np.dtype([('I_lw', 'uint8'), ('T_a', 'uint8'),
                               ('e_a', 'uint16'), ('u', 'uint16'),
                               ('T_g', 'uint8')])
        dt = _bands_to_dtype(bands)

        assert expectedDt == dt, "%s != %s" % (str(set(expectedDt)), str(set(dt)))


class TestUtils(unittest.TestCase):
    """
    Test things like calculating floating point value
    """
    def setUp(self):
        pass

    def test_float_convert(self):
        """
        Convert an integer to a float using the header information in a Band
        """
        testBand = Band("Band Name", 1, 8, 0, 255, -27.5, 33.0)

        testInt = 10

        byHandFloat = -25.1274509804

        npt.assert_approx_equal(byHandFloat,
                                _calc_float_value(testBand, testInt))
