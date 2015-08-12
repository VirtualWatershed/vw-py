"""
Utilities for interacting with dflow and casimir models via the virtual
watershed.
"""

from numpy import fromstring, reshape, int16


class Ascii:

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

            data_str = ' '.join([l.strip() for l in f.readlines()])

            self.data = fromstring(data_str, dtype=int16, sep=' ')

    def as_matrix(self):
        return reshape(self.data, (self.nrows, self.ncols))
