__author__ = 'jerickson'

import os
import shutil
import subprocess

def runPRMS(control_in):
    #make sure our inputs are in the correct folder
    basename = os.path.basename(control_in).split('.')[0]
    data_name = basename + ".data"
    param_name = basename + ".param"
    input_path = "./input"
    output_path = "./output"
    if not os.path.exists(input_path):
        os.mkdir(input_path)
    if not os.path.exists(input_path + "/" + data_name):
        if not os.path.exists(data_name):
            print "*************************"
            print "* Cannot find data file *"
            print "*************************"
            return -1
        else:
            shutil.copy(data_name, input_path + "/" + data_name)
            print "Copied " + data_name + " to " + input_path + "/" + data_name
    if not os.path.exists(input_path + "/" + param_name):
        if not os.path.exists(param_name):
            print "*************************"
            print "* Cannot find data file *"
            print "*************************"
            return -1
        else:
            shutil.copy(param_name, input_path + "/" + param_name)
            print "Copied " + param_name + " to " + input_path + "/" + param_name
    #make sure there is a place for outputs
    if not os.path.exists(output_path):
        os.mkdir(output_path)
    #run model using gsflow
    command = []
    command.append("gsflow")
    command.append(control_in)
    try:
        subprocess.check_output(command)
    except subprocess.CalledProcessError as err:
        print err.output
        return -1
    return os.listdir(output_path)

if __name__=="__main__":
    ret = runPRMS("LC.control")
    if ret == -1:
        print "Model Run Failed"
    else:
        print ret