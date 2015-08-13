#! /usr/local/bin/python
"""
Usage:
    get_dflow_inputs {virtual watershed model_run_uuid} {output_path}

Example:
    get_dflow_inputs 663acb18-ece7-4061-ad54-9a2a10b80221 vw_nvals.asc
"""
import sys

from wcwave_adaptors.dflow_casimir import get_vw_nvalues


uuid = sys.argv[1]

asc_nvals_path = sys.argv[2]

asc_nvals = get_vw_nvalues(uuid)

asc_nvals.write(asc_nvals_path)
