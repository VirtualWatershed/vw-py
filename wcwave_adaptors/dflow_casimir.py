"""
Utilities for interacting with dflow and casimir models via the virtual
watershed.
"""
import os

from numpy import fromstring, reshape
from pandas import Series, read_excel
from uuid import uuid4

from .watershed import default_vw_client

def vegcode_to_nvalue(asc_path, lookup_path):
    """
    Creat an ESRIAsc representation of an ESRI .asc file that contains roughness
    values substituted for vegetation codes. The translation is found in the
    Excel file found at lookup_path.

    Arguments:
        asc_path (str): path to ESRI .asc file with vegetation codes
        lookup_path (str): path to Excel file with vegetation codes mapped
            to Manning's roughness n-values. The Excel file must have four
            columns with headers
                veg_code	veg_id	full_name	n_value
            on the first sheet.

    Raises:
        (ValueError) if there is a vegetation code in the .asc that is not
            found in the lookup table

    Returns:
        (ESRIAsc) instance representing the ESRI .asc required as input to DFLOW
    """
    asc = ESRIAsc(asc_path)

    lookup_df = read_excel(lookup_path)
    lookup_dict = dict(zip(lookup_df.veg_code.values,
                           lookup_df.n_value.values))

    asc.data.replace(lookup_dict, inplace=True)

    return asc


def get_vw_nvalues(model_run_uuid):
    """
    Given a model run uuid that contains the lookup table and ESRI .asc with
    vegetation codes, return an ascii file that has the n-values properly
    assigned
    """
    vwc = default_vw_client()

    records = vwc.dataset_search(model_run_uuid=model_run_uuid).records

    downloads = [r['downloads'][0] for r in records]

    asc_url = filter(lambda d: d.keys().pop() == 'ascii',
                     downloads).pop()['ascii']

    xlsx_url = filter(lambda d: d.keys().pop() == 'xlsx',
                      downloads).pop()['xlsx']

    asc_path = 'tmp_' + str(uuid4()) + '.asc'
    vwc.download(asc_url, asc_path)

    xlsx_path = 'tmp_' + str(uuid4()) + '.xlsx'
    vwc.download(xlsx_url, xlsx_path)

    asc_nvals = vegcode_to_nvalue(asc_path, xlsx_path)

    os.remove(asc_path)
    os.remove(xlsx_path)

    return asc_nvals


class ESRIAsc:

    def __init__(self, file_path=None):

        self.ncols = None
        self.nrows = None
        self.xllcorner = None
        self.yllcorner = None
        self.cellsize = 1
        self.NODATA_value = 1
        self.data = None

        if file_path:

            getnextval = lambda f: f.readline().strip().split()[1]

            f = open(file_path, 'r')

            self.ncols = int(getnextval(f))
            self.nrows = int(getnextval(f))
            self.xllcorner = getnextval(f)
            self.yllcorner = getnextval(f)
            self.cellsize = getnextval(f)
            self.NODATA_value = getnextval(f)

            # should not be necessary for well-formed ESRI files, but
            # seems to be for CASiMiR
            data_str = ' '.join([l.strip() for l in f.readlines()])

            self.data = Series(fromstring(data_str, dtype=float, sep=' '))

            colrow_prod = self.nrows*self.ncols
            assert len(self.data) == colrow_prod, \
                "length of .asc data does not equal product of ncols * nrows" \
                "\nncols: {}, nrows: {}, ncols*nrows: {} len(data): {}".format(
                    self.ncols, self.nrows, colrow_prod, len(self.data))

    def as_matrix(self):
        "Convenience method to give 2D numpy.ndarray representation"
        return reshape(self.data, (self.nrows, self.ncols))

    def write(self, write_path):
        with open(write_path, 'w+') as f:
            f.write("ncols {}\n".format(self.ncols))
            f.write("nrows {}\n".format(self.nrows))
            f.write("xllcorner {}\n".format(self.xllcorner))
            f.write("yllcorner {}\n".format(self.yllcorner))
            f.write("cellsize {}\n".format(self.cellsize))
            f.write("NODATA_value {}\n".format(self.NODATA_value))
            f.write(' '.join(self.data.map(lambda val: str(val)).values)
                    + '\n')

    def __eq__(self, other):

        if isinstance(other, ESRIAsc):
            ret = self.ncols == other.ncols
            ret = self.nrows == other.nrows and ret
            ret = self.xllcorner == other.xllcorner and ret
            ret = self.yllcorner == other.yllcorner and ret
            ret = self.cellsize == other.cellsize and ret
            ret = self.NODATA_value == other.NODATA_value and ret
            ret = all(self.data == other.data) and ret

            return ret

        return NotImplemented
