#!/usr/local/bin/python
import pandas as pd
import numpy as np
import sys

import matplotlib.pyplot as plt

from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})

is_test = sys.argv[1]

# nice looking plots are default with pandas
pd.options.display.mpl_style = "default"

# load data saved to csv from previous example
df = pd.read_csv("data/temperature_sensitivity_example.csv")
# have to re-assign because pandas doesn't parse it automatically. probably a
# way to tell it to read the index as a date_time.

# set styles and plot
styles = ['-', '--', '-', '--', '-', '--', '-', '--', '-']

if not is_test == "isTest":
    df.index = pd.date_range('10/01/2010', periods=8758, freq='H')
    df_3day = df.resample('3D', how=np.sum)
    ax = df_3day.plot(lw=3.0, style=styles)
else:
    ax = df.plot(lw=1.5, style=styles)
    df.index = pd.date_range('10/01/2010', periods=11, freq='H')

plt.title('Three-day sum of melt for observed/obs-plus temperatures',
          fontsize=21)

plt.xlabel('Date', fontsize=17)
plt.ylabel('Melt (kg/m^2)', fontsize=17)

# draw the legend in the upper-left corner
leg = plt.legend(loc=2, prop={'size': 15})

# set the linewidth of each legend object
for legobj in leg.legendHandles:
        legobj.set_linewidth(1.0)

ax.tick_params(axis='both', which='major', labelsize=15)
# plt.savefig("example_plot.png", dpi=180, format='png')
plt.savefig("example_plot.pdf", format='pdf')

df_weekly = df.resample('1W', how=np.sum)
df_weekly_csum = df_weekly.cumsum()
ax = df_weekly_csum.plot(lw=3.0, style=styles)
leg = plt.legend(loc=2, prop={'size': 15})

# set the linewidth of each legend object
for legobj in leg.legendHandles:
        legobj.set_linewidth(1.0)

ax.tick_params(axis='both', which='major', labelsize=15)
# plt.title('Weekly cumulative sum of snow melt',
          # fontsize=21)

plt.xlabel('Date', fontsize=17)
plt.ylabel('Total Melt YTD (kg/m^2)', fontsize=17)


