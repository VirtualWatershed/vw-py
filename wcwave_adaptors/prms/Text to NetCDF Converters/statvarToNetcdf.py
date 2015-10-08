#statistic variables to netcdf converter
#originally from Lisa Palathingal at https://github.com/lisapalathingal/PRMS_Adaptor
#modified for use in this coding structure

import netCDF4
import sys

def find_output_variables(fileHandle, numberOfVariables):
    
    """
 
    Returns the names and array indices of the output variables in the file. 
    Two lists, outputVariableNames and outputVariableArrayIndices are created
    to append the names and indices respectively. 

    Args:
        numberOfVariables (int): is the total number of output variables. This
	value is indicated on the first line of the file.
    
    """
   
    outputVariableNames = []
    outputVariableArrayIndices = []  
    
    for index in range(numberOfVariables):    
	words = fileHandle.next().strip().split()
	outputVariableNames.append(words[0])
	outputVariableArrayIndices.append(words[1])	       

    return outputVariableNames, outputVariableArrayIndices

def find_column_values(fileInput, numberOfVariables, numberOfDataValues, position):

    """
    
    Returns the values of variables in the file. 

    Args:
        numberOfVariables (int): is the total number of output variables. This
	value is indicated on the first line of the file.
	numberOfDataValues (int): is the number of values for each variable. This
        value is equal to the time-step value on the last line of the file.
	position (int): is the column position from where the values can be 
        retrieved.
    
    """

    values = []
    
    fileHandle = open(fileInput, 'r')
    
    for i in range(numberOfVariables+1):
        fileHandle.next()
    
    for j in range(numberOfDataValues):
	valuesInLine = fileHandle.next().strip().split()[7:]
        values.append(valuesInLine[position])
   
    return values

def find_metadata(outputVariableName):

    fileHandle = open('../outputVariables.txt', 'r')
    
    for line in fileHandle:
        if outputVariableName in line:
	    variableNameFromFile = line.strip()		
	    lengthOfVariableName = len(variableNameFromFile)
	    positionOfNameStart = variableNameFromFile.index(':') + 2
 	    variableName = variableNameFromFile[positionOfNameStart:lengthOfVariableName]
		
	    variableDescriptionFromFile = fileHandle.next().strip()
	    lengthOfVariableDescription = len(variableDescriptionFromFile)
	    positionOfDescriptionStart = variableDescriptionFromFile.index(':') + 2
	    variableDescription = variableDescriptionFromFile[positionOfDescriptionStart:lengthOfVariableDescription]
		
	    variableUnitFromFile = fileHandle.next().strip()
	    lengthOfVariableUnit = len(variableUnitFromFile)
	    positionOfUnitStart = variableUnitFromFile.index(':') + 2
	    variableUnit = variableUnitFromFile[positionOfUnitStart:lengthOfVariableUnit]

	    variableTypeFromFile = fileHandle.next().strip()
	    lengthOfVariableType = len(variableTypeFromFile)
	    positionOfTypeStart = variableTypeFromFile.index(':') + 2
	    variableType = variableTypeFromFile[positionOfTypeStart:lengthOfVariableType]
		
	    break;
          
    return variableName, variableDescription, variableUnit, variableType


def statvar_to_netcdf(fileInput, outputFileName):
   
    indexOfDataLine = []

    fileHandle = open(fileInput, 'r')
    lastLine = fileHandle.readlines()[-1].split()
    lastTimeStepValue = int(lastLine[0])

    for index in range(1, lastTimeStepValue+1):
        indexOfDataLine.append(index)
    
    # Finding the number of variable values
    fileHandle = open(fileInput, 'r')
    numberOfVariables = int(fileHandle.next().strip())
       
    # Finding the names and array indices of output variables
    outputVariables = find_output_variables(fileHandle, numberOfVariables)
    outputVariableNames = outputVariables[0]
    outputVariableArrayIndices = outputVariables[1]
   
    # Finding the first date
    firstDate = fileHandle.next().strip().split()[1:7]
    year = firstDate[0]
    month = firstDate[1]
    day = firstDate[2]
    hour = firstDate[3]
    minute = firstDate[4]
    second = firstDate[5]

    # Initialize new dataset
    ncfile = netCDF4.Dataset(outputFileName, mode='w')

    # Initialize dimensions
    time = ncfile.createDimension('time', lastTimeStepValue)  

    # Define time variable
    time = ncfile.createVariable('time', 'i4', ('time',))
    time.long_name = 'time'  
    time.units = 'days since '+year+'-'+month+'-'+day+' '+hour+':'+minute+':'+second
    time[:] = indexOfDataLine
    
    # Define other variables  
    for index in range(len(outputVariableNames)):

        metadata = find_metadata(outputVariableNames[index])
	variableName = metadata[0]
	variableDescription = metadata[1]
	variableUnit = metadata[2]
	variableType = metadata[3]
        
        if variableType == 'real':
	    value = 'f4'
	elif variableType == 'double':
	    value = 'f4'
	elif variableType == 'integer':
	    value = 'i4'

        var = ncfile.createVariable(outputVariableNames[index]+'_'+outputVariableArrayIndices[index], value, ('time',))
	var.layer_name = variableName
	var.layer_desc = variableDescription
	var.layer_units = variableUnit
      
        columnValues = find_column_values(fileInput, numberOfVariables, lastTimeStepValue, index)
        var[:] = columnValues
    
    # Global attributes
    ncfile.title = 'Statistic Variables File'
    ncfile.bands = 1
    ncfile.bands_name = 'nsteps'
    ncfile.bands_desc = 'Output variable information for ' + fileInput

    # Close the 'ncfile' object
    ncfile.close()


if __name__ == "__main__":
       
    statvar_to_netcdf(sys.argv[1], 'statvar.nc')

