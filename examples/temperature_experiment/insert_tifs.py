"""
Create .tif files for all output directories for insert to the virtual
watershed.
"""
import os

from glob import glob

from wcwave_adaptors.isnobal import upsert

# First "outputs" directory should be the parent uuid; all others inherit it
parent_directory = \
    "/Users/mturner/workspace/full_output_ta_example/data/outputs_tif"


child_directories = \
    [d for d in
     glob("/Users/mturner/workspace/full_output_ta_example/data/outputsP*")
     if os.path.isdir(d)]

config_file = "/Users/mturner/workspace/adaptors/january.conf"
description = "Output from T_a toy experiment"

# insert parent directory
print "upserting " + parent_directory
p, u = upsert(parent_directory, description, config_file=config_file)

# use that parent uuid for each of the modified temperature outputs
for d in child_directories:
    print "upserting " + d
    upsert(d, description, parent_model_run_uuid=p,
           config_file=config_file)
