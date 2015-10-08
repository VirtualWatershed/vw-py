# PRMS Adaptor

In order for PRMS data to be interoperable with the rest of the Virtual
Watershed (VW) ecosystem, we need to be able to convert to NetCDF format,
the reference data format of the VW. To do this we've developed the PRMS
adaptors as an element of the growing suite of VW adaptors. 
  

Module Documentation
--------------------

PRMS model has 3 input files - Control File, Data File, and Parameter File. 
The Control File contains all of the control parameters that PRMS uses during the course of the simulation. 
It includes details such as input and output filenames, content of the output files, and simulation starting and ending dates. The Data File contains measured time-series data used in a PRMS simulation. 
The Parameter File contains the values of the parameters that do not change during a simulation. 
The input parameter file contains a set of parameters with a number of values for each hru (Hydrologic Response Unit). 
The file includes space dependent, time dependent, and space and time dependednt parameters. 
PRMS model has 2 output files - Animation File and Statistic Variables File.

Following are the commands to convert `PRMS` file in `TXT` format to a `NetCDF` format:


```bash

Data File: python dataToNetcdf.py LC.data
Control File: python controlToNetcdf.py LC.control
Parameter File: python parameterToNetcdf.py -nrows 49 -ncols 96 -data LC.param -loc XY.DAT -nhru 4704
Animation File: python animationToNetcdf.py -data animation.out.nhru -loc XY.DAT -nhru 4704 -nrows 49 -ncols 96
prms.out File: python prmsoutToNetcdf.py prms.out

    -nrows : number of rows of the dataset 
    -ncols : number of columns of the dataset
    -data : parameter file
    -loc : file that includes latitude and longitude values of each HRU 
    -nhru : number of HRUs for PRMS 

Statistic Variables File: python statvarToNetcdf.py statvar.dat

```
   
