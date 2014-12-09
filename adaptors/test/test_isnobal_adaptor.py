"""
Tests for the isnobal_adaptor module
"""

import logging
import numpy.testing as npt
import numpy as np
import os
import pandas as pd
import subprocess
import struct
import unittest

from nose.tools import raises

from StringIO import StringIO
from adaptors.isnobal import VARNAME_DICT, _make_bands,\
    GlobalBand, Band, _calc_float_value, _bands_to_dtype, _build_ipw_dataframe,\
    _bands_to_header_lines, _floatdf_to_binstring, _recalculate_header, IPW,\
    metadata_from_file
from adaptors.watershed import get_config
from test_vw_adaptor import show_string_diff


class TestHeaderParser(unittest.TestCase):
    """
    Test the creation of the header dictionary to be used as a member of the
    IPW class.
    """
    def setUp(self):

        # mirrors what is done in class IPWLines
        # there are five bands in this one, so we'll get to test handling of
        # the "sun-down" number of bands. There is one more in daylight hours
        test_file = 'adaptors/test/data/in.0000'

        with open(test_file, 'rb') as f:
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

        self.ipw = IPW(test_file)

        self.test_file = test_file

        self.model_run_uuid = "09079630-5ef8-11e4-9803-0800200c9a66"

        self.parent_model_run_uuid = "373ae181-a0b2-4998-ba32-e27da190f6dd"


    def test_header_dict(self):
        """
        Check that header lines are properly built into a dictionary
        """
        expectedHeaderDict = \
            {
                'global': GlobalBand("0123", 148, 170, 5),
                'I_lw': Band('I_lw', 0, 1, 8, 0, 255, 284.31372549, 390.196078431),
                'T_a': Band('T_a', 1, 1, 8, 0, 255, 22.39999962, 23.39999962),
                'e_a': Band('e_a', 2, 2, 16, 0, 65535, 468.7428284, 469.7428284),
                'u': Band('u', 3, 2, 16, 0, 65535, 0.8422899842, 1.8422899842),
                'T_g': Band('T_g', 4, 1, 8, 0, 255, 0, 1)
            }

        headerDict = self.headerDict

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
                assert genBand.int_min is not None
                assert genBand.int_max is not None
                assert genBand.float_min is not None
                assert genBand.float_max is not None

                assert genBand.varname == expectedBand.varname
                assert genBand.bytes_ == expectedBand.bytes_
                assert genBand.bits_ == expectedBand.bits_
                assert genBand.int_min == expectedBand.int_min
                assert genBand.int_max == expectedBand.int_max
                assert genBand.float_min == expectedBand.float_min
                assert genBand.float_max == expectedBand.float_max

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
        ipw_cmd = "primg -a -i adaptors/test/data/in.0000"
        text_array = subprocess.check_output(ipw_cmd, shell=True)
        expectedDf = \
            pd.DataFrame(np.genfromtxt(StringIO(text_array), delimiter=" "),
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
             "map = 0 284.31372549 ",
             "map = 255 390.196078431 ",
             "!<header> lq 1 $Revision: 1.6 $",
             "map = 0 22.39999962 ",
             "map = 255 23.39999962 ",
             "!<header> lq 2 $Revision: 1.6 $",
             "map = 0 468.7428284 ",
             "map = 65535 469.7428284 ",
             "!<header> lq 3 $Revision: 1.6 $",
             "map = 0 0.8422899842 ",
             "map = 65535 1.8422899842 ",
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
        df['this'] = df['this'] + bands[0].float_max + 5.0
        # decrease variable the other to five less than the Band's minimum
        df['the other'] = df['the other'] - (bands[2].float_min - 5.0)

        _recalculate_header(bands, df)

        assert bands[0].float_max == df['this'].max()
        assert bands[2].float_min == df['the other'].min()

    def test_save_ipw(self):
        """
        Load 5- and 6-band input and em/snow output IPW files and save back to a new file
        """
        ### Note: can't test the building of headers because I'm stripping out
        ### extraneous info like random variable units.

        def _tester(test_data):
            logging.debug("testing load/save of file " + test_data)
            # load test_data
            ipw = IPW(test_data)

            # create and write IPW data to a new file
            outfile = test_data + ".rewrite"
            ipw.recalculate_header()
            ipw.write(outfile)

            # use primg (http://cgiss.boisestate.edu/~hpm/software/IPW/man1/primg.html)
            # to print the floating point data and capture in python for both
            ipw_cmd = "primg -a -i " + test_data
            expected_text_array = subprocess.check_output(ipw_cmd, shell=True)

            ipw_cmd += ".rewrite"
            text_array = subprocess.check_output(ipw_cmd, shell=True)

            # check equality
            assert expected_text_array == text_array,\
                "expected: %s\ngenerated: %s" % \
                (expected_text_array[:300], text_array[:300])

            os.remove(outfile)

        test_data = ["adaptors/test/data/" + f for f in
                     ("in.0000", "in.0010", "em.0134", "snow.1345")]

        i = 0
        for d in test_data:
            _tester(d)
            i += 1

        assert i == 4, "Tests did not run! i = %s" % i

    def test_modify_save_ipw(self):
        """
        Test start-to-finish steps of load, modify, and save an IPW file using the IPW class
        """
        ipw = IPW("adaptors/test/data/in.0000")
        data_frame = ipw.data_frame()
        data_frame.T_a = data_frame.T_a + 2.0
        print data_frame.head()
        data_frame['I_lw'] += 23.0

        ipw.recalculate_header()

        outfile = "adaptors/test/data/in.0000.modified"
        ipw.write(outfile)
        # read in the float data array from the modified IPW file we just wrote
        ipw_cmd = "primg -a -i adaptors/test/data/in.0000"
        origTextArray = subprocess.check_output(ipw_cmd, shell=True)

        ipw_cmd = "primg -a -i " + outfile
        modTextArray = subprocess.check_output(ipw_cmd, shell=True)

        bands = self.bands
        modified_df =\
            pd.DataFrame(np.genfromtxt(StringIO(modTextArray), delimiter=" "),
                         columns=[b.varname for b in bands])
        original_df =\
            pd.DataFrame(np.genfromtxt(StringIO(origTextArray), delimiter=" "),
                         columns=[b.varname for b in bands])

        assert all(modified_df['T_a'] > original_df['T_a']),\
            "modified: %s\noriginal: %s" % \
            (str(modified_df['T_a']), str(original_df['T_a']))
        assert all(modified_df['I_lw'] > original_df['I_lw']),\
            "modified: %s\noriginal: %s" % \
            (str(modified_df['I_lw']), str(original_df['I_lw']))

        os.remove(outfile)

    def test_watershed_connection(self):
        """
        Test watershed functions operating on an IPW instance or as a static method
        """
        # load expected json metadata file
        expected = open("adaptors/test/data/expected1_in.json", 'r').read()

        description = "Testing metadata!"

        generated = metadata_from_file(self.test_file,
                                       self.parent_model_run_uuid,
                                       self.model_run_uuid,
                                       description,
                                       config_file="adaptors/test/test.conf")

        # check equality
        assert generated == expected, show_string_diff(generated, expected)
