# Virtual Watershed Data Adaptors

## The Virtual Watershed


## Get some data from the virtual watershed using Python [requests](http://docs.python-requests.org/en/latest/)


## Demonstration: Adaptors for a run of ISNOBAL using Kormos, et al, data

Based on the work done in this paper,
[Snow distribution, melt and surface water inputs to the soil in the mountain
rain-snow transition zone, Kormos, et. al., Journal of Hydrology
2014](http://www.sciencedirect.com/science/article/pii/S0022169414005113), we
will tweak and enhance a "virtual watershed" (VW) based on the data Kormos, et al, collected. 
There they describe their setup for collecting data and describe their iSNOBAL
model run. See the [Image Processing Workbench (IPW) User's
Guide](http://cgiss.boisestate.edu/~hpm/software/IPW/userGuide/index.html) for
more information on the commands we use from this software package. The 
Virtual Watershed already exists as a customized instance of the
[GSToRE](http://gstore.unm.edu/) "data framework for data discovery, delivery and
documentation". In addition to guiding the development of the VW itself, we will
develop a set of "adaptors" to connect models with the VW and models with each
other, and the output of models (stored in the VW) to the visualization team.


