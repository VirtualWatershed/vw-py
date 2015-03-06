.. Documentation for the vw_adaptor module

Virtual Watershed Adaptor
=========================

The ``adaptors.watershed`` module is designed as a general interface for any 
model or modeling framework, such as ISNOBAL or CSDMS. 

VWClient: User Interface to the Virtual Watershed
`````````````````````````````````````````````````


The ``VWClient`` performs several routine virtual watershed functions. The
first, performed in the constructor, is to verify that the user/password
is an authorized account. There is a ``search`` method with options 
currently limited but easily scalable. ``fetch_records`` will fetch all 
JSON Watershed metadata records available for a given ``modelRunUUID``.
There are obvious ``download`` and ``upload`` functions. Finally there is
an ``insert_metadata`` function that pushes JSON watershed metadata to the
database.

.. autoclass:: watershed.VWClient
    :members:

Typically there will be no need to directly use the constructor to create a new
``VWClient`` instance. Instead use this convenience function that will read
``default.conf`` and establish a connection with 

.. autofunction:: watershed.default_vw_client

VW Client Examples
------------------

Assuming you have properly filled out your ``default.conf`` file with the 
IP address of the watershed and your login information, you can do the 
following.

>>> import adaptors.watershed as vw_adaptor
>>> vwClient = vw_adaptor.default_vw_client()
>>> modelRunUUID = "373ae181-a0b2-4998-ba32-e27da190f6dd"
>>> records = vwClient.search(model_run_uuid=modelRunUUID)
>>> records.total
8759
>>> records.fetchedTotal
15
>>> records.records[0]
{u'categories': [{u'location': u'Dry Creek',
   u'modelname': u'isnobal',
      u'state': u'Idaho'}],
       u'description': u'Test ISNOBAL Arizona input binary file Hour 0000',
        u'downloads': [{u'bin': u'http://129.24.196.43//apps/my_app/datasets/7ac44fa7-6515-422e-a3a9-e9aadf4924bb/in.0000.original.bin'}], ...

The default number of results fetched (enforced by the watershed) is 15, so to 
get 30, use the ``limit`` keyword, for example

>>> thirty = vwClient.fetch_records(modelRunUUID, limit=30)

If you're using the pincushion watershed IP address, you should get the exact
same number of records and get the same output.

When using the ``VWClient.search`` function, you can specify any of the 
key/value pairs specified in the `virtual watershed documentation 
<http://129.24.196.43//docs/stable/search.html#search-objects>`_.

The search function returns a ``QueryResult`` instance.

.. autoclass:: watershed.QueryResult
    :members:


Metadata builders
`````````````````

There are two functions for building metadata. One for creating JSON-formatted
Virtual Watershed metadata and one for generating XML-formatted FGDC "science"
metadata. The templates used to implement these functions are stored in the
``resources/`` directory.

.. autofunction:: watershed.make_watershed_metadata

.. autofunction:: watershed.make_fgdc_metadata

Configuration File Getter
`````````````````````````

The configuration files are loaded with a short conveneince function, 
``get_config``. Loading of this file was kept separate from the metadata making
functions because it would be wasteful to continually reload the config file.
Instead, we force the user to pass in the configuration file. It may be 
called with no arguments if called from the root folder. Otherwise the 
configuration file must be specified. See below for an example.

.. autofunction:: watershed.get_config

Example using metadata builders and the VW Client
`````````````````````````````````````````````````

Here we upload a file stored at ``'data/in.0001'`` to the virtual watershed 
and create the appropriate metadata for it. We pretend the variable names
that are represented in this file are ``R_n,H,L_v_E,G,M,delta_Q``, they are
input files. This is the procedure for inserting a brand-new, parent-free
model run set of data. Soon the "initial insert" section of this will be 
automated.

Get a VW Client connection (will soon be done during initialization)
--------------------------------------------------------------------

>>> vw_client = default_vw_client(configFile) # gets connection info from file

Initialize a new model run
--------------------------

>>> description = "New model run for doing SCIENCE!!!"
>>> new_uuid = vw_client.initialize_model_run(description)

Upload File
-----------

>>> dataFile = "src/test/data/in.0001"
>>> vw_client.upload(new_uuid, "src/test/data/in.0001")

Build metadata
--------------

>>> fgdcXML = make_fgdc_metadata(dataFile, config, new_uuid=new_uuid)
>>> watershedJSON = make_watershed_metadata(dataFile, config, new_uuid, new_uuid, "inputs", "Description of the data", model_vars="R_n,H,L_v_E,G,M,delta_Q", fgdcMetadata=fgdcXML) 

Insert Metadata
---------------

>>> vw_client.insert_metadata(watershedJSON)

I wrote out all of the previous steps to show what is possible with the 
watershed. The function that puts this all together, though, is the ``upsert``
function, which allows the user to upload and insert either a single file or a
whole directory to the virtual watershed

.. autofunction:: watershed.upsert


Make Watershed Metadata
```````````````````````

.. autofunction:: watershed.metadata_from_file
