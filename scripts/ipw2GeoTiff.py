#!/usr/bin/python

# ipw2GeoTiff.py - convert IPW Isnobal file to collection of Geotiffs
# File created by William Hudspeth on August 26, 2014
# Last edited on August 28, 2014

import os
from subprocess import *

#set environmental variables to point to IPW binaries
os.environ["PATH"] = os.environ["PATH"] + ":/home/william/IPW/ipw-2.1.0/bin/"
os.environ["IPW"] = "/home/william/IPW/ipw-2.1.0/"

#set source and output directories
ipw_srcdir="/home/william/IPW/src/"
ipw_outputdir="/home/william/IPW/output/"

#An example processing the SNO data; could do the same for EM data
ipw_src=os.listdir(ipw_srcdir)

for j in ipw_src:
    inputfilePath=os.path.join(ipw_srcdir,j)
    output=Popen(["ipwfile", inputfilePath], stdout=PIPE)
    bands=int(output.communicate()[0].split(' ')[4])
    for b in range(bands):
	
	b=str(b)
	outputImagePath=os.path.join(ipw_outputdir,'image_' + str(j)+'.'+str(b))
	outputGridPath=os.path.join(ipw_outputdir,'grid_' + str(j)+'.'+str(b))
	outputTiffPath=os.path.join(ipw_outputdir,'temp_' + str(j)+'.'+str(b)+'.tif')

	#First, use demux to extract bands to image file
	with open(outputImagePath,'w') as output:
	    server=Popen(["demux","-b",b,inputfilePath],stdout=output)
	    server.communicate()
	#Next, use ipw2grid to export band image to a useable format understood by GDAL
	tempGrid=Popen(["ipw2grid", outputImagePath,outputGridPath], stdout=PIPE).wait()
		
	#Then, use gdal_translate to translate the grid to geotiff
	inputGridPath=os.path.join(ipw_outputdir,'grid_' + str(j)+'.'+str(b)+'.bip')
	inputGridLQ=os.path.join(ipw_outputdir,'grid_' + str(j)+'.'+str(b)+'.lq')
	inputGridHDR=os.path.join(ipw_outputdir,'grid_' + str(j)+'.'+str(b)+'.hdr')
	tempTiff=Popen(["gdal_translate",inputGridPath,outputTiffPath], stdout=PIPE).wait()
	
	#Finally, use gdalwarp to transform the tif at the same time writing it to the output dir
	finalTiffPath=os.path.join(ipw_outputdir,str(j)+'.'+str(b)+'.tif')
	finalTiff=Popen(["gdalwarp","-t_srs","EPSG:26911",outputTiffPath,finalTiffPath],stdout=PIPE).wait()
	
	#Clean up intermediate files; You can delete these rm lines if you want to keep the files created during transformation to geotiffs.
	os.remove(outputImagePath)
	os.remove(inputGridPath)
	os.remove(inputGridLQ)	
	os.remove(inputGridHDR)	
	os.remove(outputTiffPath)
