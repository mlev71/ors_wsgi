#!/usr/bin/env python3 
from flask import Flask, render_template, request, Response 
import json
import requests
import re
import os
import sys
from neo4j.v1 import GraphDatabase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from components.helper_functions import *
from components.identifier_objects import *
from components.neo_helpers import *


app = Flask(__name__, template_folder='templates')

# load environment variables 
NEO_USER = os.environ.get('NEO_USER')
NEO_PASSWORD = os.environ.get('NEO_PASSWORD')
NEO_URL = "".join(["bolt://", os.environ.get('NEO_URL', 'none_found'), ":7687"])


# configure flask application settings
app.config['Debug'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = False
app.config['Testing'] = False

# global constants
JSON_MIMETYPES = set(['application/json', 'application/ld+json', 'application/json+ld'])


@app.route('/home', methods = ['GET'])
def Home():
    """
        Display a homepage for the Broker
    """
    return "HOMEPAGE for the Broker"



@app.route('/mint', methods = ['PUT'])
def Mint(): 
    """ Mint a DOI or an Ark from this endpoint
    """

    payload = json.loads(request.data)

    # Check Authentication
    if not request.authorization.password or not request.authorization.username:
        return Response( status = 401,
                response = '{"error": {"description": "Missing Login information, cannot mint/updates IDs without authentication"}]}',
                mimetype = 'application/ld+json') 

    basicAuth = requests.auth.HTTPBasicAuth(request.authorization.username, request.authorization.password)


    # TODO if @id is missing assign to namespace 


    # unwrap metadata and options from payload

    if payload.get("metadata") == None:
            data = payload
            options = {
                "_target": "https://ors.datacite.org/"+data.get('@id'),
                "_status": "reserved"
                } 
    else:
            data = payload.get("metadata")
            if payload.get("options") == None:
                options = {
                    "_target": "https://ors.datacite.org/"+data.get('@id'),
                    "_status": "reserved"
                } 
            else:
                options = payload.get("options")


    if re.match('ark:/', data.get('@id')):
        try:
            obj = Ark(data, options)
            response = obj.postAPI(auth = basicAuth)
            obj.postNeo()
            return Response(
                    status = response.status_code,
                    response = str(response.content)
                    )
        except AssertionError:
            req = Ark.required_keys
            missing = ", ".join(req.difference(req.intersection(data.keys())) )
            missing_message = {
                            "message": "Missing Required Keys",
                            "GUID": data.get('@id', None),
                            "missingKeys": " ".join(["[", missing, "]"]) 
                            }
            return Response( 
                    status =400,
                    response = json.dumps(missing_message)
                    )
    
    if re.match('doi:', data.get('@id')):
        obj = Doi(data, options)

    else:
        return Response(status = 400,
                response = json.dumps({"target": data.get('@id'), "message": "Unsupported Guid"}), 
                mimetype = "application/json")

    response = obj.postAPI(auth = basicAuth)
    
    # TODO return sucess or failure from neo function
    obj.postNeo()

    # need to format into JSON
        # Cache: {}
        # apiResponse: {}
    return Response(status = response.status_code,
            message = str(response.content))

@app.route('/dc/put', methods = ['PUT'])
def MintDC():
    payload = json.loads(request.data)
    
    options = {
            "_target": "https://ors.datacite.org/"+payload.get('@id'),
            "_status": "reserved"
            } 

    obj = DataCatalog(payload, options)

    if not request.authorization.password or not request.authorization.username:
        return Response( 
                status = 401,
                response = '{"message": "Missing Login information, cannot mint/updates IDs without authentication"}',
                mimetype = 'application/ld+json') 

    basicAuth = requests.auth.HTTPBasicAuth(request.authorization.username, request.authorization.password)

    api_response = obj.postAPI(auth = basicAuth)
    neo_response = obj.postNeo()

    return Response(
            status = api_response.status_code,
            response = str(api_response.content)
            )

@app.route('/dc/delete/<path:GUID>', methods=['DELETE'])
def DeleteDC(GUID):
    if not request.authorization.password or not request.authorization.username:
        return Response( 
                status = 401,
                response = '{"message": "Missing Login information, cannot mint/updates IDs without authentication"}',
                mimetype = 'application/ld+json') 
    basicAuth = requests.auth.HTTPBasicAuth(request.authorization.username, request.authorization.password)


    endpoint = "https://ezid.cdlib.org/id/"+GUID

    api_response = requests.delete(endpoint, auth=basicAuth)

    removed_data = deleteCache(GUID)
    response_message = {
            "cache": {"metadata": removed_data, "message": "Removed from cache"},
            "api": {"status_code": api_response.status_code, "message": str(api_response.content)}
                }

    return Response(
            status=201,
            response = json.dumps(response_message)
            )


@app.route('/dc/get/<path:GUID>', methods = ['GET'])
def GetDC(GUID):
    ''' Retrieves object from cache with query to neo
    '''

    endpoint = "https://ezid.cdlib.org/id/"+GUID
    api_response = requests.get(
            url = endpoint
            )
    payload = str(api_response.content.decode('utf-8'))

    final_payload = recursiveUnpack(removeProfileFormat(ingestAnvl(payload)))

    return Response(
            response = json.dumps(final_payload)
            )



@app.route('/cache/import/<path:GUID>', methods =['GET'])
def importCache(GUID):
    '''
    '''

    pass

@app.route('/cache/<path:GUID>', methods = ['GET'])
def ManageCache(GUID):
   return Response(
           status_code = 200,
           message= json.dumps(getCache(GUID)),
           mimetype="application/json"
           )
           


@app.route('/<path:ID>', methods = ['GET', 'DELETE'])
def ManageGUID(ID):
    """ Common Path for GUID Broker
    """

    if request.method == 'GET':
        # fetch the metadata from external service 
        if re.match('doi:', ID): 
            # ez api endpoint
            # endpoint = "https://ez.datacite.org"+ID
            # perm endpoint

            endpoint = "https://api.datacie.org/works"+ID
            template = 'Ark.html'
        if re.match('ark:/', ID):
            endpoint = "https://ezid.cdlib.org/id/" + ID
            template = 'Doi.html'

        response = requests.get(endpoint)         

        data = formatJson(
                recursiveUnpack(
                    removeProfileFormat(str(response.content.decode('utf-8')) )
                    )
                )


        if request.headers['Accept'] in JSON_MIMETYPES:
            return Response( status = 200,
                mimetype = 'application/ld+json; profile="http://schema.org"',  
                response = data )

        # if text/html render a landing page
        if request.headers['Accept'] == 'text/html':
            return render_template(template, data = data)

        else:
            return render_template(template, data = data)

    if request.method == 'DELETE':

        if not request.authorization.password or not request.authorization.username:
            return Response( 
                    status = 401,
                    response = '{"message": "Missing Login information, cannot mint/updates IDs without authentication"}',
                    mimetype = 'application/ld+json') 

        basicAuth = requests.auth.HTTPBasicAuth(request.authorization.username, request.authorization.password)

 
        # delete from EZID service
        response = requests.delete(target, auth=basicAuth)

        # TODO determine sucsess from deleteCache
        deleteCache(Id)

        # forward the API response
        return Response( status = 200,
                response = json.dumps({"target": str(target), "response": str(response.content) }) ,
                mimetype = "application/json")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)

