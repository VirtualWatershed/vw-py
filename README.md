# WC-WAVE Adaptors: Tools for watershed modeling and data management

Welcome to the home for the WC-WAVE `adaptors`! Here you can clone the source
code, raise issues if you'd like to have a feature added or if you run into a
bug or other error, and collaborate with us by submitting your own additions or
changes.

To install you'll need to first install the NetCDF library. To use some scripts,
you'll also need GDAL installed. Then, 

```bash
git clone https://github.com/tri-state-epscor/wcwave_adaptors.git
```

To install all other dependencies, start up a virtual environment in the 
`wcwave_adaptors` directory 

```bash
virtualenv venv && source venv/bin/activate
```

and install requirements

```bash
pip install -r requirements.txt
```

To deactivate the virtual environment, simply use the `deactivate` command
that the sourced virtual environment provides.

For usage instructions, please see the [WC-WAVE
documentation](http://tri-state-epscor.github.io/vw-doc/tutorial.html).

For developer information including guidelines for contributing, see the [wiki](https://github.com/tri-state-epscor/adaptors/wiki).
