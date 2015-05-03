"""
Tests for the isnobal_adaptor module
"""

import logging
import datetime
import numpy.testing as npt
import numpy as np
import os
import pandas as pd
import subprocess
import struct
import unittest

from netCDF4 import Dataset
from nose.tools import raises

from StringIO import StringIO
from ..isnobal import (VARNAME_DICT, _make_bands,
    GlobalBand, Band, _calc_float_value, _bands_to_dtype, _build_ipw_dataframe,
    _bands_to_header_lines, _floatdf_to_binstring, _recalculate_header, IPW,
    reaggregate_ipws, _is_consecutive, AssertISNOBALInput, ISNOBALNetcdfError)


class TestIPW(unittest.TestCase):
    """
    Test the creation of the header dictionary to be used as a member of the
    IPW class.
    """
    def setUp(self):

        # mirrors what is done in class IPWLines
        # there are five bands in this one, so we'll get to test handling of
        # the "sun-down" number of bands. There is one more in daylight hours
        test_file = 'wcwave_adaptors/test/data/in.0000'

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

    def test_read_precip(self):
        "Precip files read into precip_tuple_list"
        pptfile = 'wcwave_adaptors/test/data/ppt_desc'
        pptlines = open(pptfile, 'r').readlines()

        ipw_tups = IPW.precip_tuple(pptfile)

        assert len(pptlines) == len(ipw_tups)

        for ipw_tup in ipw_tups:

            assert len(ipw_tup) == 2

            df = ipw_tup[1].data_frame()

            assert len(df.columns)
            assert all(df.columns ==
                       ['m_pp', 'percent_snow', 'rho_snow', 'T_pp'])

            assert all(df[['m_pp', 'rho_snow', 'T_pp']].sum().abs() > 0)

    def test_read_init(self):
        "Read init IPW file"
        ipw = IPW('wcwave_adaptors/test/data/init.ipw')
        df = ipw.data_frame()

        assert all(df[['z', 'z_0']].sum().abs() > 0)

        assert len(df.columns)
        assert (df.columns == ['z', 'z_0', 'z_s', 'rho', 'T_s_0',
                               'T_s', 'h2o_sat']).all()

    def test_read_mask(self):
        "Read mask IPW file"
        ipw = IPW('wcwave_adaptors/test/data/tl2p5mask.ipw', file_type='mask')
        df = ipw.data_frame()

        assert df.sum()['mask'] > 0

        assert len(df.columns)
        assert df.columns == ['mask']

    def test_read_dem(self):
        "Read DEM IPW file"
        ipw = IPW('wcwave_adaptors/test/data/tl2p5_dem.ipw', file_type='dem')
        df = ipw.data_frame()

        assert df.sum()['alt'] > 0

        assert len(df.columns)
        assert df.columns == ['alt']

    @raises(Exception)
    def test_bad_filetype(self):
        "When reading mask, dem, or ppt_desc, IPWFileError is thrown instead of KeyError when file_type is not given"

        IPW('wcwave_adaptors/test/data/tl2p5mask.ipw')
        IPW('wcwave_adaptors/test/data/tl2p5_dem.ipw')
        IPW('wcwave_adaptors/test/data/tl2p5_dem.ipw')

    def test_header_dict(self):
        """
        Check that header lines are properly built into a dictionary
        """
        expectedHeaderDict = \
            {
                'global': GlobalBand("0123", 148, 170, 5),
                'I_lw': Band('I_lw', 0, 1, 8, 0, 255, 284.31372549, 390.196078431,
                             4842544.9, 569029.6, -2.5, 2.5, "meters", "UTM"),
                'T_a': Band('T_a', 1, 1, 8, 0, 255, 22.39999962, 23.39999962,
                            4842544.9, 569029.6, -2.5, 2.5, "meters", "UTM"),
                'e_a': Band('e_a', 2, 2, 16, 0, 65535, 468.7428284, 469.7428284,
                            4842544.9, 569029.6, -2.5, 2.5, "meters", "UTM"),
                'u': Band('u', 3, 2, 16, 0, 65535, 0.8422899842, 1.8422899842,
                          4842544.9, 569029.6, -2.5, 2.5, "meters", "UTM"),
                'T_g': Band('T_g', 4, 1, 8, 0, 255, 0, 1,
                            4842544.9, 569029.6, -2.5, 2.5, "meters", "UTM")
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
                assert genBand.bline is not None
                assert genBand.bsamp is not None
                assert genBand.dline is not None
                assert genBand.dsamp is not None
                assert genBand.geo_units is not None
                assert genBand.coord_sys_ID is not None

                assert genBand.varname == expectedBand.varname
                assert genBand.bytes_ == expectedBand.bytes_
                assert genBand.bits_ == expectedBand.bits_
                assert genBand.int_min == expectedBand.int_min
                assert genBand.int_max == expectedBand.int_max
                assert genBand.float_min == expectedBand.float_min
                assert genBand.float_max == expectedBand.float_max
                assert genBand.bline == expectedBand.bline
                assert genBand.bsamp == expectedBand.bsamp,\
                    "Variable: %s\nGenerated: %s, Expected: %s" % \
                    (variable, genBand.bsamp, expectedBand.bsamp)

                assert genBand.dline == expectedBand.dline
                assert genBand.dsamp == expectedBand.dsamp
                assert genBand.geo_units == expectedBand.geo_units
                assert genBand.coord_sys_ID == expectedBand.coord_sys_ID

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
        ipw_cmd = "primg -a -i wcwave_adaptors/test/data/in.0000"
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
             "map = 255 1 ",
             "!<header> geo 0 $Revision: 1.7 $",
             "bline = 4842544.9 ",
             "bsamp = 569029.6 ",
             "dline = -2.5 ",
             "dsamp = 2.5 ",
             "units = meters ",
             "coord_sys_ID = UTM ",
             "!<header> geo 1 $Revision: 1.7 $",
             "bline = 4842544.9 ",
             "bsamp = 569029.6 ",
             "dline = -2.5 ",
             "dsamp = 2.5 ",
             "units = meters ",
             "coord_sys_ID = UTM ",
             "!<header> geo 2 $Revision: 1.7 $",
             "bline = 4842544.9 ",
             "bsamp = 569029.6 ",
             "dline = -2.5 ",
             "dsamp = 2.5 ",
             "units = meters ",
             "coord_sys_ID = UTM ",
             "!<header> geo 3 $Revision: 1.7 $",
             "bline = 4842544.9 ",
             "bsamp = 569029.6 ",
             "dline = -2.5 ",
             "dsamp = 2.5 ",
             "units = meters ",
             "coord_sys_ID = UTM ",
             "!<header> geo 4 $Revision: 1.7 $",
             "bline = 4842544.9 ",
             "bsamp = 569029.6 ",
             "dline = -2.5 ",
             "dsamp = 2.5 ",
             "units = meters ",
             "coord_sys_ID = UTM "]

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

        test_data = ["wcwave_adaptors/test/data/" + f for f in
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
        ipw = IPW("wcwave_adaptors/test/data/in.0000")
        data_frame = ipw.data_frame()
        data_frame.T_a = data_frame.T_a + 2.0
        print data_frame.head()
        data_frame['I_lw'] += 23.0

        ipw.recalculate_header()

        outfile = "wcwave_adaptors/test/data/in.0000.modified"
        ipw.write(outfile)
        # read in the float data array from the modified IPW file we just wrote
        ipw_cmd = "primg -a -i wcwave_adaptors/test/data/in.0000"
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



class TestResampleIPW(unittest.TestCase):
    """
    Test resampling capabilities of a series of IPW objects
    """
    def test_resample_throws_on_nonconsecutive(self):
        """
        Test that resample_ipws throws error when ipws aren't consecutive
        """
        ipws = [IPW() for f in range(3)]

        water_year_start = 2010

        ipws[0].start_datetime = datetime.datetime(water_year_start, 10, 01, 0)
        ipws[0].end_datetime = datetime.datetime(water_year_start, 10, 01, 1)

        ipws[1].start_datetime = datetime.datetime(water_year_start, 10, 01, 1)
        ipws[1].end_datetime = datetime.datetime(water_year_start, 10, 01, 2)

        ipws[2].start_datetime = datetime.datetime(water_year_start, 10, 01, 2)
        ipws[2].end_datetime = datetime.datetime(water_year_start, 10, 01, 3)

        assert _is_consecutive(ipws)

        ipws[2].start_datetime = datetime.datetime(water_year_start, 10, 01, 5)
        ipws[2].end_datetime = datetime.datetime(water_year_start, 10, 01, 6)

        assert not _is_consecutive(ipws)

    def test_resample_and_save(self):
        """
        Resample the data and check that the metadata reflects the resampling
        """
        # initialize dataframes
        df1 = pd.DataFrame([[1, 2],
                            [0, 1],
                            [1, 1],
                            [1, 1]],
                columns=['melt', 'z_s'],
                dtype='float64')

        df2 = df1.copy()
        df3 = df1.copy()
        df4 = df1.copy()

        # modify the melt variables of the first column
        df2.melt[0] = 4.0
        df2.melt[1] = 0.0
        df2.melt[2] = 0.0
        df2.melt[3] = 2.0

        # have more melt than previous so to check recalc'd min doesn't trfr
        df3.melt[0] = 5.0
        df3.melt[1] = 2.0
        df3.melt[2] = 2.0
        df3.melt[3] = 2.0

        df4.melt[0] = 1.0
        df4.melt[1] = 0.0
        df4.melt[2] = 2.0
        df4.melt[3] = 2.0

        # modify the snow temperature variable (z_s) of the second column
        df2.z_s[0] = 2.0
        df2.z_s[1] = 4.0
        df2.z_s[2] = 3.0
        df2.z_s[3] = 3.0

        # have larger snow depth than previous so to make sure max is recal'd
        df3.z_s[0] = 10.0
        df3.z_s[1] = 12.0
        df3.z_s[2] = 2.0
        df3.z_s[3] = 4.0

        df4.z_s[0] = 11.0
        df4.z_s[1] = 0.0
        df4.z_s[2] = 2.0
        df4.z_s[3] = 1.0

        time_idx = pd.date_range("2010-10-01", freq='H', periods=5)

        ipws = []
        for df in [df1, df2, df3, df4]:
            ipw = IPW()
            ipw._data_frame = df
            ipws.append(ipw)

        ipws = pd.Series(ipws, time_idx[:4])

        # making sure attributes are properly transferred
        # for this they don't need to make physical sense
        geotransform = [2.0, 0.0, 2.0, 5.0, 1.1, 2.2]

# GlobalBand = namedtuple("GlobalBand", 'byteorder nLines nSamps nBands')
        header_dict = {"global": GlobalBand('0123', 2, 2, 2),
                       "melt": Band("melt", 0, 2, 16, 0, 65535, -100.0, 100.0),
                       "z_s": Band("z_s", 1, 1, 8, 0, 255, 0, 30.0), }
        file_type = "out"
        bands = [Band("melt", 0, 2, 16, 0, 65535, -100.0, 100.0),
                 Band("z_s", 1, 1, 8, 0, 255, 0, 30.0)]

        nonglobal_bands = bands
        for ipw_idx, ipw in enumerate(ipws):
            ipw.start_datetime = time_idx[ipw_idx]
            ipw.end_datetime = time_idx[ipw_idx + 1]
            ipw.geotransform = geotransform
            ipw.header_dict = header_dict
            ipw.file_type = file_type
            ipw.bands = bands
            ipw.nonglobal_bands = nonglobal_bands

        reaggregated_ipws = reaggregate_ipws(ipws, rule='2H')

        assert len(reaggregated_ipws) == 2

        df_new1 = reaggregated_ipws[0].data_frame()
        df_new2 = reaggregated_ipws[1].data_frame()

        assert df_new1.melt[0] == 5.0
        assert df_new2.melt[0] == 6.0
        assert df_new1.melt[1] == 0.0
        assert df_new2.melt[1] == 2.0
        assert df_new1.melt[2] == 1.0
        assert df_new2.melt[2] == 4.0
        assert df_new1.melt[3] == 3.0
        assert df_new2.melt[3] == 4.0

        assert df_new1.z_s[0] == 4.0
        assert df_new2.z_s[0] == 21.0
        assert df_new1.z_s[1] == 5.0
        assert df_new2.z_s[1] == 12.0
        assert df_new1.z_s[2] == 4.0
        assert df_new2.z_s[2] == 4.0
        assert df_new1.z_s[3] == 4.0
        assert df_new2.z_s[3] == 5.0

        # check that the start and end times of each IPW are as expected
        assert reaggregated_ipws[0].start_datetime == time_idx[0]
        assert reaggregated_ipws[1].start_datetime == time_idx[2]
        assert reaggregated_ipws[0].end_datetime == time_idx[2]
        assert reaggregated_ipws[1].end_datetime == time_idx[4]

        i = 0
        for j, reagg_ipw in enumerate(reaggregated_ipws):
            assert reagg_ipw.geotransform == geotransform
            assert reagg_ipw.file_type == file_type

            expected_nonglob = nonglobal_bands
            gen_nonglob = reagg_ipw.nonglobal_bands

            for i, b in enumerate(gen_nonglob):
                exp = expected_nonglob[i]
                assert b.bits_ == exp.bits_
                assert b.bytes_ == exp.bytes_
                assert b.bline == exp.bline
                assert b.bsamp == exp.bsamp
                assert b.dline == exp.dline
                assert b.dsamp == exp.dsamp
                assert b.varname == exp.varname

            for key in reagg_ipw.header_dict:
                if key != "global":
                    band = reagg_ipw.header_dict[key]
                    expected = header_dict[key]
                    assert band.bits_ == expected.bits_
                    assert band.bytes_ == expected.bytes_
                    assert band.bline == expected.bline
                    assert band.bsamp == expected.bsamp
                    assert band.dline == expected.dline
                    assert band.dsamp == expected.dsamp
                    assert band.varname == expected.varname

            # make sure file can be written-implicitly checks bands are correct
            write_file = "wcwave_adaptors/test/data/tmp_write_reagg"
            if os.path.isfile(write_file):
                os.remove(write_file)

            reagg_ipw.write(write_file)

            i += 1

        assert i == 2
        del i
        # check that saving and re-loading the individual IPWs succeeds.
        # for this part, we'll use one real file so that the sum is just a prod

        # create ipws
        test_file = "wcwave_adaptors/test/data/in.0000"
        ipws = [IPW(test_file) for i in range(4)]

        # artificially modify the start and end times
        dt = datetime.timedelta(0, 3600)

        ipws[1].start_datetime += dt
        ipws[2].start_datetime += 2*dt
        ipws[3].start_datetime += 3*dt

        ipws[1].end_datetime += dt
        ipws[2].end_datetime += 2*dt
        ipws[3].end_datetime += 3*dt

        reagg_ipws = reaggregate_ipws(ipws, rule='2H')

        expected_df = ipws[0].data_frame() * 2.0

        # check that loaded-from-file data has been properly aggregated
        t = 0
        for i in range(len(reagg_ipws)):
            assert (reagg_ipws[i].data_frame() ==
                    expected_df).all().all(), "reagg: %s\nexpect: %s" % \
                   (reagg_ipws[i].data_frame().head(), expected_df.head())
            t += 1

        assert t == 2

        # now save and re-load to check that all is well with headers
        rtest0 = "wcwave_adaptors/test/data/in.tmp_reagg.0"
        rtest1 = "wcwave_adaptors/test/data/in.tmp_reagg.1"
        rtest_files = [rtest0, rtest1]

        dt = pd.Timedelta('2 hours')
        for i, reagg_ipw in enumerate(reagg_ipws):
            if os.path.isfile(rtest_files[i]):
                os.remove(rtest_files[i])
            reagg_ipw.write(rtest_files[i])

            reimported = IPW(rtest_files[i], dt=dt)

            assert (reimported.data_frame() ==
                    reagg_ipw.data_frame()).all().all(), \
                "\nreimported:\n%s\nreagg:\n%s" % \
                (str(reimported.data_frame().head()),
                 str(reagg_ipw.data_frame().head()))

            os.remove(rtest_files[i])

            assert reimported.end_datetime ==\
               datetime.datetime(2010, 10, 1, 2*(i+1), 0), \
               "reimported datetime: %s" % str(reimported.end_datetime)

class TestISNOBAL(unittest.TestCase):
    """Tests for particularities of the Python iSNOBAL interface"""
    def setUp(self):
        nc_in_fname = 'wcwave_adaptors/test/data/ref_in.nc'
        self.nc_in = Dataset(nc_in_fname)
        nc_out_fname = 'wcwave_adaptors/test/data/ref_out.nc'
        self.nc_out = Dataset(nc_out_fname)

    def test_is_isnobal(self):
        """Enforce a NetCDF satisfies iSNOBAL requirements for input"""
        AssertISNOBALInput(self.nc_in)

    @raises(ISNOBALNetcdfError)
    def test_not_isnobal_raises(self):
        "If a NetCDF does not satisfy iSNOBAL requirements, throw ISNOBALNetcdfError"
        AssertISNOBALInput(self.nc_out)
