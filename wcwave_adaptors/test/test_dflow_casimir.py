"""
Tests for posting/ingetsting dflow and casimir data to each respective model
to/from the virtual watershed.
"""
import unittest

from nose.tools import eq_
from datetime import datetime

from ..dflow_casimir import ESRIAsc, vegcode_to_nvalue, get_vw_nvalues

from ..watershed import (default_vw_client, make_fgdc_metadata,
                         metadata_from_file, _get_config)


class TestDflow(unittest.TestCase):
    """
    Functions for working with DFLOW inputs and outputs
    """
    def setUp(self):
        self.ascii_veg = 'wcwave_adaptors/test/data/dflow_casimir/vegcode.asc'
        self.excel_veg_to_nval = \
            'wcwave_adaptors/test/data/dflow_casimir/lookup_table.xlsx'
        self.expected_ascii_roughness = \
            'wcwave_adaptors/test/data/dflow_casimir/roughness.asc'

        self.expected_ascii_nvals = \
            ESRIAsc(self.expected_ascii_roughness)

        self.config = _get_config('wcwave_adaptors/test/test.conf')

        self.vwc = default_vw_client()

        modelruns = self.vwc.modelrun_search()
        unittest_uuids = [r['Model Run UUID'] for r in modelruns.records
                          if 'unittest' in r['Model Run Name']]

        for u in unittest_uuids:
            s = self.vwc.delete_modelrun(u)
            print "pre-test cleanup success on %s: %s" % (u, str(s))

        self.model_run_uuid = \
            self.vwc.initialize_modelrun('dflow_casimir unittest',
                                         'unittest run '.format(datetime.now()),
                                         'wcwave_adaptors unittester',
                                         'test,unittest')


    def test_asc_veg_to_nvals(self):
        "Properly build nvals ESRI .asc from vegetation code .asc and lookup table"
        ascii_nvals = vegcode_to_nvalue(self.ascii_veg, self.excel_veg_to_nval)

        eq_(ascii_nvals, self.expected_ascii_nvals)

    def test_vw_vegcode_to_nvalue(self):
        "Fetch vegcode ESRI .asc and Excel lookup table from VW and build roughness .asc"
        # upload test data
        self.vwc.upload(self.model_run_uuid, self.ascii_veg)
        self.vwc.upload(self.model_run_uuid, self.excel_veg_to_nval)

        # create and insert vegetation map metadata
        veg_fgdc_md = make_fgdc_metadata(self.ascii_veg, self.config,
            self.model_run_uuid, "2010-10-01 00:00:00", "2010-10-01 01:00:00")

        asc_veg_md = metadata_from_file(self.ascii_veg, self.model_run_uuid,
            self.model_run_uuid, 'vegetation ascii for unittest',
            'Valles Caldera', 'New Mexico', model_name='HydroGeoSphere',
            epsg=4326, orig_epsg=26911, model_set_taxonomy='file',
            model_set_type='file', file_ext='ascii', fgdc_metadata=veg_fgdc_md,
            start_datetime='2010-10-01 00:00:00', taxonomy='file',
            end_datetime='2011-09-30 23:00:00')

        self.vwc.insert_metadata(asc_veg_md)

        lookup_fgdc_md = make_fgdc_metadata(self.excel_veg_to_nval,
            self.config, self.model_run_uuid, "2010-10-01 00:00:00",
            "2010-10-01 01:00:00")

        lookup_md = metadata_from_file(self.excel_veg_to_nval, self.model_run_uuid,
            self.model_run_uuid, 'veg/nval lookup Excel sheet for unittest',
            'Valles Caldera', 'New Mexico', model_name='HydroGeoSphere',
            epsg=4326, orig_epsg=26911, model_set_taxonomy='file',
            model_set_type='grid', file_ext='xlsx', taxonomy='file',
            model_set='inputs',
            fgdc_metadata=lookup_fgdc_md, start_datetime='2010-10-01 00:00:00',
            end_datetime='2011-09-30 23:00:00')

        self.vwc.insert_metadata(lookup_md)

        import ipdb; ipdb.set_trace()

        ascii_nvals = get_vw_nvalues(self.model_run_uuid)

        eq_(ascii_nvals, self.expected_ascii_nvals)

        assert False

    def test_unstruc_mesh_to_ascii(self):
        assert False
