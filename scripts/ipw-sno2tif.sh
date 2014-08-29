#!/bin/bash
#change the first 4 lines as needed.
srcdir=/var/www/html/snobal-outputs/
outputdir=/var/www/html/ipw-outputs/
export IPW=/opt/ipw-2.1.0/
export PATH=$PATH:/opt/ipw-2.1.0/bin/
cd $srcdir
for srcfile in `ls`
do
#get the number of bands in the file
bands=`ipwfile $srcfile | awk '{print $4}'`
#because the bands start with zero...
let "bands = $bands - 1"
#for each one of the bands do...
for bnd in $(seq 0 $bands)
do
#use demux to extract each band to a seperate file
demux -b $bnd $srcfile > singleband$srcfile.$bnd
#Use ipw2grid to export the band to a usable format that is understood by gdal
ipw2grid singleband$srcfile.$bnd grid$srcfile
#Use gdal_translate to translate the grid to tif
gdal_translate grid$srcfile.bip $srcfile.b$bnd.tif
#use gdalwarp to transform the tif at the same time writing it to the output dir
gdalwarp -t_srs EPSG:26911 $srcfile.b$bnd.tif $outputdir/$srcfile.b$bnd.tif
#clean up. You can delete these rm lines if you want to keep the files created during transformation to geotifs.
rm singleband$srcfile.*
rm $srcfile.b$bnd.tif
rm grid$srcfile.*
done
done

