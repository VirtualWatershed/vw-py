"""
Wrappers for running models. Functions are like `vw_{model}`
"""
import os
import shutil
import netCDF4 as netCDF4

from datetime import datetime

from vwpy import default_vw_client, isnobal, metadata_from_file


def vw_isnobal(input_dataset_uuid):
    """
    Run isnobal with data from the virtual watershed
    """
    vwc = default_vw_client()

    input_records = vwc.dataset_search(uuid=input_dataset_uuid).records

    assert len(input_records) == 1, \
        "Current implementation of vw_isnobal requires the user\n" + \
        "to use as input a model_run_uuid pointing to a model run\n" + \
        "with a single record that is an input. Found %s records" \
        % len(input_records)

    input_record = input_records[0]

    try:
        dl_url = input_record['downloads'][0]['nc']
    except KeyError as e:
        e.args = ("downloads or nc not found in isnobal input record")
        raise

    if not os.path.exists('tmp/'):
        os.mkdir('tmp/')

    model_run_uuid = input_record['model_run_uuid']

    writedir = 'tmp/' + model_run_uuid
    if os.path.exists(writedir):
        shutil.rmtree(writedir)
    os.mkdir(writedir)

    input_file = os.path.join(writedir, 'in.nc')

    vwc.download(dl_url, input_file)

    input_nc = netCDF4.Dataset(input_file)

    output_file = os.path.join(writedir, 'out.nc')

    isnobal(input_nc, output_file)

    vwc.upload(model_run_uuid, output_file)

    parent_model_run_uuid = input_record['parent_model_run_uuid']
    now_str = datetime.now().isoformat()
    watershed = input_record['categories'][0]['location']
    state = input_record['categories'][0]['state']

    md = metadata_from_file(output_file, parent_model_run_uuid,
                            model_run_uuid,
                            'output netcdf from isnobal run ' + now_str,
                            watershed, state, model_name='isnobal',
                            model_set='outputs', taxonomy='geoimage',
                            model_set_taxonomy='netcdf_isnobal')

    dataset_uuid = vwc.insert_metadata(md).text

    shutil.rmtree(writedir)

    return (dataset_uuid, model_run_uuid)
