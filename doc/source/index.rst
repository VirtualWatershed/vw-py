.. Virtual Watershed Adaptors documentation master file, created by
   sphinx-quickstart on Mon Nov 10 20:59:15 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the WC-WAVE Adaptors and Model Integration documentation!
====================================================================

Python API for Dynamic Waterhsed Science Modeling
`````````````````````````````````````````````````

This API targets two main tasks of watershed hydrology modeling: data management
and model running and manipulation. The only model currently supported is the
`iSNOBAL <http://cgiss.boisestate.edu/~hpm/software/IPW/man1/isnobal.html>`_ 
model from the `Software Tools for Hydro-Climatic Modeling and Analysis 
Image Processing Workbench (IPW) <http://cgiss.boisestate.edu/~hpm/software/IPW/index.html>`_. 

For data management, this API provides a wrapper of the Virtual Watershed (VW)
The VW is an extension of the 
`GSToRE architecture <http://gstore.unm.edu/docs/index.html>`_ hosted by the
Earth Data Analysis Center at the University of New Mexico. It is a specialized
database for hydrological data. By properly utilizing metadata, we may, for 
example, very intuitively create multiple "model runs", where a given 
hydrological model or coupled hydrological models operate on a set of input 
data. This input data may then be modified, fed to another model run, with 
new outputs, and all this may be stored sanely. 

For a quick look at what's possible with the iSNOBAL interface, see the 
`demonstration experiment of iSNOBAL <isnobal_experiment.html>`_ where we 
modify some observed IPW binary data to increase the temperature, run iSNOBAL
on every set of modified input data, and plot the results with 
pandas/matplotlib.

.. toctree::
   :maxdepth: 2

   vw_adaptor
   isnobal
   isnobal_experiment


Quickstart
``````````

This part is very simple and basically consists of three parts: 

1. Clone the repository
2. Install dependencies using ``pip install -r requirements.txt``
3. Copy ``default.conf.template`` to ``default.conf`` and 
   ``src/test/test.conf.template`` to ``src/test/test.conf`` and fill out both
   with your login credentials and correct paths to the XML and JSON metadata
   templates
4. Check that all is well by running the unittests

Clone repository
----------------

The repository is 
`hosted on github <https://github.com/tri-state-epscor/adaptors>`_. Clone it
like so:

.. code-block:: bash

    git clone https://github.com/tri-state-epscor/adaptors

Install dependencies
--------------------

You need `pip <https://pypi.python.org/pypi/pip>`_ installed to complete this
step.

From the root folder of the repository, run

.. code-block:: bash

    pip install -r requirements.txt

Copy configuration files and edit them appropriately
----------------------------------------------------

First, copy the configuration file templates:

.. code-block:: bash

    $ cp default.conf.template default.conf
    $ cp src/test/test.conf.template src/test/test.conf

Next open ``default.conf`` in your text editor and fill in ``watershedIP``,
``user``, and ``passwd`` fields appropriately. For the two ``template_path``
variables in the two different sections, change ``EDIT-THIS-PATH-TO`` to the
actual path to your ``adaptors`` directory.

Run Unittests
-------------

Finally, run the unittests from the root ``adaptors`` directory like so

.. code-block:: bash

    nosetests

If all is well, you will see the following output:

.. code-block:: bash

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






Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

