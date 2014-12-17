[![Documentation Status](https://readthedocs.org/projects/epscor-wc-wave-adaptors/badge/?version=latest)](https://readthedocs.org/projects/epscor-wc-wave-adaptors/?badge=latest)
# Adaptors for ISNOBAL in the Virtual Watershed

Contributors:
+ [Hays Barrett](mailto:hays.barrett@gmail.com)
+ [Bill Hudspeth](mailto:bhudspeth@edac.unm.edu)
+ [Moinul Hossain Rifat](mailto:moinul.cse@gmail.com)
+ [Matthew Turner](mailto:maturner01@uidaho.edu)
+ [Chase Carthen](mailto:chasec2331@gmail.com)

## Quickstart


This part is very simple and basically consists of three parts: 

1. Clone the repository
2. Install dependencies using `pip install -r requirements.txt`
3. Copy `default.conf.template` to `default.conf` and 
   `src/test/test.conf.template` to `src/test/test.conf` and fill out both
   with your login credentials and correct paths to the XML and JSON metadata
   templates
4. Check that all is well by running the unittests

### Clone repository

The repository is 
[hosted on github](https://github.com/tri-state-epscor/adaptors). Clone it
like so:

```bash
$ git clone https://github.com/tri-state-epscor/adaptors
```

### Install dependencies

You need [pip](https://pypi.python.org/pypi/pip) installed to complete this
step.

From the root folder of the repository, run

```bash
$ pip install -r requirements.txt
```

### Copy configuration files and edit them appropriately

The configuration files store metadata that doesn't change between model runs
for a given project. Thus, a lot of the complexity of creating metadata is
kept behind the scenes. You'll see more as you fill out the configuration files.
Currently you must edit both the test configuration and the default
configuration if you want to run the tests as well as connect arbitrarily to the
virtual watershed. Hopefully this will not always be the case.


#### Required edits to config files

First, copy the configuration file templates:

```bash
$ cp default.conf.template default.conf
$ cp src/test/test.conf.template src/test/test.conf
```

Next open `default.conf` in your text editor and fill in `watershedIP`,
`user`, and `passwd` fields appropriately. For the two `template_path`
variables in the two different sections, change `EDIT-THIS-PATH-TO` to the
actual path to your `adaptors` directory.

#### You should also edit this stuff

There are many other fields like "researcherName", "mailing_address",
city, state, zip code, research phone number, and more that should be modified
appropriately. 

If you don't see a field that should be included in the metadata.


### Run Unittests

Finally, run the unittests from the root `adaptors` directory like so

```bash
$ nosetests
```

If all is well, you will see the following output:

```
Test that a single metadata JSON string is properly built (FGDC) ... ok
Test that a single metadata JSON string is properly built (JSON) ... ok
Test that failed authorization is correctly caught ... /Users/mturner/anaconda/lib/python2.7/site-packages/requests/packages/urllib3/connectionpool.py:730: InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.org/en/latest/security.html (This warning will only appear once by default.)
InsecureRequestWarning)
ok
VW Client properly downloads data ... ok
VW Client throws error on failed download ... ok
VW Client properly inserts data ... ok
VW Client throws error on failed insert ... ok
VW Client properly uploads data ... ok

----------------------------------------------------------------------
Ran 8 tests in 21.585s

OK
```

### First steps to inserting data

Follow these steps to insert some visualization data to the virtual watershed.
For more on the capabilities and structure of the Virtual Watershed Client
see the [API
documentation](http://epscor-wc-wave-adaptors.readthedocs.org/en/latest/vw_adaptor.html#vwclient-user-interface-to-the-virtual-watershed)


#### Connect to the watershed

For this you need to make sure you filled out the `watershedIP`, `user`, and
`passwd` in your personal `default.conf`. 

```python
# instantiate a new model run. this will soon be automated
from adaptors.vw_adaptor import get_config, default_vw_client, \
    makeFGDCMetadata, makeWatershedMetadata


 use whatever path necessary to access default.conf
config = get_config('adaptors/default.conf')
commonConfig = config['Common']

hostname = config['watershedIP']
modelIdUrl = "https://" + hostname + "/apps/my_app/newmodelrun"
# here "description" becomes "model_run_name" in the metadata
data = {"description": "Model Run Name"}
result = requests.post(modelIdUrl, data=json.dumps(data), 
    auth=(commonConfig['user'], commonConfig['passwd']), verify=False)

modelRunUUID = result.text
```

#### get a VW Client connection

```python
vwClient = default_vw_client(configFile) #could leave empty if in root directory
```

#### Upload File

```python
visFile = "em0001.3.tif"
vwClient.upload(modelRunUUID, "path/to/data/em0001.3.tif")
```

#### Build Metadata

Let's pretend that the single-banded tif we are uploading is temperature.
Then the `model_vars` variable is `T_a`.


```python
fgdcXml = makeFGDCMetadata(visFile, config, modelRunUUID=modelRunUUID)

# here we pass modelRunUUID as both the modelRunUUID and parentModelRunUUID

watershedJSON = makeWatershedMetadata(visFile, config, modelRunUUID,
                                      modelRunUUID, "outputs", 
                                      description="Atmospheric Temperature Vis Data",
                                      model_vars="T_a", model_vars="T_a",
                                      fgdcMetadata=fgdcXML)
```

#### Insert Metadata

```python
vwClient.insert_metadata(watershedJSON)
```

## Contribution guidelines

Stay as close to [PEP 8](http://legacy.python.org/dev/peps/pep-0008) 
possible with regards to
[indentation](http://legacy.python.org/dev/peps/pep-0008#indentation).
Specifically, let's follow these two rules so all our text editors can agree:

1. Use 4 spaces per indentation level.
2. Spaces are the preferred indentation method. Tabs should be used solely to
   remain consistent with code that is already indented with tabs.

I am slowly converting function names to the PEP-8 standard, which is 
`words_underscore_sep`. 


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

