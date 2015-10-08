__author__ = 'jerickson'
import os
import json
import uuid
import requests
import subprocess

def uploadPRMSOutputFiles(prmsOutputName, vwpBaseURL, username, password, modeluuid, basejson):
    '''

    :param prmsOutputName:
    :param vwpBaseURL:
    :param username:
    :param password:
    :param modeldata:
    :param basejson:
    :return:
    '''
    animation_nc = prmsOutputName + "_animation.nc"
    statvar_nc = prmsOutputName + "_statvar.nc"
    prmsout_nc = prmsOutputName + "_prmsout.nc"

    currentdir = os.getcwd()

    loginurl = vwpBaseURL + "/apilogin"
    insert_dataset_url = vwpBaseURL + "/apps/vwp/datasets"
    data_upload_url = vwpBaseURL + "/apps/vwp/data"
    gettokenurl = vwpBaseURL + "/gettoken"
    swiftuploadurl = vwpBaseURL + '/apps/vwp/swiftdata'

    s = requests.Session()
    s.auth = (username, password)
    s.verify = False

    l=s.get(loginurl)
    if l.status_code == 200:
        first_two_of_uuid = modeluuid[:2]
        uploadpayload={"name": "prms", "modelid": modeluuid}
        print "*************************"
        print "* Upload Animation File *"
        print "*************************"
        outputAnimationFilepath = os.path.join("/geodata/watershed-data",first_two_of_uuid,modeluuid,animation_nc).replace("\\", "/")
        #files = {'file': open(currentdir + "/" + animation_nc, 'rb')}
        #r = s.post(data_upload_url, files=files, data=uploadpayload)

        #Because Animation files are big, we need to use swift upload

        #request token
        token = json.loads(s.get(gettokenurl).text)

        preauthurl = token['preauthurl']
        preauthtoken = token['preauthtoken']

        # upload to swift using token
        containername = modeluuid
        segmentsize = 1073741824 # 1 Gig

        command = ['swift']
        command.append('upload')
        command.append(containername)
        command.append('-S')
        command.append(str(segmentsize))
        command.append(animation_nc)
        command.append('--os-storage-url='+preauthurl)
        command.append('--os-auth-token='+preauthtoken)

        print "uploading..."

        print command
        ls_output = subprocess.check_output(command)

        print ls_output

        print "telling VWP to download..."

        params = {'modelid':modeluuid,'filename':animation_nc,'preauthurl':preauthurl,'preauthtoken':preauthtoken}

        r = s.get(swiftuploadurl, params=params)

        if r.status_code == 200:
            print "Upload animation file successful!"
            animation_json = basejson
            animation_json = animation_json.replace('$parent_model_run_uuid', modeluuid)
            animation_json = animation_json.replace('$inputFilePath', outputAnimationFilepath)
            animation_json = animation_json.replace('$model_run_uuid', modeluuid)
            animation_json = animation_json.replace('$description', "PRMS- " + prmsOutputName + " Animation File")
            animation_json = animation_json.replace('$basename', prmsOutputName + "_animation")
            animation_json = animation_json.replace('$taxonomy', 'netcdf')
            animation_json = animation_json.replace('$model_set_taxonomy', 'grid')
            animation_json = animation_json.replace('$mimetype', 'application/x-netcdf')
            animation_json = animation_json.replace('$ext', 'nc')
            animation_json = animation_json.replace('$formats', 'nc')
            animation_json = animation_json.replace('"services": []', '"services": ["wms", "wcs"]')
            print animation_json
            insert = s.put(insert_dataset_url, data=animation_json)
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
            print "****************************"
            print "* Upload animation failure *"
            print "****************************"
            print r.text
            return -1
        #statvar file
        print "***********************"
        print "* Upload Statvar File *"
        print "***********************"
        outputStatvarFilepath = os.path.join("/geodata/watershed-data",first_two_of_uuid,modeluuid,statvar_nc).replace("\\", "/")
        files = {'file': open(currentdir + "/" + statvar_nc, 'rb')}
        r = s.post(data_upload_url, files=files, data=uploadpayload)
        if r.status_code == 200:
            print "Upload statvar file successful!"
            statvar_json = basejson
            statvar_json = statvar_json.replace('$parent_model_run_uuid', modeluuid)
            statvar_json = statvar_json.replace('$inputFilePath', outputStatvarFilepath)
            statvar_json = statvar_json.replace('$model_run_uuid', modeluuid)
            statvar_json = statvar_json.replace('$description', "PRMS- " + prmsOutputName + " StatVar File")
            statvar_json = statvar_json.replace('$basename', prmsOutputName + "_statvar")
            statvar_json = statvar_json.replace('$taxonomy', 'netcdf')
            statvar_json = statvar_json.replace('$model_set_taxonomy', 'grid')
            statvar_json = statvar_json.replace('$mimetype', 'application/x-netcdf')
            statvar_json = statvar_json.replace('$ext', 'nc')
            statvar_json = statvar_json.replace('$formats', 'nc')
            statvar_json = statvar_json.replace('"services": []', '"services": ["wms", "wcs"]')
            print statvar_json
            insert = s.put(insert_dataset_url, data=statvar_json)
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
            print "* Upload statvar failure *"
            print "**************************"
            print r.text
            return -1
        #prmsout file
        print "***********************"
        print "* Upload prmsout File *"
        print "***********************"
        outputPrmsOutFilepath = os.path.join("/geodata/watershed-data",first_two_of_uuid,modeluuid,prmsout_nc).replace("\\", "/")
        files = {'file': open(currentdir + "/" + prmsout_nc, 'rb')}
        r = s.post(data_upload_url, files=files, data=uploadpayload)
        if r.status_code == 200:
            print "Upload prms file successful!"
            prmsout_json = basejson
            prmsout_json = prmsout_json.replace('$parent_model_run_uuid', modeluuid)
            prmsout_json = prmsout_json.replace('$inputFilePath', outputPrmsOutFilepath)
            prmsout_json = prmsout_json.replace('$model_run_uuid', modeluuid)
            prmsout_json = prmsout_json.replace('$description', "PRMS- " + prmsOutputName + " PRMS Out File")
            prmsout_json = prmsout_json.replace('$basename', prmsOutputName + "_prmsout")
            prmsout_json = prmsout_json.replace('$taxonomy', 'netcdf')
            prmsout_json = prmsout_json.replace('$model_set_taxonomy', 'grid')
            prmsout_json = prmsout_json.replace('$mimetype', 'application/x-netcdf')
            prmsout_json = prmsout_json.replace('$ext', 'nc')
            prmsout_json = prmsout_json.replace('$formats', 'nc')
            prmsout_json = prmsout_json.replace('"services": []', '"services": ["wms", "wcs"]')
            print prmsout_json
            insert = s.put(insert_dataset_url, data=prmsout_json)
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
            print "* Upload prmsout failure *"
            print "**************************"
            print r.text
            return -1
    else:
        print "*****************"
        print "* Login Failure *"
        print "*****************"
        print l.text
        return -1

    return 0

if __name__ == "__main__":
    prmsOutputName = "LC"
    vwpBaseURL = "https://vwp-dev.unm.edu"
    username = "dummyname"
    password = "*********"
    model_run_uuid = "$model_run_uuid"
    basejson = json.dumps({"description": "$description", "records": "1", "taxonomy": "$taxonomy", "basename":"$basename", "parent_model_run_uuid": "$parent_model_run_uuid", "apps":["vwp"], "model_set_taxonomy":"$model_set_taxonomy", "model_run_uuid": "$model_run_uuid", "sources":[{"mimetype": "$mimetype", "files": ["$inputFilePath"], "set": "original", "external": "False", "extension": "$ext"}], "model_set": "outputs", "spatial": {"geomtype": "grid", "records": "1", "epsg": "4326", "features": "1", "bbox": "-114.323106,38.9831811224489,-114.21300990625,39.028019"}, "formats":["$formats"], "services": [], "model_set_type": "viz", "standards": ["FGDC-STD-001-1998", "ISO-19115:2003", "ISO-19119", "ISO-19110"], "active": "true", "model_vars": " ", "categories": [{"state": "Nevada", "modelname": "prms", "location": "Lehman Creek"}], "metadata": {"xml" : "$xml", "upgrade": "true", "standard": "FGDC-STD-001-1998"}})
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
    if uploadPRMSOutputFiles(prmsOutputName, vwpBaseURL, username, password, model_run_uuid, basejson):
        print "upload failed!!!"
    else:
        print "upload to virtual watershed succeeded!"