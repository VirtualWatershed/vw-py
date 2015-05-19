"""Tests of NetCDF functionality including enforcement of CF standards,
   metadata gleaning, CF-Station data conversion, and maybe more, like opendap.
"""

import os
import unittest
import numpy as np
from netCDF4 import Dataset

from ..netcdf import utm2latlon, ncgen_from_template
# include tests for generate_standard_nc in this module
from ..isnobal import (_nc_insert_ipw, IPW, nc_to_standard_ipw,
                                     GlobalBand, generate_standard_nc)


class TestIsnobalNetCDF(unittest.TestCase):
    """Unittests for NetCDF to iSNOBAL Adaptor Functionality
    """
    def setUp(self):
        test_dir = os.path.join(os.path.dirname(__file__), 'data')

        input_data_sources = ['inputs', 'ppt_desc', 'init.ipw',
                              'tl2p5_dem.ipw', 'tl2p5mask.ipw']

        self.input_data_sources = map(lambda x: os.path.join(test_dir, x),
                                      input_data_sources)

        self.output_data_source = os.path.join(test_dir, 'outputs')

        self.nlines = 148
        self.nsamps = 170

        self.base_data_dir = 'wcwave_adaptors/test/data'
        self.full_nc_base_dir = os.path.join(self.base_data_dir,
                                             'full_nc_example')

        self.full_nc_out = 'wcwave_adaptors/test/data/full_nc_example/nc.tmp'

    def test_generate_standard_nc_inputs(self):
        "Check that a sample NetCDF is properly built from a series of inputs"

        nc = generate_standard_nc(self.full_nc_base_dir, self.full_nc_out)

        # check new file was created
        assert os.path.isfile(self.full_nc_out)

        _validate_input_nc(self, nc)

        nc.close()

        nc = Dataset(self.full_nc_out, 'r')

        _validate_input_nc(self, nc)

        os.remove(self.full_nc_out)

    def test_generate_standard_nc_outputs(self):
        "Check that a sample NetCDF is properly built from a series of outputs"
        outputs_dir = os.path.join(self.base_data_dir, 'outputs')
        outputs_nc_out = os.path.join(self.base_data_dir, 'nc_outputs.tmp')

        nc = generate_standard_nc(outputs_dir, outputs_nc_out)

        # check new file was created
        assert os.path.isfile(outputs_nc_out)

        assert set(nc.groups.keys()) == set(['em', 'snow'])

        # check that nc created in memory is valid
        _validate_input_nc(self, nc, type_='outputs')

        nc.close()

        nc = Dataset(outputs_nc_out, 'r')
        # check that the nc read from file is valid
        _validate_input_nc(self, nc, type_='outputs')

        os.remove(outputs_nc_out)

    def test_nc_insert_ipw(self):
        "Private helper function _nc_insert_ipw inserts all IPW file_types"
        datadir = "wcwave_adaptors/test/data/"

        ipw = IPW(datadir + 'in.0000')

        gt = ipw.geotransform

        gb = filter(lambda x: type(x) is GlobalBand, ipw.bands)[0]

        template_args = dict(bline=gt[3], bsamp=gt[0], dline=gt[5],
                             dsamp=gt[1], nsamps=gb.nSamps, nlines=gb.nLines,
                             dt=1, year=2010, month=10, day='01')

        nc = ncgen_from_template('ipw_in_template.cdl',
                                 datadir + 'nc_insert_ipw.tmp',
                                 **template_args)

        # helper for getting varnames within a group
        group_varnames = lambda g: [var for var in nc.groups[g].variables]

        # input
        _nc_insert_ipw(nc, ipw, 0, self.nlines, self.nsamps)

        # check that nc and nc_insert_ipw.tmp have been updated properly
        g = 'Input'
        assert group_varnames(g) == ['I_lw', 'T_a', 'e_a', 'u', 'T_g', 'S_n']

        for varname in group_varnames(g):

            curvar = nc.groups[g].variables[varname]

            assert curvar.shape == (1, gb.nLines, gb.nSamps)

            if varname in ['I_lw', 'T_a', 'e_a', 'u']:
                assert all(abs(np.ravel(curvar)) > 0) and\
                    all(abs(np.ravel(curvar)) < 1e6)

        # init
        ipw = IPW(datadir + 'init.ipw')
        _nc_insert_ipw(nc, ipw, None, self.nlines, self.nsamps)
        # check that nc and nc_insert_ipw.tmp have been updated properly
        g = 'Initial'
        assert group_varnames(g) == \
            ['z', 'z_0', 'z_s', 'rho', 'T_s_0', 'T_s', 'h2o_sat']

        for varname in group_varnames(g):

            curvar = nc.groups[g].variables[varname]

            assert nc.groups[g].variables[varname].shape ==\
                (gb.nLines, gb.nSamps)

            if varname in ['z', 'z_0']:
                assert all(abs(np.ravel(curvar)) > 0) and\
                    all(abs(np.ravel(curvar)) < 1e6)
        # mask
        ipw = IPW(os.path.join(self.full_nc_base_dir, 'tl2p5mask.ipw'),
                  file_type='mask')

        _nc_insert_ipw(nc, ipw, None, self.nlines, self.nsamps)
        # check that nc and nc_insert_ipw.tmp have been updated properly

        # precip; include time index manually for this test
        ipw = IPW(os.path.join(self.full_nc_base_dir, 'ppt_images_dist/ppt4b_10.ipw'),

                  file_type='precip')

        # insert an input file at the tenth timestep, making len of timevar 11
        _nc_insert_ipw(nc, ipw, 10, self.nlines, self.nsamps)

        # check that nc and nc_insert_ipw.tmp have been updated properly
        g = 'Precipitation'
        assert group_varnames(g) ==\
            ['m_pp', 'percent_snow', 'rho_snow', 'T_pp']


        for varname in group_varnames(g):

            curvar = nc.groups[g].variables[varname]

            assert curvar.shape == (11, gb.nLines, gb.nSamps),\
                "shape not expected, it's %s" % str(curvar.shape)

            if varname in ['m_pp', 'rho_snow', 'T_pp']:
                assert all(abs(np.ravel(curvar[-1])) > 0) and\
                    all(abs(np.ravel(curvar[-1])) < 1e6)

        # now input shape should have changed with the input of the 16
        # timestep data
        for varname in group_varnames('Input'):

            curvar = nc.groups['Input'].variables[varname]

            assert curvar.shape == (11, gb.nLines, gb.nSamps), \
                "shape is %s should be %s" % \
                (curvar.shape, (11, gb.nLines, gb.nSamps))


        # dem
        ipw = IPW(datadir + 'tl2p5_dem.ipw', file_type='dem')
        _nc_insert_ipw(nc, ipw, None, self.nlines, self.nsamps)

    def test_netcdf_to_standard_ipw(self):
        "Proper NetCDF file can be extracted to iSNOBAL standard directory structure"
        nc = generate_standard_nc(self.full_nc_base_dir, self.full_nc_out)

        nc = Dataset(self.full_nc_out, mode='r')

        new_ipw_basedir = os.path.join(self.full_nc_base_dir, 'ipw_from_nc')

        nc_to_standard_ipw(nc, new_ipw_basedir)

        new_ipw_dirlist = os.listdir(new_ipw_basedir)

        assert len(new_ipw_dirlist) == 6

        assert set(new_ipw_dirlist) == set(['inputs', 'init.ipw', 'ppt_desc',
                                            'ppt_images_dist', 'dem.ipw',
                                            'mask.ipw'])

        inputs = os.listdir(os.path.join(new_ipw_basedir, 'inputs'))
        ppt_images = os.listdir(os.path.join(new_ipw_basedir,
                                'ppt_images_dist'))

        assert len(inputs) == np.shape(nc.groups['Input'].variables['T_a'])[0]

        assert len(ppt_images) > 0
        # length of the directory with images should match # lines of ppt_desc
        assert len(ppt_images) == len(open(os.path.join(new_ipw_basedir,
                                           'ppt_desc'), 'r').readlines())

        orig_dir = os.path.join(self.full_nc_base_dir, 'inputs')
        new_dir = os.path.join(new_ipw_basedir, 'inputs')

        i = 0
        for bname in inputs:

            # b = os.path.basename(f)
            orig_f = os.path.join(orig_dir, bname)
            f = os.path.join(new_dir, bname)

            ipw0 = IPW(orig_f)
            ipw = IPW(f)

            df0 = ipw0.data_frame()
            df = ipw.data_frame()

            # in rewritten version we always include S_n for simplicity.
            # in base IPW, S_n (solar rad) gets dropped when sun is "down"
            if 'S_n' not in df0.columns:
                df.drop('S_n', axis=1, inplace=True)

            # http://pandas.pydata.org/pandas-docs/version/0.15.0/basics.html#comparing-if-objects-are-equivalent
            assert all(df0 - df < 0.01), \
                "ipw0:\n%s\n\nipw:\n%s" % \
                (ipw0.data_frame().head(), ipw.data_frame().head())
            i += 1

        assert i == len(inputs), "len(inputs): %s, i: %s" % (len(inputs), i)

        orig_dir = os.path.join(self.full_nc_base_dir, 'ppt_images_dist')
        new_dir = os.path.join(new_ipw_basedir, 'ppt_images_dist')

        i = 0
        for bname in ppt_images:

            # name change for ppt images because I can
            orig_f = os.path.join(orig_dir, 'ppt4b_' + bname.split('_')[1])
            f = os.path.join(new_dir, bname)

            ipw0 = IPW(orig_f, file_type='precip')
            ipw = IPW(f, file_type='precip')

            df0 = ipw0.data_frame()
            df = ipw.data_frame()

            assert all(df0 - df < 0.01), "ipw0:\n%s\n\nipw:\n%s" % \
                (df0.head(), df.head())

            i += 1

        assert i == len(ppt_images), \
            "len(inputs): %s, i: %s" % (len(inputs), i)

        dem_file = os.path.join(new_ipw_basedir, 'dem.ipw')
        mask_file = os.path.join(new_ipw_basedir, 'mask.ipw')
        init_file = os.path.join(new_ipw_basedir, 'init.ipw')

        # clumsy but enough for now to check that these files are not empty
        assert len(open(dem_file).readlines()) > 0

        assert len(open(mask_file).readlines()) > 0

        assert len(open(init_file).readlines()) > 0

        dem0_f = os.path.join(self.full_nc_base_dir, 'tl2p5_dem.ipw')
        df0 = IPW(dem0_f, file_type='dem').data_frame()
        df = IPW(dem_file, file_type='dem').data_frame()
        assert all(df0 - df < 0.01)

        mask_f0 = os.path.join(self.full_nc_base_dir, 'tl2p5mask.ipw')
        df0 = IPW(mask_f0, file_type='mask').data_frame()
        df = IPW(mask_file, file_type='mask').data_frame()
        assert all(df0 - df < 0.01)

        init0_f = os.path.join(self.full_nc_base_dir, 'init.ipw')
        df0 = IPW(init0_f, file_type='init').data_frame()
        df = IPW(init_file, file_type='init').data_frame()
        assert all(df0 - df < 0.01)


def _validate_input_nc(test_obj, nc, type_='inputs'):
    # helper for getting varnames within a group
    group_varnames = lambda g: [var for var in nc.groups[g].variables]

    if type_ == 'inputs':

        g = 'Input'

        assert group_varnames(g) == ['I_lw', 'T_a', 'e_a', 'u', 'T_g', 'S_n']

        for varname in group_varnames(g):

            curvar = nc.groups[g].variables[varname]

            assert curvar.shape == (16, test_obj.nlines, test_obj.nsamps),\
                "wrong shape: %s should be %s" %\
                (str(curvar.shape), (16, test_obj.nlines, test_obj.nsamps))

            if varname in ['I_lw', 'T_a', 'e_a', 'u']:
                assert all(abs(np.ravel(curvar)) > 0) and\
                    all(abs(np.ravel(curvar)) < 1e6)

        g = 'Initial'
        assert group_varnames(g) == \
            ['z', 'z_0', 'z_s', 'rho', 'T_s_0', 'T_s', 'h2o_sat']

        for varname in group_varnames(g):

            curvar = nc.groups[g].variables[varname]

            assert nc.groups[g].variables[varname].shape ==\
                (test_obj.nlines, test_obj.nsamps)

            if varname in ['z', 'z_0']:
                assert all(abs(np.ravel(curvar)) > 0) and\
                    all(abs(np.ravel(curvar)) < 1e6)

        g = 'Precipitation'
        assert group_varnames(g) ==\
            ['m_pp', 'percent_snow', 'rho_snow', 'T_pp']

        ppt_idx = [int(ppt_line.strip().split('\t')[0])
                   for ppt_line in
                   open('wcwave_adaptors/test/data/ppt_desc', 'r').readlines()]

        for idx, varname in enumerate(group_varnames(g)):

            curvar = nc.groups[g].variables[varname]

            assert curvar.shape == (16, test_obj.nlines, test_obj.nsamps)

            if idx in ppt_idx:
                if varname in ['m_pp', 'rho_snow', 'T_pp']:
                    assert all(abs(np.ravel(curvar[idx])) > 0) and\
                        all(abs(np.ravel(curvar[idx])) < 1e6)

            else:
                assert all(np.ravel(curvar[idx]) > 1e6)

        # check DEM, mask are present as expected
        assert nc.variables['alt'].shape == (test_obj.nlines, test_obj.nsamps)
        assert nc.variables['mask'].shape == (test_obj.nlines, test_obj.nsamps)

        assert np.sum(nc.variables['mask']) == 2575

    elif type_ == 'outputs':

        g = 'em'
        assert group_varnames(g) == ['R_n', 'H', 'L_v_E', 'G', 'M', 'delta_Q',
                                     'E_s', 'melt', 'ro_predict', 'cc_s']

        for varname in group_varnames(g):

            curvar = nc.groups[g].variables[varname]

            assert curvar.shape == (16, test_obj.nlines, test_obj.nsamps),\
                "wrong shape: %s should be %s" %\
                (str(curvar.shape), (16, test_obj.nlines, test_obj.nsamps))

            assert all(abs(np.ravel(curvar)) >= 0) and\
                all(abs(np.ravel(curvar)) < 1e6)

        g = 'snow'

        assert group_varnames(g) == ['z_s', 'rho', 'm_s', 'h2o', 'T_s_0',
                                     'T_s_l', 'T_s', 'z_s_l', 'h2o_sat']

        for varname in group_varnames(g):

            curvar = nc.groups[g].variables[varname]

            assert curvar.shape == (16, test_obj.nlines, test_obj.nsamps),\
                "wrong shape: %s should be %s" %\
                (str(curvar.shape), (16, test_obj.nlines, test_obj.nsamps))

            assert all(abs(np.ravel(curvar)) >= 0) and\
                all(abs(np.ravel(curvar)) < 1e6)

    else:
        raise Exception('_validate_input_nc requires type_ to be \'inputs\' or\
                         \'outputs\'')

    # test easting, northing, lat, lon, and time variables exist at all t
    for varname in ['time', 'easting', 'lat', 'lon']:
        curvar = nc.variables[varname]
        assert all(abs(np.ravel(curvar[:])) >= 0) and all(abs(np.ravel(curvar[:])) < 1e6), \
            'Defaults still present for dimension {}'.format(varname)

    # make sure there is no dumb stuff going on like this
    assert all(np.ravel(nc.variables['lat'][:] - nc.variables['lon'][:]))

    north = nc.variables['northing']
    assert all(abs(north[:]) > 0) and all(abs(north[:]) < 5e7)


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
                             nlines=50, nsamps=10, dt='hours', year=2010,
                             month=10, day="01")

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
