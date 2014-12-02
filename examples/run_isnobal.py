#!/usr/local/bin/python
"""
Usage: ./run_isnobal inputDir outputDir

Developed to be run in conjunction with GNU Parallel or some other runner that
first generates a list of in/out dirs
"""

import sys
import os
from adaptors.src.isnobal_adaptor import isnobal

inputDir = sys.argv[1]
outputDir = sys.argv[2]

input_prefix = inputDir + "/in"
em_prefix = outputDir + "/em"
snow_prefix = outputDir + "/snow"

if not os.path.exists(outputDir):
    os.makedirs(outputDir)

# assumes a full run with 8758 steps and 8759 input files
isnobal(input_prefix=input_prefix, em_prefix=em_prefix,
        snow_prefix=snow_prefix)
