from dateutil.rrule import rrule, DAILY
from netCDF4 import Dataset
import datetime
import os
import sys

def find_attribute_names(fileHandle):
  
    headerLabelValues = []
    
    for variable in fileHandle.variables:
        if variable != 'time':
	    # Get attribute names of all the variables except time
            attributesOfAVariable = fileHandle.variables[variable].ncattrs()
	    break
    
    # Get attribute names - added Type and excluded units
    headerLabelValues.append('Type')
    for index in range(len(attributesOfAVariable)):
        if attributesOfAVariable[index] != 'layer_name' and attributesOfAVariable[index] != 'layer_desc' and attributesOfAVariable[index] != 'layer_units':
	    headerLabelValues.append(str(attributesOfAVariable[index]))

    return headerLabelValues

def find_unit_label(fileHandle):
  
    for variable in fileHandle.variables:
        if variable != 'time':
	    # Get attribute names of all the variables except time
            attributesOfAVariable = fileHandle.variables[variable].ncattrs()
	    break
    
    # Get attribute names - added Type and excluded units
    for index in range(len(attributesOfAVariable)):
        if attributesOfAVariable[index] == 'layer_units':
	    unitLabel = str(attributesOfAVariable[index])

    return unitLabel


def find_and_write_attribute_values_to_file(headerLabelValues, fileHandle, temporaryFileHandle, variablesFromFile):

    temporaryFileHandle.write('///////////////////////////////////////////////////////////////////\n// Station metadata:\n// ')
    
    for label in headerLabelValues:
        temporaryFileHandle.write(label+' ')

    for variable in variablesFromFile:

        if variable != 'time':
            var = fileHandle.variables[variable]

            if '_' in variable:
                position = variable.find('_')
                temporaryFileHandle.write('\n// '+variable[0:position]+' ')

	    else:
	        temporaryFileHandle.write('\n// '+variable+' ')

            for label in headerLabelValues:
                if label != 'Type':
                    temporaryFileHandle.write(getattr(var, label)+' ')

def find_variable_units_from_file(unitLabel, variablesFromFile, fileHandle):

    variableUnitsFromFile = []

    for variable in variablesFromFile:
	var = fileHandle.variables[variable]
        if variable == 'time':
	     variableUnitsFromFile.append(getattr(var, 'units'))
	elif variable != 'time':
	     variableUnitsFromFile.append(getattr(var, unitLabel))
	
    return variableUnitsFromFile


def find_variables_and_variable_units(variablesFromFile, variableUnitsFromFile):

    variables = []
    variableUnits = []

    for index in range(len(variablesFromFile)):
        if '_' in variablesFromFile[index]:
            position = variablesFromFile[index].find('_')
            if variablesFromFile[index][0:position] not in variables:
                variables.append(str(variablesFromFile[index][0:position]))
		variableUnits.append(str(variableUnitsFromFile[index]))	
    
        elif variablesFromFile[index] != 'time':
            variables.append(str(variablesFromFile[index]))	
	    variableUnits.append(str(variableUnitsFromFile[index]))	

    return variables, variableUnits


def find_variables_and_variable_units_in_metadata(variables, variableUnits):

    variablesInMetaData = []
    variableUnitsInMetaData = []
    for variable in variables:

        if variable == 'tmax' or variable == 'tmin':
	    if 'temperature' not in  variablesInMetaData:
	        variablesInMetaData.append('temperature')
		position = variables.index(variable)
        	variableUnitsInMetaData.append(variableUnits[position])
	else:
	    variablesInMetaData.append(variable)
            position = variables.index(variable)
            variableUnitsInMetaData.append(variableUnits[position])
      
    return variablesInMetaData, variableUnitsInMetaData


def write_variable_units_to_file(temporaryFileHandle, variablesInMetadata, variableUnitsInMetadata):

    temporaryFileHandle.write('\n///////////////////////////////////////////////////////////////////\n// Unit: ')
    for index in range(len(variablesInMetadata)):
        if index != len(variablesInMetadata)-1:
            temporaryFileHandle.write(variablesInMetadata[index]+' = '+ variableUnitsInMetadata[index]+", ")
        else:
	    temporaryFileHandle.write(variablesInMetadata[index]+' = '+ variableUnitsInMetadata[index]+"\n")
    temporaryFileHandle.write('///////////////////////////////////////////////////////////////////\n')


def find_count_of_variables(variables, variablesFromFile):

    count = 0
    countOfVariables = []

    for index in range(len(variables)):
        for variable in variablesFromFile:
	
	    if '_' in variable:
	        position = variable.find('_')
	        variable = variable[0:position]
	
	    if variables[index] == variable:
	        count = count + 1
    
        if(count > 0):
            countOfVariables.append(count)
        count = 0

    return countOfVariables


def write_variables_to_file(temporaryFileHandle, variables, countOfVariables):

    for index in range(len(variables)):
        temporaryFileHandle.write(variables[index]+' '+str(countOfVariables[index])+'\n')


def find_start_and_end_dates(fileHandle):

    for variable in fileHandle.variables:
        if variable == 'time':
            units = str(fileHandle.variables[variable].units)
            startDate = units.rsplit(' ')[2]
            startYear = int(startDate.rsplit('-')[0].strip())
	    startMonth = int(startDate.rsplit('-')[1].strip())
	    startDay = int(startDate.rsplit('-')[2].strip())
        
	    shape = str(fileHandle.variables[variable].shape)
	    numberOfValues = int(shape.rsplit(',')[0].strip('('))
	
	    endDate = str(datetime.date (startYear, startMonth, startDay) + datetime.timedelta (days = numberOfValues-1))
            endYear = int(endDate.rsplit('-')[0].strip())
	    endMonth = int(endDate.rsplit('-')[1].strip())
	    endDay = int(endDate.rsplit('-')[2].strip())

    return startYear, startMonth, startDay, endYear, endMonth, endDay


def write_variable_data_to_file(fileHandle, temporaryFileHandle, date):
    
    startYear = date[0]
    startMonth = date[1]
    startDay = date[2]
    endYear = date[3]
    endMonth = date[4]
    endDay = date[5]    
	
    timestamp = 0

    startDate = datetime.date(startYear, startMonth, startDay)
    endDate = datetime.date(endYear, endMonth, endDay)
	    
    for dt in rrule(DAILY, dtstart=startDate, until=endDate):
    	temporaryFileHandle.write(dt.strftime("%Y %m %d 0 0 0")+" ")
	for variable in fileHandle.variables:
	    if variable != 'time':
		temporaryFileHandle.write(str(fileHandle.variables[variable][timestamp])+" ")
	temporaryFileHandle.write("\n")
	timestamp = timestamp + 1
	
def netcdf_to_data(inputFileName, outputFileName):
   
    variablesFromFile = [] 
    variableUnitsFromFile = []
    
    fileHandle = Dataset(inputFileName, 'r')
    temporaryFileHandle = open(outputFileName, 'w')

    for variable in fileHandle.variables:
        variablesFromFile.append(variable)
       
    attributeNames = find_attribute_names(fileHandle)
    attributeValues = find_and_write_attribute_values_to_file(attributeNames, fileHandle, temporaryFileHandle, variablesFromFile)

    unitLabel = find_unit_label(fileHandle)
    variableUnitsFromFile = find_variable_units_from_file(unitLabel, variablesFromFile, fileHandle)
    
    var = find_variables_and_variable_units(variablesFromFile, variableUnitsFromFile)
    variables = var[0]
    variableUnits = var[1]

    varInMetadata = find_variables_and_variable_units_in_metadata(variables, variableUnits)
    variablesInMetadata = varInMetadata[0] 
    variableUnitsInMetadata = varInMetadata[1]

    write_variable_units_to_file(temporaryFileHandle, variablesInMetadata, variableUnitsInMetadata)
    countOfVariables = find_count_of_variables(variables, variablesFromFile)
    write_variables_to_file(temporaryFileHandle, variables, countOfVariables)

    temporaryFileHandle.write('####################################################################\n')

    date = find_start_and_end_dates(fileHandle)
    write_variable_data_to_file(fileHandle, temporaryFileHandle, date)
    
if __name__ == "__main__":
  
    netcdf_to_data(sys.argv[1], 'LC.data')
    
