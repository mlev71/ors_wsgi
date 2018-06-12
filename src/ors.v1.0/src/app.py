#!/usr/bin/env python3 
from flask import Flask, render_template, request, Response 
import json
import requests
import re
import os
import sys
from neo4j.v1 import GraphDatabase

#sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.components.payload_handler import *

app = Flask(__name__, template_folder='templates')

# load environment variables 
NEO_USER = os.environ['NEO_USER']
NEO_PASSWORD = os.environ['NEO_PASSWORD']
NEO_URL = "".join(["bolt://", os.environ['NEO_URL'], ":7687"])


# configure flask application settings
app.config['Debug'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = False
app.config['Testing'] = False

# global constants
JSON_MIMETYPES = set(['application/json', 'application/ld+json', 'application/json+ld'])


@app.route('/', methods = ['GET'])
def Home():
    """
        Display a homepage for the Broker
    """
    return "HOMEPAGE for the Broker"

@app.route('/mint', methods = ['PUT'])
def Mint(): 
    """ Mint a DOI or an Ark from this endpoint
    """

    got_json = json.loads(request.data)

    # Check Authentication
    if not request.authorization.password or not request.authorization.username:
        return Response( status = 401,
                response = '{"error": {"description": "Missing Login information, cannot mint/updates IDs without authentication"}]}',
                mimetype = 'application/ld+json') 

    basicAuth = requests.auth.HTTPBasicAuth(request.authorization.username, request.authorization.password)


    # Connect the Driver to the Neo Service 
    try:
        NEO_DRIVER = GraphDatabase.driver(NEO_URL,auth = (NEO_USER, NEO_PASSWORD) )
    except ServiceUnavailable:
        return Response( status = 500,
                response = json.dumps({"Location": NEO_URL, "message": "Neo Database Unavailable, request was terminated"}),
                mimetype = 'application/json')


    try:
        anvlObj = PayloadFactory(got_json, "JSON") #, NEO_DRIVER)
    except (NotCoreObject, InvalidParent) as err:
        return err.output()


    ID = anvlObj.GUID

    try:
        target = detTarget(ID)
    except UnsupportedGuid as err:
        return err.output()

    response = requests.put(url=target, 
                    auth = basicAuth, 
                    headers = {'Content-Type': 'text/plain; charset=UTF-8'}, 
                    data = anvlObj.returnANVL() )

    # need to change 
    return Response(status = response.status_code,
            response = json.dumps({"target": target, "response": response.content.decode("utf-8")}), 
            mimetype = "application/json")


@app.route('/<path:ID>', methods = ['GET', 'DELETE'])
def GetDelete(ID):
    """ Common Path for GUID Broker
    """

    try:
        target = detTarget(ID)
    except UnsupportedGuid as err:
        return err.output()

    try:
        NEO_DRIVER = GraphDatabase.driver(NEO_URL, auth = (NEO_USER, NEO_PASSWORD)  )
    except ServiceUnavailable:
        return Response( status = 500,
               response = json.dumps({"Location": NEO_URL, "message": "Neo Database Unavailable, request was terminated"}),
                mimetype = 'application/json')



    if request.method == 'GET':
        # fetch the metadata
        response = requests.get(target)  
       
        #return Response(status = response.status_code, response = response.content)

        if response.status_code in [400, 404] or response.content == b'error: bad request - no such identifier':
            return Response(status = 404,
                    response = json.dumps({"Guid": ID, "message": "No record of this Identifier was found"}),
                    mimetype = 'application/ld+json')
        

        try:
            jsonObj = PayloadFactory(response.content, "ANVL") #, NEO_DRIVER)
        except (NotCoreObject, InvalidParent) as err:
            return err.output()

        if request.headers['Accept'] in JSON_MIMETYPES:
            return Response( status = 200,
                mimetype = 'application/ld+json; profile="http://schema.org"',  
                response = jsonObj.returnJSON() )

        # if text/html render a landing page
        if request.headers['Accept'] == 'text/html':
            return jsonObj.RenderLandingPage()

        else:
            return jsonObj.RenderLandingPage()

    if request.method == 'DELETE':

        if not request.authorization.password or not request.authorization.username:
            return Response( 
                    status = 401,
                    response = '{"message": "Missing Login information, cannot mint/updates IDs without authentication"}',
                    mimetype = 'application/ld+json') 
        basicAuth = requests.auth.HTTPBasicAuth(request.authorization.username, request.authorization.password)


       
        # delete from EZID service
        response = requests.delete(target, auth=basicAuth)

        # delete the object from neo 
        #deleteGUID(ID, NEO_DRIVER)

        # forward the API response
        return Response( status = 200,
                response = json.dumps({"target": str(target), "response": str(response.content) }) ,
                mimetype = "application/json")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port="8080")

