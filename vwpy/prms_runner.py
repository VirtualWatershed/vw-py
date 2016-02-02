import os
import datetime
from shutil import copyfile
from shutil import rmtree
import subprocess

from prms import netcdf_to_data
from prms import netcdf_to_parameter
from prms import animation_to_netcdf
from prms import prmsout_to_netcdf
from prms import statvar_to_netcdf

from pyee import EventEmitter

# GLOBALS
PRMS_RUN_DIR = '/tmp/prms_runs'
PRMS_TMP_DIR = '/tmp/prms_tmp'
CONTROL_SEPERATOR = '####'
CONTROL_VAR_TYPES = {1: 'int', 2: 'float', 3: '???', 4: 'string'}
CONTROL_VAR_TYPES_INV = {v: k for k, v in CONTROL_VAR_TYPES.items()}


def execute(directory, command):
    '''
    This calls the underlying model command from the directory specified.
    It is assumed that the directory has the structure:
    directory:
        - input
            - somename.data
            - somename.param
        - output
        - somename.control
    '''
    devnull = open('/dev/null', 'w')
    #devnull = None
    process = subprocess.Popen(
        command, stdout=devnull, stderr=devnull, cwd=directory)
    retcode = process.wait()
    return retcode


def parse_control(control_in):
    '''
    This function parses a control fille and puts all the data in a python dictionary in the format:
    {
        'header':'The header line',
        'data':{
            'varname':{
                'datatype':0,
                'len':5,
                values:[1,2,3,4,5]
            },
            ...
        }
    }
    '''
    lines = []
    with open(control_in) as f:
        for line in f:
            lines.append(line.strip())
    control_header = lines.pop(0)
    data = {}

    i = 0
    while i < len(lines):
        if CONTROL_SEPERATOR == lines[i]:
            try:
                var_name = lines[i + 1]
                num_vars = int(lines[i + 2])
                var_type = int(lines[i + 3])
                data[var_name] = {
                    'datatype': CONTROL_VAR_TYPES[var_type],
                    'len': num_vars,
                    'values': []
                }

                for j in range(i + 4, i + 4 + num_vars):
                    data[var_name]['values'].append(lines[j])
            except:
                raise Exception(
                    'control file ill formatted.Possible problem at line {0}'.format(i + 1))
        else:
            raise Exception(
                'control file ill formatted.Possible problem at line {0}'.format(i + 1))
        i = i + 4 + num_vars

    return {'header': control_header, 'data': data}


def create_control(control_data, output_path):
    '''
    This function creates a control file from the given control data
    in a python dictionary specified in the function: parse_control(control_in)
    '''
    with open(output_path, 'w') as f:
        if 'header' in control_data:
            f.write(control_data['header'] + '\n')
            data = control_data['data']
        for variable in sorted(data.keys()):
            f.write(CONTROL_SEPERATOR + '\n')
            f.write(variable + '\n')
            f.write(str(data[variable]['len']) + '\n')
            f.write(str(CONTROL_VAR_TYPES_INV[
                    data[variable]['datatype']]) + '\n')
            for d in data[variable]['values']:
                f.write(str(d) + '\n')


def run_prms(prmsdir=None, data_in=None, param_in=None, control_in=None,
             event_emitter=None, *args, **kwargs):
    if not (data_in or param_in or control_in):
        return False

    inputdir = os.path.join(prmsdir, 'input')
    outputdir = os.path.join(prmsdir, 'output')

    if not os.path.exists(prmsdir):
        os.makedirs(prmsdir)
        os.makedirs(inputdir)
        os.makedirs(outputdir)

    # copy the files
    control_loc = os.path.join(prmsdir, 'prms.control')
    data_loc = os.path.join(inputdir, 'prms.data')
    param_loc = os.path.join(inputdir, 'prms.param')
    copyfile(control_in, control_loc)
    copyfile(data_in, data_loc)
    copyfile(param_in, param_loc)

    # modify different file loc
    control_vars = parse_control(control_loc)
    control_vars['data']['data_file']['values'] = ['./input/prms.data']
    control_vars['data']['param_file']['values'] = ['./input/prms.param']
    control_vars['data']['stat_var_file']['values'] = ['./output/statvar.dat']
    control_vars['data']['mms_user_dir']['values'] = ['./']
    control_vars['data']['mms_user_out_dir']['values'] = ['./output/']
    control_vars['data']['var_save_file']['values'] = ['./output/prms_ic.out']
    control_vars['data']['stats_output_file'][
        'values'] = ['./output/statvar.dat']
    control_vars['data']['ani_output_file'][
        'values'] = ['./output/animation.out']
    control_vars['data']['csv_output_file']['values'] = ['./output/gsflow.csv']
    control_vars['data']['model_output_file']['values'] = ['./output/prms.out']
    control_vars['data']['gsflow_output_file'][
        'values'] = ['./output/gsflow.out']
    control_vars['data']['param_print_file']['values'] = ['./output/LC.parprt']

    create_control(control_vars, control_loc)

    # now go to the dir
    # os.chdir(prmsdir)
    # and run prms !
    command = ['gsflow', 'prms.control']
    # print 'running model'
    # execute(command)
    output = execute(prmsdir, command)
    # print 'done running model'
    # coution: prms adds nhru extension at the end of animation file name
    # automatically
    output_locs = {
        'ani_output_file': os.path.join(outputdir, 'animation.out.nhru'),
        'model_output_file': os.path.join(outputdir, 'prms.out'),
        'stats_output_file': os.path.join(outputdir, 'statvar.dat')
    }
    return output, output_locs


def prms(data_path=None, param_path=None, control_path=None, output_path=None,
         animation_path=None, statsvar_path=None, event_emitter=None, *args, **kwargs):
    kwargs['event_name'] = 'initializing_prms'
    kwargs['event_description'] = 'Initializing PRMS model Run'
    kwargs['progress_value'] = 0
    if event_emitter:
        event_emitter.emit('progress', **kwargs)

    prms_tmp_dir = os.path.join(PRMS_TMP_DIR, str(
        datetime.datetime.now()).replace(' ', ''))
    prmsdir = os.path.join(PRMS_RUN_DIR, str(
        datetime.datetime.now()).replace(' ', ''))

    if not os.path.exists(prms_tmp_dir):
        os.makedirs(prms_tmp_dir)
    data_in = os.path.join(prms_tmp_dir, 'prms.data')
    param_in = os.path.join(prms_tmp_dir, 'prms.param')

    kwargs['event_name'] = 'initializing_prms'
    kwargs['event_description'] = 'Initializing PRMS model Run'
    kwargs['progress_value'] = 100
    if event_emitter:
        event_emitter.emit('progress', **kwargs)

    netcdf_to_data(data_path, data_in, event_emitter=event_emitter, **kwargs)
    netcdf_to_parameter(param_path, param_in,
                        event_emitter=event_emitter, **kwargs)

    kwargs['event_name'] = 'running_prms'
    kwargs['event_description'] = 'Running PRMS model'
    kwargs['progress_value'] = 0
    if event_emitter:
        event_emitter.emit('progress', **kwargs)

    output, output_locs = run_prms(prmsdir=prmsdir, data_in=data_in, param_in=param_in,
                                   control_in=control_path, *args, **kwargs)

    kwargs['event_name'] = 'running_prms'
    kwargs['event_description'] = 'Running PRMS model'
    kwargs['progress_value'] = 100
    if event_emitter:
        event_emitter.emit('progress', **kwargs)

    #copyfile(output_locs['model_output_file'], output_path)
    #copyfile(output_locs['ani_output_file'], animation_path)
    #copyfile(output_locs['stats_output_file'], statsvar_path)
    if os.path.exists(output_locs['model_output_file']):
        prmsout_to_netcdf(output_locs['model_output_file'], output_path,
                          event_emitter=event_emitter, **kwargs)
    if os.path.exists(output_locs['ani_output_file']):
        animation_to_netcdf(output_locs['ani_output_file'], param_path, animation_path,
                            event_emitter=event_emitter, **kwargs)
    if os.path.exists(output_locs['stats_output_file']):
        statvar_to_netcdf(output_locs['stats_output_file'], statsvar_path,
                          event_emitter=event_emitter, **kwargs)

    kwargs['event_name'] = 'done_prms'
    kwargs['event_description'] = 'Done running prms model'
    kwargs['progress_value'] = 100
    if event_emitter:
        event_emitter.emit('progress', **kwargs)

    # clean up
    rmtree(prmsdir)
    rmtree(prms_tmp_dir)


'''if __name__=="__main__":
    prms(data_path='/home/escenic/prms_chao/run1/LC.data.nc',
        param_path='/home/escenic/prms_chao/run1/LC.param.nc',
        control_path='/home/escenic/prms_chao/run1/LC.control',
        output_path='/home/escenic/prms_chao/run1/prms.out.nc',
        animation_path='/home/escenic/prms_chao/run1/animation.out.nc',
        statsvar_path='/home/escenic/prms_chao/run1/statsvar.out.nc',event_emitter=ee)
    #run_prms_on_nc('/home/escenic/prms_chao/LC.data.nc','/home/escenic/prms_chao/LC.param.nc',
                            '/home/escenic/prms_chao/LC.control',event_emitter=ee)'''
