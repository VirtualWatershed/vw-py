""" Virtual Watershed Adaptor. Handles fetching and searching of data, model
    run initialization, and pushing of data. Does this for associated metadata
    as well. Each file that's either taken as input or produced as output gets
    associated metadata.
"""

import configparser
from string import Template
import os
import os.path as path
import requests


def pushMetadata(metadataIterator):

    config = getConfig()
    commonConfig = config['Common']

    INSERT_URL = \
        "https://" + commonConfig['watershedIP'] + "/apps/my_app/datasets"

    u = commonConfig['user']
    p = commonConfig['passwd']

    # see http://docs.python-requests.org/en/latest/user/quickstart/#more-complicated-post-requests
    # for how to send strings as files
    for m in metadataIterator:
        requests.put(INSERT_URL, data=m, auth=(u, p), verify=False)


def makeMetadata(dataDir, kind):
    """ Given `dataDir`, create XML FGDC or Virtual Watershed JSON metadata for
        every file in the directory. Whether its FGDC or VW metadata depends on
        `kind`, as seen in the assert directly below.

        Returns: generator of fgdc metadata text
    """
    assert kind in ['FGDC', 'Watershed'], "Metadata type must be \
            'FGDC' or 'Watershed'!"

    files = (path.join(dataDir, f) for f in os.listdir(dataDir)
             if path.isfile(path.join(dataDir, f)))

    # get configuration for FGDC Metadata
    config = getConfig()
    config = config[kind + ' Metadata']

    if kind == 'FGDC':
        metadata = (makeFGDCMetadatum(f, config) for f in files)
    if kind == 'Watershed':
        metadata = (makeWatershedMetadatum(f, config) for f in files)

    return metadata


def makeFGDCMetadatum(dataFile, config, model_run_uuid):
    """ For a single `dataFile`, write the XML FGDC metadata

        Returns: XML metadata string
    """
    statinfo = os.stat(dataFile)
    filesizeMB = "%s" % str(statinfo.st_size/1000000)

    fgdcConfig = config['FGDC Metadata']
    commonConfig = config['Common']

    # use templates and the fgdc configuration to write the metadata for a file
    xml_template = fgdcConfig['template_path']

    template_object = open(xml_template, 'r')
    template = Template(template_object.read())

    output = template.substitute(filename=dataFile,
                                 filesizeMB=filesizeMB,
                                 model_run_uuid=model_run_uuid,
                                 procdate=fgdcConfig['procdate'],
                                 begdate=fgdcConfig['begdate'],
                                 enddate=fgdcConfig['enddate'],
                                 westBnd=commonConfig['westBnd'],
                                 eastBnd=commonConfig['eastBnd'],
                                 northBnd=commonConfig['northBnd'],
                                 southBnd=commonConfig['southBnd'],
                                 themekey=fgdcConfig['themekey'],
                                 model=commonConfig['model'],
                                 researcherName=fgdcConfig['researcherName'],
                                 mailing_address=fgdcConfig['mailing_address'],
                                 city=fgdcConfig['city'],
                                 state=fgdcConfig['state'],
                                 zipCode=fgdcConfig['zipCode'],
                                 researcherPhone=fgdcConfig['researcherPhone'],
                                 researcherEmail=fgdcConfig['researcherEmail'],
                                 rowcount=fgdcConfig['rowcount'],
                                 columncount=fgdcConfig['columncount'],
                                 latres=fgdcConfig['latres'],
                                 longres=fgdcConfig['longres'],
                                 mapUnits=fgdcConfig['mapUnits'])

    return output


def makeWatershedMetadatum(dataFile, config,
                           model_run_uuid, model_set, description="",
                           xmlFilePath=""):

    """ For a single `dataFile`, write the corresponding Virtual Watershed JSON
        metadata.

        Take the model_run_uuid from the result of initializing a new model
        run in the virtual watershed.

        model_set must be

        Returns: JSON metadata string
    """
    assert model_set in ["inputs", "outputs"], "parameter model_set must be \
            either 'inputs' or 'outputs'"

    RECS = "1"
    FEATURES = "1"

    # logic to figure out mimetype and such based on extension
    _, ext = os.path.splitext(dataFile)
    if ext == '.tif':
        wcs = 'wcs'
        wms = 'wms'
        tax = 'geoimage'
        ext = 'tif'
        mimetype = 'application/x-zip-compressed'
        # type_subdir = 'geotiffs'
        model_set_type = 'vis'
    else:
        wcs = ''
        wms = ''
        tax = 'file'
        ext = 'bin'
        mimetype = 'application/x-binary'
        # type_subdir = 'bin'
        model_set_type = 'binary'

    basename = os.path.basename(dataFile)

    watershedConfig = config['Watershed Metadata']
    commonConfig = config['Common']

    # TODO clean up the variable names here: snake or camel; going w/ camel
    parent_model_run_uuid = commonConfig['parent_model_run_uuid']
    first_two_of_parent_uuid = parent_model_run_uuid[:2]

    # this and XML path are given since they are known. TODO: check
    #  what happens if these are not given... or better yet try it!

    if model_set == "inputs":
        inputFilePath = os.path.join("/geodata/watershed-data",
                                     first_two_of_parent_uuid,
                                     parent_model_run_uuid,
                                     dataFile)
    else:
        inputFilePath = ""

    json_template = watershedConfig['template_path']

    template_object = open(json_template, 'r')
    template = Template(template_object.read())

    # write the metadata for a file
    output = template.substitute(# determined by file ext, set within function
                                 wcs=wcs,
                                 wms=wms,
                                 tax=tax,
                                 ext=ext,
                                 mimetype=mimetype,
                                 model_set_type=model_set_type,
                                 # passed as args to parent function
                                 model_run_uuid=model_run_uuid,
                                 description=description,
                                 model_set=model_set,
                                 xmlFilePath=xmlFilePath,
                                 # derived from parent function args
                                 basename=basename,
                                 inputFilePath=inputFilePath,
                                 # given in config file
                                 parent_model_run_uuid=commonConfig['parent_model_run_uuid'],
                                 modelname=commonConfig['model'],
                                 state=watershedConfig['state'],
                                 model_set_taxonomy=commonConfig['model_set_taxonomy'],
                                 orig_epsg=watershedConfig['orig_epsg'],
                                 westBnd=commonConfig['westBnd'],
                                 eastBnd=commonConfig['eastBnd'],
                                 northBnd=commonConfig['northBnd'],
                                 southBnd=commonConfig['southBnd'],
                                 epsg=watershedConfig['epsg'],
                                 location=watershedConfig['location'],
                                 # static default values defined at top of func
                                 recs=RECS,
                                 features=FEATURES
                                 )

    return output

class VWClient:
    """ Client class for interacting with a Virtual Watershed (VW). A VW
        is essentially a structured database with certain rules for its
        metadata and for uploading or inserting data.
    """
    def __init__(self, ipAddress, uname, passwd):
        """ Initialize a new connection to the virtual watershed """
        authUrl = "https://" + ipAddress + "/apps/my_app/auth"
        r = requests.get(authUrl, auth=(uname, passwd), verify=False)
        r.raise_for_status()

    def upload(self, model_run_uuid, data):
        """ Upload data for a given model_run_uuid to the VW """
        pass

    def fetchRecords(self, model_run_uuid):
        pass


def getConfig(configFile="../default.conf"):
    """ Provide user with a ConfigParser that has read the `configFile`

        Returns: ConfigParser()
    """
    config = configparser.ConfigParser()
    config.read(configFile)
    return config
