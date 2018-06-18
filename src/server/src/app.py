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

app = Flask('ors', template_folder='templates')

# a secret key is required for sessions
Flask.secret_key = 'gdbcvA5K+3FmlmG0Ss8YMnPiwaABVieYqJ7neBv1raI=kiapsdf'


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
    
    Return JWT granted by globus auth
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

        # update the session
        session.update(
                tokens = tokens.by_resource_server,
                is_authenticated=True
                )

        # return the tokens
        return Response( 
                response = json.dumps(tokens.by_resource_server),
                status = 200
                )

@app.route('/logout')
def logout():
    client = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

    # revoke all the tokens in the session
    for token in (token_info['access_token'] for token_info in session['tokens'].values()):
        client.oauth2_revoke_token(token)

    for arg_token in request.args.get('access_token'):
        client.oauth2_revoke_token(arg_token)

    # clear the session state
    session.clear()

    redirect_uri = url_for('home', _external=True)

    # call globus to invalidate tokens
    globus_logout_url = (
        'https://auth.globus.org/v2/web/logout' +
        '?client={}'.format(CLIENT_ID) +
        '&redirect_uri={}'.format(redirect_uri) +
        '&redirect_name=Globus Example App')
    return redirect(globus_logout_url)


########################################################
#                      Data Catalog                    #
########################################################
@app.route('/dc/put', methods = ['PUT'])
@auth_required
def MintDC():
    payload, options =  parse_payload(json.loads(request.data), request.args) 
    obj = DataCatalog(data=payload, options=options)

    neo_response = obj.postNeo()
    api_async_response = obj.postAPI() # is now an AysncResult object from celery

    response_dict = api_async_response.get()
    response_message = {
            "api": {"status": response_dict.get('status_code'), "messsage": response_dict.get('content')},
            "cache": {"created": neo_response}
            }

    return Response(
            status = response_dict.get('status_code'),
            response = json.dumps(response_message)
            )

@app.route('/dc/delete/<path:GUID>', methods=['DELETE'])
@auth_required
def DeleteDC(GUID):
    ''' Delete Identifier from EZID and Cache
    '''
    dc = DataCatalog(guid=GUID)

    # adds removal to 
    api_async_response = dc.deleteAPI()
    response_dict = api_async_response.get()

    # removes from cache
    removed_data = dc.deleteCache(GUID)

    response_message = {
            "cache": {"metadata": removed_data, "message": "Removed from cache"},
            "api": {"status_code": response_dict.get('status_code'), "message": response_dict.get('content')}
                }

    return Response(
            status=201,
            response = json.dumps(response_message)
            )


@app.route('/dc/get/<path:GUID>', methods = ['GET'])
@auth_required
def GetDC(GUID):
    ''' Resolves object from Endpoint and returns JSON-LD 
    '''
    endpoint = "https://ezid.cdlib.org/id/"+GUID
    api_response = requests.get(url = endpoint)

    if api_response.status_code != 200:
        return Response(
                status = 404,
                response = json.dumps({'api': api_response.content.decode('utf-8')})
                )

    else:
        payload = str(api_response.content.decode('utf-8'))
        final_payload = formatJson(unroll(removeProfileFormat(ingestAnvl(payload))))

        return Response(response = json.dumps(final_payload))


@app.route('/dc/landing/<path:GUID>', methods = ['GET'])
def GetDCLandingPage(GUID): 
    ''' Return Landing Page 
    '''
    endpoint = "https://ezid.cdlib.org/id/"+GUID
    api_response = requests.get(url = endpoint)
    payload = str(api_response.content.decode('utf-8'))


    template_data = unroll(removeProfileFormat(ingestAnvl(payload)))
    template_data = formatJson(template_data)

    return render_template('DataCatalog.html', data = template_data)


@app.route('/dc/import/<path:GUID>', methods = ['GET'])
@auth_required
def ImportDC(GUID):
    ''' Attempt to import the data from EZID
    '''
    api_response = requests.get(url = "https://ezid.cdlib.org/id/"+GUID)

    # format the payload 
    payload = str(api_response.content.decode('utf-8'))
    final_payload = formatJson(unroll(removeProfileFormat(ingestAnvl(payload))))

    # read into DC interface
    obj = DataCatalog(data=final_payload, guid=GUID)  
    post = obj.postNeo()

    response_message = {"cache": {"imported": post} }

    return Response(
            status = 201,
            response = json.dumps(response_message),
            mimetype= 'application/json'
            )


##########################################################
#                        ARK                             #
##########################################################

@app.route('/ark/put', methods = ['PUT'])
@auth_required
def MintArk():
    payload, options = parse_payload(json.loads(request.data), request.args)
    obj = Ark(data=payload, options=options)


    neo_response = obj.postNeo()
    api_async_response = obj.postAPI()

    response_dict = api_async_response.get()

    response_message = {
            "api": {"status": response_dict.get('status_code'), "messsage": response_dict.get('content')},
            "cache": {"created": neo_response}
            }

    return Response(
            status = response_dict.get('status_code'),
            response = json.dumps(response_message)
            )


@app.route('/ark/delete/<path:GUID>', methods= ['DELETE'])
@auth_required
def DeleteArk(GUID):
    ark = Ark(guid=GUID)

    api_async_response = ark.deleteAPI()
    neo_response = ark.neo_driver.deleteCache(GUID)

    response_dict = api_async_response.get()

    response_message = {
            "cache": {"metadata": neo_response, "message": "Removed from cache"},
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
    payload, options = parse_payload(json.loads(request.data))
    obj = Doi(payload, options)


    api_async_response = obj.postAPI()
    neo_response = obj.postNeo()

    response_dict = api_async_response.get()

    response_message = {
            "api": {"status": response_dict.get('status_code'), "messsage": response_dict.get('content')},
            "cache": {"created": neo_response}
            }

    return Response(
            status = response_dict.get('status_code'),
            response = json.dumps(response_message)
            )


@app.route('/doi/delete/<path:GUID>', methods= ['DELETE'])
@auth_required
def DeleteDoi(GUID):
    doi = Doi(guid=GUID)

    api_async_response = doi.deleteAPI()
    neo_response = doi.deleteCache(GUID)


    response_dict = api_async_response.get()
    response_message = {
            "cache": {"metadata": neo_response, "message": "Removed from cache"},
            "api": {"status_code": response_dict.get('status_code'), "message": response_dict.get('content')}
                }

    return Response(
            status=201,
            response = json.dumps(response_message)
            )


@app.route('/doi/get/<path:GUID>', methods = ['GET'])
@auth_required
def GetDoi(GUID):
    endpoint = "https://ez.test.datacite.org/id/"+GUID

    api_response = requests.get(
            url = endpoint
            )

    if api_response.status_code == 404:
        return Response(
                response = json.dumps({"status":404, "message": "No record of Identifier"})
                )

    payload = str(api_response.content.decode('utf-8'))

    unpacked_payload = unroll(removeProfileFormat(ingestAnvl(payload)))

    final_payload = formatJson(unpacked_payload)
    
    return Response(
            response = json.dumps(final_payload)
            )


@app.route('/doi/landing/<path:GUID>', methods = ['GET'])
def GetDoiLandingPage(GUID):
    endpoint = "https://ez.test.datacite.org/id/"+GUID
    api_response = requests.get( url = endpoint)

    if api_response.status_code == 404:
        return Response(
                response = json.dumps({"status":404, "message": "No record of Identifier"})
                )

    payload = str(api_response.content.decode('utf-8'))
    template_data = formatJson(unroll(removeProfileFormat(ingestAnvl(payload))))
 
    return render_template('Doi.html', data = template_data)


@app.route('/doi/import/<path:GUID>', methods = ['GET'])
@auth_required
def ImportDoi(GUID):
    endpoint = "https://ez.test.datacite.org/id/"+GUID

    api_response = requests.get(
            url = endpoint
            )

    # format the payload 
    payload = str(api_response.content.decode('utf-8'))
    final_payload = formatJson(unroll(removeProfileFormat(ingestAnvl(payload))))

    # read into DC interface
    obj = Doi(final_payload)  
    post = obj.postNeo()

    response_message = {"cache": {"imported": post} }

    return Response(
            status = 201,
            response = json.dumps(response_message),
            mimetype= 'application/json'
            )


#############################################################
# Cache Interfaces 
###############################################################
@app.route('/cache/get/<path:GUID>', methods = ['GET'])
@auth_required
def RetrieveCache(GUID):
    neo_conn = NeoConn()
    response_message = json.dumps(neo_conn.getCache(GUID))
    return Response(
           status = 200,
           response = response_message,
           mimetype="application/json"
           )
           
@app.route('/cache/delete/<path:GUID>', methods =['DELETE'])
@auth_required
def DeleteCache(GUID):
    neo_conn = NeoConn()
    deleted_properties = neo_conn.deleteCache(GUID)
    return Response(
            status = 201,
            response = json.dumps(deleted_properties),
            mimetype="application/json"
            )



if __name__ == '__main__':
    app.run(
            ssl_context=('cert.pem','key.pem'), 
            #ssl_context='adhoc',
            host="0.0.0.0", 
            port=8080
            )

