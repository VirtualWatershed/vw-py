"""
File: examples/isnobal_netcdf/run.py

Script to demonstrate running iSNOBAL with NetCDF as input and output format

Usage:
    In a python shell, execute `run run.py`. Then there will be a NetCDF
    Dataset object ready to inspect called `nc_out` in your shell.

Author: Matthew Turner <maturner@uidaho.edu>
Date: 22 April, 2015
"""
import sys
from os.path import dirname, join

sys.path.append(join(dirname(__file__), '../../'))

from netCDF4 import Dataset
from wcwave_adaptors.isnobal import isnobal

nc_in = Dataset(join(dirname(__file__), 'isnobal_inputs.nc'), 'r')

nc_out = isnobal(nc_in)
