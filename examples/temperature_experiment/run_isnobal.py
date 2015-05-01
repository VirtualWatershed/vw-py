#!/usr/local/bin/python
"""
Usage: ./run_isnobal inputDir outputDir

Developed to be run in conjunction with GNU Parallel or some other runner that
first generates a list of in/out dirs
"""

import sys
import os

sys.path.append('../../')

from wcwave_adaptors.isnobal import isnobal

inputDir = sys.argv[1]
outputDir = sys.argv[2]
is_test = sys.argv[3]

input_prefix = inputDir + "/in"
em_prefix = outputDir + "/em"
snow_prefix = outputDir + "/snow"

if not os.path.exists(outputDir):
    os.makedirs(outputDir)

nsteps = 11 if is_test == "isTest" else 8758

isnobal(nsteps=nsteps, input_prefix=input_prefix, em_prefix=em_prefix,
        snow_prefix=snow_prefix)
