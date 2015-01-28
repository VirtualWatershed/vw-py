"""
Module for testing web app functionality.
"""
from ..app import make_model_run_panels

import unittest


class TestApp(unittest.TestCase):
    """
    Tests for our 'human adaptor', the web app. Check things like if HTML has
    been built as expected.
    """
    def setUp(self):
        pass

    def test_make_model_boxes(self):
        """
        Check that our search browsing page correctly builds test examples
        """
        generated_panels = \
            open('adaptors/human/test/data/expected_modelrun_boxes.html',
                 'r').read()

        search_results = ""
        expected_panels = make_model_run_panels(search_results)

        assert generated_panels == expected_panels
