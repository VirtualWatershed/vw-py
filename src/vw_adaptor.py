"""
Virtual Watershed Adaptor. Handles fetching and searching of data, model
run initialization, and pushing of data. Does this for associated metadata
as well. Each file that's either taken as input or produced as output gets
associated metadata.
"""

import configparser
from lxml import etree
import logging
import json
import os
import requests
import urllib

from string import Template


def makeFGDCMetadatum(dataFile, config, modelRunUUID):
    """
    For a single `dataFile`, write the XML FGDC metadata

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
                                 model_run_uuid=modelRunUUID,
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


def makeWatershedMetadatum(dataFile, config, parentModelRunUUID,
                           modelRunUUID, model_set, description="",
                           fgdcMetadata=""):

    """ For a single `dataFile`, write the corresponding Virtual Watershed JSON
        metadata.

        Take the modelRunUUID from the result of initializing a new model
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
    firstTwoParentUUID = parentModelRunUUID[:2]

    # this and XML path are given since they are known. TODO: check
    #  what happens if these are not given... or better yet try it!

    if model_set == "inputs":
        inputFilePath = os.path.join("/geodata/watershed-data",
                                     firstTwoParentUUID,
                                     parentModelRunUUID,
                                     os.path.basename(dataFile))
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
                                 model_run_uuid=modelRunUUID,
                                 description=description,
                                 model_set=model_set,
                                 fgdcMetadata=fgdcMetadata,
                                 # derived from parent function args
                                 basename=basename,
                                 inputFilePath=inputFilePath,
                                 # given in config file
                                 parent_model_run_uuid=parentModelRunUUID,
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
    """
    Client class for interacting with a Virtual Watershed (VW). A VW
    is essentially a structured database with certain rules for its
    metadata and for uploading or inserting data.
    """
    def __init__(self, ipAddress, uname, passwd):
        """ Initialize a new connection to the virtual watershed """

        # Check our credentials
        authUrl = "https://" + ipAddress + "/apps/my_app/auth"
        r = requests.get(authUrl, auth=(uname, passwd), verify=False)
        r.raise_for_status()

        self.uname = uname
        self.passwd = passwd

        # Initialize URLS used by class methods
        self.insertDatasetUrl = "https://" + ipAddress + \
            "/apps/my_app/datasets"
        self.dataUploadUrl = "https://" + ipAddress + "/apps/my_app/data"
        self.uuidCheckUrl = "https://" + ipAddress + \
            "/apps/my_app/checkmodeluuid"
        self.searchUrl = "https://" + ipAddress + \
            "/apps/my_app/search/datasets.json?version=3"

    def search(self, limit=None, offset=None, modelRunUUID=None,
               parentModelRunUUID=None):
        """ Search the VW for JSON metadata records with matching parameters

            Returns: a list of JSON records as dictionaries
        """
        fullUrl = self.searchUrl

        if limit:
            fullUrl = fullUrl + "&limit=%s" % str(limit)

        if offset:
            fullUrl = fullUrl + "&offset=%s" % str(offset)

        if modelRunUUID:
            fullUrl = fullUrl + "&model_run_uuid=%s" % modelRunUUID

        if parentModelRunUUID:
            fullUrl = fullUrl + "&parent_model_run_uuid=%s" % \
                parentModelRunUUID

        r = requests.get(fullUrl, verify=False)
        metadata = r.json()['results']

        return metadata

    def fetch_records(self, modelRunUUID):
        """ Fetch JSON records with given modelRunUUID """

        uuiddata = {"modelid": modelRunUUID}
        r = requests.post(self.uuidCheckUrl, data=uuiddata, verify=False)

        status = r.text
        assert status.lower() == "true", "Invalid modelRunUUID!"

        # query for a valid model run uuid
        results = self.search(modelRunUUID=modelRunUUID)

        return results

    def download(self, url, outFile):
        """ Download a file from the VW using url to localFile on local disk

            Returns: None
        """
        data = urllib.urlopen(url)

        assert data.getcode() == 200, "Download Failed!"

        with file(outFile, 'w+') as out:
            out.writelines(data.readlines())

        return None

    def insert_metadata(self, watershedMetadata, fgdcMetadata):
        """ Insert metadata to the virtual watershed. The data that gets
            uploaded is the FGDC XML metadata.

            Returns: None
        """
        assert fgdcMetadata, "Must pass FGDC metadata to accompany watershed \
                metadata"

        # put the XML directly into the JSON metadata
        postData = json.loads(watershedMetadata)
        # xml = etree.fromstring(fgdcMetadata)
        # postData['metadata']['xml'] = etree.tostring(xml, encoding=unicode)
        # postData['metadata']['xml'] = "<validxml></validxml>"
        postData['metadata']['xml'] = fgdcMetadata

        logging.debug("insertDatasetUrl:\n" + self.insertDatasetUrl)
        logging.debug("post data dumped:\n" + json.dumps(postData))

        result = requests.put(self.insertDatasetUrl, data=json.dumps(postData),
                              auth=(self.uname, self.passwd), verify=False)

        logging.debug(result.content)

        result.raise_for_status()

        return None

    def upload(self, modelRunUUID, dataFilePath):
        """ Upload data for a given modelRunUUID to the VW """

        dataPayload = {"name": "test", "modelid": modelRunUUID}

        result = requests.post(self.dataUploadUrl, data=dataPayload,
                               files={'file': open(dataFilePath, 'rb')},
                               auth=(self.uname, self.passwd), verify=False)

        result.raise_for_status()

        return None


def default_vw_client(configFile="default.conf"):
    """ Use the credentials in configFile to initialize a new VWClient instance

        Returns: VWClient connected to the ip address given in configFile
    """
    config = get_config(configFile)
    common = config['Common']

    return VWClient(common['watershedIP'], common['user'], common['passwd'])


def get_config(configFile="../default.conf"):
    """ Provide user with a ConfigParser that has read the `configFile`

        Returns: ConfigParser()
    """
    config = configparser.ConfigParser()
    config.read(configFile)
    return config
