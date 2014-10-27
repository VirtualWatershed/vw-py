""" Testing module for Virtual Watershed Data adaptor.
"""

from vw_adaptor import get_all_with_uuid

import unittest


class TestUUID(unittest.TestCase):
    """ Tests for getting data using a UUID """

    def test_enforce_uuid_is_string(self):
        """ Disallow non-string UUIDs """

        numRun = 0
        for badUUID in (42, 2.233, {'hey': 'joe'}):

            with self.assertRaises(AssertionError):
                numRun += 1
                get_all_with_uuid(badUUID)

        assert numRun == 3, "Test did not run! numRun="+str(numRun)

    def test_get_all_with_uuid(self):
        """ Make sure we return something """
        assert get_all_with_uuid("2202-1120-AXFF-")
