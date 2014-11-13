"""
Author: Chase Carthen
Description: The following script converts IPW files to tifs.
"""

import sys
import re
import struct
import gdal
import numpy as np
import osr
#The following lambda function scales the input between the float min and max
convert = lambda i,fmin,fmax,imin,imax: (float(i-imin)/float(imax-imin))*(fmax-fmin)+fmin

class header:
    """
    Class: Header
    Description: The following class stores information about one band and its headers

    Variables: di is a dictionary that holds information about each header.
                 band_number is the band number for this particular header object.
    Supported IPW Headers: This class only supports geo, basic image, and lq headers.
    """
    def __init__(self,i):
         self.di = {}
         self.band_number = i

    def hasGeo(self):
         return 'geo' in self.di.keys()

    def hasBasicImagec(self):
         return 'basic_image' in self.di.keys()

    def hasLq(self):
         return 'lq' in self.di.keys()
'''class Header:
    def __init__(self,i):
         self.bn = i
         # Geo Variables
         # LQ Variables
         # Basic Image Variables
         # Header Strings'''
def getNumBytes(string):
    """
    Function: getNumBytes
    Description: The following function returns the total number of bytes in the header portion of an ipw file.
    """
    a = re.findall('!<header>.*\$',string)[-1]
    return len(a) + string.find(a)+2

def getHeaderAreas(string):
    """
    Function: getHeaderAreas
    Description: The following function returns all of the header areas in the header porition of an ipw file.
    These headers areas will be in the form (beginning of string index, end of string index)
    """
    a = re.findall('!<header>.*\$',string)
    #print a
    areas = []
    previous = 0
    append = areas.append
    for i in a:
         cur  = string.find(i)
         append((previous,cur))
         previous = cur
    del(areas[0])
    return areas

# This requires the header areas.
def getHeaderStrings(areas,string):
    """
    Function: getHeaderStrings
    Description: The following function will return the strings based on string index tuples passed to it.
    """
    strings = []
    for i in areas:
         strings.append(string[i[0]:i[1]])
    return strings

#Tokenize strings -- This will turn the header into tokens.
def tokenizeStrings(strings):
    """
    Function: tokenizeStrings
    Description: The following function tokenizes any strings passed into it and combine together any relevant inforamtion.
    """
    tokens = []
    headers = {}
    past = False
    for i in strings:
         # Process strings
         getHeaderInformation(i,headers)
    return headers

'''
All headers will have a dictionary formulated for each them.
At this moment only the basic_image,lq,and geoheaders are supported.
This is where one must define how to get the header information.
'''
def isNumber(string):
    try:
         float(string)
         return True
    except ValueError:
         #print 'False'
         return False

# GetHeaderInformation
def getHeaderInformation(string,headers):
    """
    Function: getHeaderInformation
    Description: The following function gets information about the headers and populates a headers dictionary.
    The headers dictionary is arranged as for example {"1" : header(), "2" : header()} where "1" and "2"
    are the bands numbers of the specific ipw file.

    Note: This function does not handle the case where there is no header. A catch statement will be added later to deal with this issue.
    """
    past = False
    types = 'misc'

    #Tokenize string lidy
    tokens = []

    #Remove irrelevant information
    strings = string.split('\n')
    for word in xrange(0,len(strings)):
         i = strings[word]
         tokens.append([])
         words = i.split()
         for k in xrange(0,len(words)):
            j = words[k]
            # This meant to skip an extra word after the $Revision symbol. --This information could be relevant.--
            if past:
               past = False
               continue
            if j == '$Revision:':
               past = True
            # Push into tokens list the relevant information.
            if j != '!<header>' and j != '=' and j != '$' and j != '$Revision:' and not past:
               tokens[-1].append(j)

    #Get the type of header
    types = tokens[0][0]
    band_num = tokens[0][1]

    # If band_num exists add this type of header to dictionary.
    # This does not handle the case where this number will go outside the index. --fix--
    if band_num in headers.keys():
         headers[band_num].di[types] = {}

    del(tokens[0])

    #Get Information from a single ipw header that has been tokenized
    for i in xrange(0,len(tokens)):
         if len(tokens[i]) == 0:
            continue
         # This particular band is the one that contains information about nbands here is where need to add a check for the number of bands
         if band_num == '-1':
            headers[tokens[i][0]] = tokens[i][1]
            if tokens[i][0] == 'nbands':
               # Since we know the number of bands create new headers for it in the dictionary.
               for j in xrange(0,int(tokens[i][1])):
                  headers[str(j)] = header(i)
                  #print j
         else:
            # The map token gives information about the float and int range handled in the else
            # Otherwise it is assumed that there is only one symbol after a token. -- fix -- Make this versatile to grab a whole sentence or paragraph.
            if tokens[i][0] != 'map':
               headers[band_num].di[types][tokens[i][0]] = tokens[i][1]
            else:
               if not 'int' in headers[band_num].di[types].keys():
                  headers[band_num].di[types]['int'] = []
                  headers[band_num].di[types]['float'] = []
               headers[band_num].di[types]['int'].append(tokens[i][1])
               headers[band_num].di[types]['float'].append(tokens[i][2])

def parse_file(headerinfo,filestr):
    """
    Function: parse_file
    Description: The following function literraly parses the file string.
    The function will use the previously obtained header information to push everything into arrayss to be later used by gdal.
    """

    # Find the number of bytes to skip the header portion of the ipw file.
    bytestoskip = getNumBytes(filestr)

    # Copy the string to a new object without the header portion--- This could be costly.
    copy = filestr[bytestoskip:]

    #Number of bits per string and number bands
    nbands = int(headerinfo['nbands'])
    ncols = int(headerinfo['nsamps'])
    nrows = int(headerinfo['nlines'])
    byte = []
    imin = []
    imax = []
    fmax = []
    fmin = []
    data = []
    total = 0

    # Populate relevant information and allocate lists to hold data.
    for i in xrange(0,nbands):
        total += int( headerinfo[str(i)].di['basic_image']['bytes'])
        byte.append(int( headerinfo[str(i)].di['basic_image']['bytes']))
        fmin.append(float( headerinfo[str(i)].di['lq']['float'][0]))
        fmax.append(float( headerinfo[str(i)].di['lq']['float'][1]))
        imin.append(int( headerinfo[str(i)].di['lq']['int'][0]))
        imax.append(int( headerinfo[str(i)].di['lq']['int'][1]))
        data.append([[]])

    # Read through the file
    #print imin,imax,fmin,fmax

    displace = 0
    i = 0
    counter = 0
    counter2 = 0
    offset = 0

    print total
    #print
    jump2 = total
    end = total
    unpack = struct.unpack

    #Iterate through the bands and convert bytes into proper float range.
    #Note: ipw data is stored in bip format or band interleaved by pixel
    #So the areas of the form b1b2b3 where bn = band n.
    #The following loop jumps from band to band.
    for i in xrange(0,nbands):
         # counter2 is used to keep track of the number of columns to know when to push to the list --
         # would preallocating be faster.

         counter2 = 0

         # jump2 keeps track of the the number of consumed bytes
         if i != 0 or nbands == 1:
            jump2 = jump2 - byte[i-1]

         #Keep track the number of bytes to jump by.
         jump = byte[i]

         # Keep track of the starting byte
         if nbands > 1:
            offset = total - jump2
         else:
            offset = 0

         # if at the end of the bands send the end to the proper offset.
         if i == nbands - 1:
            end = end - byte[i]

         #print offset,i,jump,total-jump2,len(copy),len(copy) - end, end
         for j in xrange(offset,len(copy)-end+1,total):
            if j == len(copy):
               continue
            if counter2 != 0 and counter2 % ncols == 0 and len(data[i]) < nrows:
               # I can do a test for nrows at the end
               #print len(data[i][-1])
               data[i].append([])
            # -fix- As of this moment most of the data sets are 1 or 2 byte unsigned integers this may need to be changed to support more.
            if jump == 1:
               data[i][-1].append(convert(unpack('B',copy[j:j+jump])[0],fmin[i],fmax[i],imin[i],imax[i]))
            elif jump == 2:
               print len(copy[j:j+jump]),len(copy),offset,total,j
               data[i][-1].append(convert(unpack('H',copy[j:j+jump])[0],fmin[i],fmax[i],imin[i],imax[i]))
            counter2 += 1

         # move the end
         end = end - byte[i]
         #offset = byte[(i+1) % nbands]
    print len(data[-1][-1]),nbands
    #print data[0][-1][-1]
    #sys.exit(0)
    # An old slow loop...... keeping this.
    ''' while i != len(copy):
         jump = byte[counter]
         if jump == 1:
            data[counter][-1].append(convert(struct.unpack('B',copy[i:i+jump])[0],fmin[counter],fmax[counter],imin[counter],imax[counter]))
         if jump == 2:
            data[counter][-1].append(convert(struct.unpack('H',copy[i:i+jump])[0],fmin[counter],fmax[counter],imin[counter],imax[counter]))
         counter = (counter + 1) % nbands

         if counter == 0:
            counter2 += 1
         if counter2 != 0 and counter2 % ncols == 0 and len(data[counter]) < nrows:
            # I can do a test for nrows at the end
            data[counter].append([])
         i += jump'''
    #print data[0][0]
    return data,headerinfo

def getGeoInformation(dictitem):
    first = float(dictitem['bsamp'])
    second = float(dictitem['dsamp'])
    third  = float(dictitem['bline'])
    fourth = float(dictitem['dline'])
    return (first,second,third,fourth)

def write_dem(data,headers,outfile,epsg=-1,singlebanded=True):
    '''
    Function: write_dem
    Descrition: This function takes the data obtained from the ipw file and
    writes it out to a dem through gdal's dataset.
    gdal handles any fileio by itself.
    '''
    print "EPSG",epsg
    #print headers
    # Register all gdal drivers with gdal
    gdal.AllRegister()

    # Outputing my data as 32 bit floats
    datatype = gdal.GDT_Float32

    # capture all specific infiormation
    nbands = int(headers['nbands'])
    ysize = int(headers['nlines'])
    xsize = int(headers['nsamps'])

    # Grab the specific driver need in this case the one for geotiffs.
    # This could be used with other formats!
    driver = gdal.GetDriverByName('gtiff')
    try:
         if singlebanded:
            ds = driver.Create(outfile+'.tif',xsize,ysize,nbands,datatype,[])
         else:
            ds = []
            for i in range(0,nbands):
               ds.append(driver.Create(outfile+"."+str(i)+".tif",xsize,ysize,1,datatype,[]))
    except:
         print "ERROR"
    #Caputring geo information..... one bad thing is that this assumes all inforamtion is in the same geolocation.
    # --fix-- bad apples here. Not sure what to do about this.........
    prevgeo = True
    for i in xrange(0,nbands):
         if 'geo' in headers[str(i)].di.keys():
            val = str(i)
            c  = getGeoInformation(headers[str(i)].di['geo'])
            if prevgeo != True and prevgeo != c:
               pass # need to create a seperate dataset for this band
            prevgeo = c
            #break
    #geoTransform = ds.GetGeoTransform()
    #0,1,3,5 -- place pixels in correct place -- arc grid places pixels at their centers!

    second = float(headers[val].di['geo']['dsamp'])
    fourth = float(headers[val].di['geo']['dline'])
    first = float(headers[val].di['geo']['bsamp'])-second/2.0
    third  = float(headers[val].di['geo']['bline'])-fourth/2.0

    # Here I am assuming that north is up in this projection
    # Some more bad apples here.
    geoTransform = (first,second,0,third,0,fourth)
    print geoTransform
    if singlebanded:
         ds.SetGeoTransform(geoTransform)
    else:
         for i in ds:
            i.SetGeoTransform(geoTransform)
    print geoTransform, first, second,third,fourth
    #print geoTransform
    #Write Basic Metadata
    if singlebanded:
         for key in headers.keys():
            if not isNumber(key):
               ds.SetMetadataItem(key,headers[key])

    #Write out data
    if singlebanded:
         for i in xrange(0,nbands):
            band = ds.GetRasterBand(i+1)
            #print data[i][0],len(data[i])
            #raw_input()

            # Here the float arrays are finally writtens out as numpy arrays :).
            band.WriteArray(np.array(data[i],dtype=np.float32),0,0)
            SetMetadataItem = band.SetMetadataItem
            for j in headers[str(i)].di.keys():
               for k in headers[str(i)].di[j].keys():
                  val = headers[str(i)].di[j][k]
                  if type(val) != str:
                     for l in val:
                        SetMetadataItem(j+'_'+k+'_'+str(val.index(l)),l)
                  else:
                      SetMetadataItem(j+'_'+k,val)
    else:
         for i in xrange(0,nbands):
            print len(ds)
            band = ds[i].GetRasterBand(1)
            band.WriteArray(np.array(data[i],dtype=np.float32),0,0)

    # apply projection to data
    if epsg != -1:
         print "EPSG", epsg
         try:
            # First create a new spatial reference
            sr = osr.SpatialReference()

            # Second specify the EPSG map code to be used
            if 6 == sr.ImportFromEPSG(epsg):
               print "IGNORING EPSG VALUE TO SPECIFIED REASON"
               return

            # Third apply this projection to the dataset(s)
            if singlebanded:
               ds.SetProjection(sr.ExportToWkt())
            else:
               for i in ds:
                  i.SetProjection(sr.ExportToWkt())
            print sr
         except:
            print "IGNORING EPSG VALUE"

def ipwToTif(infile,outfile,epsg=-1,singlebanded=True):
    test = open(infile,'rb')
    teststr = test.read()
    test.close()
    areas = getHeaderAreas(teststr)
    strings = getHeaderStrings(areas,teststr)
    headers = tokenizeStrings(strings)

    #print tokens
    #raw_input()
    #headers = getHeaderDetails(tokens)

    data,headers = parse_file(headers,teststr)

    #print headers
    write_dem(data,headers,outfile,epsg,singlebanded)
    print 'DONE'


if __name__ == '__main__':
    if len(sys.argv) > 1 and len(sys.argv) < 3:
         print 'Converting'
         ipwToTif(sys.argv[1],sys.argv[1])
    elif len(sys.argv) > 2:
         epsg = -1
         try:
            epsg = int(sys.argv[2])
         except:
            print "ERROR THIS PARAMETER MUST BE AN INT."
         ipwToTif(sys.argv[1],sys.argv[1],epsg)
    elif len (sys.argv) == 3:
         epsg = -1
         singlebanded = True
         try:
            epsg = int(sys.argv[2])
         except:
            print "ERROR THIS PARAMETER MUST BE AN INT."
         if argv[3].contains("F"):
            singlebanded = False
         ipwToTif(sys.argv[1],sys.argv[1],epsg,singlebanded)

