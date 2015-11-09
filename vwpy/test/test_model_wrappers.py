"""
Tests for the modeling interface of the virtual watershed platform
"""
import time
import unittest

from xray import open_dataset

from ..watershed import default_vw_client, metadata_from_file

from ..vw_model_wrappers import vw_isnobal


class IsnobalWrapperTestCase(unittest.TestCase):

    def setUp(self):

        # netcdfs we'll use for input and check output against
        nc_isnobal_input = 'vwpy/test/data/isnobal_input.nc'
        nc_isnobal_output = 'vwpy/test/data/isnobal_output.nc'

        # connect to the virtual watershed
        self.vwc = default_vw_client()

        # load NetCDF inputs and outputs from test data
        self.input_dataset = open_dataset(nc_isnobal_input)
        self.output_dataset = open_dataset(nc_isnobal_output)

        # insert NetCDF test input to virtual watershed
        input_mr_name = 'webapp-testing-input'

        modelruns = self.vwc.modelrun_search()
        unittest_uuids = [r['Model Run UUID'] for r in modelruns.records
                          if r['Model Run Name'] == 'webapp-testing-input']

        for u in unittest_uuids:
            s = self.vwc.delete_modelrun(u)
            print "pre-test cleanup success on %s: %s" % (u, str(s))

        self.model_run_uuid = \
            self.vwc.initialize_modelrun(
                model_run_name=input_mr_name,
                description='test in vwplatform',
                researcher_name='Matt Turner',
                keywords='test,isnobal,webapp')

        self.vwc.upload(self.model_run_uuid, nc_isnobal_input)

        self.start_datetime = '2010-10-01 00:00:00'
        self.end_datetime = '2010-10-01 16:00:00'

        md = metadata_from_file(nc_isnobal_input, self.model_run_uuid,
                                self.model_run_uuid,
                                'test input for isnobal run',
                                'Dry Creek', 'Idaho', model_name='isnobal',
                                start_datetime=self.start_datetime,
                                end_datetime=self.end_datetime,
                                model_set='inputs', taxonomy='geoimage',
                                model_set_taxonomy='grid')
        # import ipdb; ipdb.set_trace()

        self.input_uuid = self.vwc.insert_metadata(md).text

        time.sleep(1)

    def test_isnobal(self):
        """Test iSNOBAL wrapper is working properly"""

        # vw_isnobal gives the user the uuid of the file
        vw_isnobal(self.input_uuid)

        # download output file
        output_records = \
            self.vwc.dataset_search(model_run_uuid=self.model_run_uuid,
                                    model_set="outputs").records

        assert len(output_records) == 1, \
            "more than one output record for isnobal test"

        dl_url = output_records[0]['downloads'][0]['nc']

        self.vwc.download(dl_url, 'test/data/nc_out_fromvw.tmp')

        # compare output file from VW to expected
        dataset_from_vw = open_dataset('test/data/nc_out_fromvw.tmp')

        assert dataset_from_vw.identical(self.output_dataset)
