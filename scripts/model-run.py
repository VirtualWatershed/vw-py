#!/usr/local/bin/python


import os
import simplejson as json
from string import Template
import datetime
import uuid
import glob
import json
from lxml import etree
import requests
from os.path import splitext, basename
from urlparse import urlparse
import urllib
from subprocess import *
import getpass

#get user input
hostname = '129.24.196.43'  # raw_input('Hostname or IP Address: ')
u = 'idaho'  # raw_input('Username: ')
p = 'WaterShed!'
parent_model_run_uuid = '373ae181-a0b2-4998-ba32-e27da190f6dd'  #raw_input('Enter the model_run_uuid that you want to use as a source: ')

#Filename: isnobal_insert_processing.py..........last edited on October 14, 2014

#-------File written by William Hudspeth and Hays Barrett

#-------Script to insert isnobal input data into Virtual Watershed

#-------Uses templates for the JSON and XML files

#-------To run:    ./isnobal_insert_processing.py

#-------There are no paramaters required for this script



#---------------------VARIABLE SETUP FOR UNIQUE MODEL SET-----------------------------------------



procdate="10082014"

begdate="01012010"

enddate="12312010"

westBnd="-116.142905556"

eastBnd="-116.137583333"

northBnd="43.7326972222"

southBnd="43.7294055556"

themekey="watershed"

model="isnobal"

state="Idaho"

researcherName="Luke Sheneman"

mailing_address="University of Idaho"

zipCode="443029"

city="Boise"

epsg="26911"

researcherPhone="(208)885-4228"

researcherEmail="sheneman@uidaho.edu"

rowcount="170"

columncount="148"

latres="2.5"

longres="2.5"

mapUnits="meters"

modelname="isnobal"

location="Dry Creek"

orig_epsg="4326"


model_set_taxonomy = "grid"

data = {"description": "inital insert"}

model_id_url = "https://" + hostname + "/apps/my_app/newmodelrun"

result = requests.post(model_id_url, data=json.dumps(data), auth=(u, p), verify=False)
model_run_uuid = result.text

os.environ["PATH"] = os.environ["PATH"] + ":/Users/mturner/workspace/ipw-2.1.0/bin/"
os.environ["IPW"] = "/Users/mturner/workspace/ipw-2.1.0/"

INSERT_DATASET_URL = "https://" + hostname + "/apps/my_app/datasets"
DATA_UPLOAD_URL = "https://" + hostname + "/apps/my_app/data"
UUID_CHECK_URL = "https://" + hostname + "/apps/my_app/checkmodeluuid"
SRC_DATASET_URL = "https://"+ hostname + "/apps/my_app/search/datasets.json?version=3&model_run_uuid=" + parent_model_run_uuid + "&limit=12"



#----------------------PATHS---------------------------------------

baseDir = os.getcwd()
currentdir = os.getcwd()

json_template="resources/watershed_template.json"

xml_template="resources/fgdc_template.xml"

isnobal_inputDir="inputs/"
mkisnobalDir=os.path.join(baseDir,isnobal_inputDir)
if not os.path.isdir(mkisnobalDir):
    os.mkdir(mkisnobalDir)

isnobal_outputDir = "outputs/"
mkisnobalDir=os.path.join(baseDir,isnobal_outputDir)
if not os.path.isdir(mkisnobalDir):
    os.mkdir(mkisnobalDir)

jsonDir="JSON/"

xmlDir="XML/"


first_two_of_uuid = model_run_uuid[:2]
inputpath = os.path.join(baseDir,isnobal_inputDir)
parent_dir = os.path.join(inputpath, first_two_of_uuid)
full_in_path = os.path.join(parent_dir, model_run_uuid)

outputpath = os.path.join(baseDir,isnobal_outputDir)
parent_dir_out = os.path.join(outputpath, first_two_of_uuid)
full_out_path = os.path.join(parent_dir_out, model_run_uuid)
full_tiff_out_path = os.path.join(parent_dir_out, model_run_uuid, "geotiffs")
full_bin_out_path = os.path.join(parent_dir_out, model_run_uuid, "bin")
alldirs = [inputpath, parent_dir, full_in_path, outputpath, parent_dir_out, full_out_path, full_tiff_out_path, full_bin_out_path]
for i in alldirs:
        if not os.path.isdir(i):
                os.mkdir(i)




isnobalOutDir=os.path.join(baseDir,isnobal_outputDir)

#---------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------
#---------------------BEGIN FUNCTION DEFINITIONS----------------------------------------------------
#---------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------


def fetchInputData(parent_model_run_uuid):
    print ("Checking if model_run_uuid " + parent_model_run_uuid + " exists...")
    uuiddata = {"modelid": parent_model_run_uuid}
    r = requests.post(UUID_CHECK_URL, data=uuiddata, verify=False)
    status = r.text
    if status.lower() in ['true']:
        print "It Does!"
        print "Querying Virutal Watershed for records with model run uuid %s" % parent_model_run_uuid
        first_two_of_uuid = model_run_uuid[:2]
        inputpath = os.path.join(baseDir,isnobal_inputDir)
        parent_dir = os.path.join(inputpath, first_two_of_uuid)
        output_path = os.path.join(parent_dir, model_run_uuid)
        if not os.path.isdir(inputpath):
            os.mkdir(inputpath)
        if not os.path.isdir(parent_dir):
            os.mkdir(parent_dir)
        if not os.path.isdir(output_path):
            os.mkdir(output_path)
        r = requests.get(SRC_DATASET_URL, verify=False)
        data = json.loads(r.text)
        for i,f in enumerate(data["results"]):
            print "\n"
            full = f["downloads"][0]["bin"]
            print full
            disassembled = urlparse(full)
            filename, file_ext = splitext(basename(disassembled.path))
            # print filename
            # fname = os.path.splitext(filename)[0]
            stringNum = str(i) if i > 9 else "0" + str(i)
            fname = "in." + stringNum
            print fname
            outfile = os.path.join(output_path, fname)
            print "Writing %s ------> %s" % (full,outfile)
            urllib.urlretrieve(full, outfile)
    else:
        print " "
        print "This model_run_uuid does not exist!"
        print "QUITTING!"
        exit()



def runModel():

        in_prefix = "in"
        in_pre = os.path.join(full_in_path, in_prefix)
        init_img = os.path.join(baseDir,"init.ipw")
        pr_file = os.path.join(baseDir,"ppt_desc")
        mask_file = os.path.join(baseDir,"tl2p5mask.ipw")
        rootdir = full_bin_out_path
        ipw_outputdir = full_tiff_out_path

        if not os.path.isdir(rootdir):
                print("rootdir does not exist")
                exit()

        os.chdir(rootdir)

        datatstep = "60"
        # nsteps = "2001"
        nsteps = "11"
        outfreq = "1"

        isnobalcmd = "isnobal -t " + datatstep  + " -n " + nsteps  + " -I " + init_img  + " -p " + pr_file  + " -m " + mask_file + " -i " + in_pre + " -O " + outfreq + " -e em -s snow"
        print "Running model "
        print isnobalcmd
        print "Please be patient..."
        os.system(isnobalcmd)



        ipw_srctmp = [f for f in os.listdir(rootdir) if os.path.isfile(f)]
        ipw_src = ipw_srctmp[:12]
        for j in ipw_src:
            print "****** printing aptly-named variable j!!! ******"
            print j
            inputfilePath=os.path.join(rootdir,j)
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





def processFiles(inputDir):
    os.chdir(currentdir)
    if(model_set_type == "vis"):
        type_subdir = "geotiffs"
        ext = "tif"
        tax = "geoimage"
        wcs = "wcs"
        wms = "wms"
        mimetype = "application/x-zip-compressed"
    elif(model_set_type == "binary"):
        type_subdir = "bin"
        ext = "bin"
        wcs = " "
        wms = " "
        mimetype = "application/x-binary"
        tax  = "file"
    else:
        print "unknown model_set_type"
        exit()
    working_dir=os.path.join(inputDir,type_subdir)
    print working_dir
    if not os.path.isdir(working_dir):
        os.mkdir(working_dir)
    xml_directory=os.path.join(inputDir,type_subdir,xmlDir)
    if not os.path.isdir(xml_directory):
        os.mkdir(xml_directory)
    json_directory=os.path.join(inputDir,type_subdir,jsonDir)
    if not os.path.isdir(json_directory):
        os.mkdir(json_directory)
    json_logs_directory=os.path.join(inputDir, "logs")
    if not os.path.isdir(json_logs_directory):
        os.mkdir(json_logs_directory)

    isnobalDir=working_dir

    dir_listtmp=os.listdir(isnobalDir)
    dir_listtmp.sort()
    dir_list = dir_listtmp[:100]

    for q in dir_list:
        # q is something like em.2001 or in.2234 or snow.3324
        filename=q
        source_filepath=os.path.join(working_dir,q)
        if(os.path.isfile(source_filepath)):

            #--------------------------------XML Build--------------------------------------

            XMLFilePath=os.path.join(xml_directory,q+".xml")
            print XMLFilePath
            print "\nBuilding XML file ---> %s" % XMLFilePath
            statinfo=os.stat(source_filepath)
            filesizeMB="%s" % str(statinfo.st_size/1000000)
            template_object=open(xml_template,'r')
            template=Template(template_object.read())
            output = template.substitute(filesizeMB=filesizeMB,model_run_uuid=model_run_uuid,procdate=procdate,begdate=begdate,enddate=enddate,westBnd=westBnd,eastBnd=eastBnd,northBnd=northBnd,southBnd=southBnd,themekey=themekey,model=model,state=state,researcherName=researcherName,mailing_address=mailing_address,zipCode=zipCode,city=city,researcherPhone=researcherPhone,researcherEmail=researcherEmail,rowcount=rowcount,columncount=columncount,latres=latres,longres=longres,mapUnits=mapUnits,filename=filename)
            print "\nCreating XML file ----> %s" % XMLFilePath
            XMLfile=open(XMLFilePath,'w')
            XMLfile.write(output)
            XMLfile.close()
            template_object.close()
            XMLfile.close()

            #--------------------------------JSON Build--------------------------------------

            filePath=os.path.join(json_directory,q + ".json")
            print "\nCreating JSON file ----> %s" % filePath
            inputDay=q.split(".")[1]
            description="Test ISNOBAL Arizona input binary file Hour %s" % inputDay
            basename=filename
            recs="1"
            features="1"
            first_two_of_uuid = model_run_uuid[:2]
            inputFilePath=os.path.join("/geodata/watershed-data",first_two_of_uuid,model_run_uuid,filename)

            xmlFilePath=os.path.join(xml_directory,q + ".xml")
            if(os.path.isfile(source_filepath)):
                jsonFilePath=os.path.join(json_directory,q+".json")
                template_object=open(json_template,'r')
                template=Template(template_object.read())
                output = template.substitute(wcs=wcs,wms=wms,tax=tax,ext=ext,mimetype=mimetype,orig_epsg=orig_epsg,westBnd=westBnd,eastBnd=eastBnd,northBnd=northBnd,southBnd=southBnd,epsg=epsg,parent_model_run_uuid=parent_model_run_uuid,model_run_uuid=model_run_uuid,description=description,basename=basename,recs=recs,features=features,modelname=modelname,location=location,state=state,inputFilePath=inputFilePath,xmlFilePath=xmlFilePath,model_set=model_set,model_set_type=model_set_type,model_set_taxonomy=model_set_taxonomy)

                print output
                JSONfile=open(jsonFilePath,'w')
                JSONfile.write(output)
                JSONfile.close()
                template_object.close()
                JSONfile.close()

            #--------------------------------INSERT DATASET TO VIRTUAL WATERSHED--------------------------------------

            json_files = [jsonFilePath]
            for json_file in json_files:
                print 'PROCESSING: ', json_file
                with open(json_file, 'r') as f:
                    post_data = json.loads(f.read())

                #### ONLY USED TO PRINT THE _PARENT_ MODEL RUN UUID ####
                model_set_uuid=post_data['model_run_uuid']
                print "Model Run UUID %s" % model_set_uuid
                ####  ************************************* ####

                xml = etree.parse(post_data['metadata']['xml'])
                print etree.tostring(xml, encoding=unicode)
                post_data['metadata']['xml'] = etree.tostring(xml, encoding=unicode)

                # **** The only app that gets used is 'my_app' so this is
                # not useful for the VW client
                apps = post_data['apps']
                if len(apps) > 1:
                    the_url = INSERT_DATASET_URL % {'app':apps[0]}
                    post_data.update({"apps": apps[1:]})
                else:
                    the_url = INSERT_DATASET_URL % {'app':apps[0]}
                    post_data.update({"apps": []})
                # also this is no use
                post_data['active'] = 'true'
                #upload the data
                uploadpayload = {"name": "hbtest","modelid": model_run_uuid}
                print "\n\n******** THE source_filepath *******\n\n"
                print source_filepath

                files = {'file': open(source_filepath, 'rb')}
                # HOW THE FILE NAME IS KEPT TRACK OF IN THE VIRTUAL WATERSHED
                # The JSON file contains the XML itself. It also contains a
                # string like /geodata/watershed-data/0a/0a64e994-8f18-4e8c-bf9b-6c3d8b1577dd/em.09.7.tif
                # upload the newly-generated output file
                r = requests.post(DATA_UPLOAD_URL, files=files, data=uploadpayload, auth=(u, p), verify=False)
                # create the new record for the inserted file and insert metadata
                print json.dumps(post_data)
                result = requests.put(INSERT_DATASET_URL, data=json.dumps(post_data), auth=(u, p), verify=False)
                print result.text
                if result.status_code != 200:
                    print '\tFAILED INSERT', result.status_code
                    print '\t', result.content
                    continue
                new_dataset = result.content
                print '\tDATASET INSERTED: ', new_dataset
                print '\t', result.content
                with open(os.path.join(json_logs_directory, json_file.split('/')[-1].replace('.json', '_rsp.json')), 'w') as f:
                    f.write('{"dataset_uuid":"%s"}' % new_dataset)




def processParentFiles(isnobal_inputDir):
    os.chdir(currentdir)
    if(model_set_type == "vis"):
        type_subdir = "geotiffs"
        ext = "tif"
        tax = "geoimage"
        wcs = "wcs"
        wms = "wms"
        mimetype = "application/x-zip-compressed"
    elif(model_set_type == "binary"):
        type_subdir = "bin"
        ext = "bin"
        wcs = " "
        wms = " "
        mimetype = "application/x-binary"
        tax  = "file"
    else:
        print "unknown model_set_type"
        exit()

    print "running?"
    baseDir=isnobal_inputDir
    xml_directory=os.path.join(baseDir,xmlDir)
    if not os.path.isdir(xml_directory):
        os.mkdir(xml_directory)
    json_directory=os.path.join(baseDir,jsonDir)
    if not os.path.isdir(json_directory):
        os.mkdir(json_directory)
    json_logs_directory=os.path.join(baseDir, "logs")
    if not os.path.isdir(json_logs_directory):
        os.mkdir(json_logs_directory)
    isnobalDir=baseDir
    dir_listtmp=os.listdir(isnobalDir)
    dir_listtmp.sort()
    dir_list = dir_listtmp[:100]
    for i,q in enumerate(dir_list):
        filename=q
        stringNum = "00" + str(i) if i > 9 else "000" + str(i)
        filename = "in." + stringNum
        source_filepath=os.path.join(baseDir,isnobal_inputDir,q)
        if(os.path.isfile(source_filepath)):
            XMLFilePath=os.path.join(xml_directory,q+".xml")
            print "\nBuilding XML file ---> %s" % xml_directory
            statinfo=os.stat(source_filepath)
            filesizeMB="%s" % str(statinfo.st_size/1000000)
            template_object=open(xml_template,'r')
            template=Template(template_object.read())
            output = template.substitute(filesizeMB=filesizeMB,parent_model_run_uuid=parent_model_run_uuid,model_run_uuid=model_run_uuid,procdate=procdate,begdate=begdate,enddate=enddate,westBnd=westBnd,eastBnd=eastBnd,northBnd=northBnd,southBnd=southBnd,themekey=themekey,model=model,state=state,researcherName=researcherName,mailing_address=mailing_address,zipCode=zipCode,city=city,researcherPhone=researcherPhone,researcherEmail=researcherEmail,rowcount=rowcount,columncount=columncount,latres=latres,longres=longres,mapUnits=mapUnits,filename=filename)
            print "\nCreating XML file ----> %s" % XMLFilePath
            XMLfile=open(XMLFilePath,'w')
            XMLfile.write(output)
            XMLfile.close()
            template_object.close()
            XMLfile.close()
            filePath=os.path.join(baseDir,jsonDir,q + ".json")
            print "\nCreating JSON file ----> %s" % filePath
            print "YEAH HERE"
            inputDay=q.split(".")[1]
            description="Test ISNOBAL Arizona input binary file Hour %s" % inputDay
            basename=filename
            recs="1"
            features="1"
            first_two_of_uuid = model_run_uuid[:2]
            first_two_of_parent_uuid = parent_model_run_uuid[:2]
            inputFilePath=os.path.join("/geodata/watershed-data",first_two_of_parent_uuid,parent_model_run_uuid,filename)
            xmlFilePath=os.path.join(baseDir,xmlDir,q + ".xml")
            if(os.path.isfile(source_filepath)):
                jsonFilePath=os.path.join(json_directory,q+".json")
                template_object=open(json_template,'r')
                template=Template(template_object.read())
                output = template.substitute(wcs=wcs,wms=wms,tax=tax,ext=ext,mimetype=mimetype,orig_epsg=orig_epsg,westBnd=westBnd,eastBnd=eastBnd,northBnd=northBnd,southBnd=southBnd,epsg=epsg,parent_model_run_uuid=parent_model_run_uuid,model_run_uuid=model_run_uuid,description=description,basename=basename,recs=recs,features=features,modelname=modelname,location=location,state=state,inputFilePath=inputFilePath,xmlFilePath=xmlFilePath,model_set=model_set,model_set_type=model_set_type,model_set_taxonomy=model_set_taxonomy)
                JSONfile=open(jsonFilePath,'w')
                JSONfile.write(output)
                JSONfile.close()
                template_object.close()
                JSONfile.close()
            json_files = [jsonFilePath]
            for json_file in json_files:
                print 'PROCESSING: ', json_file
                with open(json_file, 'r') as f:
                    post_data = json.loads(f.read())
                model_set_uuid=post_data['model_run_uuid']
                print "Model Run UUID %s" % model_set_uuid
                xml = etree.parse(post_data['metadata']['xml'])
                post_data['metadata']['xml'] = etree.tostring(xml, encoding=unicode)
                apps = post_data['apps']
                if len(apps) > 1:
                    the_url = INSERT_DATASET_URL % {'app':apps[0]}
                    post_data.update({"apps": apps[1:]})
                else:
                    the_url = INSERT_DATASET_URL % {'app':apps[0]}
                    post_data.update({"apps": []})
                post_data['active'] = 'true'
                result = requests.put(INSERT_DATASET_URL,
                        data=json.dumps(post_data), auth=(u, p), verify=False)
                print result.text
                if result.status_code != 200:
                    print '\tFAILED INSERT', result.status_code
                    print '\t', result.content
                    continue
                new_dataset = result.content
                print '\tDATASET INSERTED: ', new_dataset
                print '\t', result.content
                with open(os.path.join(json_logs_directory, json_file.split('/')[-1].replace('.json', '_rsp.json')), 'w') as f:
                    f.write('{"dataset_uuid":"%s"}' % new_dataset)

#---------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------

#-----------------------------MAIN---------------------------------------------------------------

#---------------------END FUNCTION DEFINITIONS------------------------------------------------------

#---------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    model_set = "inputs"
    model_set_type = "binary"

    fetchInputData(parent_model_run_uuid)

    processParentFiles(full_in_path)

    runModel()

    model_set = "outputs"

    processFiles(full_out_path)

    model_set_type = "vis"

    processFiles(full_out_path)
