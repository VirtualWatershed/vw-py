from isnobal import isnobal
import netCDF4
def run_isnobal(input_path=None, output_path=None, event_emitter=None, **kwargs):
    input_nc = netCDF4.Dataset(input_path)
    nc_out = isnobal(input_nc, output_path, event_emitter=event_emitter, **kwargs)
    nc_out.close()
