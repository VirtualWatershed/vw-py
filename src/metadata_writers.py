""" We have three metadata hierarchy levels. At the top is the "Project"
    hierarchy. This includes a description of the goal of the project. For 
    example, if we are successively increasing the average temperature 
    throughout the year by 1 degree on average, we need to describe that. 
    
    Within a project run, there are individual model runs. Some metadata here
    might describe what the distinguishing characteristics are of the run, 
    e.g. temperature was manually increased compared to the raw, or reference,
    or 'real' run as opposed to simulated. So that might be a flag, too, 
    whether or not a model run was a simulation.

    At the most granular level we have data sets. We've agreed that this means
    a single file and its associated metadata. 
"""

class Metadata:
    """ No constructor here. Each subclass will get its own specialized 
        constructor.
    """
    @private
    def allFieldsPopulated(self):
        """ Check if all the required fields are populated"""
        populated = True
        return populated

    def writeFinalMetadata(self, writeFile):
        """ First checks if all fields are populated. If so, write the output
            to writeFile. If not, throw error.
        """
        if self.allFieldsPopulated():
            # write files here
            print("Metadata here, get yer metadata!")

        return None


class DatasetMetadata(Metadata):
    
    def __init__(self, parentModelRunMetadata):
        assert type(parentModelRunMetadata) is ModelRunMetadata, \
            "DatasetMetadata constructor argument must be of type " + \
            "ModelRunMetadata"

     
class ModelRunMetadata(Metadata):
    
    def __init__(self, identifier):
        self.identifier = identifier
        


