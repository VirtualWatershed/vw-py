"""
Virtual Watershed Adaptor. Handles fetching and searching of data, model
run initialization, and pushing of data. Does this for associated metadata
as well. Each file that's either taken as input or produced as output gets
associated metadata.
"""

import configparser
from datetime import datetime
import logging
import json
import os
import requests
import urllib

from string import Template


def makeFGDCMetadata(dataFile, config, modelRunUUID):
    """
    For a single `dataFile`, write the XML FGDC metadata

    Returns: XML metadata string
    """
    try:
        statinfo = os.stat(dataFile)
        filesizeMB = "%s" % str(statinfo.st_size/1000000)
    except OSError:
        filesizeMB = "NA"

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


def makeWatershedMetadata(dataFile, config, parentModelRunUUID,
                          modelRunUUID, model_set, description="",
                          model_vars="", fgdcMetadata="", start_datetime=None,
                          end_datetime=None):

    """ For a single `dataFile`, write the corresponding Virtual Watershed JSON
        metadata.

        Take the modelRunUUID from the result of initializing a new model
        run in the virtual watershed.

        model_set must be

        Returns: JSON metadata string
    """
    assert model_set in ["inputs", "outputs"], "parameter model_set must be \
            either 'inputs' or 'outputs', not %s" % model_set

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

    firstTwoUUID = modelRunUUID[:2]
    inputFilePath = os.path.join("/geodata/watershed-data",
                                 firstTwoUUID,
                                 modelRunUUID,
                                 os.path.basename(dataFile))

    json_template = watershedConfig['template_path']

    template_object = open(json_template, 'r')
    template = Template(template_object.read())

    # properly escape xml metadata escape chars
    fgdcMetadata = fgdcMetadata.replace('\n','\\n').replace('\t','\\t')

    # If one of the datetimes is missing
    if start_datetime is None or end_datetime is None:
        start_datetime = "1970-10-01 00:00:00"
        end_datetime = "1970-10-01 01:00:00"
    elif type(start_datetime) is datetime and type(end_datetime) is datetime:
        fmt = lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S')
        start_datetime, end_datetime = map(fmt, (start_datetime, end_datetime))
    else:
        raise Exception("Either pass no start/end datetime or pass a \
                         datetime object")

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
                                 model_vars=model_vars,
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
                                 start_datetime=start_datetime,
                                 end_datetime=end_datetime,
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
    def __init__(self, ip_address, uname, passwd):
        """ Initialize a new connection to the virtual watershed """

        # Check our credentials
        authUrl = "https://" + ip_address + "/apps/my_app/auth"
        r = requests.get(authUrl, auth=(uname, passwd), verify=False)
        r.raise_for_status()

        self.uname = uname
        self.passwd = passwd

        # Initialize URLS used by class methods
        self.insertDatasetUrl = "https://" + ip_address + \
            "/apps/my_app/datasets"

        self.dataUploadUrl = "https://" + ip_address + "/apps/my_app/data"

        self.uuidCheckUrl = "https://" + ip_address + \
            "/apps/my_app/checkmodeluuid"

        self.searchUrl = "https://" + ip_address + \
            "/apps/my_app/search/datasets.json?version=3"

        self.new_run_url = "https://" + ip_address + \
            "/apps/my_app/newmodelrun"

        # number of times to re-try an http request
        self._retry_num = 3

    def initialize_model_run(self, description):
        """
        Iniitalize a new model run.

        Returns: (str) a newly-intialized model_run_uuid
        """
        assert description, \
            "You must provide a description for your new model run"

        data = {'description': description}

        auth = (self.uname, self.passwd)

        result = requests.post(self.new_run_url, data=json.dumps(data),
                               auth=auth, verify=False)

        result.raise_for_status()

        return result.text

    def search(self, **kwargs):
        """
        Search the VW for JSON metadata records with matching parameters.
        Use key, value pairs as specified in the `Virtual Watershed
        Documentation
        <http://129.24.196.43//docs/stable/search.html#search-objects>`_

        Returns: a list of JSON records as dictionaries
        """
        fullUrl = self.searchUrl

        for key, val in kwargs.iteritems():

            if type(val) is not str:
                val = str(val)

            fullUrl += "&%s=%s" % (key, val)

        r = requests.get(fullUrl, verify=False)


        return QueryResult(r.json())

    def download(self, url, outFile):
        """ Download a file from the VW using url to localFile on local disk

            Returns: None
        """
        data = urllib.urlopen(url)

        assert data.getcode() == 200, "Download Failed!"

        with file(outFile, 'w+') as out:
            out.writelines(data.readlines())

        return None

    def insert_metadata(self, watershedMetadata):
        """ Insert metadata to the virtual watershed. The data that gets
            uploaded is the FGDC XML metadata.

            Returns: None
        """

        # logging.debug("insertDatasetUrl:\n" + self.insertDatasetUrl)
        # logging.debug("post data dumped:\n" + json.dumps(watershedMetadata))

        num_tries = 0
        while num_tries < self._retry_num:
            try:
                result = requests.put(self.insertDatasetUrl,
                                      data=watershedMetadata,
                                      auth=(self.uname, self.passwd),
                                      verify=False)

                logging.debug(result.content)

                result.raise_for_status()
                return result

            except requests.HTTPError:
                num_tries += 1
                continue

        print result.content
        raise requests.HTTPError()

    def upload(self, modelRunUUID, dataFilePath):
        """ Upload data for a given modelRunUUID to the VW """

        # currently 'name' is unused
        dataPayload = {'name': os.path.basename(dataFilePath),
                       'modelid': modelRunUUID}

        num_tries = 0
        while num_tries < self._retry_num:
            try:
                result = \
                    requests.post(self.dataUploadUrl, data=dataPayload,
                                  files={'file': open(dataFilePath, 'rb')},
                                  auth=(self.uname, self.passwd), verify=False)

                result.raise_for_status()
                return result

            except requests.HTTPError:
                num_tries += 1
                continue

        raise requests.HTTPError()


class QueryResult:
    """
    A request for records using the url built by ``VWClient.search`` and
    ``VWClient.fetch_records`` returns a JSON string with three base fields:
    ``total``, ``subtotal``, and ``results``. This structure wraps that
    functionality and is returned by the aforementioned VWClient functions.
    """
    def __init__(self, json):
        self.json = json

    @property
    def total(self):
        """
        Return the total records `known by the virtual watershed` that matched
        the parameters passed to either the fetch_records or search function.
        """
        return self.json['total']

    @property
    def subtotal(self):
        """
        Return the `subtotal`, or the actual number of records that have been
        transferred by the virtual watershed.
        """
        return self.json['subtotal']

    @property
    def records(self):
        """
        Return the records themselves returned by the Virtual Watershed in
        response to the query built by either ``search`` or ``fetch_records``.
        """
        return self.json['results']


def default_vw_client(config_file="default.conf"):
    """ Use the credentials in config_file to initialize a new VWClient instance

        Returns: VWClient connected to the ip address given in config_file
    """
    config = get_config(config_file)
    common = config['Common']

    return VWClient(common['watershedIP'], common['user'], common['passwd'])


def get_config(config_file=None):
    """ Provide user with a ConfigParser that has read the `config_file`

        Returns: ConfigParser()
    """
    if config_file is None:
        config_file = \
            os.path.join(os.path.dirname(__file__), '../default.conf')

    assert os.path.isfile(config_file), "Config file %s does not exist!" \
        % os.path.abspath(config_file)

    config = configparser.ConfigParser()
    config.read(config_file)
    return config
