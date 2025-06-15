from flask import request, jsonify
from functools import wraps
import jwt
from service import app
from service.models import UserModel


def token_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        token = None
        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']
        print("No token found in request headers", request.headers)
        if not token:
            print("No token found in request headers")
            return {'message': 'Permission denied'}, 400
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = UserModel.query.filter_by(temp_token=data['token']).first()
        except Exception as e:
            return jsonify({'message': 'Session expired, please login' + str(e)}), 401

        return f(current_user, data, *args, **kwargs)
    return inner
