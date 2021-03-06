"""
Virtual Watershed Adaptor. Handles fetching and searching of data, model
run initialization, and pushing of data. Does this for associated metadata
as well. Each file that's either taken as input or produced as output gets
associated metadata.
"""

import configparser
import json
import logging
import pandas as pd
import os
import requests
requests.packages.urllib3.disable_warnings()
import subprocess
import urllib

from datetime import datetime, date, timedelta
from jinja2 import Environment, FileSystemLoader


VARNAME_DICT = \
    {
        'in': ["I_lw", "T_a", "e_a", "u", "T_g", "S_n"],
        'em': ["R_n", "H", "L_v_E", "G", "M", "delta_Q", "E_s", "melt",
               "ro_predict", "cc_s"],
        'snow': ["z_s", "rho", "m_s", "h2o", "T_s_0", "T_s_l", "T_s",
                 "z_s_l", "h2o_sat"],
        'init': ["z", "z_0", "z_s", "rho", "T_s_0", "T_s", "h2o_sat"],
        'precip': ["m_pp", "percent_snow", "rho_snow", "T_pp"],
        'mask': ["mask"],
        'dem': ["alt"]
    }


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

        self.host_url = host_url

        # Check our credentials
        auth_url = host_url + "/apilogin"
        self.sesh = requests.session()

        l = self.sesh.get(auth_url, auth=(uname, passwd), verify=False)
        l.raise_for_status()

        self.uname = uname
        self.passwd = passwd

        # Initialize URLS used by class methods
        self.insert_dataset_url = host_url + "/apps/vwp/datasets"

        self.data_upload_url = host_url + "/apps/vwp/data"

        self.uuid_check_url = host_url + "/apps/vwp/checkmodeluuid"

        self.dataset_search_url = \
            host_url + "/apps/vwp/search/datasets.json?version=3"

        self.modelrun_search_url = \
            host_url + "/apps/vwp/search/modelruns.json?version=3"

        self.modelrun_delete_url = host_url + "/apps/vwp/deletemodelid"

        self.new_run_url = host_url + "/apps/vwp/newmodelrun"

        self.gettoken_url = host_url + "/gettoken"

    def initialize_modelrun(self, model_run_name=None, description=None,
                             researcher_name=None, keywords=None):
        """Iniitalize a new model run.

        Args:
            model_run_name (str): is the name for the new model run

            description (str): a description of the new model run

            researcher_name (str): contact person for the model run

            keywords (str): comma-separated list of keywords associated with
                model run

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

    def modelrun_search(self, **kwargs):
        """
        Get a list of model runs in the database. Currently no actual "search"
        (see, e.g. dataset_search) is available from the Virtual Watershed
        Data API.

        Returns:
            (QueryResult) A query result, containing total records matching,
                the number of results returned (subtotal), and the records
                themselves, which is a list of dict.
        """
        full_url = _build_query(self.modelrun_search_url, **kwargs)
        r = self.sesh.get(full_url, verify=False)

        return QueryResult(r.json())

    def dataset_search(self, **kwargs):
        """
        Search the VW for JSON metadata records with matching parameters.
        Use key, value pairs as specified in the `Virtual Watershed
        Documentation
        <http://vwp-dev.unm.edu/docs/stable/search.html#search-objects>`_

        Returns:
            (QueryResult) A query result, containing total records matching,
                the number of results returned (subtotal), and the records
                themselves, which is a list of dict.
        """
        full_url = _build_query(self.dataset_search_url, **kwargs)

        r = self.sesh.get(full_url, verify=False)

        return QueryResult(r.json())

    def download(self, url, out_file):
        """
        Download a file from the VW using url to out_file on local disk

        Returns:
            None

        Raises:
            AssertionError: assert that the status code from downloading is 200
        """
        data = urllib.urlopen(url)

        assert data.getcode() == 200, "Download Failed!"

        with file(out_file, 'w+') as out:
            out.writelines(data.readlines())

        return None

    def insert_metadata(self, watershed_metadata):
        """ Insert metadata to the virtual watershed. The data that gets
            uploaded is the FGDC XML metadata.

            Returns:
                (requests.Response) Returned so that the user may inspect
                the response.
        """
        num_tries = 0
        while num_tries < self._retry_num:
            try:
                result = self.sesh.put(self.insert_dataset_url,
                                       data=watershed_metadata,
                                       auth=(self.uname, self.passwd),
                                       verify=False)

                logging.debug(result.content)

                result.raise_for_status()
                return result

            except requests.HTTPError:
                num_tries += 1
                continue

        return result

    def upload(self, model_run_uuid, data_file_path):
        """
        Upload data for a given model_run_uuid to the VW

        Returns:
            None

        Raises:
            requests.HTTPError: if the file cannot be successfully uploaded
        """
        # currently 'name' is unused
        dataPayload = {'name': os.path.basename(data_file_path),
                       'modelid': model_run_uuid}

        num_tries = 0
        while num_tries < self._retry_num:
            try:
                result = \
                    self.sesh.post(self.data_upload_url, data=dataPayload,
                                   files={'file': open(data_file_path, 'rb')},
                                   auth=(self.uname, self.passwd), verify=False)

                result.raise_for_status()
                return result

            except requests.HTTPError:
                num_tries += 1
                continue

        raise requests.HTTPError()

    def swift_upload(self, model_run_uuid, data_file_path):
        """
        Use the Swift client from openstack to upload data.
        (http://docs.openstack.org/cli-reference/content/swiftclient_commands.html)
        Seems to outperform 'native' watershed uploads via HTTP.

        Returns:
            None

        Raises:
            requests.HTTPError if the file cannot be successfully uploaded
        """
        _swift_upload_url = self.host_url + '/apps/vwp/swiftdata'

        segmentsize = 1073741824  # 1 Gig

        token_resp = self.sesh.get(self.gettoken_url).text

        token = json.loads(token_resp)

        preauth_url = token['preauthurl']
        preauth_token = token['preauthtoken']

        # the container name is model_run_uuid
        command = ['swift', 'upload', model_run_uuid, '-S', str(segmentsize),
                   data_file_path, '--os-storage-url=' + preauth_url,
                   '--os-auth-token=' + preauth_token]

        output = subprocess.check_output(command)

        # after we upload to a swift directory we ask VW to download
        vw_dl_params = {'modelid': model_run_uuid, 'filename': data_file_path,
                        'preauthurl': preauth_url,
                        'preauthtoken': preauth_token}

        res = self.sesh.get(_swift_upload_url, params=vw_dl_params)

        if res.status_code != 200:
            raise requests.HTTPError(
                "Swift Upload Failed! Server response:\n" + res.text)

        return output

    def delete_modelrun(self, model_run_uuid):
        """
        Delete a model run associated with model_run_uuid

        Returns:
            (bool) True if successful, False if not
        """
        full_url = self.modelrun_delete_url + model_run_uuid

        result = self.sesh.delete(self.modelrun_delete_url,
            data=json.dumps({'model_uuid': model_run_uuid}), verify=False)

        if result.status_code == 200:
            return True
        else:
            return False

    def create_new_user(self, userid, first_name, last_name, email, password,
                        address1, address2, city, state, zipcode, tel_voice,
                        country='USA'):
        """
        Create a new virtual watershed user. This is only available to users
        with admin status on the virtual waterhsed.

        Returns:
            (bool) True if succesful, False if not
        """
        pass


def _build_query(search_route, **kwargs):
    "build the end of a query by translating dict to key1=val1&key2=val2..."
    full_url = search_route
    for key, val in kwargs.iteritems():

        if type(val) is not str:
            val = str(val)

        full_url += "&%s=%s" % (key, val)

    return full_url

class QueryResult:
    """
    Represents the response from the VW Data API search methods, , which gives three fields,
    'total', 'subtotal', and 'records', represented by the properties explained
    in their own docstrings.
    """
    def __init__(self, json):
        #: raw json returned from the VW
        self.json = json
        #: total results available on VW
        self.total = 0
        #: total results returned to client with the query
        self.subtotal = 0
        #: a list of the results
        self.records = json['results']

        if 'total' in json:
            self.total = int(json['total'])
        else:
            self.total = len(json['results'])

        if 'subtotal' in json:
            self.subtotal = int(json['subtotal'])
        else:
            self.subtotal = len(json['results'])


def default_vw_client(config_file=None):
    """ Use the credentials in config_file to initialize a new VWClient instance

        Returns: VWClient connected to the ip address given in config_file
    """
    if not config_file:
        config_file = os.path.join(os.path.dirname(__file__),
                                   '..', 'default.conf')

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
                       description, watershed_name, state, start_datetime=None,
                       end_datetime=None, model_name=None, fgdc_metadata=None,
                       model_set_type=None, model_set_taxonomy=None,
                       taxonomy=None, water_year_start=2010,
                       water_year_end=2011, config_file=None, dt=None,
                       model_set=None, model_vars=None, file_ext=None,
                       **kwargs):
    """
    Generate metadata for input_file.

    Arguments:
        **kwargs: Set union of kwargs from make_fgdc_metadata and
            make_watershed_metadata

    Returns:
        (str) watershed metadata
    """
    assert dt is None or issubclass(type(dt), timedelta)
    dt_multiplier = 1  # default if nothing else is known

    if config_file:
        config = _get_config(config_file)
    else:
        config = _get_config(
            os.path.join(os.path.dirname(__file__), '../default.conf'))

    input_basename = os.path.basename(input_file)

    input_split = input_basename.split('.')

    input_prefix = input_split[0]

    if not file_ext:
        file_ext = input_file.split('.')[-1]

    if not model_set:
        model_set = ("outputs", "inputs")[input_prefix == "in"]

    start_datetime_str = ""
    end_datetime_str = ""

    is_ipw = False
    try:
        # the number on the end of an isnobal file is the time index
        dt_multiplier = int(input_split[1])
        is_ipw = True
    except (ValueError, IndexError):
        pass

    if file_ext == 'tif':

        model_set_type = 'vis'
        kwargs['taxonomy'] = 'geoimage'
        kwargs['mimetype'] = 'application/x-zip-compressed'

    elif file_ext == 'asc':
        file_ext = 'ascii'
        model_set_type = 'file'
        model_set_taxonomy = 'file'
        kwargs['taxonomy'] = 'file'

    elif file_ext == 'xlsx':
        model_set_taxonomy = 'file'
        model_set_type = 'file'
        kwargs['taxonomy'] = 'file'

    elif model_name == 'isnobal' and is_ipw:
        #: ISNOBAL variable names to be looked up to make dataframes + metadata
        try:
            model_vars = ','.join(VARNAME_DICT[input_prefix])
        except:
            model_vars = ''

        if 'proc_date' in kwargs:
            proc_date = kwargs['proc_date']
        else:
            proc_date = None

        fgdc_metadata = make_fgdc_metadata(input_basename, config,
                                           model_run_uuid, start_datetime,
                                           end_datetime, proc_date=proc_date)

    elif model_name == 'isnobal' and file_ext == 'nc':

        model_vars = ','.join([','.join(v) for v in VARNAME_DICT.itervalues()])

    if dt is None:
        dt = pd.Timedelta('1 hour')

    # calculate the "dates" fields for the watershed JSON metadata
    start_dt = dt * dt_multiplier

    if (start_datetime is None and end_datetime is None):
        start_datetime = datetime(water_year_start, 10, 01) + start_dt
        start_datetime_str = start_datetime.strftime('%Y-%m-%d %H:%M:%S')

        end_datetime = start_datetime + dt
        end_datetime_str = datetime.strftime(start_datetime + dt,
                                             '%Y-%m-%d %H:%M:%S')

    elif type(start_datetime) is str and type(end_datetime) is str:
        start_datetime_str = start_datetime
        end_datetime_str = end_datetime

    elif type(start_datetime) is datetime and type(end_datetime) is datetime:
        start_datetime_str = datetime.strftime(start_datetime,
                                               '%Y-%m-%d %H:%M:%S')
        end_datetime_str = datetime.strftime(end_datetime,
                                             '%Y-%m-%d %H:%M:%S')

    else:
        import ipdb; ipdb.set_trace()
        raise TypeError('bad start_ and/or end_datetime arguments')

    # we pretty much always want to try to set these
    kwargs['wms'] = 'wms'
    kwargs['wcs'] = 'wcs'

    if file_ext == 'nc':
        kwargs['taxonomy'] = 'netcdf_isnobal'

    if 'taxonomy' not in kwargs:
        kwargs['taxonomy'] = 'file'
    elif kwargs['taxonomy'] == '':
        kwargs['taxonomy'] = 'file'

    return \
        make_watershed_metadata(input_basename,
                                config,
                                parent_model_run_uuid,
                                model_run_uuid,
                                model_set,
                                watershed_name,
                                state,
                                model_name=model_name,
                                model_set_type=model_set_type,
                                model_set_taxonomy=model_set_taxonomy,
                                fgdc_metadata=fgdc_metadata,
                                description=description,
                                model_vars=model_vars,
                                start_datetime=start_datetime_str,
                                end_datetime=end_datetime_str,
                                file_ext=file_ext,
                                **kwargs)


def make_fgdc_metadata(file_name, config, model_run_uuid, beg_date, end_date,
                       **kwargs):
    """
    For a single `data_file`, write the XML FGDC metadata
       valid kwargs:
           proc_date: date data was processed

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

    if not config:
        config = _get_config(
            os.path.join(os.path.dirname(__file__), '../default.conf'))

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


def make_watershed_metadata(file_name, config, parent_model_run_uuid,
                            model_run_uuid, model_set, watershed_name,
                            state, fgdc_metadata=None, file_ext=None,
                            **kwargs):

    """ For a single `file_name`, write the corresponding Virtual Watershed JSON
        metadata.

        valid kwargs:
            orig_epsg: original EPSG code of projection

            epsg: current EPSG code

            taxonomy: likely 'file'; representation of the data

            model_vars: variable(s) represented in the data

            model_set: 'inputs', 'outputs', or 'reference'; AssertionError if not

            model_set_type: e.g., 'binary', 'csv', 'tif', etc.

            model_set_taxonomy: 'grid', 'vector', etc.

            west_bound: westernmost longitude of bounding box

            east_bound: easternmost longitude of bounding box

            north_bound: northernmost latitude of bounding box

            south_bound: southernmost latitude of bounding box

            start_datetime: datetime observations began, formatted like "2010-01-01 22:00:00"

            end_datetime: datetime observations ended, formatted like "2010-01-01 22:00:00"

            wms: True if wms service can and should be enabled

            wcs: True if wcs service can and should be enabled

            watershed_name: Name of watershed, e.g. 'Dry Creek' or 'Lehman Creek'

            model_name: Name of model, if applicaple; e.g. 'iSNOBAL', 'PRMS'

            mimetype: defaults to application/octet-stream

            file_ext: extension to be associated with the dataset; make_watershed_metadata
             will take the extension of file_name if not given explicitly

            fgdc_metadata: FGDC md probably created by make_fgdc_metadata; if not
             given, a default version is created (see source for details)

        Returns: JSON metadata string
    """
    assert model_set in ["inputs", "outputs", "reference"], \
        "parameter model_set must be either 'inputs' or 'outputs', not %s" \
        % model_set

    # TODO get valid_states and valid_watersheds from VW w/ TODO VWClient method
    valid_states = ['Idaho', 'Nevada', 'New Mexico']
    assert state in valid_states, "state passed was " + state + \
            ". Must be one of " + ", ".join(valid_states)

    valid_watersheds = ['Dry Creek', 'Valles Caldera', 'Jemez Caldera',
                        'Lehman Creek', 'Reynolds Creek']
    assert watershed_name in valid_watersheds, "watershed passed was " + \
            watershed_name + ". Must be one of " + ", ".join(valid_watersheds)

    # logic to figure out mimetype and such based on extension
    if not file_ext:
        file_ext = file_name.split('.')[-1]

        # check that the file extension is not a digit as might happen for isnobal
        if file_ext.isdigit():
            raise ValueError("The extension is a digit. You must explicitly"
                + " provide the file extension with keyword 'file_ext'")

    if file_ext == 'tif':
        if 'wcs' not in kwargs:
            kwargs['wcs'] = True
        if 'wms' not in kwargs:
            kwargs['wms'] = True
        if 'tax' not in kwargs:
            kwargs['tax'] = 'geoimage'
        if 'mimetype' not in kwargs:
            kwargs['mimetype'] = 'application/x-zip-compressed'
        if 'model_set_type' not in kwargs:
            kwargs['model_set_type'] = 'vis'

    if 'mimetype' not in kwargs:
        kwargs['mimetype'] = 'application/octet-stream'

    # If one of the datetimes is missing
    if not ('start_datetime' in kwargs and 'end_datetime' in kwargs):
        kwargs['start_datetime'] = "1970-10-01 00:00:00"
        kwargs['end_datetime'] = "1970-10-01 01:00:00"

    if not fgdc_metadata:

        fgdc_kwargs = {k: v for k,v in kwargs.iteritems()
                       if k not in ['start_datetime', 'end_datetime']}
        # can just include all remaining kwargs; no problem if they go unused
        fgdc_metadata = make_fgdc_metadata(file_name, config, model_run_uuid,
                                           kwargs['start_datetime'],
                                           kwargs['end_datetime'],
                                           **fgdc_kwargs)

    basename = os.path.basename(file_name)

    geo_config = config['Geo']

    firstTwoUUID = model_run_uuid[:2]
    input_file_path = os.path.join("/geodata/watershed-data",
                                 firstTwoUUID,
                                 model_run_uuid,
                                 os.path.basename(file_name))

    # properly escape xml metadata escape chars
    fgdc_metadata = \
        fgdc_metadata.replace('\n', '\\n').replace('\t', '\\t')

    geoconf = config['Geo']
    resconf = config['Researcher']

    # if any of the bounding boxes are not given, all go to default
    if not ('west_bound' in kwargs and 'east_bound' in kwargs
            and 'north_bound' in kwargs and 'south_bound' in kwargs):
        kwargs['west_bound'] = geoconf['default_west_bound']
        kwargs['east_bound'] = geoconf['default_east_bound']
        kwargs['north_bound'] = geoconf['default_north_bound']
        kwargs['south_bound'] = geoconf['default_south_bound']

    # write the metadata for a file
    # output = template.substitute(# determined by file file_ext, set within function
    template_env = Environment(loader=FileSystemLoader(
                               os.path.join(os.path.dirname(__file__),
                                            '../templates')))

    template = template_env.get_template('watershed_template.json')

    if 'wcs' in kwargs and kwargs['wcs']:
        wcs_str = 'wcs'
    else:
        wcs_str = None

    if 'wms' in kwargs and kwargs['wms']:
        wms_str = 'wms'
    else:
        wms_str = None

    if kwargs['model_name'] == 'isnobal' and file_ext != 'tif':
        basename = basename
    else:
        basename = os.path.splitext(basename)[0]

    output = template.render(basename=basename,
                             parent_model_run_uuid=parent_model_run_uuid,
                             model_run_uuid=model_run_uuid,
                             model_set=model_set,
                             watershed_name=watershed_name,
                             state=state,
                             wcs_str=wcs_str,
                             wms_str=wms_str,
                             input_file_path=input_file_path,
                             fgdc_metadata=fgdc_metadata,
                             file_ext=file_ext,
                             **kwargs) + '\n'
    return output
