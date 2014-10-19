#!/usr/bin/python


import requests
import json

url = "http://129.24.196.43/apps/my_app/search/datasets.json?version=3&model_run_uuid=20f303cd-624d-413d-b485-6113319003d4&model_set=outputs&model_set_type=vis"

r = requests.get(url)
data = json.loads(r.text)
for i in data["results"]:
    full = i["services"][0]["wms"]
    print full
