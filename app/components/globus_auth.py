import pickle
import hashlib
import string
import os


from functools import wraps
import globus_sdk
from flask import redirect, request, session, url_for, Response
from json import dumps


from neomodel import (config, StructuredNode, EmailProperty, StringProperty, JSONProperty, ArrayProperty,
                      DateTimeProperty, RelationshipTo, RelationshipFrom, install_labels, cardinality)
import datetime, base64, json

NEO_PASSWORD = os.environ.get('NEO_PASSWORD', 'localtest')
NEO_URL = os.environ.get('NEO_URL', 'localhost')

config.DATABASE_URL = 'bolt://neo4j:'+ NEO_PASSWORD +'@'+ NEO_URL +':7687'


# globus auth global constants
CLIENT_ID = 'd0b62e2d-a6df-44cc-adf7-b4a1ead2178a'
CLIENT_IDENTITY_USERNAME = 'd0b62e2d-a6df-44cc-adf7-b4a1ead2178a@clients.auth.globus.org'
CLIENT_SECRET = 'gdbcvA5K+3FmlmG0Ss8YMnPiwaABVieYqJ7neBv1raI='

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'ors_test')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ors_test')

# open up pickle and load into global vars
with open('email_hashed.p', 'rb') as pickle_file:
    GLOBAL_SALT, EMAIL_HASHES = pickle.load(pickle_file)

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



def globus_auth(f):
    ''' Wrapper for Route's that require authentication
    '''
    @wraps(f)
    def auth_wrap(*args, **kwargs): 
        access_token = session.get('access_token',
                request.args.get('code', 
                    request.headers.get('Authorization')
                    )
                )

        # if no token redirect to login 
        if access_token is None:
            return redirect(url_for('login'))
        else:
            # look in the database for the user with that token
            access_token.replace('Bearer ', '')
            login = GlobusLoginNode.nodes.get_or_none(accessToken=access_token)
            if login is not None:
                user = login.authenticates
                if user is not None:
                    return f(user=user, *args, **kwargs)

                else:
                    return redirect(url_for('register'))
            else:
                return redirect(url_for('login'))


    return auth_wrap


class TeamNode(StructuredNode):
    element = StringProperty(required=True)
    kc = StringProperty(required=True)

install_labels(TeamNode)

class UserNode(StructuredNode):
    email = EmailProperty(unique_index=True, required=True)
    firstName = StringProperty(required=True)
    lastName = StringProperty(required=True) 

    team = RelationshipTo('TeamNode', 'memberOf', cardinality=cardinality.ZeroOrOne)
    token = RelationshipTo('GlobusLoginNode', 'auth', cardinality=cardinality.ZeroOrOne)

install_labels(UserNode)

class GlobusLoginNode(StructuredNode):
    ''' Obtained by Logging in
    '''
    refreshToken = StringProperty(required=True, unique_index = True)
    accessToken = StringProperty(required=True)

    inspected = RelationshipTo('InspectedTokenNode', 'details', cardinality=cardinality.ZeroOrOne)
    authenticates = RelationshipTo('UserNode', 'authFor', cardinality=cardinality.ZeroOrOne)
    identities = RelationshipTo('GlobusIdentityNode', 'identity')
    
install_labels(GlobusLoginNode)

class InspectedTokenNode(StructuredNode): 
    email = EmailProperty(required=True, unique_index = True)
    name = StringProperty(required=True)
    username = StringProperty(required=True)
    
    exp = DateTimeProperty(required=True)
    iat = DateTimeProperty(required=True)
 
    identitiesSet = ArrayProperty() 
    login = RelationshipTo('GlobusLoginNode', 'detailsFor')


install_labels(InspectedTokenNode)


class GlobusIdentityNode(StructuredNode):
    email = EmailProperty()
    globusId = StringProperty()
    name = StringProperty()
    organization = StringProperty()
    username = StringProperty()    
    login = RelationshipTo('GlobusLoginNode', 'identityFrom')    



install_labels(GlobusIdentityNode)

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


