#!/usr/bin/python

import os
from subprocess import *

os.environ["PATH"] = os.environ["PATH"] + ":/opt/ipw-2.1.0/bin/"
os.environ["IPW"] = "/opt/ipw-2.1.0/"

outputdir = "./"
msg = 'Absolute Path to file: '
inputfilePath = raw_input(msg).strip()


output = Popen(["ipwfile", inputfilePath], stdout=PIPE)
bands = int(output.communicate()[0].split(' ')[4])
path, filename = os.path.split(inputfilePath)
j = os.path.splitext(filename)[0]
extension = os.path.splitext(filename)[1]
for b in range(bands):
        b = str(b)
        outputImagePath = os.path.join(outputdir, 'image_' + str(j)+'.'+str(b))
        outputGridPath = os.path.join(outputdir, 'grid_' + str(j)+'.'+str(b))
        outputTiffPath = os.path.join(outputdir,
                                      'temp_' + str(j)+'.'+str(b)+'.tif')
        # First, use demux to extract bands to image file
        with open(outputImagePath, 'w') as output:
            server = Popen(["demux", "-b", b, inputfilePath], stdout=output)
            server.communicate()
        # Next, use ipw2grid to export band image to a useable format
        # understood by GDAL
        tempGrid = Popen(["ipw2grid", outputImagePath, outputGridPath],
                         stdout=PIPE).wait()

        inputGridPath = os.path.join(outputdir,
                                     'grid_' + str(j)+'.'+str(b)+'.bip')

        inputGridLQ = os.path.join(outputdir,
                                   'grid_' + str(j)+'.'+str(b)+'.lq')

        inputGridHDR = os.path.join(outputdir,
                                    'grid_' + str(j)+'.'+str(b)+'.hdr')

        tempTiff = Popen(["gdal_translate", "-ot", "Float32", inputGridPath,
                          outputTiffPath], stdout=PIPE).wait()
        # Finally, use gdalwarp to transform the tif at the same time writing
        # it to the output dir
        finalTiffPath = os.path.join(outputdir, str(j)+'.'+str(b)+'.tif')
        finalTiff = Popen(["gdalwarp", "-t_srs", "EPSG:26911", outputTiffPath,
                          finalTiffPath], stdout=PIPE).wait()

        # Clean up intermediate files; You can delete these rm lines if you
        # want to keep the files created during transformation to geotiffs.
        os.remove(outputImagePath)
        os.remove(inputGridPath)
        os.remove(inputGridLQ)
        os.remove(inputGridHDR)
        os.remove(outputTiffPath)

# Great! Now we use gdalbuildvrt to create a vert from the tifs
outputNCPath = os.path.join(outputdir, str(j) + str(extension) + '.nc')
os.system('gdalbuildvrt -separate temp.vrt *.tif')
# Now that we have a vrt we can make a NetCDF file
os.system('gdal_translate -of netcdf temp.vrt ' + outputNCPath)
print 'Writing out ' + outputNCPath

# Now we can get rid of the tifs
filelist = [f for f in os.listdir(".") if f.endswith(".tif")]
for f in filelist:
    os.remove(f)

# and the vrt
os.remove('temp.vrt')
