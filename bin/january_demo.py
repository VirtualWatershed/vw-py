"""

"""

import configparser
import os


def runISNOBAL(inputDir, outputDir):
    """ Use the Virtual Watershed Adaptors and the Model Connector framework
        to run the ISNOBAL model.
    """
    config = configparser.ConfigParser()
    config.read('default.conf')

    commonConfig = config['Common']

    # initialization
    os.environ["PATH"] = \
        os.environ["PATH"] + ":" + commonConfig['isnobal_exec_path']

    os.environ["IPW"] = commonConfig['ipw_root_path']

    # get data from virtual watershed, save to inputDir
    getVWData(watershedIP)

    # run isnobal, reading from input dir writing to outputdir
    isnobal(inputDir, outputDir)

    # convert output files to geotiffs
    binToGeotiffAll(outputDir)

    # create metadata; writeFGDCMetadatum reads
    inputFGDCMetadata = writeFGDCMetadata(inputDir)
    # writeFGDCMetadata handles .tif/.bin separately
    outputFGDCMetadata = writeFGDCMetadata(outputDir)

    # push input and output data to VW
    pushData(inputFGDCMetadata, inputDir, watershedIP)
    pushData(outputFGDCMetadata, outputDir, watershedIP)



if __name__ == '__main__':

    # get input variables

    # run model (model run)

    inputDir = argv[1]
    outputDir = argv[2]

    runISNOBAL(inputDir, outputDir)
