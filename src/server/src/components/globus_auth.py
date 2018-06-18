import pickle
import hashlib
import string
from functools import wraps
import globus_sdk
from flask import request, session


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

    Uses Sessions for Browsers
    Uses Argments for REST interface
    '''
    @wraps(f)
    def auth_wrap(*args, **kwargs): 


        # check the session and the arguments for an access_token
        sess_token = session.get('tokens', {}).get('auth.globus.org', {}).get('access_token')


        arg_token   = request.args.get('access_token')

        # if the session is new attempt to read args for access_token
        if arg_token is None and sess_token is None:
            return redirect(url_for('login'))
        if arg_token is not None and sess_token is None:
            token = arg_token
        if arg_token is None and sess_token is not None:
            token = sess_token
        if arg_token is not None and sess_token is not None:
            token = arg_token 

        # APP Client Used to Validate Token
        client = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

        # check token is valid
        valid_token = client.oauth2_validate_token(token)

        # check if token is valid
        if valid_token['active']== True:

            if session.get('is_authorized'):
                return f(*args, **kwargs)

            if not session.get('is_authorized'): 
                # set up auth client to retrieve identities
                ac = globus_sdk.AuthClient( authorizer = globus_sdk.AccessTokenAuthorizer(token) )

                valid_email = validate_email(ac.oauth2_userinfo().data.get('email'))

                if valid_email:
                    session.update(is_authorized = True)
                    return f(*args, **kwargs)
                else:
                    return redirect(url_for('register'))


        if valid_token['active']!= True:
            try:
                # attempt to refresh token
                new_token = ac.oauth2_refresh_token(token)

            except:
                return redirect(url_for('login'))

            # update the session
            session.update( tokens = new_token, is_authenticated=True)

            # authorize user 
            if not session.get('is_authorized'): 
                # set up auth client to retrieve identities
                ac = globus_sdk.AuthClient(authorizer = globus_sdk.AccessTokenAuthorizer(new_token))

                valid_email = validate_email(ac.oauth2_userinfo().data.get('email'))


                if valid_email:
                    session.update(is_authorized = True)
                    return f(*args, **kwargs)
                else:
                    return redirect(url_for('register'))


    return auth_wrap


