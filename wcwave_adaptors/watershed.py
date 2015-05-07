"""
Virtual Watershed Adaptor. Handles fetching and searching of data, model
run initialization, and pushing of data. Does this for associated metadata
as well. Each file that's either taken as input or produced as output gets
associated metadata.
"""

import configparser
import logging
import json
import os
import requests
requests.packages.urllib3.disable_warnings()

import urllib
import pandas as pd

from datetime import datetime, date, timedelta
from jinja2 import Environment, FileSystemLoader
from progressbar import ProgressBar
from string import Template



class VWClient:
    """
    Client class for interacting with a Virtual Watershed (VW). A VW
    is essentially a structured database with certain rules for its
    metadata and for uploading or inserting data.
    """
    # number of times to re-try an http request
    _retry_num = 3

    def __init__(self, host_url, uname, passwd):
        """ Initialize a new connection to the virtual watershed """

        # Check our credentials
        auth_url = host_url + "/apilogin"
        self.sesh = requests.session()

        l = self.sesh.get(auth_url, auth=(uname, passwd), verify=False)
        l.raise_for_status()

        self.uname = uname
        self.passwd = passwd

        # Initialize URLS used by class methods
        self.insert_dataset_url = host_url + \
            "/apps/vwp/datasets"

        self.data_upload_url = host_url + "/apps/vwp/data"

        self.uuid_check_url = host_url + \
            "/apps/vwp/checkmodeluuid"

        self.search_url = host_url + \
            "/apps/vwp/search/datasets.json?version=3"

        self.new_run_url = host_url + \
            "/apps/vwp/newmodelrun"

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

        result = self.sesh.post(self.new_run_url, data=json.dumps(data),
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
                result = self.sesh.put(self.insert_dataset_url,
                                       data=watershedMetadata,
                                       auth=(self.uname, self.passwd),
                                       verify=False)

                logging.debug(result.content)

                result.raise_for_status()
                return result

            except requests.HTTPError:
                num_tries += 1
                continue

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
                    self.sesh.post(self.data_upload_url, data=dataPayload,
                                   files={'file': open(dataFilePath, 'rb')},
                                   auth=(self.uname, self.passwd), verify=False)

                result.raise_for_status()
                return result

            except requests.HTTPError:
                num_tries += 1
                continue

        import ipdb
        ipdb.set_trace()
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
    config = _get_config(config_file)
    conn = config['Connection']

    return VWClient(conn['watershed_url'], conn['user'], conn['pass'])


def _get_config(config_file=None):
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
    assert dt is None or issubclass(type(dt), timedelta)

    if config_file:
        config = _get_config(config_file)
    else:
        config = _get_config(
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
        datetime(water_year_start, 10, 01) + start_dt

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
    assert dt is None or issubclass(type(dt), timedelta)

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
    conn = _get_config(config_file)['Connection']

    vw_client = VWClient(conn['watershed_url'], conn['user'], conn['pass'])

    # get either parent_model_run_uuid and/or model_run_uuid if need be
    # final case to handle is if model_run_uuid is given but not its parent
    if not parent_model_run_uuid:
        parent_model_run_uuid = \
            vw_client.initialize_model_run(model_run_name=model_run_name,
               description=description, keywords=keywords,
               researcher_name=_get_config(config_file)['Researcher']['researcher_name'])

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

    with ProgressBar(maxval=len(files)) as progress:
        for i, file_ in enumerate(files):
            _upsert(file_)
            progress.update(i)

    return (parent_model_run_uuid, model_run_uuid)


def make_fgdc_metadata(file_name, config, model_run_uuid, beg_date, end_date,
                       **kwargs):
    """
    For a single `data_file`, write the XML FGDC metadata
       valid kwargs:
           proc_date: date data was processed

           begin_date: date observations began

           end_date: date observations ended

           theme_key: thematic keywords

           model: scientific model, e.g., WindNinja, iSNOBAL, PRMS, etc.

           researcher_name: name of researcher

           mailing_address: researcher's mailing address

           city: research institute city

           state: research institute state

           zip_code: research institute zip code

           researcher_phone: researcher phone number

           row_count: number of rows in dataset

           column_count: number of columns in dataset

           lat_res: resolution in latitude direction (meters)

           lon_res: resolution in longitude direction (meters)

           map_units: distance units of the map (e.g. 'm')

           west_bound: westernmost longitude of bounding box

           east_bound: easternmost longitude of bounding box

           north_bound: northernmost latitude of bounding box

           south_bound: southernmost latitude of bounding box

           file_ext: extension of file used to fill out digtinfo:formname;
            if not specified, make_fgdc_metadata takes extension

        Any other kwargs will be ignored

    Returns: XML FGDC metadata string
    """
    try:
        statinfo = os.stat(file_name)
        file_size = "%s" % str(statinfo.st_size/1000000)
    except OSError:
        file_size = "NA"

    # handle missing required fields not provided in kwargs
    geoconf = config['Geo']
    resconf = config['Researcher']

    # if any of the bounding boxes are not given, all go to default
    if not ('west_bound' in kwargs and 'east_bound' in kwargs
            and 'north_bound' in kwargs and 'south_bound' in kwargs):
        kwargs['west_bound'] = geoconf['default_west_bound']
        kwargs['east_bound'] = geoconf['default_east_bound']
        kwargs['north_bound'] = geoconf['default_north_bound']
        kwargs['south_bound'] = geoconf['default_south_bound']

    if not 'proc_date' in kwargs:
        kwargs['proc_date'] = date.strftime(date.today(), '%Y-%m-%d')

    if not 'researcher_name' in kwargs:
        kwargs['researcher_name'] = resconf['researcher_name']

    if not 'mailing_address' in kwargs:
        kwargs['mailing_address'] = resconf['mailing_address']

    if not 'city' in kwargs:
        kwargs['city'] = resconf['city']

    if not 'state' in kwargs:
        kwargs['state'] = resconf['state']

    if not 'zip_code' in kwargs:
        kwargs['zip_code'] = resconf['zip_code']

    if not 'researcher_phone' in kwargs:
        kwargs['researcher_phone'] = resconf['phone']

    if not 'researcher_email' in kwargs:
        kwargs['researcher_email'] = resconf['email']

    if 'file_ext' not in kwargs:
        kwargs['file_ext'] = file_name.split('.')[-1]

    template_env = Environment(loader=FileSystemLoader(
                               os.path.join(os.path.dirname(__file__), '../templates')))

    template = template_env.get_template('fgdc_template.xml')

    output = template.render(file_name=file_name,
                             file_size=file_size,
                             model_run_uuid=model_run_uuid,
                             **kwargs)

    return output


def make_watershed_metadata(dataFile, config, parentModelRunUUID,
                          modelRunUUID, model_set, orig_epsg=None, epsg=None,
                          model_set_taxonomy="grid", water_year=None,
                          model_name=None, description=None, model_vars=None,
                          fgdcMetadata=None, start_datetime=None,
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

    geo_config = config['Geo']

    firstTwoUUID = modelRunUUID[:2]
    inputFilePath = os.path.join("/geodata/watershed-data",
                                 firstTwoUUID,
                                 modelRunUUID,
                                 os.path.basename(dataFile))

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
    # output = template.substitute(# determined by file ext, set within function
    template_env = Environment(loader=FileSystemLoader(
                               os.path.join(os.path.dirname(__file__), 'cdl')))

    template = template_env.get_template('../templates/watershed_template.json')

    output = template.render(wcs=wcs,
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
                             fgdc_metadata=fgdc_metadata,
                             # derived from parent function args
                             basename=basename,
                             inputFilePath=inputFilePath,
                             # given in config file
                             parent_model_run_uuid=parentModelRunUUID,
                             model_name=model_name,
                             state=state,
                             model_set_taxonomy=model_set_taxonomy,
                             orig_epsg=orig_epsg,

                             west_bound=geo_config['default_west_bound'],
                             east_bound=geo_config['default_east_bound'],
                             north_bound=geo_config['default_north_bound'],
                             south_bound=geo_config['default_south_bound'],

                             start_datetime=start_datetime,
                             end_datetime=end_datetime,
                             epsg=epsg,
                             watershed_name=watershed_name,

                             # static default values defined at top of func
                             recs=RECS,
                             features=FEATURES
                             )

    return output

