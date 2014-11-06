""" Testing module for Virtual Watershed Data adaptor.
"""

from vw_adaptor import *  # get_all_with_uuid

import unittest
import sys

from difflib import Differ


def showStringDiff(s1, s2):
    """ Writes differences between strings s1 and s2 """
    d = Differ()
    diff = d.compare(s1.splitlines(), s2.splitlines())
    # diffList = [ el.strip().replace(' ', '') + '\n' for el in diff
    diffList = [ el + '\n' for el in diff
                if el[0] != ' ' and el[0] != '?' ]

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
        """ initialize the class with some appropriate entry
            metadata from file
        """
        configPath = "/Users/mturner/workspace/adaptors/src/test/test.conf"
        config = configparser.ConfigParser()
        config.read(configPath)
        self.config = config

        self.model_run_uuid = "09079630-5ef8-11e4-9803-0800200c9a66"
        self.parent_model_run_uuid = "373ae181-a0b2-4998-ba32-e27da190f6dd"

    def testCorrectMetadatum(self):
        """ Test that a single metadata JSON string is properly built (JSON)"""
        # Run test for 'inputs' model_set
        # create metadata file
        model_set = "inputs"
        generated = makeWatershedMetadatum("src/test/data/i_dont_exist.data",
                                           self.config, self.model_run_uuid,
                                           model_set,
                                           "Testing metadata!",
                                           "/Users/mturner/workspace/adaptors/scripts/inputs/54/549068c5-a136-4b86-a1b2-e862b943d837/XML/in.00.xml"
                                           )
        # load expected json metadata file
        expected = open("src/test/data/expected1_in.json", 'r').read()

        # check equality
        assert generated == expected, "generated: %s\n\nexpected:\n%s" % \
            (generated, expected)

        # TODO Run test for 'outputs' model set??? No, but do for output with
        # 'services'

    def testCorrectMetadata(self):
        """ A series of metadata is correctly built (JSON)"""
        assert False


class TestFGDCMetadata(unittest.TestCase):
    """ Test individual and sets of XML FGDC-standard metadata are being
        properly generated and uploaded to the Virtual Watershed
    """
    def setUp(self):
        """ initialize the class with some appropriate entry
            metadata from file
        """
        configPath = "/Users/mturner/workspace/adaptors/src/test/test.conf"
        config = configparser.ConfigParser()
        config.read(configPath)
        self.config = config

        self.model_run_uuid = "09079630-5ef8-11e4-9803-0800200c9a66"
        self.parent_model_run_uuid = "373ae181-a0b2-4998-ba32-e27da190f6dd"
        self.dataFile = "src/test/data/in.00"

    def testCorrectMetadatum(self):
        """ Test that a single metadata JSON string is properly built (FGDC)"""

        generated = makeFGDCMetadatum(self.dataFile, self.config,
                                      self.model_run_uuid)

        expected = open("src/test/data/expected1_in.xml", 'r').read()
        assert generated == expected, \
            showStringDiff(generated, expected)

    def testCorrectMetadata(self):
        """ A series of metadata is correctly built (FGDC)"""
        assert False


class TestVWClient(unittest.TestCase):
    """ Test the functionality of the Virtual Watershed client """
    def setUp(self):
        pass

    # TODO not a test until we prepend "test" somewheres
    def insert(self, args):
        """ Does VW Client properly insert data? """
        assert False
