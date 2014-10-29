""" Testing module for Virtual Watershed Data adaptor.
"""

from vw_adaptor import *  # get_all_with_uuid

import unittest


class TestJSONMetadata(unittest.TestCase):
    """ Test that individual and sets of JSON metadata are being properly
        generated. """
    def setUp(self):
        """ initialize the class with some appropriate entry
            metadata from file
        """
        configPath = '/Users/mturner/workspace/adaptors/src/test/test.conf'
        config = configparser.ConfigParser()
        config.read(configPath)
        self.config = config

        self.model_run_uuid = "09079630-5ef8-11e4-9803-0800200c9a66"

    def testCorrectMetadatum(self):
        """ Test that a single metadata JSON string is properly built (JSON)"""
        # Run test for 'inputs' model_set
        # create metadata file
        model_set = "inputs"
        generated = makeWatershedMetadatum('src/test/test1.json', self.config,
                                           self.model_run_uuid, model_set)
        print generated
        # load expected json metadata file
        expected = ""

        # check equality
        assert generated == expected, "generated: %s" % generated
        # Run test for 'outputs' model set
        # create metadata file
        model_set = "outputs"
        generated = makeWatershedMetadatum('src/test/test1.json', self.config,
                                           self.model_run_uuid, model_set)
        # load expected json metadata file
        expected = ""

        # check equality
        assert generated == expected, "generated: %s" % generated

    def testCorrectMetadata(self):
        """ A series of metadata is correctly built (JSON)"""
        assert False

    def testCorrectVWInsert(self):
        """ The metadata has been properly inserted to virtual watershed (JSON)"""
        assert False


class TestFGDCMetadata(unittest.TestCase):
    """ Test individual and sets of XML FGDC-standard metadata are being
        properly generated and uploaded to the Virtual Watershed
    """
    def setUp(self):
        """ initialize the class with some appropriate entry
            metadata from file
        """
        pass

    def testCorrectMetadatum(self):
        """ Test that a single metadata JSON string is properly built (FGDC)"""
        assert False

    def testCorrectMetadata(self):
        """ A series of metadata is correctly built (FGDC)"""
        assert False

    def testCorrectVWInsert(self):
        """ The metadata has been properly inserted to virtual watershed (FGDC)"""
        assert False


# class TestUUID(unittest.TestCase):
    # """ Tests for getting data using a UUID """

    # def test_enforce_uuid_is_string(self):
        # """ Disallow non-string UUIDs """

        # numRun = 0
        # for badUUID in (42, 2.233, {'hey': 'joe'}):
            # with self.assertRaises(AssertionError):
                # numRun += 1
                # get_all_with_uuid(badUUID)

        # assert numRun == 3, "Test did not run! numRun="+str(numRun)

    # def test_get_all_with_uuid(self):
        # """ Make sure we return something """
        # assert get_all_with_uuid("2202-1120-AXFF-")
