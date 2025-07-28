from flask import request, jsonify, abort
from functools import wraps
import jwt
from service import app
from common import consumer_secret
from service.models import UserModel


class TokenError(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code

class PermissionDeniedError(TokenError):
    def __init__(self, message="Permission denied"):
        super().__init__(message, 400)
        abort(401, 'User not authenticated')

class TokenExpiredError(TokenError):
    def __init__(self, message="Token has expired"):
        super().__init__(message, 401)

class InvalidTokenError(TokenError):
    def __init__(self, message="Invalid token"):
        super().__init__(message, 401)

class TokenDecodeError(TokenError):
    def __init__(self, message="An error occurred during token decoding"):
        super().__init__(message, 500)


def token_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        token = None
        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']
        if token is None:
            abort(401, description="Insufficient permission to access resource.")
        try:
            data = jwt.decode(token, consumer_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            abort(401, description="Token has expired.")
        except jwt.InvalidTokenError:
            abort(401, description="Invalid Token.")
        except Exception as e:
            abort(401, description="Error decoding token" + str(e))
        current_user = UserModel.query.filter_by(temp_token=data['token']).first()
        if not current_user:
            raise InvalidTokenError()
        return f(current_user, *args, **kwargs)
    return inner
