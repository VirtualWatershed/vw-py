WC-WAVE Adaptors Tutorial: Common Tasks
=======================================

.. _prereq:

Pre-requisite
-------------

The only pre-requisite is that you have edited ``default.conf.template`` by 
adding your personally-unique data and a user name, password, and IP address 
which can be obtained by contacting `Matthew Turner <mailto:maturner@uidaho.edu>`_ 
via email.

See :ref:`the configuration note on the index page <config-index>` for more 
details.

Upload and insert data and metadata
-----------------------------------

In this section we cover uploading data to the virtual watershed using the 
VW Python API. 

Upload new data to an existing model run
````````````````````````````````````````

First, we'll go over as briefly as possible the terms and concepts that we 
will use.

The virtual watershed's primary concern is with _models_. We do this because we
want to track the relationship between model runs in a parent-child and sibling
fashion. For example, we may collect some data and put it into a model_run. But
then we might do some manipulations on that data, and the manipulated data 
becomes a child model run with its own unique identifier. However that new 
manipulated dataset has a ``parent_model_run_uuid`` equal to that of its parent's
``model_run_uuid``. See the example below for how this works in practice.

If your data is not associated with a particular model, don't be alarmed. Just 
use terms like ``model_run_name`` to mean ``dataset_name``, for example. 

Before we go in to an example where there are multiple model runs, let's look
at initializing a brand new model run, uploading associated data for that
model run, and automatically generating and inserting metadata for that model
run.

.. _pyapi_upsert_new:

Upload data, automatically create and insert metadata
`````````````````````````````````````````````````````

The Virtual Watershed adaptors provide functionality to upload either a directory 
or an individual file to the Virtual watershed and automatically generate and
insert the metadata record(s) for the file(s) by using the :ref:`upsert function <upsert-ref>`. 
This is done through a series of helper functions, which are documented along 
with upsert in the :ref:`watershed adaptor documentation <watershed-main>`.

Uploading either a file or directory is fairly simple, with some caveats. 
Assuming all the data for a model run is in one directory, you'd just run this:

.. code-block:: python

    from wcwave_adaptors.watershed import upsert

    dir_to_share = '/Users/mturner/workspace/data_to_share'
    model_run_name = 'Unique description of resource'
    description = 'Potentially longer description beyond the name'
    # keywords should be a single string of comma-separated values
    keywords = 'isnobal,snow,snow melt'

    new_model_run_uuid, _ = upsert(dir_to_share, model_run_name=model_run_name,
                                   description=description, keywords=keywords)
    

A keyword argument that gets automatically filled in is the ``config_file``
kwarg. All will work well as long as you have edited ``default.conf.template``
by filling in information specific to you and saved it as ``default.conf``. 
This, along with the files themselves, provides ``upsert``, via our metadata
builders, all the information it needs to automatically generate metadata
for each file and for this model run so that another virtual watershed user can
readily discover your shared data.

We assign the results of the call to ``upsert`` to two variables, ``new_model_run_uuid``
and a dummy variable ``_``. This is because ``upsert`` returns two strings, the
``parent_model_run_uuid`` and the ``model_run_uuid``, which are the same in
this case, so we only assign the parent.

.. _pyapi_upsert_append:

Upload new data to an existing model run
````````````````````````````````````````

In the example above, we saved the new model run UUID to a variable. Let's 
assume later on in our imaginary script, we need to put another file into 
the same container our other files went in. If we are looking at the view 
of our data in the virtual watershed web app, we want to add more files as
entries in a data resource. In this case, we don't need to provide a name, 
description, or any keywords, because we already did. We do have to provide the
``model_run_uuid`` that is associated with the resource we want to augment.

.. code-block:: python
    
    upsert('/Users/mturner/workspace/more_root_data', 
           parent_model_run_uuid=new_model_run_uuid, 
           model_run_uuid=new_model_run_uuid)


Here we've actually inserted more data to the "root" model run. We communicate
that by passing the same model run UUID as both the parent and the id. There is 
no hierarchy. In this next example, we create a new child model run of this root
model run and insert some data there.

.. code-block:: python

    newer_uuid = upsert('/Users/mturner/workspace/derived_data',
                        parent_model_run_uuid=new_model_run_uuid)


Search for data
---------------

Once you upload data, you'll want to search for the data you just inserted.
Here's how to do that.

For a little bit of background, here's how you would check that your model
run was actually inserted

.. code-block:: python
    
    # default_vw_client uses our default.conf to connect to the watershed
    from wcwave_adaptors.watershed import default_vw_client
    # get a new VWClient connected as described in default.conf
    vw_client = default_vw_client()
    # on searching, we get a QueryResult object; we want the 'records' attribute
    results = vw_client.search(model_run_uuid=newer_uuid)

Or go to your browser and enter this url: 

``http://129.24.196.23/apps/my_app/search/datasets.json?version=3&model_run_uuid=e6a4841a-691e-4764-9271-2f33e0ec39e8``

but put in the appropriate IP address as well as the model run UUID you got
from your upsert calls.
