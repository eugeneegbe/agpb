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
            return jsonify({'message': 'Permission denied'}), 400
        try:
            data = jwt.decode(token, consumer_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'message': 'An error occurred during token decoding ' + str(e)}), 500

        current_user = UserModel.query.filter_by(temp_token=data['token']).first()
        if not current_user:
            return jsonify({'message': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)
    return inner
