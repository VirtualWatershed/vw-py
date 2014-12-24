"""
Create .tif files for all output directories for insert to the virtual
watershed.
"""

import os
import sys

from glob import glob

from adaptors.isnobal import IPW
from adaptors.watershed import get_config

# ipw_directories = \
    # [d for d in
     # glob("/Users/mturner/workspace/full_output_ta_example/data/outputsP*")
     # if os.path.isdir(d)]

d = sys.argv[1]
print d

# print ipw_directories

# iterate over directories and convert to .tifs

# get the epsg from the config file
config_file = "/Users/mturner/workspace/adaptors/default.conf"
config = get_config(config_file)
epsg = int(config['Watershed Metadata']['orig_epsg'])

# for d in ipw_directories:
# d = "/Users/mturner/workspace/full_output_ta_example/data/mixed_test"
# for d in ipw_directories:

out_dir = d + '_tif'
if not os.path.isdir(out_dir):
    os.makedirs(out_dir)

for f in os.listdir(d):

    ipw = IPW(d + '/' + f)
    ipw.export_geotiff(output_dir=out_dir)
