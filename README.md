# Adaptors for ISNOBAL in the Virtual Watershed

Contributors:
+ [Hays Barrett](mailto:hays.barrett@gmail.com)
+ [Bill Hudspeth](mailto:bhudspeth@edac.unm.edu)
+ [Moinul Hossain Rifat](mailto:moinul.cse@gmail.com)
+ [Matthew Turner](mailto:maturner01@uidaho.edu)
+ [Chase Carthen](mailto:chasec2331@gmail.com)

## Intro

We need to write adaptors to connect ISNOBAL to the Virtual Watershed.
This is partly a proof of concept to show that we can connect
arbitrary models to the virtual watershed. To start with we have three
main adaptors that must be developed. One of those is freestanding:
the visualization. The other two may seem to be coupled, but if we
apply good principles, we see that in fact they are separate. Those
are to fetch data from the Virtual Watershed (VW) in a general way.
This will result in clean, reusable code. In brief, the Virtual
Watershed is a repository of watershed data accessed via web services.
More about the VW API, the VW metadata, and other VW capabilities will
be discussed below.

## Requirements
For now, let's think about the difference between data adaptors and
model adaptors. We'll assume that the model adaptor only interacts
with a data adaptor. We are going with a test-driven approach with an eye
towards continuous integration in the future on our github repo.

### Virtual Watershed Data Adaptor

+ Search for data with the virtual watershed via its API.
+ Expose the web service with Python wrappers, e.g., UUID would be a class
  attribute if known or there may be a flag for whether or not this is a new
  dataset being uploaded
+ Support the data hierarchy as described below in the "Virtual Watershed Data
  Hierarchy" section 
+ Handle metadata automagically

### ISNOBAL Model Adaptor

+ Implement functionality provided by the VW Data Adaptor to serve data to
  ISNOBAL: Input and output data and metadata for both
+ Provide command line interface to interact with with ISNOBAL's command line 
  interface

#### Sketch of ISNOBAL adaptor

```bash
# import data from VW, saving to out_dir
MODEL_RUN_NAME=my_model_run
prepare_vw_isnobal -i$MODEL_RUN_NAME -o out_dir/
# run the model referencing the newly fetched and prepped data
run_vw_isnobal -iout_dir/$MODEL_RUN_NAME -o out_dir/$MODEL_RUN_NAME/isnobal_output
# push data
push_vw_isnobal_output -i out_dir/$MODEL_RUN_NAME/isnobal_output
```

### Visualization Adaptor

For now I'll leave the visualization adaptor requirements for Moinul.


## January Demo: Adaptors for a run of ISNOBAL using Kormos, et al, data

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

Here is the map of the Treeline Catchment from the paper:

![Map of the treeline catchment](doc/figures/treeline_map.jpg)

