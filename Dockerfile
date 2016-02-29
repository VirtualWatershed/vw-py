FROM ubuntu:14.04
MAINTAINER Moinul Hossain, Matthew Turner
LABEL description="This Image builds an ubuntu 14.04 image will all the dependencies and the models defined in vw-py." \
      version="1.0"

# Start installation with some necessary packages
RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential \
    git wget curl unzip m4 openssh-client

# install zlib from source, a dependency for netcdf4-c
RUN wget http://zlib.net/zlib-1.2.8.tar.gz && \
    tar xzfv zlib-1.2.8.tar.gz && cd zlib-1.2.8 && \
    ./configure --prefix=/usr/local && \
    make check && make install && \
    cd .. && rm -rf zlib-1.2.8.tar.gz zlib-1.2.8

# install hdf5 from source, another dependency for netcdf4-c
RUN wget ftp://ftp.unidata.ucar.edu/pub/netcdf/netcdf-4/hdf5-1.8.13.tar.gz && \
    tar xzfv hdf5-1.8.13.tar.gz && cd hdf5-1.8.13 && \
    ./configure --with-zlib=/usr/local --prefix=/usr/local/ --enable-hl --enable-shared && \
    make && make check && make install && make check-install && ldconfig && \
    cd .. && rm -rf hdf5-1.8.13.tar.gz hdf5-1.8.13

# install netcdf4-c
# ref: http://www.unidata.ucar.edu/software/netcdf/docs/getting_and_building_netcdf.html#build_default
#      http://unidata.github.io/netcdf4-python/
RUN wget https://github.com/Unidata/netcdf-c/archive/v4.3.3.1.tar.gz && \
    tar xzfv v4.3.3.1.tar.gz && cd netcdf-c-4.3.3.1 && \
    CPPFLAGS=-I/usr/local/include LDFLAGS=-L/usr/local/lib && \
    ./configure --enable-netcdf-4 --enable-shared --prefix=/usr/local && \
    make check && make install && ldconfig && \
    cd .. && rm -rf v4.3.3.1.tar.gz netcdf-c-4.3.3.1

# install gdal from source, this install the python bindings as well
RUN wget http://download.osgeo.org/gdal/1.10.0/gdal-1.10.0.tar.gz && \
    tar xvfz gdal-1.10.0.tar.gz && cd gdal-1.10.0 && \
    ./configure --with-python && \
    make && make install && ldconfig


# install isnobal
RUN wget https://github.com/VirtualWatershed/vw-py/raw/master/water-ipw-master.zip && \
    unzip water-ipw-master.zip -d /opt && \
    mv /opt/water-ipw-master/ /opt/water-ipw/ && \
    cd .. && rm -rf water-ipw-master.zip


# install prms from usgs website
RUN wget http://water.usgs.gov/ogw/gsflow/GSFLOW-v1.2.0/gsflow_v1.2.0.zip && \
    unzip gsflow_v1.2.0.zip -d /opt && \
    mv /opt/GSFLOW_1.2.0/ /opt/gsflow/ && \
    cd .. && rm -rf gsflow_v1.2.0.zip


# Some more dependencies needed for numpy and scipy
RUN apt-get install -y libblas-dev liblapack-dev libatlas-base-dev gfortran libgfortran3
# Time to install the python module itself
#RUN git clone --recursive https://github.com/VirtualWatershed/vw-py /opt/vw-py
COPY . /opt/vw-py
RUN NETCDF4_DIR=/usr/local && HDF5_DIR=/usr/local && cd /opt/vw-py && pip install -r requirements.txt



#set the env vars
# Make isnobal and prms available in path
ENV PATH $PATH:/opt/water-ipw/bin:/opt/gsflow/bin
# This env var is used by netcdf4-python while installing with pip
ENV NETCDF4_DIR /usr/local
ENV HDF5_DIR=/usr/local
# In case the terminal is not initialized
ENV TERM xterm
# Make the module available in PYTHONPATH
ENV PYTHONPATH /opt/vw-py
