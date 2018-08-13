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


app.config['DEBUG'] = True
app.config['TESTING'] = True
app.config['SECRET_KEY'] = 'kYhD3X9@8Z}FeX2'

LOGIN_URL = os.environ.get('LOGIN', 'https://ors.datacite.org')

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

# @app.before_request
# @app.after_request

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
   return render_template('docs.html') 


@app.route('/login')
def login():
    """ Run Oauth2 flow with globus auth 
    """ 
    client = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

    client.oauth2_start_flow(
            redirect_uri= LOGIN_URL, 
            refresh_tokens=True)

    if 'code' not in request.args:
        authorize_url = client.oauth2_get_authorize_url() 
        return redirect(authorize_url)

    else:
        auth_code = request.args.get('code')
        try:
            tokens = client.oauth2_exchange_code_for_tokens(auth_code)
        except:
            return Response(
                    response = "Invalid Credentials: Cannot Grant Tokens for an old Authorization Code",
                    status = 401
                    )
        
        access_token = tokens.data.get('access_token')
        refresh_token = tokens.data.get('refresh_token')
        oidc_token = tokens.decode_id_token()
  

        session.update(
                access_token = access_token,
                oidc_token = oidc_token,
                refresh_token = refresh_token
            )

        globus_token = GlobusToken(access_token, refresh_token)
        globus_token.register_token()


        return 'ACCESS TOKEN: {}'.format(access_token)


@app.route('/logout')
def logout():
    ''' Clear all provided tokens
    Authorization Headers with bearer tokens
    Query parameter 'code'
    Sessions for web browsers
    '''
    client = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

 
    access_token = session.get('access_token',
            request.args.get('code', 
                request.headers.get('Authorization')
                )
            )

    if access_token is None:
        return "Please Provide an Access Token to Logout"

    globus_login = GlobusLoginNode.nodes.get_or_none(accessToken=access_token) 
    if globus_login is not None:
        globus_details = globus_login.inspected
        globus_identities = globus_login.identities

        for desc in globus_details:
            desc.delete()
        for identity in globus_identities:
            identity.delete()

        globus_login.delete()
 
    # clear all identities
    client.oauth2_revoke_token(access_token)

    session.update(
        access_token = None,
        refresh_token = None,
        oidc_token = None
            )

    
    #redirect_uri = url_for('home', _external=True)
    redirect_uri = 'https://localhost/'

    # call globus to invalidate tokens
    globus_logout_url = (
        'https://auth.globus.org/v2/web/logout' +
        '?client={}'.format(CLIENT_ID) +
        '&redirect_uri={}'.format(redirect_uri) +
        '&redirect_name=Object Registration Service'
        )

    return redirect(globus_logout_url)


@app.route('/register', methods = ['GET', 'POST', 'DELETE'])
def register():
    ''' Administrate with HTTP Basic Auth
    '''

    if request.method == 'DELETE':
        auth = request.authorization
                
        if not auth or not (auth.username == ADMIN_USERNAME and auth.password == ADMIN_PASSWORD):
            return Response(
                    'Could not verify admin credentials.\n'
                    'You have to login with proper credentials', 401,
                    {'WWW-Authenticate': 'Basic realm="Login Required"'}
                    )
         
        payload = json.loads(request.data)
        if payload.get('email') is not None and payload.get('firstName') is not None and payload.get('lastName') is not None:
            del_user = UserNode.nodes.get_or_none(
                email = payload.get('email'),
                firstName = payload.get('firstName'),
                lastName = payload.get('lastName') 
                )
            if del_user is not None:
                del_user.delete()
                return Response(
                        status = 200,
                        response = json.dumps({'deletedUser': payload}),
                        mimetype = 'application/json'
                        )
            else:
                return Response( 
                        status = 404,
                        response = json.dumps({'nonExistantUser': payload}),
                        mimetype = 'application/json'
                        )
        else:
            return "Please Describe the User to Delete in the JSON request body"


    # add a user to the database 
    if request.method == 'POST':
        auth = request.authorization
                
        if not auth or not (auth.username == ADMIN_USERNAME and auth.password == ADMIN_PASSWORD):
            return Response(
                    'Could not verify admin credentials.\n'
                    'You have to login with proper credentials', 401,
                    {'WWW-Authenticate': 'Basic realm="Login Required"'}
                    )
                
        payload = json.loads(request.data)

        if type(payload) == dict:
            registered_team = TeamNode.get_or_create(
                    {'element': payload.get('team'), 'kc': payload.get('kc')}
                    )
            try:
                new_user = UserNode(
                        email = payload.get('email'),
                        firstName = payload.get('firstName'),
                        lastName = payload.get('lastName'),
                        team = registered_team[0]
                        )
                new_user.save()
                return Response(
                        status = 201,
                        response = json.dumps({'registeredUser': payload}),
                        mimetype = 'application/json'
                        )

            except:
                user = UserNode.nodes.get_or_none( email = payload.get('email'))

                if user is not None:
                    user.firstName = payload.get('firstName')
                    user.lastName = payload.get('lastName') 
                    user.team.connect(registered_team[0])
                    
                    user.save()

                    return Response(
                            status = 201,
                            response = json.dumps({'updatedUser': payload}),
                            mimetype = 'application/json'
                            )
                else:
                    return Response(
                            status = 500,
                            response = "Unable to update")


        else:
            return Response( 
                    status = 400,
                    response =json.dumps({'badPayload':payload}),
                    mimetype= 'application/json'
                    )
            
    
    if request.method == 'GET':
        return "Contact max.adam.levinson@gmail.com to be placed on whitelist"


##########################################################
#                        ARK                             #
##########################################################

@app.route('/ark/put', methods = ['PUT'])
@globus_auth
def MintArk(user):
    payload = json.loads(request.data)

    try:
        ark = Ark(data=payload)   
    
    except MissingKeys as err:
        return err.output()

    status = request.args.get('status', 'reserved')
    api_response = ark.post_api(status)

    return api_response


@app.route('/ark:/<path:Shoulder>/<path:Id>', methods = ['DELETE'])
@globus_auth
def DeleteArk(Shoulder, Id, user):
    GUID = 'ark:/'+Shoulder+'/'+Id
    ark = Ark(guid=GUID)
    return ark.delete_api()



@app.route('/ark:/<path:Shoulder>/<path:Id>', methods = ['GET'])
def GetArk(Shoulder, Id):
    guid = 'ark:/'+Shoulder+'/'+Id
 
    content_type = request.accept_mimetypes.best_match(['text/html', 'application/json', 'application/ld+json'])

    if Shoulder == '57799':
        ark_obj = Minid(guid)
    else:
        ark_obj = Ark(guid=guid)

    try:
        ark_obj.fetch()
    except (Identifier404)  as err:
        if content_type == 'text/html':
            return err.html_response()
        else:
            return err.json_response()
    try:
        payload, profile =  ark_obj.to_json_ld()

    except (UnknownProfile400) as e:
        if content_type == 'text/html':
            return err.html_response()
        else:
            return err.json_response()
    
    
    if content_type == 'application/json' or content_type == 'application/ld+json':
        return Response(
                status = 200, 
                response = json.dumps(payload))
    
    else:
        if profile == 'doi':
            return render_template('Doi.html', data = payload)
        else:
            return render_template('Ark.html', data = payload, profile = profile)



###########################################
# Doi Interfaces                          #
###########################################

@app.route('/doi/put', methods = ['PUT'])
@globus_auth
def MintDoi(user):
    if user.email != 'max.adam.levinson@gmail.com':
        return Response(
                status = 403,
                response = "You are not Authorized to Mint DOIs"
                )
    
    payload = json.loads(request.data)

    try:
        obj = Doi(data=payload)

    except MissingKeys as err:
        return err.output()


    api_response = obj.post_api()

    return Response(
            status = 201,
            response = json.dumps(api_response)
            )


@app.route('/doi:/<path:Shoulder>/<path:Id>', methods = ['DELETE'])
@globus_auth
def DeleteDoi(Shoulder, Id, user):
    if user.email != 'max.adam.levinson@gmail.com':
        return Response(
                status = 403,
                response = "You are not Authorized to Mint DOIs"
                )
    GUID = Shoulder +'/'+ Id
    doi = Doi(guid=GUID)
    
    response_dict = doi.delete_api()

    response_message = {
            "api": {"status_code": response_dict.get('status_code'), "message": response_dict.get('content')}
                }

    return Response(
            status=204,
            response = json.dumps(response_message)
            )


@app.route('/doi:/<path:Shoulder>/<path:Id>', methods = ['GET'])
def GetDoi(Shoulder, Id): 
    content_type = request.accept_mimetypes.best_match(['text/html', 'application/json', 'application/ld+json'])

    GUID = Shoulder +'/'+ Id
   
    datacite_request = requests.get(
            url = 'https://data.datacite.org/application/vnd.schemaorg.ld+json/'+ GUID
            )

    if datacite_request.status_code == 404:
        if content_type == 'text/html':
            return render_template('DoiNotFound.html', doi= 'http://doi.org/'+self.guid)
        else:
            return Response(status=404,
                    response = json.dumps({
                        '@id': GUID, 
                        'code': 404,
                        'url':'https://data.datacite.org/application/vnd.schemaorg.ld+json/'+ GUID,
                        'error': 'Doi Was not Found'}),
                    mimetype='application/ld+json')

    payload = json.loads(datacite_request.content.decode('utf-8'))


    # get content contentURL from the works API
    works_response = requests.get(url = 'https://api.datacite.org/works/'+GUID)

    works = json.loads(works_response.content.decode('utf-8'))
    media = works.get('data', {}).get('attributes').get('media')

    payload['contentUrl'] = [media_elem.get('url') for media_elem in media]
    payload['fileFormat'] = list(set([media_elem.get('media_type') for media_elem in media]))


    if content_type == 'text/html':
        return render_template('Doi.html', data = payload)
    else:
        return Response(status=200,
                response = json.dumps(payload),
                mimetype = 'application/ld+json'
                )


from bugsnag.wsgi.middleware import BugsnagMiddleware
app = BugsnagMiddleware(app)

if __name__=="__main__":
    app.run(use_debugger= True, debug=app.debug, use_reloader=True, host='0.0.0.0')
