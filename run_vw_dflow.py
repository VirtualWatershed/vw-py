#! /usr/local/bin/python
"""
Example of how a DFLOW model run meant to interface with CASiMiR will work.
This assumes that Sarah has already uploaded the Excel vegetation
code-to-roughness table and a .asc vegetation map for that time step and it's
in the Virtual Watershed with a uuid of {uuid}.

This script gets those two files, creates a .asc of roughness values subbed for
vegetation codes, and saves it to a temporary location. Next,

Usage:
     export PATH=/{path}/{to}/{wcwave_adaptors repository}:$PATH
     run_vw_dflow.py {virtual watershed model_run_uuid}
"""
