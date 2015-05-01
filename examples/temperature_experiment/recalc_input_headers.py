#!/usr/local/bin/python
"""
Turns out the header recalculation results in a different I_lw value by about
.05 (fifth sig dig). Not super important for doing these temp modulation
test demos, but better to at least be consistent. Here I'm just loading into
IPW and saving back to the inputs directory.

Original files gotten from FTP site
(ftp://icewater.boisestate.edu/boisefront-products/other/projects/Kormos_iSNOBAL/input.dp/)
now in `original_inputs`
"""

import sys
import os

sys.path.append('../../')

from wcwave_adaptors.isnobal import IPW

input_file = sys.argv[1]

# load file
ipw = IPW(input_file)

# save file to the appropriate outputdir
ipw.recalculate_header()

save_dir = os.path.join(os.path.dirname(input_file).split('/')[0], "inputs/")

if not os.path.exists(save_dir):
    os.makedirs(save_dir)

ipw.write(save_dir + os.path.basename(input_file))
