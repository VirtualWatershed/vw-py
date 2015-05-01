#!/bin/bash
#
# ipw2geotiff.sh
#
# Simplified version (operates on a single file) of the script written by Bill
# Hudspeth (ipw2GeoTiff.py)
#
# Example usage (use full path for IPW functions):
# find -f /Users/mturner/data/ | parallel ./ipw2geotiff.sh 1 4326 I_lw
#
# Date: January 7, 2015

band_idx=$1
epsg=$2
band_name=$3
input_file=$4

printf "$input_file\n"

printf "demux\n"
demuxed=$input_file.demux
printf "$demuxed\n"
demux -b $band_idx $input_file > $demuxed

printf "ipw2grid\n"
gridded=$input_file.gridded
ipw2grid $demuxed $gridded

printf "gdal_translate\n"
pre_tiff=$input_file.pre.tif
gdal_translate $gridded.bip $pre_tiff

printf "gdalwarp\n"
tiff=$input_file.$band_name.tif
gdalwarp -t_srs EPSG:26911 $pre_tiff $tiff

rm $gridded* $demuxed $pre_tiff
