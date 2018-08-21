import pickle
import hashlib
import string
import os


from functools import wraps
import globus_sdk
from flask import redirect, request, session, url_for, Response
from json import dumps


from neomodel import (config, StructuredNode, EmailProperty, StringProperty, JSONProperty, ArrayProperty,
                      DateTimeProperty, RelationshipTo, RelationshipFrom, install_labels)
import datetime, base64, json

NEO_PASSWORD = os.environ.get('NEO_PASSWORD', 'localtest')
NEO_URL = os.environ.get('NEO_URL', 'localhost')

config.DATABASE_URL = 'bolt://neo4j:'+ NEO_PASSWORD +'@'+ NEO_URL +':7687'




# globus auth global constants
CLIENT_ID = 'd0b62e2d-a6df-44cc-adf7-b4a1ead2178a'
CLIENT_IDENTITY_USERNAME = 'd0b62e2d-a6df-44cc-adf7-b4a1ead2178a@clients.auth.globus.org'
CLIENT_SECRET = 'gdbcvA5K+3FmlmG0Ss8YMnPiwaABVieYqJ7neBv1raI='

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'localtest')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'localtest')

# open up pickle and load into global vars
#with open('email_hashed.p', 'rb') as pickle_file:
#    GLOBAL_SALT, EMAIL_HASHES = pickle.load(pickle_file)

def validate_email(input_email):
    if any([hash_email(input_email, GLOBAL_SALT)==stored_email for stored_email in EMAIL_HASHES]):
        return True
    else:
        return False


def hash_email(email, salt, iterations=1000):        
    """ Iterativley hash emails
    """
    encoded_email = bytes(email, encoding='utf-8')
    encoded_salt = bytes(salt, encoding='utf-8')
    
    email_hash = hashlib.sha3_512(encoded_email+encoded_salt).hexdigest()
    
    for _ in range(iterations):
        email_hash = hashlib.sha3_512(
            bytes(email_hash, encoding="utf-8")+encoded_email
        ).hexdigest()
    
    return email_hash


def auth_required(f):
    ''' Wrapper for Route's that require authentication
 
    Checks the query parameters, authorization header, and session for the globus access_token
    '''
    @wraps(f)
    def auth_wrap(*args, **kwargs): 

        # connect to auth client
        auth_client = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

        # look for tokens in url as query params
        access_token = request.args.get('code')

        # look for tokens in the authorization header, trim the bearer part
        if request.headers.get('Authorization') is not None:
            access_token = request.headers.get('Authorization').replace('Bearer ', '')
        
        # look for tokens in the session 
        if session.get('access_token') is not None:
            access_token = session.get('access_token')

        # if access_token is provided check it before refreshing
        if access_token is not None:

            # validate token
            valid_token = auth_client.oauth2_validate_token(access_token)
            if valid_token['active']==True:
                ac = globus_sdk.AuthClient(authorizer = globus_sdk.AccessTokenAuthorizer(access_token))

            else: 
                return redirect(url_for('login'))

            # inspect token to return list of identities
            token_info = auth_client.oauth2_token_introspect(access_token, include='identities_set')
            id_list = token_info.get('identities_set') 

            # retrieve all identities associated with that token
            identity_list = auth_client.get_identities(ids = id_list).data.get('identities')

            
            # if any of the identities are a member, return to authorized function
            if any([validate_email(identity.get('email')) for identity in identity_list]):
                return f(*args, **kwargs) 

            else: 
                return redirect(url_for('register'))

        else:
            return redirect(url_for('login'))

    return auth_wrap



class NeoUser(StructuredNode):
    email = EmailProperty(unique_index=True, required=True)
    firstName = StringProperty(required=True)
    lastName = StringProperty(required=True) 

install_labels(NeoUser)

class NeoToken(StructuredNode):
    refreshToken = StringProperty(required=True, unique_index=True)
    accessToken = StringProperty(required=True, unique_index=True)
    
    email = EmailProperty(required=True)
    name = StringProperty(required=True)
    username = StringProperty(required=True)
    
    exp = DateTimeProperty(required=True)
    iat = DateTimeProperty(required=True)
    
    identitiesSet = ArrayProperty()
    identities = RelationshipTo('NeoIdentity', 'hasIdentity')
    authenticates = RelationshipTo('NeoUser', 'authenticates')

install_labels(NeoToken)


class NeoIdentity(StructuredNode):
    email = EmailProperty()
    Id = StringProperty()
    name = StringProperty()
    organization = StringProperty()
    username = StringProperty()

install_labels(NeoIdentity)

class GlobusToken():
    authClient = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

    def __init__(self, accessToken, refreshToken):        
        self.accessToken = accessToken
        self.refreshToken = refreshToken

    def query_token(self):
        token_query = NeoToken.nodes.get_or_none(
                accessToken=self.accessToken, 
                refreshToken=self.refreshToken
                )
        return token_query

    def inspect_token(self):
        ''' Search for Token
        ''' 
        token = self.authClient.oauth2_token_introspect(self.accessToken, include='identities_set').data  
        td = {}
        td['accessToken'] = self.accessToken
        td['refreshToken'] = self.refreshToken
        td['email'] = token.get('email')
        td['name'] = token.get('name')
        td['username'] = token.get('username')
        td['iat'] = datetime.datetime.fromtimestamp(token.get('iat'))
        td['exp'] = datetime.datetime.fromtimestamp(token.get('exp'))
        td['identitiesSet'] = token.get('identities_set')
        td['serializedToken'] = base64.b64encode(json.dumps(token).encode('utf-8'))
             
        self.token = td

    def save_token(self):
        self.node = NeoToken.get_or_create(self.token)[0]    
        return self.node


    def check_linked(self):
        ''' Check if the Globus Token is linked to a User Node
        '''
        return self.node.authenticates.all() is not None


    def link_identity(self):
        ''' Try to link a globus token to a registrered user
        '''
        matched_user = NeoUser.nodes.get_or_none(email=self.node.email)
        if matched_user is not None:
            matched_user.tokens.connect(self.node)
 
        
        identities = self.authClient.get_identities(ids= self.node.identitiesSet).get('identities')        

        id_nodes = [{'email':id_elem.get('email'), 'Id': id_elem.get('id'), 'name': id_elem.get('name'), 
          'organization': id_elem.get('organization'), 'username':id_elem.get('username')} for id_elem in identities]
         
        created_identity_nodes = Identity.create_or_update(*id_nodes)
        for identity in created_identity_nodes:
            self.node.identities.connect(identity)
         
            matched_users = User.nodes.filter(email=identity.email)[:]
            for match in matched_users:
                match.tokens.connect(self.node)


