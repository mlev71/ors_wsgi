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
from app.components.identifier_objects import *

from app.components.neo_helpers import *

app = Flask('ors', 
        template_folder='app/templates',
        static_folder= 'app/static'
        )

app.config['Debug'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = False
app.config['Testing'] = False

# set session secret
app.config['SECRET_KEY']= '3156218277'


#####################################
#            General                #
#####################################

@app.route('/', methods = ['GET'])
def home():
    ''' Render Homepage with Content Information
    '''

    # count the number of downloads, datasets, and 
    neo_driver = GraphDatabase.driver(uri = NEO_URI, auth = (NEO_USER, NEO_PASSWORD) )
    with neo_driver.session() as session:
        with session.begin_transaction() as tx:
            result_count = tx.run(
                    "MATCH (dset:Dataset) "
                    "MATCH (dcat:DataCatalog) " 
                    "MATCH (ddown:Download) " 
                    "RETURN count(dset), count(dcat), count(ddown)"
                    )
    result_dict = result_count.single().data()

    # return all data dictionaries
    
    # list all dataset guids

    return str(result_dict)


@app.route('/browse', methods = ['GET'])
@auth_required
def browse():
    ''' View a visualization of all the GUIDs
    '''

    return render_template('browse.html')


@app.route('/docs', methods = ['GET'])
def docs():
    """ Display a homepage for the Broker

    """
    return render_template('docs.html') 


@app.route('/login')
def login():
    """ Run Oauth2 flow with globus auth 
    """ 
    client = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

    client.oauth2_start_flow(redirect_uri= url_for('login', _external=True), refresh_tokens=True)

    if 'code' not in request.args:
        authorize_url = client.oauth2_get_authorize_url() 
        return redirect(authorize_url)

    else:
        auth_code = request.args.get('code')
        tokens = client.oauth2_exchange_code_for_tokens(auth_code)
        
        access_token = tokens.data.get('access_token')
        refresh_token = tokens.data.get('refresh_token')

        #OIDC token
        oidc_token = tokens.decode_id_token()

        session.update(
                access_token = access_token,
                oidc_token = oidc_token,
                refresh_token = refresh_token
            )

        return 'Access Token: {}'.format(access_token) 


@app.route('/logout')
def logout():
    ''' Clear all provided tokens

    Authorization Headers with bearer tokens
    Query parameter 'code'
    Sessions for web browsers
    '''
    client = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

    token_list = []

    token_list.append(request.args.get('code'))
    token_list.append(request.headers.get('Authorization').replace('Bearer ', ''))
    token_list.append(session.get('access_token'))


    for access_token in token_list:
        if access_token is not None:
            client.oauth2_revoke_token(access_token)

    if all([token==None for token in access_token]):
        return "Please provide a token to logout"

    session.update(
        access_token = None,
        refresh_token = None
            )

    redirect_uri = url_for('home', _external=True)

    # call globus to invalidate tokens
    globus_logout_url = (
        'https://auth.globus.org/v2/web/logout' +
        '?client={}'.format(CLIENT_ID) +
        '&redirect_uri={}'.format(redirect_uri) +
        '&redirect_name=Globus Example App')

    return redirect(globus_logout_url)


@app.route('/register')
def register():
    ''' Will need to automate for the whole project use
    '''
    return "Contact max.adam.levinson@gmail.com to be placed on whitelist"


##########################################################
#                        ARK                             #
##########################################################

@app.route('/ark/put', methods = ['PUT'])
@auth_required
def MintArk():
    payload = json.loads(request.data)

    try:
        ark = Ark(data=payload)   
    
    except MissingKeys as err:
        return err.output()


    api_response = ark.postAPI()
    ark.postNeo()


    return Response(
            status = api_response.get('status_code'),
            response = json.dumps(api_response)
            )


@app.route('/ark:/<path:Shoulder>/<path:Id>', methods = ['DELETE'])
@auth_required
def DeleteArk(Shoulder, Id):
    GUID = 'ark:/'+Shoulder+'/'+Id
    ark = Ark(guid=GUID)

    api_async = ark.deleteAPI() 

    deleteNeoByGuid.delay(GUID)

    response_dict = api_async.get()

    response_message = {
            "api": {"status_code": response_dict.get('status_code'), "message": response_dict.get('content')},
            }

    return Response(
            status= response_dict.get('status_code'),
            response = json.dumps(response_message)
            )



@app.route('/ark:/<path:Shoulder>/<path:Id>', methods = ['GET'])
def GetArk(Shoulder, Id):
    GUID = 'ark:/'+Shoulder+'/'+Id
    ark = Ark(guid=GUID) 
    payload = ark.getAPI()

    content_type = request.accept_mimetypes.best_match(['text/html', 'application/json', 'application/json-ld'])

    if content_type == 'application/json' and request.accept_mimetypes[content_type]> request.accept_mimetypes['text/html']:
        return Response(response = json.dumps(payload))
    else:
        return render_template('Ark.html', data = payload)



@app.route('/ark/import/<path:GUID>', methods = ['GET'])
@auth_required
def ImportArk(GUID):
    ark = Ark(GUID=GUID)
    return ark.importAPI()


###########################################
# Doi Interfaces                          #
###########################################

@app.route('/doi/put', methods = ['PUT'])
@auth_required
def MintDoi():
    ''' Posting to Neo 
    '''
    payload = json.loads(request.data)

    try:
        obj = Doi(data=payload)

    except MissingKeys as err:
        return err.output()


    obj.postNeo()
    api_response = obj.postAPI()


    response_message = {
            "api": api_response
            }

    return Response(
            status = api_response.get('status_code'),
            response = json.dumps(response_message)
            )


@app.route('/doi:/<path:Shoulder>/<path:Id>', methods = ['DELETE'])
@auth_required
def DeleteDoi(Shoulder, Id):
    GUID = Shoulder +'/'+ Id
    doi = Doi(guid=GUID)
    
    neo_task = deleteNeoByGuid.delay(GUID)
    response_dict = doi.deleteAPI()

    response_message = {
            "api": {"status_code": response_dict.get('status_code'), "message": response_dict.get('content')}
                }

    return Response(
            status=201,
            response = json.dumps(response_message)
            )


@app.route('/doi:/<path:Shoulder>/<path:Id>', methods = ['GET'])
def GetDoi(Shoulder, Id):
    GUID = Shoulder +'/'+ Id
    doi = Doi(guid=GUID)
    payload = doi.getAPI()

    content_type = request.accept_mimetypes.best_match(['text/html', 'application/json', 'application/json-ld'])
    if content_type == 'application/json' and request.accept_mimetypes[content_type]> request.accept_mimetypes['text/html']:
        return Response(response = json.dumps(payload))
    else:
        return render_template('Doi.html', data = payload)


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

