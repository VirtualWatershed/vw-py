#!/usr/bin/python

from osgeo import gdal, osr

def GetExtent(gt,cols,rows):
    ext = []
    xarr = [0,cols]
    yarr = [0,rows]

    for px in xarr:
        for py in yarr:
            x = gt[0]+(px*gt[1])+(py*gt[2])
            y = gt[3]+(px*gt[4])+(py*gt[5])
            ext.append([x,y])
            #print x,y
        yarr.reverse()
    return ext

def ReprojectCoords(coords,src_srs,tgt_srs):

    trans_coords = []
    transform  =  osr.CoordinateTransformation( src_srs, tgt_srs)
    for x,y in coords:
        x,y,z  =  transform.TransformPoint(x,y)
        trans_coords.append([x,y])
    return trans_coords

import sys
raster = sys.argv[1]
ds = gdal.Open(raster)

gt = ds.GetGeoTransform()
cols  =  ds.RasterXSize
rows  =  ds.RasterYSize
ext = GetExtent(gt,cols,rows)
#print "EXT: %s" % ext

src_srs = osr.SpatialReference()
src_srs.ImportFromWkt(ds.GetProjection())
print "type(src_srs): " + str(type(src_srs))
print src_srs
#tgt_srs = osr.SpatialReference()
#tgt_srs.ImportFromEPSG(4326)
tgt_srs  =  src_srs.CloneGeogCS()
#print tgt_srs

geo_ext = ReprojectCoords(ext,src_srs,tgt_srs)
print "LatLong coords: %s" % geo_ext
lat = []
longit = []

for x,y in geo_ext:
    print x
    print y
    lat.append(y)
    longit.append(x)

print lat
print longit

west = min(longit)
east = max(longit)
north = max(lat)
south = min(lat)

print "\nWest: %s, South: %s, East: %s, North: %s" % (west, south, east, north)
bbox = "%s,%s,%s,%s" % (west, south, east, north)

print bbox

