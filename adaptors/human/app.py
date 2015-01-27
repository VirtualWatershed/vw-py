"""
file: adaptors/human/app.py

So far only search is exposed. Done via static/search.js.
"""
from flask import Flask, request
from adaptors.watershed import default_vw_client

app = Flask(__name__)

vw_client = default_vw_client("../../default.conf")

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
SEARCH_JS = \
    '<script src="//ajax.googleapis.com/ajax/libs/jquery/1.2.6/jquery.min.js">'\
    + '</script><script src="static/search.js"></script>'

SEARCH_FORM = \
    '<form>Model run name:<input type="text" name="model_run_name" ' +\
    'id="model_run_name" placeholder="insert name here!"></form> ' +\
    '<button id="search">Search!</button>' + SEARCH_JS +\
    '<p><a href="/">HOME</a></p>'

@app.route('/search', methods=['GET'])
def search():
    "Search the virtual watershed and display results"

    # If there are no arguments passed, provide a form for searching
    if len(request.args.keys()) == 0:
        return SEARCH_FORM

    # if the user has passed Virtual Watershed arguments, use them, ret results
    else:
        res = vw_client.search(**(request.args.to_dict()))
        return str(res.records) + "<h1>Search again:</h1>" + SEARCH_FORM

if __name__ == "__main__":
    app.run()
