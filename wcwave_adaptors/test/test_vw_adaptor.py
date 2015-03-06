"""
Testing module for Virtual Watershed Data adaptor.
"""

from wcwave_adaptors.watershed import make_watershed_metadata, make_fgdc_metadata, \
    VWClient, default_vw_client, get_config, upsert, metadata_from_file

import datetime
import json
import pandas as pd
import os
import requests
import time
import unittest
from uuid import uuid4

from difflib import Differ
from requests.exceptions import HTTPError

from nose.tools import raises

from wcwave_adaptors.isnobal import VARNAME_DICT


def show_string_diff(s1, s2):
    """ Writes differences between strings s1 and s2 """
    d = Differ()
    diff = d.compare(s1.splitlines(), s2.splitlines())
    diffList = [el for el in diff
                if el[0] != ' ' and el[0] != '?']

    for l in diffList:

        if l[0] == '+':
            print '+' + bcolors.GREEN + l[1:] + bcolors.ENDC
        elif l[0] == '-':
            print '-' + bcolors.RED + l[1:] + bcolors.ENDC
        else:
            assert False, 'Error, diffList entry must start with + or -'


class bcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'

VW_CLIENT = default_vw_client('wcwave_adaptors/test/test.conf')


class TestJSONMetadata(unittest.TestCase):
    """ Test that individual and sets of JSON metadata are being properly
        generated. """
    def setUp(self):
        """
        initialize the class with some appropriate entry
        metadata from file
        """
        self.config = get_config('wcwave_adaptors/test/test.conf')

        self.modelRunUUID = '09079630-5ef8-11e4-9803-0800200c9a66'
        self.parentModelRunUUID = '373ae181-a0b2-4998-ba32-e27da190f6dd'

    def testCorrectMetadatum(self):
        """ Test that a single metadata JSON string is properly built (JSON)"""
        # Run test for 'inputs' model_set
        # create metadata file
        model_set = 'inputs'
        description = 'Testing metadata!'
        model_vars = 'R_n,H,L_v_E,G,M,delta_Q'
        fgdcMetadata = '<XML>yup.</XML>'
        dataFile = 'wcwave_adaptors/test/data/i_dont_exist.data'
        start_datetime = datetime.datetime(2010, 10, 01, 0)
        end_datetime = datetime.datetime(2010, 10, 01, 1)
        generated = make_watershed_metadata(dataFile,
                                          self.config,
                                          self.parentModelRunUUID,
                                          self.modelRunUUID,
                                          model_set,
                                          description,
                                          model_vars,
                                          fgdcMetadata,
                                          start_datetime,
                                          end_datetime
                                          )
        # load expected json metadata file
        expected = open('wcwave_adaptors/test/data/expected1_in.json', 'r').read()

        # check equality
        assert generated == expected, \
            show_string_diff(generated, expected)

        dataFile = 'wcwave_adaptors/test/data/fake_output.tif'
        model_set = 'outputs'
        generated = make_watershed_metadata(dataFile,
                                          self.config,
                                          self.parentModelRunUUID,
                                          self.modelRunUUID,
                                          model_set,
                                          description,
                                          model_vars,
                                          fgdcMetadata,
                                          start_datetime,
                                          end_datetime
                                          )
        # load expected json metadata file
        expected = \
            open('wcwave_adaptors/test/data/expected_w_services.json', 'r').read()

        # check equality
        assert generated == expected, \
            show_string_diff(generated, expected)


class TestFGDCMetadata(unittest.TestCase):
    """ Test individual and sets of XML FGDC-standard metadata are being
        properly generated and uploaded to the Virtual Watershed
    """
    def setUp(self):
        """ initialize the class with some appropriate entry
            metadata from file
        """
        self.config = get_config('wcwave_adaptors/test/test.conf')

        self.modelRunUUID = '09079630-5ef8-11e4-9803-0800200c9a66'
        self.dataFile = 'wcwave_adaptors/test/data/in.0000'

    def testCorrectMetadatum(self):
        """ Test that a single metadata JSON string is properly built (FGDC)"""

        generated = make_fgdc_metadata(self.dataFile, self.config,
                                       self.modelRunUUID)

        expected = open('wcwave_adaptors/test/data/expected1_in.xml', 'r').read()
        assert generated == expected, \
            show_string_diff(generated, expected)


class TestVWClient(unittest.TestCase):
    """ Test the functionality of the Virtual Watershed client """
    def setUp(self):

        self.config = get_config('wcwave_adaptors/test/test.conf')

        self.kwargs = {'keywords': 'Snow,iSNOBAL,wind',
                       'researcher_name': self.config['Common']['researcherName'],
                       'description': 'unittest',
                       'model_run_name': 'unittest' + str(uuid4())}

        self.UUID = VW_CLIENT.initialize_model_run(**self.kwargs)

        self.parent_uuid = self.UUID

        upsert('wcwave_adaptors/test/data/in.0000', 'unittest insert for download',
               parent_model_run_uuid=self.parent_uuid,
               model_run_uuid=self.UUID, config_file='wcwave_adaptors/test/test.conf')

        time.sleep(1)

    def test_initialize_model_run(self):
        """
        Test that a new model_run_uuid corresponding to new model run is properly initialized
        """
        kwargs = {'keywords': 'Snow,iSNOBAL,wind',
                  'researcher_name': 'Matthew Turner',
                  'description': 'model run db testing',
                  'model_run_name': 'initialize unittest ' + str(uuid4())}

        new_uuid = \
            VW_CLIENT.initialize_model_run(**kwargs)

        result = VW_CLIENT.search(model_run_uuid=new_uuid)

        assert result.total == 0, \
            'Result does not exist?? result.total = %d' % result.total

    @raises(HTTPError)
    def test_duplicate_error(self):
        """
        If the user tries to init a new model run with a previously used name, catch HTTPError
        """
        keywords = 'Snow,iSNOBAL,wind'
        description = 'model run db testing'

        model_run_name = 'dup_test ' + str(uuid4())

        VW_CLIENT.initialize_model_run(keywords=keywords,
                                       description=description,
                                       model_run_name=model_run_name,
                                       researcher_name=self.config['Common']['researcherName'])

        print "first inserted successfully"

        # TODO get watershed guys to make researcher, model run name be PK
        # at that point, this test will fail, but re-inserting Bill's
        # fake submission will throw

        VW_CLIENT.initialize_model_run(keywords=keywords,
                                       researcher_name=self.config['Common']['researcherName'],
                                       description=description,
                                       model_run_name=model_run_name)

    @raises(HTTPError)
    def test_authFail(self):
        """ Test that failed authorization is correctly caught """
        actualVWip = '129.24.196.23'
        VWClient(actualVWip, 'fake_user', 'fake_passwd')

    def test_insert(self):
        """ VW Client properly inserts data """
        kwargs = {'keywords': 'Snow,iSNOBAL,wind',
                  'researcher_name': self.config['Common']['researcherName'],
                  'description': 'unittest',
                  'model_run_name': 'unittest' + str(uuid4())}
        UUID = \
            VW_CLIENT.initialize_model_run(**kwargs)

        VW_CLIENT.upload(UUID, 'wcwave_adaptors/test/data/in.0000')

        dataFile = 'wcwave_adaptors/test/data/in.0000'

        fgdcXML = \
            make_fgdc_metadata(dataFile, self.config, modelRunUUID=UUID)

        watershedJSON = \
            make_watershed_metadata(dataFile, self.config, UUID,
                                    UUID, 'inputs',
                                    'Description of the data',
                                    model_vars='R_n,H,L_v_E,G,M,delta_Q',
                                    fgdcMetadata=fgdcXML)

        VW_CLIENT.insert_metadata(watershedJSON)

        vwTestUUIDEntries = VW_CLIENT.search(model_run_uuid=UUID)

        assert vwTestUUIDEntries,\
            'No VW Entries corresponding to the test UUID'

    @raises(HTTPError)
    def test_insertFail(self):
        """ VW Client throws error on failed insert"""
        VW_CLIENT.insert_metadata('{"metadata": {"xml": "mo garbage"}}')

    def test_upload(self):
        """ VW Client properly uploads data """
        # fetch the file from the url we know from the VW file storage pattern
        results = \
            VW_CLIENT.search(model_run_uuid=self.UUID, limit=1)

        url = results.records[0]['downloads'][0]['bin']

        outfile = "wcwave_adaptors/test/data/back_in.0000"

        if os.path.isfile(outfile):
            os.remove(outfile)

        VW_CLIENT.download(url, outfile)

        # check that the file now exists in the file system as expected
        assert os.path.isfile(outfile)

        os.remove(outfile)

    def test_download(self):
        """
        VW Client properly downloads data
        """
        result = \
            VW_CLIENT.search(model_run_uuid=self.UUID, limit=1)

        r0 = result.records[0]
        url = r0['downloads'][0]['bin']

        outfile = "wcwave_adaptors/test/data/test_dl.file"

        if os.path.isfile(outfile):
            os.remove(outfile)

        VW_CLIENT.download(url, outfile)

        assert os.path.isfile(outfile)

        os.remove(outfile)

    @raises(AssertionError)
    def test_downloadFail(self):
        """ VW Client throws error on failed download """
        url = "http://httpbin.org/status/404"

        VW_CLIENT.download(url, "this won't ever exist")


    def test_upsert(self):
        """
        Check that a directory and individual files are correctly uploaded/inserted to VW
        """
        test_conf = "wcwave_adaptors/test/test.conf"
        vwc = default_vw_client(test_conf)

        # convenience for testing upsert performed as expected
        def _worked(p_uuid, UUID, dir_=True, inherited=False):
            time.sleep(1) # pause to let watershed catch up

            if inherited:
                factor = 2
            else:
                factor = 1

            if dir_:
                num_expected = 4 * factor
            else:
                num_expected = 1 * factor

            res = vwc.search(model_run_uuid=UUID)
            print "testing model_run_uuid %s" % UUID
            assert res.total == num_expected, \
                "Data was not upserted as expected.\n" +\
                "Total inserted: %s, Expected: %s\n" %\
                (res.total, num_expected)
                # "For test on p_uuid=%s, uuid=%s" %\

            i = 0
            for r in res.records:
                assert r['parent_model_run_uuid']
                i += 1

                ftype = r['name'].split('.')[0]
                assert r['model_vars'] == ','.join(VARNAME_DICT[ftype]),\
                    "model vars were not appropriately set!\n" + \
                    "Expected: %s, Generated: %s" %\
                    (','.join(VARNAME_DICT[ftype]), r['model_vars'])

            assert i == num_expected

        upsert_dir = 'wcwave_adaptors/test/data/upsert_test/'

        ## test upsert of entire directory
        # as a brand-new parent/model run
        print "On test 1"
        kwargs = {'keywords': 'Snow,iSNOBAL,wind',
                  'description': 'unittest',
                  'model_run_name': 'unittest' + str(uuid4())}

        print kwargs['model_run_name']
        parent_uuid, UUID = upsert(upsert_dir,
                                   config_file=test_conf, **kwargs)
        _worked(parent_uuid, UUID)

        kwargs = {'keywords': 'Snow,iSNOBAL,wind',
                  'description': 'unittest',
                  'model_run_name': 'unittest' + str(uuid4())}

        # with no slash after directory name
        parent_uuid, UUID = \
            upsert('wcwave_adaptors/test/data/upsert_test',
                   config_file=test_conf, **kwargs)
        _worked(parent_uuid, UUID)

        kwargs = {'keywords': 'Snow,iSNOBAL,wind',
                  'description': 'unittest',
                  'model_run_name': 'unittest' + str(uuid4())}
        # as an existing model run
        inherit_parent = parent_uuid
        parent_uuid, uuid = upsert(upsert_dir, parent_model_run_uuid=inherit_parent,
                                   model_run_uuid=UUID, config_file=test_conf, **kwargs)

        assert parent_uuid == inherit_parent, "Parent UUID not inherited!"

        _worked(parent_uuid, UUID, inherited=True)

        ## test upsert of a single file
        upsert_file = upsert_dir + "/snow.1345"
        # as a brand-new parent/model run
        kwargs = {'keywords': 'Snow,iSNOBAL,wind',
                  'description': 'unittest',
                  'model_run_name': 'unittest' + str(uuid4())}

        parent_uuid, UUID = upsert(upsert_file,
                                   config_file=test_conf, **kwargs)
        _worked(parent_uuid, UUID, dir_=False)

        # with no slash after directory name
        kwargs = {'keywords': 'Snow,iSNOBAL,wind',
                  'description': 'unittest',
                  'model_run_name': 'unittest' + str(uuid4())}

        parent_uuid, UUID = upsert(upsert_file,
                                   config_file=test_conf, **kwargs)

        _worked(parent_uuid, UUID, dir_=False)

        # as a new model run with a parent
        inherit_parent = parent_uuid
        kwargs = {'keywords': 'Snow,iSNOBAL,wind',
                  'description': 'unittest',
                  'model_run_name': 'unittest' + str(uuid4())}
        parent_uuid, UUID = upsert(upsert_file, parent_model_run_uuid=inherit_parent,
                                   model_run_uuid=UUID, config_file=test_conf, **kwargs)

        assert parent_uuid == inherit_parent, "Parent UUID not inherited!"

        _worked(parent_uuid, UUID, dir_=False, inherited=True)

    def test_watershed_connection(self):
        """
        Test watershed functions operating on an IPW instance or as a static method
        """
        # load expected json metadata file
        expected = open('wcwave_adaptors/test/data/expected_ipw_metadata.json',
                        'r').read()

        description = 'Testing metadata!'

        # TODO this gets tests passing; standardize uuids in setUp on nxt rfctr
        parent_uuid = '373ae181-a0b2-4998-ba32-e27da190f6dd'
        uuid = '09079630-5ef8-11e4-9803-0800200c9a66'

        generated = metadata_from_file('wcwave_adaptors/test/data/in.0000',
                                       parent_uuid,
                                       uuid,
                                       description,
                                       config_file='wcwave_adaptors/test/test.conf')

        with open('wcwave_adaptors/test/data/expected_ipw_metadata.json', 'w') as f:
            f.write(generated)

        # check equality
        assert generated
        assert expected
        assert generated == expected, show_string_diff(generated, expected)

    def test_metadata_from_file(self):
        """
        Test that metdata is properly generated from an IPW or .tif file
        """
        # some values we're using for testing
        parent_uuid = '373ae181-a0b2-4998-ba32-e27da190f6dd'
        uuid = '09079630-5ef8-11e4-9803-0800200c9a66'
        # .tif
        generated = metadata_from_file('test/data/em.0134.melt.tif',
            parent_uuid, uuid, 'Testing metadata!',
            config_file='wcwave_adaptors/test/test.conf')

        expected = open('wcwave_adaptors/test/data/expected_tif.json', 'r').read()
        assert generated == expected, \
            show_string_diff(generated, expected)

        # now assume we have resampled to 3-day intervals
        dt = pd.Timedelta('3 days')
        generated = metadata_from_file('test/data/em.100.melt.tif',
            parent_uuid, uuid,
            'Testing metadata!', config_file='wcwave_adaptors/test/test.conf',
            dt=dt)

        expected = open('wcwave_adaptors/test/data/expected_tif_nonhourdt.json',
                        'r').read()
        assert generated == expected, \
            show_string_diff(generated, expected)
