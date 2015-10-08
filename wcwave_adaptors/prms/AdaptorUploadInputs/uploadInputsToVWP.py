__author__ = 'jerickson'
import os
import json
import uuid
import requests
import dataToNetcdf
import convertInputsToNetcdf

def loginToSession(s, loginurl):
    l = s.get(loginurl)
    return l

def uploadSingleFile():
    return 0

def uploadPRMSInputFiles(prmsInputName, vwpBaseURL, username, password, modeldata, basejson):
    '''

    :param prmsInputName: Name of the prms inputs; should be shared for control, data and param
    :param vwpBaseURL: Base URL representing the VWP we are posting to
    :param username: login info for VWP, name
    :param password: login info for VWP, password
    :param modeldata: json representing the data for the model run we are going to create
    :param basejson: basic json representing our core dataset information; will be filling in additional info in this script
    :return:
    '''
    data_nc = prmsInputName + "_data.nc"
    param_nc = prmsInputName + "_param.nc"
    control = prmsInputName + ".control"

    currentdir = os.getcwd()

    loginurl = vwpBaseURL + "/apilogin"
    newmodelurl = vwpBaseURL + "/apps/vwp/newmodelrun"
    insert_dataset_url = vwpBaseURL + "/apps/vwp/datasets"
    data_upload_url = vwpBaseURL + "/apps/vwp/data"

    s = requests.Session()
    s.auth = (username, password)
    s.verify = False

    l=s.get(loginurl)
    if l.status_code == 200:
        newuuid=str(uuid.uuid1())
        print "********************"
        print "* Create model run *"
        print "********************"
        createmodel = s.post(newmodelurl, data=modeldata)
        if createmodel.status_code == 200:
            print "Modelrun creation successful!"
            model_run_uuid = createmodel.text
            first_two_of_uuid = model_run_uuid[:2]
            uploadpayload={"name": "prms", "modelid": model_run_uuid}
            #Control File
            print "***********************"
            print "* Upload Control File *"
            print "***********************"
            inputControlFilepath = os.path.join("/geodata/watershed-data",first_two_of_uuid,model_run_uuid,control).replace("\\", "/")
            print inputControlFilepath
            files = {'file': open(currentdir + "/" + control, 'rb')}
            r = s.post(data_upload_url, files=files, data=uploadpayload)
            if r.status_code == 200:
                print "Upload control file successful!"
                control_json = basejson
                control_json = control_json.replace('$parent_model_run_uuid', model_run_uuid)
                control_json = control_json.replace('$inputFilePath', inputControlFilepath)
                control_json = control_json.replace('$model_run_uuid', model_run_uuid)
                control_json = control_json.replace('$description', "PRMS- " + prmsInputName + " Control File")
                control_json = control_json.replace('$basename', prmsInputName)
                control_json = control_json.replace('$taxonomy', 'file')
                control_json = control_json.replace('$model_set_taxonomy', 'file')
                control_json = control_json.replace('$mimetype', 'text/plain')
                control_json = control_json.replace('$ext', 'control')
                control_json = control_json.replace('$formats', 'control')
                print control_json
                insert = s.put(insert_dataset_url, data=control_json)
                if insert.status_code == 200:
                    print "Insert Successful!"
                    print insert.text
                else:
                    print "******************"
                    print "* Insert Failure *"
                    print "******************"
                    print insert.text
                    return -1
            else:
                print "**************************"
                print "* Upload control failure *"
                print "**************************"
                print r.text
                return -1
            #Param File
            print "*********************"
            print "* Upload Param File *"
            print "*********************"
            inputParamFilepath = os.path.join("/geodata/watershed-data",first_two_of_uuid,model_run_uuid,param_nc).replace("\\", "/")
            files = {'file': open(currentdir + "/" + param_nc, 'rb')}
            r = s.post(data_upload_url, files=files, data=uploadpayload)
            if r.status_code == 200:
                print "Upload param file successful!"
                param_json = basejson
                param_json = param_json.replace('$parent_model_run_uuid', model_run_uuid)
                param_json = param_json.replace('$inputFilePath', inputParamFilepath)
                param_json = param_json.replace('$model_run_uuid', model_run_uuid)
                param_json = param_json.replace('$description', "PRMS- " + prmsInputName + " Param file")
                param_json = param_json.replace('"services": []', '"services": ["wms", "wcs"]')
                param_json = param_json.replace('$basename', prmsInputName + "_param")
                param_json = param_json.replace('$taxonomy', 'netcdf')
                param_json = param_json.replace('$model_set_taxonomy', 'grid')
                param_json = param_json.replace('$mimetype', 'application/x-netcdf')
                param_json = param_json.replace('$ext', 'nc')
                param_json = param_json.replace('$formats', 'nc')
                print param_json
                insert = s.put(insert_dataset_url, data=param_json)
                if insert.status_code == 200:
                    print "Insert Successful!"
                    print insert.text
                else:
                    print "******************"
                    print "* Insert Failure *"
                    print "******************"
                    print insert.text
                    return -1
            else:
                print "************************"
                print "* Upload param failure *"
                print "************************"
                print r.text
                return -1
            #Data File
            print "********************"
            print "* Upload Data File *"
            print "********************"
            inputDataFilepath = os.path.join("/geodata/watershed-data",first_two_of_uuid,model_run_uuid,data_nc).replace("\\", "/")
            files = {'file': open(currentdir + "/" + data_nc, 'rb')}
            r = s.post(data_upload_url, files=files, data=uploadpayload)
            if r.status_code == 200:
                print "Upload param file successful!"
                data_json = basejson
                data_json = data_json.replace('$parent_model_run_uuid', model_run_uuid)
                data_json = data_json.replace('$inputFilePath', inputDataFilepath)
                data_json = data_json.replace('$model_run_uuid', model_run_uuid)
                data_json = data_json.replace('$description', "PRMS- " + prmsInputName + " Data file")
                data_json = data_json.replace('"services": []', '"services": ["wms", "wcs"]')
                data_json = data_json.replace('$basename', prmsInputName + "_data")
                data_json = data_json.replace('$taxonomy', 'netcdf')
                data_json = data_json.replace('$model_set_taxonomy', 'grid')
                data_json = data_json.replace('$mimetype', 'application/x-netcdf')
                data_json = data_json.replace('$ext', 'nc')
                data_json = data_json.replace('$formats', 'nc')
                print data_json
                insert = s.put(insert_dataset_url, data=data_json)
                if insert.status_code == 200:
                    print "Insert Successful!"
                    print insert.text
                else:
                    print "******************"
                    print "* Insert Failure *"
                    print "******************"
                    print insert.text
                    return -1
            else:
                print "***********************"
                print "* Upload data failure *"
                print "***********************"
                print r.text
                return -1
        else:
            print "*****************************"
            print "* Modelrun creation failure *"
            print "*****************************"
            print createmodel.text
            return -1
    else:
        print "*******************"
        print "*  Login Failure  *"
        print "*******************"
        print l.text
        return -1

    return 0

if __name__ == "__main__":
    prmsInputName = "LC"
    vwpBaseURL = "https://vwp-dev.unm.edu"
    username = "dummyname"
    password = "********"
    newuuid=str(uuid.uuid1())
    modeldata = json.dumps({"description": "PRMS NetCDF with Layers Test " + newuuid,"researcher_name":"Chao Chen","model_run_name":"prms netcdf inputs example "+newuuid,"model_keywords":"prms"})
    basejson = json.dumps({"description": "$description", "records": "1", "taxonomy": "$taxonomy", "basename":"$basename", "parent_model_run_uuid": "$parent_model_run_uuid", "apps":["vwp"], "model_set_taxonomy":"$model_set_taxonomy", "model_run_uuid": "$model_run_uuid", "sources":[{"mimetype": "$mimetype", "files": ["$inputFilePath"], "set": "original", "external": "False", "extension": "$ext"}], "model_set": "inputs", "spatial": {"geomtype": "grid", "records": "1", "epsg": "4326", "features": "1", "bbox": "-114.323106,38.9831811224489,-114.21300990625,39.028019"}, "formats":["$formats"], "services": [], "model_set_type": "viz", "standards": ["FGDC-STD-001-1998", "ISO-19115:2003", "ISO-19119", "ISO-19110"], "active": "true", "model_vars": " ", "categories": [{"state": "Nevada", "modelname": "prms", "location": "Lehman Creek"}], "metadata": {"xml" : "$xml", "upgrade": "true", "standard": "FGDC-STD-001-1998"}})
    xml = open('template.xml', 'r')
    xml_txt = xml.read()
    xml_txt = xml_txt.replace('\n', '')
    #print xml_txt
    xml_txt = xml_txt.replace('$westbc', '-114.323106')
    xml_txt = xml_txt.replace('$eastbc', '-114.21300990625')
    xml_txt = xml_txt.replace('$northbc', '39.028019')
    xml_txt = xml_txt.replace('$southbc', '38.9831811224489')
    basejson = basejson.replace('$xml', xml_txt)
    print basejson
    if uploadPRMSInputFiles(prmsInputName, vwpBaseURL, username, password, modeldata, basejson) != 0:
        print "upload failed!!!"
    else:
        print "upload to virtual watershed succeeded!"