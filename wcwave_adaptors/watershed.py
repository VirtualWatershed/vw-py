"""
Virtual Watershed Adaptor. Handles fetching and searching of data, model
run initialization, and pushing of data. Does this for associated metadata
as well. Each file that's either taken as input or produced as output gets
associated metadata.
"""

import configparser
import datetime
# from datetime import datetime
import logging
import json
import os
import requests
requests.packages.urllib3.disable_warnings()
import urllib
import pandas as pd

from string import Template


def make_fgdc_metadata(dataFile, config, modelRunUUID):
    """
    For a single `dataFile`, write the XML FGDC metadata

    Returns: XML metadata string
    """
    try:
        statinfo = os.stat(dataFile)
        filesizeMB = "%s" % str(statinfo.st_size/1000000)
    except OSError:
        filesizeMB = "NA"

    fgdc_config = config['FGDC Metadata']
    common_config = config['Common']

    # use templates and the fgdc configuration to write the metadata for a file
    xml_template = fgdc_config['template_path']

    template_object = open(xml_template, 'r')
    template = Template(template_object.read())

    output = template.substitute(filename=dataFile,
                                 filesizeMB=filesizeMB,
                                 model_run_uuid=modelRunUUID,
                                 procdate=fgdc_config['procdate'],
                                 begdate=fgdc_config['begdate'],
                                 enddate=fgdc_config['enddate'],
                                 westBnd=common_config['westBnd'],
                                 eastBnd=common_config['eastBnd'],
                                 northBnd=common_config['northBnd'],
                                 southBnd=common_config['southBnd'],
                                 themekey=fgdc_config['themekey'],
                                 model=common_config['model'],
                                 researcherName=common_config['researcherName'],
                                 mailing_address=fgdc_config['mailing_address'],
                                 city=fgdc_config['city'],
                                 state=fgdc_config['state'],
                                 zipCode=fgdc_config['zipCode'],
                                 researcherPhone=fgdc_config['researcherPhone'],
                                 researcherEmail=fgdc_config['researcherEmail'],
                                 rowcount=fgdc_config['rowcount'],
                                 columncount=fgdc_config['columncount'],
                                 latres=fgdc_config['latres'],
                                 longres=fgdc_config['longres'],
                                 mapUnits=fgdc_config['mapUnits'])

    return output


def make_watershed_metadata(dataFile, config, parentModelRunUUID,
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
    common_config = config['Common']

    firstTwoUUID = modelRunUUID[:2]
    inputFilePath = os.path.join("/geodata/watershed-data",
                                 firstTwoUUID,
                                 modelRunUUID,
                                 os.path.basename(dataFile))

    json_template = watershedConfig['template_path']

    template_object = open(json_template, 'r')
    template = Template(template_object.read())

    # properly escape xml metadata escape chars
    fgdcMetadata = fgdcMetadata.replace('\n', '\\n').replace('\t', '\\t')

    # If one of the datetimes is missing
    if start_datetime is None or end_datetime is None:
        start_datetime = "1970-10-01 00:00:00"
        end_datetime = "1970-10-01 01:00:00"
    elif (type(start_datetime) is datetime.datetime
          and type(end_datetime) is datetime.datetime):

        fmt = lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S')
        start_datetime, end_datetime = map(fmt, (start_datetime, end_datetime))
    else:

        raise Exception("Either pass no start/end datetime " +\
                        "or pass a datetime object. Not %s" % str(type(start_datetime)))

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
                                 modelname=common_config['model'],
                                 state=watershedConfig['state'],
                                 model_set_taxonomy=common_config['model_set_taxonomy'],
                                 orig_epsg=watershedConfig['orig_epsg'],
                                 westBnd=common_config['westBnd'],
                                 eastBnd=common_config['eastBnd'],
                                 northBnd=common_config['northBnd'],
                                 southBnd=common_config['southBnd'],
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
    # number of times to re-try an http request
    _retry_num = 3

    def __init__(self, ip_address, uname, passwd):
        """ Initialize a new connection to the virtual watershed """

        # Check our credentials
        auth_url = "https://" + ip_address + "/apps/my_app/auth"
        r = requests.get(auth_url, auth=(uname, passwd), verify=False)
        r.raise_for_status()

        self.uname = uname
        self.passwd = passwd

        # Initialize URLS used by class methods
        self.insert_dataset_url = "https://" + ip_address + \
            "/apps/my_app/datasets"

        self.data_upload_url = "https://" + ip_address + "/apps/my_app/data"

        self.uuid_check_url = "https://" + ip_address + \
            "/apps/my_app/checkmodeluuid"

        self.search_url = "https://" + ip_address + \
            "/apps/my_app/search/datasets.json?version=3"

        self.new_run_url = "https://" + ip_address + \
            "/apps/my_app/newmodelrun"

    def initialize_model_run(self, model_run_name=None, description=None,
                             researcher_name=None, keywords=None):
        """Iniitalize a new model run.

        Args:
            model_run_name (str): is the name for the new resource.

            description (str): a description of the new resource.

            researcher_name (str): contact person for the data

            keywords (str): comma-separated list of keywords associate with
            resource

        Returns:
            (str) a newly-intialized model_run_uuid

        Returns:
            (str) a newly-intialized model_run_uuid

        """
        print model_run_name
        assert description, \
            "You must provide a description for your new model run"
        assert model_run_name, \
            "You must provide a model_run_name for your new model run"
        assert researcher_name, \
            "You must provide a researcher_name for your new model run"
        assert keywords, \
            "You must provide keywords for your new model run"

        data = {'model_run_name': model_run_name,
                'description': description,
                'model_keywords': keywords,
                'researcher_name': researcher_name}

        # TODO make this class-level
        auth = (self.uname, self.passwd)

        result = requests.post(self.new_run_url, data=json.dumps(data),
                               auth=auth, verify=False)

        result.raise_for_status()

        model_run_uuid = result.text

        return model_run_uuid

    def search(self, **kwargs):
        """
        Search the VW for JSON metadata records with matching parameters.
        Use key, value pairs as specified in the `Virtual Watershed
        Documentation
        <http://129.24.196.43//docs/stable/search.html#search-objects>`_

        Returns: a list of JSON records as dictionaries
        """
        full_url = self.search_url

        for key, val in kwargs.iteritems():

            if type(val) is not str:
                val = str(val)

            full_url += "&%s=%s" % (key, val)

        r = requests.get(full_url, verify=False)


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

        # logging.debug("insert_dataset_url:\n" + self.insert_dataset_url)
        # logging.debug("post data dumped:\n" + json.dumps(watershedMetadata))

        num_tries = 0
        while num_tries < self._retry_num:
            try:
                result = requests.put(self.insert_dataset_url,
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
                    requests.post(self.data_upload_url, data=dataPayload,
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
    """Provide user with a ConfigParser that has read the `config_file`

        Returns:
            (ConfigParser) Config parser with three sections: 'Common',
            'FGDC Metadata', and 'Watershed Metadata'

    """
    if config_file is None:
        config_file = \
            os.path.join(os.path.dirname(__file__), '../default.conf')

    assert os.path.isfile(config_file), "Config file %s does not exist!" \
        % os.path.abspath(config_file)

    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def metadata_from_file(input_file, parent_model_run_uuid, model_run_uuid,
                       description, water_year_start=2010, water_year_end=2011,
                       config_file=None, dt=None):
    """
    Generate metadata for input_file.
    """
    assert dt is None or issubclass(type(dt), datetime.timedelta)

    if config_file:
        config = get_config(config_file)
    else:
        config = get_config(
            os.path.join(os.path.dirname(__file__), '../default.conf'))

    fgdc_metadata = make_fgdc_metadata(input_file, config,
                                     model_run_uuid)

    input_split = os.path.basename(input_file).split('.')

    input_prefix = input_split[0]
    output_ext = os.path.splitext(input_file)[-1]
    dt_multiplier = int(input_split[1])

    model_set = ("outputs", "inputs")[input_prefix == "in"]

    if output_ext == ".tif":
        model_vars = input_split[-2]
    else:
#: ISNOBAL variable names to be looked up to make dataframes and write metadata
        VARNAME_DICT = \
            {
                'in': ["I_lw", "T_a", "e_a", "u", "T_g", "S_n"],
                'em': ["R_n", "H", "L_v_E", "G", "M", "delta_Q", "E_s", "melt",
                       "ro_predict", "cc_s"],
                'snow': ["z_s", "rho", "m_s", "h2o", "T_s_0", "T_s_l", "T_s",
                         "z_s_l", "h2o_sat"]
            }
        model_vars = ','.join(VARNAME_DICT[input_prefix])

    if dt is None:
        dt = pd.Timedelta('1 hour')

    # calculate the "dates" fields for the watershed JSON metadata
    start_dt = dt * dt_multiplier

    start_datetime = \
        datetime.datetime(water_year_start, 10, 01) + start_dt

    end_datetime = start_datetime + dt

    return \
        make_watershed_metadata(input_file,
                              config,
                              parent_model_run_uuid,
                              model_run_uuid,
                              model_set,
                              description,
                              model_vars,
                              fgdc_metadata,
                              start_datetime,
                              end_datetime)


def upsert(input_path, model_run_name=None, description=None, keywords=None,
           parent_model_run_uuid=None, model_run_uuid=None, config_file=None,
           dt=None):
    """Upload the file or files located at input_path, which could be a
       directory. This function also creates and inserts metadata records for
       every file as required by the virtual watershed.

    Inputs:
        input_path (str): Directorty or file to upload

    Returns:
        (str, str): A two-tuple of parent_model_run_uuid and model_run_uuid

    """
    assert not (model_run_uuid is not None and parent_model_run_uuid is None),\
        "If model_run_uuid is given, its parent must also be given!"

    # redundant, but better to catch this before we continue
    assert dt is None or issubclass(type(dt), datetime.timedelta)

    # get the configuration file path if not given
    if not config_file:
        config_file = \
            os.path.join(os.path.dirname(__file__), '../default.conf')

    # build a list of files to be upserted
    if os.path.isdir(input_path):

        if input_path[-1] != '/':
            input_path += '/'

        files = [input_path + el for el in os.listdir(input_path)
                 if os.path.isfile(input_path + el)]

    elif os.path.isfile(input_path):
        files = [input_path]

    else:
        raise os.error(input_path + " is not a valid file or directory!")


    # initialize the vw_client manually (not defuault) since we need
    # config info
    commonConfig = get_config(config_file)['Common']

    vw_client = VWClient(commonConfig['watershedIP'], commonConfig['user'],
                         commonConfig['passwd'])

    # get either parent_model_run_uuid and/or model_run_uuid if need be
    # final case to handle is if model_run_uuid is given but not its parent
    if not parent_model_run_uuid:
        parent_model_run_uuid = \
            vw_client.initialize_model_run(model_run_name=model_run_name,
                                           description=description,
                                           keywords=keywords,
                                           researcher_name=commonConfig['researcherName']
                                           )

        model_run_uuid = parent_model_run_uuid

    elif not model_run_uuid and parent_model_run_uuid:
        model_run_uuid = \
            vw_client.initialize_model_run(model_run_name=model_run_name,
                                           description=description,
                                           keywords=keywords,
                                           researcher_name=commonConfig['researcherName']
                                           )

    # closure to do the upsert on each file
    def _upsert(file_):
        json = metadata_from_file(file_, parent_model_run_uuid,
                                  model_run_uuid, description,
                                  config_file=config_file, dt=dt)

        vw_client.upload(model_run_uuid, file_)
        vw_client.insert_metadata(json)

    print "upserting file(s) from %s with model_run_uuid %s" % \
        (input_path, model_run_uuid)

    for file_ in files:
        _upsert(file_)

    return (parent_model_run_uuid, model_run_uuid)
