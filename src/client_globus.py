import globus_sdk
from flask import Flask, session, redirect, render_template, request, url_for, Response 


CLIENT_ID = '6cfc4427-9a2e-4abf-af8f-5015e81e0e6a'
app = Flask(__name__)

@app.route('/')
def home():
    """
        Plaintext Home Page
    """
    return "Starting at Home"


@app.route('/index')
def index():
    """
        Needs to be authenticated to view this

            Validates Token from Session/ Query Parameter?/ Cookie?
        
            If Fails Validation attempts to refresh token 
            If Refresh fails, send error
    """
    if not session.get('is_authenticated'):
        return redirect(url_for('login'))

    # validate tokens
    ac = globus_sdk.AuthClient(
            CLIENT_ID,
            authorizer= globus_sdk.AccessTokenAuthorizer(token)
            )

    valid_token = ac.oauth2_validate_token(token)

    # check if token is valid
    if valid_token['active']== True:
        return "YOU MADE IT!"

    if valid_token['active']!= true:
        try:
            # attempt to refresh token
            new_token = ac.oauth2_refresh_token(token)

            # update the session
            session.update(
                    tokens = new_token,
                    is_authenticated=True
                    )

            return "YOU MADE IT!"

        # except a failed refresh token?
        except:
            return "BAD TOKEN"

@app.route('/login')
def login():
    """
        Produce the token for the main service
    """
   
    client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    client.oauth2_start_flow(refresh_tokens=True,
            redirect_uri= url_for('login', _external=True) )

    if 'code' not in request.args:
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

        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    client = globus_sdk.NativeAppAuthClient(CLIENT_ID)

    # revoke all the tokens
    for token in (token_info['access_token'] for token_info in session['tokens'].values()):
        client.oauth2_revoke_token(token)

    # clear the session state
    session.clear()

if __name__ =="__main__": 
    app.run(host="127.0.0.1", port=8080)

