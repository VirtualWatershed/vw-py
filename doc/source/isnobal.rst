.. python ISNOBAL interface for use with the watershed adaptor

Python ISNOBAL Interface
========================

The `Image Processing Workbench (IPW) software package 
<http://cgiss.boisestate.edu/~hpm/software/IPW/index.html>`_ is the standard on
which we base our work here. We need to extend this functionality a bit, if for
no other reason to improve the usability and documentation, which seem pretty
lacking. 

IPW is a pretty large project of which the ISNOBAL model is one part. The 
groundbreaking paper that established ISNOBAL as one of the premier snowmelt
water input models is 
:download:`Marks, et al., 1999 </downloads/marks1999A.pdf>`. The ISNOBAL 
documentation, including what each band is in each type of file, can be found
`here <http://cgiss.boisestate.edu/~hpm/software/IPW/man1/isnobal.html>`_.

The best way to find a file is by first searching through this `grouped list
of Standard IPW User Commands 
<http://cgiss.boisestate.edu/~hpm/software/IPW/userGuide/categories/All.html>`_.

Every IPW file has some lines dedicated to its header, which describes the
image, and a single binary line that must be parsed according to the information
in the header. The line of binary data represents a `data cube, visualized
here 
<http://cgiss.boisestate.edu/~hpm/software/IPW/userGuide/pixelsAndBands.html>`_. 
There are :math:`N_l` lines of data, :math:`N_s` geographic samples,
and :math:`N_b` bands. Transformed to human-readable data, the binary data
looks something like this made up example:

=====  =========    ======
Temp   Pressure     Dew Point
=====  =========    ======
23.4   101.0        21.0
24.5   100.0        20.0
24.1   102.3        22.0
...    ...          ...
=====  =========    ======


You can see what the binary data actually looks like in Python by doing the
following:

.. code-block:: python

    filePath = "path/to/in.0000"
    
    with open(filePath, 'rb') as f:
        lines = f.readlines()

    header = lines[:-1]
    binaryPart = lines[-1]

    binaryPart[:100]

Only looking at the first 100 characters will keep your screen from getting
filled with hexadecimal digits.

Before we read any of that data to be integers, which we can then convert to
floating point like in the table above, we need to know the scheme for doing so.
That is given to us in the rest of the basic image header, which tells us

1. The number of bits used to store a sample in the band
2. The number of bytes used to store these bits
3. The floating-point range of each band
4. (Optional) Annotative text describing the band



Basic IPW Operations
````````````````````

We can get a summary of this information using the IPW command `ipwfile 
<http://cgiss.boisestate.edu/~hpm/software/IPW/man1/ipwfile.html>`_:

.. code-block:: bash

    $ ipwfile in.0000
    File: "in.00"  Bands: 5  Lines: 148  Samples: 170  Bytes/Pixel: 1 1 2 2 1

Note: some input files have five bands and some have six. The last one may 
be omitted if the sun is down.

We can get a view of the floating point values stored in an image file using the
`primg command 
<http://cgiss.boisestate.edu/~hpm/software/IPW/man1/primg.html>`_:

.. code-block:: bash
    
    $ primg -a -i in.0000
    292.157 22.4 468.743 0.84229 0
    296.078 22.4 468.743 0.84229 0
    296.078 22.4 468.743 0.84229 0
    294.118 22.4 468.743 0.84229 0
    296.078 22.4 468.743 0.84229 0
    296.078 22.4 468.743 0.84229 0
    300 22.4 468.743 0.84229 0
    300 22.4 468.743 0.84229 0
    294.118 22.4 468.743 0.84229 0
    296.078 22.4 468.743 0.84229 0

Note that

.. code-block:: bash
    
    $ primg -a -iin.0000 | wc -l
    25160

is equal to the number of lines times the number of samples, which makes
"lines" seem a bit of a misnomer.

Make Watershed Metadata
```````````````````````

.. autofunction:: isnobal.metadata_from_file


Reading IPW with Python
```````````````````````

The ``IPW`` class takes care of reading, modifying, and writing modified IPW 
files. To use it, simply provide the file name you wish to load into Python.

.. autoclass:: isnobal.IPW
    :members:

Insert IPW file or directory of files to Virtual Watershed
``````````````````````````````````````````````````````````

.. autofunction:: isnobal.upsert_ipw
    
If we have some iSNOBAL data in the folders ``data/inputs`` and 
``data/outputs``, we can either upload
all the files in thosy directories or indivdual files. Providing a 
description is required. If the parent or model run IDs are provided, they will
be used. If not provided, ``upsert`` will create new ones. If the model run 
UUID is provided, its parent must also be provided, though this is may be 
changed in the near future. Some examples are shown below.

.. code-block:: python

    # set base data directory and description for this model run
    data_dir = "data/"
    description = "iSNOBAL model run with Treeline observed data"

    # upload the entire directory, creating a new parent and model run uuid
    input_dir = data_dir + "inputs"
    parent_uuid, uuid = upsert(input_dir, description)

    # use the existing parent_uuid and uuid to insert the output data
    input_dir = data_dir + "outputs"
    parent_uuid, uuid = upsert(output_dir, description, 
                               parent_model_run_uuid=parent_uuid,
                               model_run_uuid=uuid)

``upsert`` uses a config file and ``watershed.default_vw_client`` to connect to
the virtual watershed. You can set which configuration file ``upser`` uses
using the last keyword argument, ``config_file``.


Run ISNOBAL from Python
```````````````````````

The ISNOBAL interface is a simple, straight-forward wrapper for ISNOBAL. 

.. autofunction:: isnobal.isnobal

Aggregate a list or series of IPW instances to decrease timestep
````````````````````````````````````````````````````````````````

Use this function when you want to, for example, transform a list of IPW instances 
that represent one hour's worth of data to represent some larger amount of time's
data. For a specific example, we might want to sum three days' worth of hourly
data to create a single IPW instance:

.. code-block:: python

    # assume we have 21 day's worth of data, meaning 504 IPW binary files
    ipws = [IPW(f) for f in files]
    assert len(ipws) == 504

    # sum every 72 hours worth of data ('3D' = 3 days) 
    three_day_ipws = reaggregate_ipws(ipws, rule='3D')
    assert len(ipws) == 7

.. autofunction:: isnobal.reaggregate_ipws

