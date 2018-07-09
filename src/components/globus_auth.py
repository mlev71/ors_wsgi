import pickle
import hashlib
import string
from functools import wraps
import globus_sdk
from flask import redirect, request, session, url_for, Response
from json import dumps

# globus auth global constants
CLIENT_ID = 'd0b62e2d-a6df-44cc-adf7-b4a1ead2178a'
CLIENT_IDENTITY_USERNAME = 'd0b62e2d-a6df-44cc-adf7-b4a1ead2178a@clients.auth.globus.org'
CLIENT_SECRET = 'gdbcvA5K+3FmlmG0Ss8YMnPiwaABVieYqJ7neBv1raI='

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


