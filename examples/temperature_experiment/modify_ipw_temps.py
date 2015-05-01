#!/usr/local/bin/python
"""
Example of how to modify the observed Kormos data's temperature by a values and
save the modified results
"""

import sys
import os

sys.path.append('../../')

from wcwave_adaptors.isnobal import IPW

amount = float(sys.argv[1])
inputFile = sys.argv[2]

base_dir = os.path.dirname(inputFile).split('/')[0]

# output_dirs = ["data/inputsP" + amount + "/", "data/inputsM" + amount + "/"]
output_dir = base_dir + "/inputsP" + str(amount) + "/"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# load file
ipw = IPW(inputFile)

df = ipw.data_frame().copy()

# for i, amt in enumerate([float(amount), -float(amount)]):
# adjust the dataframe's temperature by amt
ipw._data_frame.T_a = df.T_a + amount

# save file to the appropriate outputdir
ipw.recalculate_header()
try:
    ipw.write(output_dir + os.path.basename(inputFile))
except Exception as e:
    print "Error on file " + inputFile
    print e.message
