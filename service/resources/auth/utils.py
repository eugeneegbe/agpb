from uuid import uuid4
from service import app
from common import consumer_key, consumer_secret


def generate_random_token():
    """
    Generates a random token for authentication purposes.
    """
    return str(uuid4())


def get_auth_object(data):
    """
    Generates an authentication object from the provided data.
    """
    auth_obj = {
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
        "access_token": data.get('access_token')['key'],
        "access_secret": data.get('access_token')['secret'],
    }
    return auth_obj
