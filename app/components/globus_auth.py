import pickle
import hashlib
import string
import os

from functools import wraps
import globus_sdk
from flask import redirect, request, session, url_for, Response
from json import dumps


from app.components.models.auth import *

# globus auth global constants
CLIENT_ID = os.environ.get('GLOBUS_CLIENT') 
CLIENT_IDENTITY_USERNAME = os.environ.get('GLOBUS_USERNAME') 
CLIENT_SECRET = os.environ.get('GLOBUS_SECRET') 

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'localtest')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'localtest')

def globus_auth(f):
    ''' Wrapper for Route's that require authentication
    '''
    @wraps(f)
    def auth_wrap(*args, **kwargs): 
        content_type = request.accept_mimetypes.best_match(
                ['text/html', 'application/json', 'application/ld+json']
                )
        access_token = session.get('access_token',
                request.args.get('code', 
                    request.headers.get('Authorization')
                    )
                )
    

        # if no token redirect to login 
        if access_token is None:
            if content_type == 'text/html': 
                return redirect(url_for('login'))
            else:
                return Response(
                        status = 405,
                        response = json.dumps({'error': 'Please Provide your access token' })
                        )
        else:
            access_token.replace('Bearer ', '')
    
            # look in the database for the user with that token
            login = GlobusLoginNode.nodes.get_or_none(accessToken=access_token)
    
            if login is not None:
                user = login.authenticates.all()[0]
                if user is not None:
                    return f(user=user, *args, **kwargs)
    
                else:
                    if content_type == 'text/html':
                        return redirect(url_for('register'))
                    else:
                        return Response(
                                status = 405,
                                response = json.dumps({'error': 'Please contact Max Levinson to be placed on the whitelist at mal8ch@virginia.edu'})
                                )
            else:
                if content_type == 'text/html':
                    return redirect(url_for('login'))
                else:
                    return Response(
                            status = 405,
                            response = json.dumps({
                                'error': 'Token is not recognized, please login'
                                })
                            )
    
    return auth_wrap


class GlobusToken():
    authClient = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

    def __init__(self, accessToken, refreshToken):        
        self.access_token = accessToken
        self.refresh_token = refreshToken

        login_query = GlobusLoginNode.nodes.get_or_none(refreshToken = refreshToken)
        if login_query is not None:
            login_query.accessToken = accessToken
            login_query.save()
            self.login_node = login_query

        else:
            self.login_node = GlobusLoginNode(
                    refreshToken = refreshToken,
                    accessToken = accessToken
                    )
            self.login_node.save()


    def register_token(self):
        ''' Inspect Token and save user metadata to Neo4j as a token
        ''' 
        token = self.authClient.oauth2_token_introspect(self.access_token, include='identities_set').data  

        # clear other GlobusLoginNodes InspectedTokens 
        for stale_token in InspectedTokenNode.nodes.filter(email=token.get('email')):
            for stale_login in stale_token.login:
                for stale_id in stale_login.identities:
                    stale_id.delete()

                stale_login.delete()
            stale_token.delete()

        self.inspected_token = InspectedTokenNode(
                email = token.get('email'),
                name = token.get('name'),
                username = token.get('username'),
                iat = datetime.datetime.fromtimestamp(token.get('iat')),
                exp = datetime.datetime.fromtimestamp(token.get('exp')),
                identitiesSet =token.get('identities_set') 
            )
                
        self.inspected_token.save()
        self.login_node.inspected.connect(self.inspected_token)
        self.inspected_token.login.connect(self.login_node)
        
 
        matched_user = UserNode.nodes.get_or_none(email=self.inspected_token.email)
        if matched_user is not None:
            self.login_node.authenticates.connect(matched_user)
        
        identities = self.authClient.get_identities(ids= self.inspected_token.identitiesSet).get('identities') 

         
        for id_elem in identities:
            identity_node = GlobusIdentityNode(
                email =id_elem.get('email'), 
                Id = id_elem.get('id'), 
                name = id_elem.get('name'), 
                organization = id_elem.get('organization'), 
                username = id_elem.get('username'))
            identity_node.save()
            self.login_node.identities.connect(identity_node) 

            matched_user = UserNode.nodes.get_or_none(email = id_elem.get('email'))
            if matched_user is not None and self.login_node.authenticates is None:
                self.login_node.authenticates.connect(matched_user)

