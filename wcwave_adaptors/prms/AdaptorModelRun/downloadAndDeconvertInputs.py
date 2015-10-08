__author__ = 'jerickson'

import requests
import json
import netcdfToData
import netcdfToParameter

def download(name, url):
    r = requests.get(url)
    with open(name, 'wb') as f:
        f.write(r.content)
        f.close()

def deconvert(basename, data_nc, param_nc):
    base_data = basename + ".data"
    base_param = basename + ".param"
    netcdfToData.netcdf_to_data(data_nc, base_data)
    netcdfToParameter.netcdf_to_parameter(param_nc, base_param)

def download_and_deconvert_model_run_inputs(vwpBaseUrl, model_run_uuid):
    url = vwpBaseUrl + "/apps/vwp/search/datasets.json"
    payload = {}
    payload['model_run_uuid'] = model_run_uuid
    payload['model_set'] = 'inputs'
    l = requests.get(url, params=payload)
    if l.status_code == 200:
        basename = ""
        l_json = json.loads(l.text)
        for i in l_json['results']:
            name = ""
            url = ""
            if "Control" in i['description']:
                basename = i['name']
                name = basename + ".control"
                url = i['downloads'][0]['control']
            else:
                name = i['name'] + ".nc"
                url = i['downloads'][0]['nc']
            print name
            print url
            download (name, url)
        deconvert(basename, basename+"_data.nc", basename+"_param.nc")
    else:
        print "***********************"
        print "* Data access failure *"
        print "***********************"
        print l.text
        return -1
    print "Files downloaded and deconverted!"
    return 0

if __name__ == "__main__":
    vwpBaseURL = "http://vwp-dev.unm.edu"
    model_run_uuid = "$model_run_uuid"
    download_and_deconvert_model_run_inputs(vwpBaseURL, model_run_uuid)