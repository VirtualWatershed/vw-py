"""
Tests for the isnobal_adaptor module
"""

import numpy.testing as npt
import numpy as np
import os
import pandas as pd
import subprocess
import struct
import unittest

from nose.tools import raises

from StringIO import StringIO
from adaptors.src.isnobal_adaptor import VARNAME_DICT, _make_bands, \
    GlobalBand, Band, _calc_float_value, _bands_to_dtype, _build_ipw_dataframe,\
    _bands_to_header_lines, _floatdf_to_binstring, _recalculate_headers, IPW


class TestHeaderParser(unittest.TestCase):
    """
    Test the creation of the header dictionary to be used as a member of the
    IPW class.
    """
    def setUp(self):

        # mirrors what is done in class IPWLines
        # there are five bands in this one, so we'll get to test handling of
        # the "sun-down" number of bands. There is one more in daylight hours
        testFile = 'src/test/data/in.00'

        with open(testFile, 'rb') as f:
            lines = f.readlines()

        self.headerLines = lines[:-1]

        self.binaryData = lines[-1]

        self.headerDict = \
            _make_bands(self.headerLines, VARNAME_DICT['in'])

        self.bands = [Band('I_lw', 0, 1, 8, 0, 255, 0, 500),
                      Band('T_a', 1, 1, 8, 0, 255, 22.39999962, 23.39999962),
                      Band('e_a', 2, 2, 16, 0, 65535, 468.7428284, 469.7428284),
                      Band('u', 3, 2, 16, 0, 65535, 0.8422899842, 1.842289925),
                      Band('T_g', 4, 1, 8, 0, 255, 0, 1)]

        self.ipw = IPW(testFile)

    def test_header_dict(self):
        """
        Check that header lines are properly built into a dictionary
        """
        expectedHeaderDict = \
            {
                'global': GlobalBand("0123", 148, 170, 5),
                'I_lw': Band('I_lw', 0, 1, 8, 0, 255, 0, 500),
                'T_a': Band('T_a', 1, 1, 8, 0, 255, 22.39999962, 23.39999962),
                'e_a': Band('e_a', 2, 2, 16, 0, 65535, 468.7428284, 469.7428284),
                'u': Band('u', 3, 2, 16, 0, 65535, 0.8422899842, 1.842289925),
                'T_g': Band('T_g', 4, 1, 8, 0, 255, 0, 1)
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
        expectedDt = np.dtype([('I_lw', 'uint8'), ('T_a', 'uint8'),
                               ('e_a', 'uint16'), ('u', 'uint16'),
                               ('T_g', 'uint8')])
        dt = _bands_to_dtype(self.bands)

        assert expectedDt == dt, \
            "%s != %s" % (str(set(expectedDt)), str(set(dt)))

    def test_float_convert(self):
        """
        Convert an integer to a float using the header information in a Band
        """
        testBand = Band("Band Name", 221, 1, 8, 0, 255, -27.5, 33.0)

        testInt = 10

        byHandFloat = -25.1274509804

        npt.assert_approx_equal(byHandFloat,
                                _calc_float_value(testBand, testInt))

    def test_build_dataframe(self):
        """
        Check that the IPW dataframe has been correctly built
        """
        data = self.binaryData
        bands = self.bands

        df = _build_ipw_dataframe(bands, data)

        # fetch the floating point data using the IPW tool primg
        # <http://cgiss.boisestate.edu/~hpm/software/IPW/man1/primg.html>
        ipwCmd = "primg -a -i src/test/data/in.00"
        textArray = subprocess.check_output(ipwCmd, shell=True)
        expectedDf = \
            pd.DataFrame(np.genfromtxt(StringIO(textArray), delimiter=" "),
                         columns=[b.varname for b in bands])

        # use .01 because of severe rounding by IPW primg
        assert all(abs(expectedDf - df) < .01),\
            (abs(expectedDf - df) < .1).any(1)

    def test_bands_to_header_lines(self):
        """
        Check that IPW header is properly re-made
        """
        expectedHeaderLines = \
            ["!<header> basic_image_i -1 $Revision: 1.11 $",
             "byteorder = 0123 ",
             "nlines = 148 ",
             "nsamps = 170 ",
             "nbands = 5 ",
             "!<header> basic_image 0 $Revision: 1.11 $",
             "bytes = 1 ",
             "bits = 8 ",
             "!<header> basic_image 1 $Revision: 1.11 $",
             "bytes = 1 ",
             "bits = 8 ",
             "!<header> basic_image 2 $Revision: 1.11 $",
             "bytes = 2 ",
             "bits = 16 ",
             "!<header> basic_image 3 $Revision: 1.11 $",
             "bytes = 2 ",
             "bits = 16 ",
             "!<header> basic_image 4 $Revision: 1.11 $",
             "bytes = 1 ",
             "bits = 8 ",
             "!<header> lq 0 $Revision: 1.6 $",
             "map = 0 0 ",
             "map = 255 500 ",
             "!<header> lq 1 $Revision: 1.6 $",
             "map = 0 22.39999962 ",
             "map = 255 23.39999962 ",
             "!<header> lq 2 $Revision: 1.6 $",
             "map = 0 468.7428284 ",
             "map = 65535 469.7428284 ",
             "!<header> lq 3 $Revision: 1.6 $",
             "map = 0 0.8422899842 ",
             "map = 65535 1.842289925 ",
             "!<header> lq 4 $Revision: 1.6 $",
             "map = 0 0 ",
             "map = 255 1 "]

        # create the header from the bands
        headerLines = _bands_to_header_lines(self.headerDict)

        assert headerLines == expectedHeaderLines, \
            "%s != %s" % (headerLines, expectedHeaderLines)

    def test_floatdf_to_binstring(self):
        """
        Test that a DF with floats is correctly translated to a binary string
        """
        df = pd.DataFrame([[10.0, -1.0, 16.0], [-85.0, 9.0, 25.0]],
                          columns=['this', 'that', 'the other'])
        bands = [Band('this', 0, 2, 16, 0, 65535, -100.0, 100.0),
                 Band('that', 1, 1, 8, 0, 255, -5, 10.0),
                 Band('the other', 2, 1, 8, 0, 255, 0, 30.0)]

        # Do a math problem by hand to figure out what these should be
        expectedIntDf = pd.DataFrame([[36044, 68, 136],
                                      [4915, 238, 212]],
                                     columns=['this', 'that', 'the other'])

        expectedBinStr = \
            "".join([struct.pack('H', expectedIntDf['this'][0]),
                     struct.pack('B', expectedIntDf['that'][0]),
                     struct.pack('B', expectedIntDf['the other'][0]),
                     struct.pack('H', expectedIntDf['this'][1]),
                     struct.pack('B', expectedIntDf['that'][1]),
                     struct.pack('B', expectedIntDf['the other'][1])])

        binStr = _floatdf_to_binstring(bands, df)

        assert binStr == expectedBinStr

    @raises(AssertionError)
    def test_floatdf_to_binstring_fail_min(self):
        """
        Error when a data val is less than a band minimum?
        """
        df = pd.DataFrame([[10.0, -10.0, 16.0], [-85.0, 9.0, 25.0]],
                          columns=['this', 'that', 'the other'])

        bands = [Band('this', 0, 2, 16, 0, 65535, -100.0, 100.0),
                 Band('that', 1, 1, 8, 0, 255, -5, 10.0),
                 Band('the other', 2, 1, 8, 0, 255, 0, 30.0)]

        _floatdf_to_binstring(bands, df)

    @raises(AssertionError)
    def test_floatdf_to_binstring_fail_max(self):
        """
        Error when a data val is less than a band maximum?
        """
        df = pd.DataFrame([[101.0, -1.0, 16.0], [-85.0, 9.0, 25.0]],
                          columns=['this', 'that', 'the other'])
        bands = [Band('this', 0, 2, 16, 0, 65535, -100.0, 100.0),
                 Band('that', 1, 1, 8, 0, 255, -5, 10.0),
                 Band('the other', 2, 1, 8, 0, 255, 0, 30.0)]

        _floatdf_to_binstring(bands, df)

    def test_recalculate_header(self):
        """
        Test that headers are successfully recalculated after data has been
        changed.
        """
        df = pd.DataFrame([[101.0, -1.0, 16.0], [-85.0, 9.0, 25.0]],
                          columns=['this', 'that', 'the other'])
        bands = [Band('this', 0, 2, 16, 0, 65535, -100.0, 100.0),
                 Band('that', 1, 1, 8, 0, 255, -5, 10.0),
                 Band('the other', 2, 1, 8, 0, 255, 0, 30.0)]

        # increase variable this by five degrees plus the Band's stated maximum
        df['this'] = df['this'] + bands[0].floatMax + 5.0
        # decrease variable the other to five less than the Band's minimum
        df['the other'] = df['the other'] - (bands[2].floatMin - 5.0)

        _recalculate_headers(bands, df)

        assert bands[0].floatMax == df['this'].max()
        assert bands[2].floatMin == df['the other'].min()

    def test_save_ipw(self):
        """
        Load an IPW file and save back to a new file; check contents are equal
        """
        ### Note: can't test the building of headers because I'm stripping out
        ### extraneous info like random variable units.
        outfile = "src/test/data/in.00.rewrite"

        self.ipw.write(outfile)

        ipwCmd = "primg -a -i src/test/data/in.00"
        expectedTextArray = subprocess.check_output(ipwCmd, shell=True)

        ipwCmd += ".rewrite"
        textArray = subprocess.check_output(ipwCmd, shell=True)

        assert expectedTextArray == textArray,\
            "expected: %s\ngenerated: %s" % \
            (expectedTextArray[:300], textArray[:300])

        os.remove(outfile)

    def test_modify_save_ipw(self):
        """
        Test start-to-finish steps of load, modify, and save an IPW file using the IPW class
        """
        ipw = IPW("src/test/data/in.00")
        ipw.dataFrame.T_a = ipw.dataFrame.T_a + 2.0
        print ipw.dataFrame.head()
        ipw.dataFrame['I_lw'] += 23.0

        ipw.recalculate_header()

        outfile = "src/test/data/in.00.modified"
        ipw.write(outfile)
        # read in the float data array from the modified IPW file we just wrote
        ipwCmd = "primg -a -i src/test/data/in.00"
        origTextArray = subprocess.check_output(ipwCmd, shell=True)

        ipwCmd = "primg -a -i " + outfile
        modTextArray = subprocess.check_output(ipwCmd, shell=True)

        bands = self.bands
        modifiedDf =\
            pd.DataFrame(np.genfromtxt(StringIO(modTextArray), delimiter=" "),
                         columns=[b.varname for b in bands])
        originalDf =\
            pd.DataFrame(np.genfromtxt(StringIO(origTextArray), delimiter=" "),
                         columns=[b.varname for b in bands])

        assert all(modifiedDf['T_a'] > originalDf['T_a']),\
            "modified: %s\noriginal: %s" % \
            (str(modifiedDf['T_a']), str(originalDf['T_a']))
        assert all(modifiedDf['I_lw'] > originalDf['I_lw']),\
            "modified: %s\noriginal: %s" % \
            (str(modifiedDf['I_lw']), str(originalDf['I_lw']))

        os.remove(outfile)
