#!/usr/bin/env python3 
from flask import Flask, render_template, request, Response, session, redirect, url_for

import globus_sdk
import json
import requests
import re
import os
import sys
import bugsnag

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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

# configure bugsnag

bugsnag.configure(
    api_key= os.environ.get('bugsnag_key'),
    project_root="/app",
)

# test to see if its running
bugsnag.notify(Exception('Test Error on Starting Application'))



#####################################
#            General                #
#####################################

@app.route('/', methods = ['GET'])
def home():
    ''' Render Homepage with Content Information
    '''
    # count the number of downloads, datasets, and

    # return all data dictionaries

    # list all dataset guids

    return render_template('home.html')


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


    if request.args.get('status') is None:
        status = 'reserved'

    else:
        status = request.args.get('status')

    api_response = ark.postAPI(status)


    #ark.postNeo()

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

    content_type = request.accept_mimetypes.best_match(['text/html', 'application/json', 'application/ld+json'])

    if content_type == 'application/json' or content_type == 'application/ld+json' and request.accept_mimetypes[content_type]> request.accept_mimetypes['text/html']:
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
    payload = json.loads(request.data)

    try:
        obj = Doi(data=payload)

    except MissingKeys as err:
        return err.output()


    #obj.postNeo()
    api_response = obj.postAPI()

    return Response(
            status = api_response.get('status_code'),
            response = json.dumps(api_response)
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
    json_ld = requests.get(url = 'https://data.datacite.org/application/vnd.schemaorg.ld+json/'+ GUID)

    if json_ld.status_code == 200:
        payload = json.loads(json_ld.content.decode('utf-8'))

    if json_ld.status_code == 204:
        doi = Doi(guid=GUID)

        try:
            payload = doi.getWorks()
        except (NotADataciteDOI, InvalidPayload, IncompletePayload) as err:
            return err.output()

    if json_ld.status_code == 404:
        return

    content_type = request.accept_mimetypes.best_match(['text/html', 'application/json', 'application/ld+json'])
    if content_type == 'application/json' or content_type == 'application/ld+json' and request.accept_mimetypes[content_type]> request.accept_mimetypes['text/html']:
        return Response(response = json.dumps(payload))
    else:
        return render_template('Doi.html', data = payload)






#@app.route('/doin:/<path:Shoulder>/<path:Id>', methods = ['GET'])
def GetWorks(Shoulder, Id):


    content_type = request.accept_mimetypes.best_match(['text/html', 'application/json', 'application/ld+json'])
    if content_type == 'application/json' or content_type == 'application/ld+json' and request.accept_mimetypes[content_type]> request.accept_mimetypes['text/html']:
        return Response(response = json.dumps(payload))
    else:
        return render_template('Doi.html', data = payload)


@app.route('/doi/import/<path:GUID>', methods = ['PUT'])
@auth_required
def ImportDoi(GUID):
    ''' Accept a json body to deposit in neo, accept a GUID to search for and import
    '''
    if request.data is not None:
        try:
            payload = json.loads(request.data)
            obj = Doi(data=payload)

        except MissingKeys as err:
            return err.output()

        return obj.postNeo()
    else:
        obj = Doi(guid=GUID)
        return obj.importAPI()


from bugsnag.wsgi.middleware import BugsnagMiddleware
app = BugsnagMiddleware(app)
