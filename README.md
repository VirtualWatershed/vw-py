# WC-WAVE Adaptors: Tools for watershed modeling and data management

## Setup

Welcome to the home for the WC-WAVE `adaptors`! Here you can clone the source
code, raise issues if you'd like to have a feature added or if you run into a
bug or other error, and collaborate with us by submitting your own additions or
changes.

To install you'll need to first install the NetCDF library with its headers. On OS X you can use [homebrew](http://brew.sh/) to install the NetCDF-C library

```bash
brew tap homebrew/science && brew install netcdf
```

On Debian/Ubuntu

```bash
sudo apt-get install libnetcdf-dev
```

To use some scripts, you'll also need GDAL installed. 


Then, 

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

## Configuration Files

In order to use functionality like default connections or setting a default
bounding box for your metadata, create a personalized version of
`default.conf.template` for yourself. To do this, first make a copy

```bash
cp default.conf.template default.conf
```

DO NOT SYNC `default.conf` WITH YOUR GIT REPO AS IT WILL CONTAIN YOUR LOGIN
INFO.

Next, edit `default.conf`, put in your personal VW Data Engine user name and
password. Edit the biographic info for yourself, and if you like, put a custom
bounding box. The values that come with the repository represent a box that 
tightly includes the three WC-WAVE states, New Mexico, Idaho, and Nevada.

In order to run unittests, copy `default.conf` to the test folder as
`test.conf`:

```bash
cp default.conf wcwave_adaptors/test/test.conf
```


## Usage and contributing

For usage instructions, please see the [WC-WAVE
documentation](http://tri-state-epscor.github.io/vw-doc/tutorial.html).

For developer information including guidelines for contributing, see the [wiki](https://github.com/tri-state-epscor/adaptors/wiki).
