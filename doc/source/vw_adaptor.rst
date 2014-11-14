.. Documentation for the vw_adaptor module

vw_adaptor.py
=============

The ``vw_adaptor`` module is designed as a general interface for any model
or modeling framework, such as ISNOBAL or CSDMS. 

VWClient: User Interface to the Virtual Watershed
`````````````````````````````````

The ``VWClient`` performs several routine virtual watershed functions. The
first, performed in the constructor, is to verify that the user/password
is an authorized account. There is a ``search`` method with options 
currently limited but easily scalable. ``fetch_records`` will fetch all 
JSON Watershed metadata records available for a given ``modelRunUUID``.
There are obvious ``download`` and ``upload`` functions. Finally there is
an ``insert_metadata`` function that pushes JSON watershed metadata to the
database.

.. autoclass:: vw_adaptor.VWClient
    :members:

Typically there will be no need to directly use the constructor to create a new
``VWClient`` instance. Instead use this convenience function that will read
``default.conf`` and establish a connection with 

.. autofunction:: vw_adaptor.default_vw_client

VW Client Examples
------------------

Assuming you have properly filled out your ``default.conf`` file with the 
IP address of the watershed and your login information, you can do the 
following.

>>> import src.vw_adaptor as vw_adaptor
>>> vwClient = vw_adaptor.default_vw_client()
>>> modelRunUUID = "373ae181-a0b2-4998-ba32-e27da190f6dd"
>>> records = vwClient.fetch_records(modelRunUUID)
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
number of records and be able to print 

Metadata builders
```````````` 

There are two functions for building metadata. One for creating JSON-formatted
Virtual Watershed metadata and one for generating XML-formatted FGDC "science"
metadata. The templates used to implement these functions are stored in the
``resources/`` directory.

.. autofunction:: vw_adaptor.makeWatershedMetadata

.. autofunction:: vw_adaptor.makeFGDCMetadata

