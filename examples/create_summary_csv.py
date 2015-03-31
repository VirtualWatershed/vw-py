#!/usr/local/bin/python
"""
For every one of our temperature scenarios, add the summed snow melt for each
scenario for every time step as a row in a pandas DataFrame. The result:

Index  |     observed     |     P0.5     |     P1.0     | ....
-----------------------------------------------------
Hour 0:|     0.002        |    1.002     |     1.202    | ...
...
Hour 433: |  33.40        |    38.14     |     45.22    | ...
...

Where each "Hour #" is replaced by the actual date_time of the observation hour
"""
import os
import sys
import pandas as pd

from wcwave_adaptors.isnobal import IPW
from collections import defaultdict

is_test = sys.argv[1]

melt_sums = defaultdict(list)

for i, val in enumerate(["", "P0.5", "P1.0", "P1.5", "P2.0", "P2.5", "P3.0",
                         "P3.5", "P4.0"]):

    print "on val: " + val

    dir_name = "data/outputs" + val

    files = ["/".join([dir_name, f])
             for f in os.listdir(dir_name)
             if f[:2] == 'em']
    # print files

    melt_sum_list = [0.0]*len(files)

    for i, f in enumerate(files):
        ipw = IPW(f)
        melt_sum_list[i] = ipw.data_frame.melt.sum()

    melt_sums[val] = melt_sum_list

periods = 11 if is_test == "isTest" else 8758
index = pd.date_range('10/01/2010', periods=periods, freq='H')

df = pd.DataFrame(melt_sums, index=index)

cols = list(df.columns)
cols[0] = "observed"

df.columns = cols

# write the dataframe to csv
df.to_csv("data/temperature_sensitivity_example.csv")
