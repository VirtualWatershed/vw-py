#data to netcdf converter
#originally from Lisa Palathingal at https://github.com/lisapalathingal/PRMS_Adaptor
#modified for use in this coding structure
import netCDF4
import sys

def find_number_of_days(fileHandle):

    """

    Returns the total number of lines of data in the file. The 
    data section starts from the line after the line with # sign. 
    Initially, the numberOfDays variable is assigned the value 
    -1. Once we find the # sign, numberOfDays keeps on incrementing 
    till the end of the file.  
    
    """

    numberOfDays = -1
    found = False
    lines = fileHandle.readlines()

    for line in lines:
        if found or "#" in line:
            numberOfDays += 1
            found = True

    return numberOfDays
    
def find_first_date(fileHandle):

    """

    Returns the date specified in the first row of the data section 
    in the file. This data is used to mention in the units attribute
    of the time variable. The first 6 columns in the data rows represent 
    the date in the order of year, month, day, hour, minute, and second 
    respectively. The function hence extracts and returns the values in 
    the first 6 columns of the first row.
    
    """
   
    for line in fileHandle:
        if "#" in line:
            firstLine = fileHandle.next().strip().split()[:6]

    return firstLine

def find_variables(fileHandle):

    """

    Returns the names and lengths of the variables in the file. Two lists, 
    variableNames and variableLengths are created to append the names and 
    lengths respectively. 
    
    """
    
    variableNames = []
    variableLengths = []  
    
    for line in fileHandle:
        if "///" in line:
            firstLine = fileHandle.next().strip()
            if not "//" in firstLine:
		insert_variables_to_list(variableNames, variableLengths, firstLine)
		nextLine = fileHandle.next().strip()
		while '#' not in nextLine:
		    insert_variables_to_list(variableNames, variableLengths, nextLine)
		    nextLine = fileHandle.next().strip()

    return variableNames, variableLengths

def insert_variables_to_list(variableNames, variableLengths, line):

    """
     
    Appends the variable name and length into lists.
    
    """

    variables = line.split()
    variableNames.append(variables[0])
    variableLengths.append(int(variables[1]))

def find_units(fileHandle):

    """

    Returns the names and units of the variables in the file. Two 
    lists, variableNames and variableUnits are created to append 
    the names and units respectively. variableNames are stored 
    because the term 'temperature' is used for the variables tmax 
    and tmin. 
    
    """

    variableNames = []
    variableUnits = [] 

    for line in fileHandle:
        if '///' in line:
            firstLine = fileHandle.next().strip()
            nextLine = fileHandle.next().strip()
            if '///' in nextLine:
	        variables = firstLine.rsplit(':')[1].strip().rsplit(',')
	        for variable in variables:
		    variableNames.append(variable.rsplit('=')[0].strip())
		    variableUnits.append(variable.rsplit('=')[1].strip())

    return variableNames, variableUnits

def find_metadata(fileHandle, totalNumberOfVariables):
    
    """
 
    Returns the metadata of the variables in the file. headerValues 
    include details such as ID, Type, Latitude, Longitude, and 
    Elevation of the stations from where the variables are measured. 
    The total number of lines of metadata specified in the file after 
    the headerline will be equal to the totalNumberOfVariables.
    
    """

    dataValues = []

    for line in fileHandle:
        if '///' in line:
            fileHandle.next().strip()
            headerValues = fileHandle.next().rsplit('//')[1].strip().split()
            
	    for i in range(totalNumberOfVariables):
                data = fileHandle.next().rsplit('//')[1].strip().split()[:len(headerValues)]    
		dataValues.append(data)	       
	    break

    return headerValues, dataValues

def find_column_values(fileHandle, numberOfDays, position):

    """
    
    Returns the values of variables in the file. 

    Args:
        numberOfDays (int): is the total number of values for the variable
	position (int): is the column position from where the values can be 
        retrieved
    
    """

    values = []

    for line in fileHandle:
        if '#' in line:
	    for j in range(numberOfDays):
	        valuesInLine = fileHandle.next().strip().split()[6:]
                values.append(valuesInLine[position])
    
    return values

def find_tmax_tmin_units(index, var, variableNames, varNames, variableUnits):

    """
    
    Adds the unit attribute for the variables. If tmax or tmin variable
    is found in the variableNames list, they will be given the unit of 
    'temperature' variable in the varNames list from the variableUnits list.

    Args:
        index (int): is the index of the list
	variableNames: list of variable names
	varNames: list of variable names
	variableUnits: list of variable units
    
    """

    if variableNames[index] == 'tmax':
        position = varNames.index('temperature')
	var.layer_units = variableUnits[position]
    elif variableNames[index] == 'tmin':
	position = varNames.index('temperature')
	var.layer_units = variableUnits[position]
    elif variableNames[index] == 'precip' or variableNames[index] == 'runoff':
	var.layer_units = variableUnits[index]


def get_metadata(variableName):

    fileHandle = open('../dataVariableDetails.txt', 'r')
    for line in fileHandle:
        if variableName in line:
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
		
	    break;

    return variableName, variableDescription, variableUnit


def add_metadata(var, dataValues, position, headerValues, variableName, variableDescription, variableUnit):
 
    """
    
    Adds the metadata of the variables. 

    Args:
        dataValues: list containing metadata of all the variables
	position (int): is the position in the list
	headerValues: list containing header values (ID, Type, Latitude, Longitude, Elevation)
    
    """
    var.ID = dataValues[position][headerValues.index('ID')]
    var.layer_desc = variableDescription
    var.Latitude = dataValues[position][headerValues.index('Latitude')]
    var.Longitude = dataValues[position][headerValues.index('Longitude')]
    var.Elevation = dataValues[position][headerValues.index('Elevation')]

    if variableName != 'precip' and variableName != 'runoff':
        var.layer_units = variableUnit
           
def data_to_netcdf(fileInput, outputFileName):
   
    totalNumberOfVariables = 0
    totalNumberofLinesOfData = []
    sumOfVariableLengths = []
    
    # Finding the total number of days
    fileHandle = open(fileInput, 'r')
    numberOfDays = find_number_of_days(fileHandle)
    for day in range(numberOfDays):
	totalNumberofLinesOfData.append(day)

    # Finding the first date
    fileHandle = open(fileInput, 'r')
    firstDate = find_first_date(fileHandle)
    year = firstDate[0]
    month = firstDate[1]
    day = firstDate[2]
    hour = firstDate[3]
    minute = firstDate[4]
    second = firstDate[5]

    # Finding the variables and their lengths
    fileHandle = open(fileInput, 'r')
    variables = find_variables(fileHandle)
    variableNames = variables[0]
    variableLengths = variables[1]
    for length in range(len(variableLengths)):
	totalNumberOfVariables = totalNumberOfVariables + variableLengths[length]
	sumOfVariableLengths.append(totalNumberOfVariables)
        
    # Finding the variable units
    fileHandle = open(fileInput, 'r')
    units = find_units(fileHandle)
    varNames = units[0]
    variableUnits = units[1]

    # Finding the metadata
    fileHandle = open(fileInput, 'r')
    metadata = find_metadata(fileHandle, totalNumberOfVariables)
    headerValues = metadata[0]
    dataValues = metadata[1]
 
    # Initialize new dataset
    ncfile = netCDF4.Dataset(outputFileName, mode='w')

    # Initialize dimensions
    time = ncfile.createDimension('time', numberOfDays)  
  
    # Define time variable
    time = ncfile.createVariable('time', 'i4', ('time',))
    time.long_name = 'time'  
    time.units = 'days since '+year+'-'+month+'-'+day+' '+hour+':'+minute+':'+second
    time[:] = totalNumberofLinesOfData

    # Define other variables
    for i in range(len(variableNames)):
        if variableLengths[i] > 1:

	    metadata = get_metadata(variableNames[i])
	    variableName = metadata[0]
	    variableDescription = metadata[1]
	    variableUnit = metadata[2]

	    position = sumOfVariableLengths[i] - variableLengths[i]

	    for j in range(variableLengths[i]):
	        var = ncfile.createVariable(variableNames[i]+'_'+str(j+1), 'f4', ('time',))
	        var.layer_name = variableName+'_'+str(j+1) 
		add_metadata(var, dataValues, position+j, headerValues, variableName, variableDescription, variableUnit)
		find_tmax_tmin_units(i, var, variableNames, varNames, variableUnits)

		fileHandle = open(fileInput, 'r')
    	        columnValues = find_column_values(fileHandle, numberOfDays, position+j)		
		var[:] = columnValues

    	else:
	    metadata = get_metadata(variableNames[i])
	    variableName = metadata[0]
	    variableDescription = metadata[1]
	    variableUnit = metadata[2]
	    	
	    position = sumOfVariableLengths[i] - 1
            var = ncfile.createVariable(variableNames[i], 'f4', ('time',))
	    var.layer_name = variableName  
            add_metadata(var, dataValues, position, headerValues, variableName, variableDescription, variableUnit)
	    find_tmax_tmin_units(i, var, variableNames, varNames, variableUnits)
	    
	    fileHandle = open(fileInput, 'r')
    	    columnValues = find_column_values(fileHandle, numberOfDays, position)
            var[:] = columnValues


    # Global attributes
    ncfile.title = 'Date File'
    ncfile.bands = 1
    ncfile.bands_name = 'nsteps'
    ncfile.bands_desc = 'Variable information for ' + fileInput
     
    # Close the 'ncfile' object
    ncfile.close()
    
if __name__ == "__main__":
       
    data_to_netcdf(sys.argv[1], 'data.nc')
    

    
   

