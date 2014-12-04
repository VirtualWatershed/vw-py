#!/usr/local/bin/python
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})

# nice looking plots are default with pandas
pd.options.display.mpl_style = "default"

# load data saved to csv from previous example
df = pd.read_csv("data/temperature_sensitivity_example.csv")
# have to re-assign because pandas doesn't parse it automatically. probably a
# way to tell it to read the index as a date_time.
df.index = pd.date_range('10/01/2010', periods=11, freq='H')

# CHANGE_FOR_FULL for full run, resample to 3-day sums
df_3day = df.resample('3D', how=np.sum)

# set styles and plot
styles = ['-', '--', '-', '--', '-', '--', '-', '--', '-']

# CHANGE_FOR_FULL toggle commenting on next two lines when doing a full run
# upper for test, lower for full
# ax = df.plot(lw=3.5, style=styles)
ax = df_3day.plot(lw=3.5, style=styles)

plt.title('Three-day sum of melt for observed/obs-plus temperatures',
          fontsize=12)
plt.xlabel('Date', fontsize=12)
plt.ylabel('Melt (kg/m^2)', fontsize=12)

# draw the legend in the upper-left corner
leg = plt.legend(loc=2, prop={'size': 7})

# set the linewidth of each legend object
for legobj in leg.legendHandles:
        legobj.set_linewidth(1.0)

ax.tick_params(axis='both', which='major', labelsize=8)
plt.savefig("example_plot.png", dpi=180, format='png')
