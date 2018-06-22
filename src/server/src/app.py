#!/usr/bin/env python3 
from flask import Flask, render_template, request, Response, session, redirect, url_for


import globus_sdk
import json
import requests
import re
import os
import sys
from neo4j.v1 import GraphDatabase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# change with __init__.py to 
# from components import *
from app.components.cel import *
from app.components.globus_auth import *
from app.components.helper_functions import *
from app.components.identifier_objects import *
from app.components.neo_helpers import *

app = Flask('ors', template_folder='app/templates')

app.config['Debug'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = False
app.config['Testing'] = False



#####################################
#            General                #
#####################################

@app.route('/home', methods = ['GET'])
def home():
    """ Display a homepage for the Broker

        Describe How many arks, doi's, and data-catalogs are registered
    """
   # describe neo4j cache
        # arks
        # dois
        # data catalogs
  
  # links for datasets

    return "Homepage for the Broker" 


@app.route('/login')
def login():
    """ Run Oauth2 flow with globus auth

    No sessions 
    
    """ 
    client = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

    client.oauth2_start_flow(redirect_uri= url_for('login', _external=True), refresh_tokens=True)

    if 'code' not in request.args:

        # request to authenticate as a rest client
        authorize_url = client.oauth2_get_authorize_url() 
        return redirect(authorize_url)

    else:
        auth_code = request.args.get('code')
        tokens = client.oauth2_exchange_code_for_tokens(auth_code)

       
        access_token = tokens.by_resource_server.get('auth.globus.org', {}).get('access_token')

        # display access code tokens
        return access_token

@app.route('/logout')
def logout():
    client = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

    access_token = request.args.get('access_token')

    if access_token is not None:
        client.oauth2_revoke_token(access_token)

    else:
        return "Please provide your token to logout"

    redirect_uri = url_for('home', _external=True)

    # call globus to invalidate tokens
    globus_logout_url = (
        'https://auth.globus.org/v2/web/logout' +
        '?client={}'.format(CLIENT_ID) +
        '&redirect_uri={}'.format(redirect_uri) +
        '&redirect_name=Globus Example App')

    return redirect(globus_logout_url)


##########################################################
#                        ARK                             #
##########################################################

@app.route('/ark/put', methods = ['PUT'])
@auth_required
def MintArk():
    payload, options = parse_payload(json.loads(request.data), request.args)

    try:
        obj = Ark(data=payload, options=options)   
    
    except MissingKeys as err:
        return err.output()


    obj.postNeo()

    api_async = obj.postAPI()
    response_dict = api_async.get()

    response_message = {
            "api": {"status": response_dict.get('status_code'), "messsage": response_dict.get('content')}
            }

    return Response(
            status = response_dict.get('status_code'),
            response = json.dumps(response_message)
            )


@app.route('/ark/delete/<path:GUID>', methods= ['DELETE'])
@auth_required
def DeleteArk(GUID):
    ark = Ark(guid=GUID)

    api_async = ark.deleteAPI() 
    deleteNeoByGuid.delay(GUID)

    response_dict = api_async.get()

    response_message = {
            "api": {"status_code": response_dict.get('status_code'), "message": response_dict.get('content')}
            }

    return Response(
            status= response_dict.get('status_code'),
            response = json.dumps(response_message)
            )


@app.route('/ark/get/<path:GUID>', methods = ['GET'])
@auth_required
def GetArk(GUID):
    endpoint = "https://ezid.cdlib.org/id/"+GUID
    api_response = requests.get(url = endpoint)

    if api_response.status_code == 404:
        return Response(
                status = 404, 
                response = json.dumps({"guid": GUID, "message": "No record of Identifier"})
                )

    payload = str(api_response.content.decode('utf-8'))

    unpacked_payload = unroll(removeProfileFormat(ingestAnvl(payload)))
    final_payload = formatJson(unpacked_payload)
    
    return Response(response = json.dumps(final_payload))


@app.route('/ark/landing/<path:GUID>', methods = ['GET'])
def GetArkLandingPage(GUID):
    endpoint = "https://ezid.cdlib.org/id/"+GUID
    api_response = requests.get(
            url = endpoint
            )

    if api_response.status_code == 404:
        return Response(
                status = 404,
                response = json.dumps({"guid":GUID, "message": "No record of Identifier"})
                )

    payload = str(api_response.content.decode('utf-8'))
    template_data = formatJson(unroll(removeProfileFormat(ingestAnvl(payload)))) 
    return render_template('Ark.html', data = template_data)


@app.route('/ark/import/<path:GUID>', methods = ['GET'])
@auth_required
def ImportArk(GUID):
    api_response = requests.get(url = "https://ezid.cdlib.org/id/"+GUID)
    # format the payload 
    payload = str(api_response.content.decode('utf-8'))
    final_payload = formatJson(unroll(removeProfileFormat(ingestAnvl(payload))))

    # read into DC interface
    obj = Ark(data=final_payload)  
    post = obj.postNeo()

    response_message = {"cache": {"imported": post} }

    return Response(
            status = 201,
            response = json.dumps(response_message),
            mimetype= 'application/json'
            )


###########################################################
# Doi Interfaces
###########################################
@app.route('/doi/put', methods = ['PUT'])
@auth_required
def MintDoi():
    ''' Posting to Neo 
    '''
    payload, options = parse_payload(json.loads(request.data), request.args)

    try:
        obj = Doi(data=payload, options=options)

    except MissingKeys as err:
        return err.output()

    obj.postNeo()

    response_dict = obj.postAPI()


    #response_dict = api_async_response.get()
    #api_async_response = obj.postAPI()

    response_message = {
            "api": {"status": response_dict.get('status_code'), "messsage": response_dict.get('content')}
            }

    return Response(
            status = response_dict.get('status_code'),
            response = json.dumps(response_message)
            )


@app.route('/doi/delete/<path:GUID>', methods= ['DELETE'])
@auth_required
def DeleteDoi(GUID):
    doi = Doi(guid=GUID)
    
    #api_async_response = doi.deleteAPI()
    #response_dict = api_async_response.get()

    neo_task = deleteNeoByGuid.delay(GUID)
    response_dict = doi.deleteAPI()

    response_message = {
            "api": {"status_code": response_dict.get('status_code'), "message": response_dict.get('content')}
                }

    return Response(
            status=201,
            response = json.dumps(response_message)
            )


@app.route('/doi/get/<path:GUID>', methods = ['GET'])
@auth_required
def GetDoi(GUID):
    doi = Doi(guid=GUID)
    return Response( 
            response = json.dumps(doi.getAPI())
            )


@app.route('/doi/landing/<path:GUID>', methods = ['GET'])
def GetDoiLandingPage(GUID):
    doi = Doi(guid=GUID)
    template_data = doi.getAPI()
    return render_template('Doi.html', data=template_data)


@app.route('/doi/import/<path:GUID>', methods = ['GET'])
@auth_required
def ImportDoi(GUID):
    doi = Doi(GUID)
    return doi.importAPI()



if __name__ == '__main__':
    app.run(
            ssl_context=('cert.pem','key.pem'), 
            #ssl_context='adhoc',
            host="0.0.0.0", 
            port=8080
            )

