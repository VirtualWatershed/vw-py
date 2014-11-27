.. python ISNOBAL interface for use with the vw_adaptor

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


Reading IPW with Python
```````````````````````

The ``IPW`` class takes care of reading, modifying, and writing modified IPW 
files. To use it, simply provide the file name you wish to load into Python.

.. autoclass:: adaptors.src.isnobal_adaptor.IPW
    :members:

Example: Load a set of inputs; change ``T_a`` at every grid point and time step
-------------------------------------------------------------------------------

.. code-block:: python

    #!/usr/local/bin/python
    # assume observations are in obs_inputs/ and destination is inputs/
   
    import os 
    import sys

    from adaptors.src.isnobal_adaptor import IPW

    # for simplicity, cl arg 1 is the source file, 2 is dest dir, and 3 is
    # amount to change by
    source_file = sys.argv[1]
    dest_dir = sys.argv[2]
    amount = float(sys.argv[3])

    ipw = IPW(source_file)
    ipw.dataFrame.T_a = ipw.dataFrame.T_a + amount
    # required for proper writing. if new amounts exceed header max, trouble ensues..
    ipw.recalculate_header()

    output_file = dest_dir + os.path.basename(source_file)
    ipw.write(output_file)
    
Example: Plot outputs from five different "climate scenarios"
-------------------------------------------------------------

I used the example above to build five different warming scenarios, with
temperatures increased by .5, 1.0, 1.5, 2.0, and 2.5 degrees Celsius, to see
what the effect would be on total melting throughout the year. I modified the
input files as shown above and ran the ISNOBAL model using the 
``isnobal_adaptors.isnobal`` function. The outputs were stored in directories
``output/``, where the observed data was stored, and ``outputP0.5/``, 
``outputP1.0/``, and so on for the outputs from the modified inputs. 

I was curious to see how this changed the timing of peak snow melts over the 
entirety of the grid. Here's how I got a timeseries of the total snow melt
in the Treeline Catchment for each one of the modified series:

.. code-block:: python

    import os
    import pandas as pd
    import matplotlib.pyplot as plt
    
    from adaptors.src.isnobal_adaptor import IPW
    from collections import defaultdict

    melt_sums = defaultdict(list)

    for i, val in ["", "P0.5", "P1.0", "P1.5", "P2.0", "P2.5"]:

        dir_name = "outputs" + val

        files = ["/".join(dir_name, f) for f in os.listdir(dir_name)]

        melt_sums[val] = [IPW(f).dataFrame.melt.sum() for f in files]

    index = pd.date_range('10/10/2010', periods=8759, freq='H')

    df = pd.DataFrame(melt_sums, index=index)

    df.plot()

    plt.show




