import requests
from requests_oauthlib import OAuth1


def make_api_request(url, PARAMS):
    """ Makes request to an end point to get data

        Parameters:
            url (str): The Api url end point
            PARAMS (obj): The parameters to be used as arguments

        Returns:
            data (obj): Json object of the recieved data.
    """

    try:
        S = requests.Session()
        r = S.get(url=url, params=PARAMS)
        data = r.json()
    except Exception as e:
        return {
            'info': str(e),
            'status_code': 503
        }

    return data


def generate_csrf_token(url, app_key, app_secret, user_key, user_secret):
    '''
    Generate CSRF token for edit request

    Keyword arguments:
    app_key -- The application api auth key
    app_secret -- The application api auth secret
    user_key -- User auth key generated at login
    user_secret -- User secret generated at login
    '''
    try:
        # We authenticate the user using the keys
        auth = OAuth1(app_key, app_secret, user_key, user_secret)

        # Get token
        token_request = requests.get(url, params={
            'action': 'query',
            'meta': 'tokens',
            'format': 'json',
        }, auth=auth)

        token_request.raise_for_status()
        if 'error' in list(token_request.json().keys()):
            print('error now going back')
            return {
                'info': 'Unable to get csrf token check user edit tokens',
                'status_code': 503
            }

        # We get the CSRF token from the result to be used in editing
        CSRF_TOKEN = token_request.json()['query']['tokens']['csrftoken']
        return CSRF_TOKEN, auth

    except Exception as e:
        return {
            'info': f'Unable to get csrf token check user edit tokens {str(e)}',
            'status_code': 503
        }
