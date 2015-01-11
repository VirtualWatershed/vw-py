"""
Testing module for Virtual Watershed Data adaptor.
"""

from adaptors.watershed import makeWatershedMetadata, makeFGDCMetadata, \
    VWClient, default_vw_client, get_config, upsert, metadata_from_file

import json
import os
import requests
import time
import unittest

from difflib import Differ
from datetime import datetime
from requests.exceptions import HTTPError

from nose.tools import raises

from adaptors.isnobal import VARNAME_DICT


def show_string_diff(s1, s2):
    """ Writes differences between strings s1 and s2 """
    d = Differ()
    diff = d.compare(s1.splitlines(), s2.splitlines())
    diffList = [el for el in diff
                if el[0] != ' ' and el[0] != '?']

    for l in diffList:

        if l[0] == '+':
            print "+" + bcolors.GREEN + l[1:] + bcolors.ENDC
        elif l[0] == '-':
            print "-" + bcolors.RED + l[1:] + bcolors.ENDC
        else:
            assert False, "Error, diffList entry must start with + or -"


class bcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'


class TestJSONMetadata(unittest.TestCase):
    """ Test that individual and sets of JSON metadata are being properly
        generated. """
    def setUp(self):
        """
        initialize the class with some appropriate entry
        metadata from file
        """
        self.config = get_config("adaptors/test/test.conf")

        self.modelRunUUID = "09079630-5ef8-11e4-9803-0800200c9a66"
        self.parentModelRunUUID = "373ae181-a0b2-4998-ba32-e27da190f6dd"

    def testCorrectMetadatum(self):
        """ Test that a single metadata JSON string is properly built (JSON)"""
        # Run test for 'inputs' model_set
        # create metadata file
        model_set = "inputs"
        description = "Testing metadata!"
        model_vars = "R_n,H,L_v_E,G,M,delta_Q"
        fgdcMetadata = "<XML>yup.</XML>"
        dataFile = "adaptors/test/data/i_dont_exist.data"
        start_datetime = datetime(2010, 10, 01, 0)
        end_datetime = datetime(2010, 10, 01, 1)
        generated = makeWatershedMetadata(dataFile,
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
        expected = open("adaptors/test/data/expected1_in.json", 'r').read()

        # check equality
        assert generated == expected, \
            show_string_diff(generated, expected)

        dataFile = "adaptors/test/data/fake_output.tif"
        model_set = "outputs"
        generated = makeWatershedMetadata(dataFile,
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
            open("adaptors/test/data/expected_w_services.json", 'r').read()

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
        self.config = get_config("adaptors/test/test.conf")

        self.modelRunUUID = "09079630-5ef8-11e4-9803-0800200c9a66"
        self.dataFile = "adaptors/test/data/in.0000"

    def testCorrectMetadatum(self):
        """ Test that a single metadata JSON string is properly built (FGDC)"""

        generated = makeFGDCMetadata(self.dataFile, self.config,
                                     self.modelRunUUID)

        expected = open("adaptors/test/data/expected1_in.xml", 'r').read()
        assert generated == expected, \
            show_string_diff(generated, expected)


class TestVWClient(unittest.TestCase):
    """ Test the functionality of the Virtual Watershed client """

    def setUp(self):

        self.vw_client = default_vw_client("adaptors/test/test.conf")

        self.uuid = self.vw_client.initialize_model_run("unittest")
        self.parent_uuid = self.uuid

        self.config = get_config("adaptors/test/test.conf")

        upsert("adaptors/test/data/in.0000", "unittest insert for download",
               parent_model_run_uuid=self.parent_uuid,
               model_run_uuid=self.uuid, config_file="adaptors/test/test.conf")

        time.sleep(1)

    def test_initialize_model_run(self):
        """
        Test that a new model_run_uuid corresponding to new model run is properly initialized
        """
        new_uuid = \
            self.vw_client.initialize_model_run("testing initialization")

        result = self.vw_client.search(model_run_uuid=new_uuid)

        assert result.total == 0, \
            "Result does not exist?? result.total = %d" % result.total

    @raises(HTTPError)
    def test_authFail(self):
        """ Test that failed authorization is correctly caught """
        actualVWip = "129.24.196.43"
        VWClient(actualVWip, "fake_user", "fake_passwd")

    def test_insert(self):
        """ VW Client properly inserts data """

        hostname = self.config['Common']['watershedIP']
        modelIdUrl = "https://" + hostname + "/apps/my_app/newmodelrun"

        data = {"description": "initial insert"}

        result = \
            requests.post(modelIdUrl, data=json.dumps(data),
                          auth=(self.vw_client.uname, self.vw_client.passwd),
                          verify=False)

        uuid = result.text

        self.vw_client.upload(uuid, "adaptors/test/data/in.0000")

        dataFile = "adaptors/test/data/in.0000"

        fgdcXML = \
            makeFGDCMetadata(dataFile, self.config, modelRunUUID=uuid)

        watershedJSON = \
            makeWatershedMetadata(dataFile, self.config, uuid,
                                  uuid, "inputs",
                                  "Description of the data",
                                  model_vars="R_n,H,L_v_E,G,M,delta_Q",
                                  fgdcMetadata=fgdcXML)

        self.vw_client.insert_metadata(watershedJSON)

        vwTestUUIDEntries = self.vw_client.search(model_run_uuid=uuid)

        assert vwTestUUIDEntries,\
            "No VW Entries corresponding to the test UUID"

    @raises(HTTPError)
    def test_insertFail(self):
        """ VW Client throws error on failed insert"""
        self.vw_client.insert_metadata('{"metadata": {"xml": "mo garbage"}}')

    def test_upload(self):
        """ VW Client properly uploads data """
        # fetch the file from the url we know from the VW file storage pattern
        results = \
            self.vw_client.search(model_run_uuid=self.uuid, limit=1)

        url = results.records[0]['downloads'][0]['bin']

        outfile = "adaptors/test/data/back_in.0000"

        if os.path.isfile(outfile):
            os.remove(outfile)

        self.vw_client.download(url, outfile)

        # check that the file now exists in the file system as expected
        assert os.path.isfile(outfile)

        os.remove(outfile)

    def test_download(self):
        """
        VW Client properly downloads data
        """
        result = \
            self.vw_client.search(model_run_uuid=self.uuid, limit=1)

        r0 = result.records[0]
        url = r0['downloads'][0]['bin']

        outfile = "adaptors/test/data/test_dl.file"

        if os.path.isfile(outfile):
            os.remove(outfile)

        self.vw_client.download(url, outfile)

        assert os.path.isfile(outfile)

        os.remove(outfile)

    @raises(AssertionError)
    def test_downloadFail(self):
        """ VW Client throws error on failed download """
        url = "http://httpbin.org/status/404"

        self.vw_client.download(url, "this won't ever exist")



    def test_upsert(self):
        """
        Check that a directory and individual files are correctly uploaded/inserted to VW
        """
        test_conf = "adaptors/test/test.conf"
        vwc = default_vw_client(test_conf)
        description = "Unit testing upsert"

        # convenience for testing upsert performed as expected
        def _worked(p_uuid, uuid, dir_=True, inherited=False):
            time.sleep(1) # pause to let watershed catch up

            if inherited:
                factor = 2
            else:
                factor = 1

            if dir_:
                num_expected = 4 * factor
            else:
                num_expected = 1 * factor

            res = vwc.search(model_run_uuid=uuid)
            print "testing model_run_uuid %s" % uuid
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

        upsert_dir = 'adaptors/test/data/upsert_test/'

        ## test upsert of entire directory
        # as a brand-new parent/model run
        print "On test 1"
        parent_uuid, uuid = upsert(upsert_dir, description,
                                   config_file=test_conf)
        _worked(parent_uuid, uuid)

        # with no slash after directory name
        parent_uuid, uuid = upsert('adaptors/test/data/upsert_test',
                                   description, config_file=test_conf)
        _worked(parent_uuid, uuid)

        # as an existing model run
        inherit_parent = parent_uuid
        parent_uuid, uuid = upsert(upsert_dir, description, inherit_parent,
                                   uuid, config_file=test_conf)

        assert parent_uuid == inherit_parent, "Parent UUID not inherited!"

        _worked(parent_uuid, uuid, inherited=True)

        ## test upsert of a single file
        upsert_file = upsert_dir + "/snow.1345"
        # as a brand-new parent/model run
        parent_uuid, uuid = upsert(upsert_file, description,
                                   config_file=test_conf)
        _worked(parent_uuid, uuid, dir_=False)

        # with no slash after directory name
        parent_uuid, uuid = upsert(upsert_file, description,
                                   config_file=test_conf)
        _worked(parent_uuid, uuid, dir_=False)

        # as a new model run with a parent
        inherit_parent = parent_uuid
        parent_uuid, uuid = upsert(upsert_file, description, inherit_parent,
                                   uuid, config_file=test_conf)

        assert parent_uuid == inherit_parent, "Parent UUID not inherited!"

        _worked(parent_uuid, uuid, dir_=False, inherited=True)

    def test_watershed_connection(self):
        """
        Test watershed functions operating on an IPW instance or as a static method
        """
        # load expected json metadata file
        expected = open("adaptors/test/data/expected_ipw_metadata.json", 'r').read()

        description = "Testing metadata!"

        generated = metadata_from_file(self.test_file,
                                       self.parent_model_run_uuid,
                                       self.model_run_uuid,
                                       description,
                                       config_file="adaptors/test/test.conf")

        # with open("adaptors/test/data/expected_ipw_metadata.json", 'w') as f:
            # f.write(generated)

        # check equality
        assert generated == expected, show_string_diff(generated, expected)

    def test_metadata_from_file(self):
        """
        Test that metdata is properly generated from an IPW or .tif file
        """
        # .tif
        generated = metadata_from_file("test/data/em.0134.melt.tif",
            self.parent_model_run_uuid, self.model_run_uuid,
            "Testing metadata!", config_file="adaptors/test/test.conf")

        expected = open("adaptors/test/data/expected_tif.json", 'r').read()
        assert generated == expected, \
            show_string_diff(generated, expected)

        # now assume we have resampled to 3-day intervals
        dt = pd.Timedelta('3 days')
        generated = metadata_from_file("test/data/em.100.melt.tif",
            self.parent_model_run_uuid, self.model_run_uuid,
            "Testing metadata!", config_file="adaptors/test/test.conf",
            dt=dt)

        expected = open("adaptors/test/data/expected_tif_nonhourdt.json",
                        'r').read()
        assert generated == expected, \
            show_string_diff(generated, expected)
