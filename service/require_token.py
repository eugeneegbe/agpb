from flask import request, jsonify
from functools import wraps
import jwt
from service import app
from common import consumer_secret
from service.models import UserModel


def token_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        token = None
        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']
        if not token:
            return {'message': 'Permission denied'}, 400
        try:
            data = jwt.decode(token, consumer_secret, algorithms=["HS256"])
            current_user = UserModel.query.filter_by(temp_token=data['token']).first()
        except Exception as e:
            return jsonify({'message': 'Session expired, please login' + str(e)}), 401

        return f(*args, **kwargs)
    return inner
