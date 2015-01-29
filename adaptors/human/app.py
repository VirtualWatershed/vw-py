"""
file: adaptors/human/app.py

So far only search is exposed. Done via static/search.js.
"""
from flask import Flask, request, render_template
from adaptors.watershed import default_vw_client, QueryResult

app = Flask(__name__)

vw_client = default_vw_client()

#### INDEX ####
@app.route('/')
def hello():
    "Splash page"
    # search URL is like https://129.24.196.28
    watershed_ip = vw_client.searchUrl.split('/')[2]

    return "<p><a href='/search'>SEARCH</a></p>" +\
           "<p>Currently using virtual watershed hosted at " \
           + watershed_ip + "</p>"


#### SEARCH ####
# TODO include this in the search or base template
SEARCH_JS = \
    '<script src="//ajax.googleapis.com/ajax/libs/jquery/1.2.6/jquery.min.js">'\
    + '</script><script src="static/search.js"></script>'

# TODO include this in the search template
SEARCH_FORM = \
    '<form align=center>Model run name:<input type="text" name="model_run_name" ' +\
    'id="model_run_name" placeholder="insert name here!">' +\
    '<button id="search">Search!</button></form> ' + SEARCH_JS +\
    '<p align=center><a href="/">HOME</a></p>'

@app.route('/search', methods=['GET'])
def search():
    "Search the virtual watershed and display results"

    # If there are no arguments passed, provide a form for searching
    if len(request.args.keys()) == 0:
        return SEARCH_FORM

    # if the user has passed Virtual Watershed arguments, use them, ret results
    else:
        # don't do anything to res, just pass it along
        res = vw_client.search(**(request.args.to_dict()))

        return "<h1 align=center>Search again:</h1>" + SEARCH_FORM + \
            make_model_run_panels(res)


def make_model_run_panels(search_results):
    """
    Create model run panels, rectangles on the search/home page that display
    summary information about the data that the VW has for a particular model
    run.

    Returns: (str) HTML string of the model run panel
    """
    # inform user if no matching records are found
    if search_results.total == 0:
        return "<h3 align=center>No records found!<h3>"

    else:
        # make a panel of each metadata record
        panels = [_make_panel(rec) for rec in search_results.records]
        # this enforces unique model_run_uuids
        panels = {p['model_run_uuid']: p for p in panels}.values()

        # pass the list of parsed records to the template to generate results page
        return render_template('search.html', panels=panels)


def _make_panel(search_record):
    """
    Extract fields we currently support from a single JSON metadata file and
    prepare them in dict form to render search.html.

    Returns: (dict) that will be an element of the list of panel_data to be
        displayed as search results
    """
    lonmin, latmin, lonmax, latmax = \
        (el for el in search_record['spatial']['bbox'])

    centerlat = latmin + 0.5*(latmax - latmin)
    centerlon = lonmin + 0.5*(lonmax - lonmin)

    assert latmin < latmax, "Error, min lat is less than max lat"
    assert latmin < latmax, "Error, min lon is less than max lon"

    cats = search_record['categories'][0]
    state = cats['state']
    modelname = cats['modelname']
    watershed = cats['location']

    model_run_name = search_record['model_run_name']
    model_run_uuid = search_record['model_run_uuid'].replace('-', '')

    panel = {"latmin": latmin, "latmax": latmax,
             "lonmin": lonmin, "lonmax": lonmax,
             "centerlat": centerlat, "centerlon": centerlon, "state": state,
             "watershed": watershed,
             "model_run_name": model_run_name,
             "model_run_uuid": model_run_uuid,
             "model": modelname}

    return panel


if __name__ == "__main__":
    # app.run()
    app.run(debug=True)
