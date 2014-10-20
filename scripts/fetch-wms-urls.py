#!/usr/bin/python


import requests
import json

host = raw_input('Hostname or IP Address: ')
model_run_uuid = raw_input('Enter the model_run_uuid: ')

model_set = "outputs"
model_set_type = "vis"

protocal = "http://"
search = "/apps/my_app/search/datasets.json?version=3"
uuid = "&model_run_uuid=" + model_run_uuid

ms = "&model_set=" + model_set
mst = "&model_set_type=" + model_set_type

url = protocal + host + search + uuid + ms + mst

r = requests.get(url)
data = json.loads(r.text)
for i in data["results"]:
        full = i["services"][0]["wms"]
        print full
