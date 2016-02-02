import os
import json


def load_schemas(model=None):
    vwpydir = os.path.dirname(os.path.dirname(__file__))
    schemadir = os.path.join(vwpydir, 'modelschema')
    modelschemas = {}
    for f in os.listdir(schemadir):
        with open(os.path.join(schemadir, f)) as schema_file:
            if f.endswith('.json'):
                data = json.load(schema_file)
                modelschemas[data['model']]=data
    if model:
        if model in modelschemas:
            return modelschemas[model]
        else:
            return {}
    return modelschemas
