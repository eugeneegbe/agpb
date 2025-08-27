from datetime import datetime, timedelta
import mwoauth
import json
import jwt
from flask import abort, jsonify, request, make_response
from flask_restful import (Resource, reqparse, fields, marshal_with)
from service.models import UserModel
from service import db
from common import (auth_base_url, consumer_key, dev_fe_url, prod_fe_url,
                    consumer_secret, is_dev)
from .utils import generate_random_token


# Used for serialization
authFields = {
    'token': fields.String,
    'username': fields.String,
    'pref_langs': fields.String
}
authGetFields = {
    'redirect_string': fields.String,
    'request_token': fields.String,
}


class AuthGet(Resource):
    @marshal_with(authGetFields)
    def get(self):
        consumer_token = mwoauth.ConsumerToken(
            consumer_key, consumer_secret)
        try:
            redirect_string, request_token = mwoauth.initiate(
                auth_base_url, consumer_token)
            # Return request token in response instead of storing in session
            request_token_dict = dict(zip(request_token._fields, request_token))
            request_token_json = json.dumps(request_token_dict)
        except Exception as e:
            abort(400, 'mwoauth.initiate failed: ' + str(e))
        return {
            "redirect_string": redirect_string,
            "request_token": request_token_json
        }, 200


class AuthCallBackPost(Resource):
    @marshal_with(authFields)
    def post(self):
        # Parse request data
        parser = reqparse.RequestParser()
        parser.add_argument('request_token', type=str, required=True, help='Request token is required')
        parser.add_argument('query_string', type=str, required=True, help='Query string is required')
        args = parser.parse_args()
        
        try:
            # Parse the request token from JSON
            request_token_dict = json.loads(args['request_token'])
            request_token = mwoauth.RequestToken(**request_token_dict)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            abort(400, f'Invalid request token format: {str(e)}')

        consumer_token = mwoauth.ConsumerToken(
            consumer_key, consumer_secret)
        try:
            access_token = mwoauth.complete(
                auth_base_url,
                consumer_token,
                request_token,
                args['query_string'])

            identity = mwoauth.identify(
                auth_base_url, consumer_token, access_token)

        except Exception as e:
            return jsonify({
                'message': f'OAuth callback failed: {str(e)}'
            }), 404

        username = identity['username']
        user = UserModel.query.filter_by(username=username).first()
        
        if user:
            # User already exists, update the temp token
            user.temp_token = generate_random_token()
            db.session.commit()
            token = jwt.encode({
                'token': user.temp_token,
                'access_token': dict(zip(access_token._fields, access_token)),
                'exp': datetime.utcnow() + timedelta(minutes=60*60)
            }, consumer_secret, "HS256")
            
            return {
                'token': token,
                'username': user.username,
                'pref_langs': user.pref_langs
            }, 200
        else:
            # User does not exist, create a new one
            new_user = UserModel(
                username=username, 
                pref_langs='de,en', 
                temp_token=generate_random_token()
            )
            db.session.add(new_user)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return {
                    'message': f"Error creating user: {str(e)}"
                }, 400
                
            token = jwt.encode({
                'token': new_user.temp_token,
                'access_token': dict(zip(access_token._fields, access_token)),
                'exp': datetime.utcnow() + timedelta(minutes=45)
            }, consumer_secret, "HS256")
            
            return {
                'token': token,
                'username': new_user.username,
                'pref_langs': new_user.pref_langs
            }, 200


class AuthLogout(Resource):
    def post(self):
        # Parse token from request
        parser = reqparse.RequestParser()
        parser.add_argument('token', type=str, required=True, help='Token is required')
        args = parser.parse_args()
        
        try:
            # Decode token to get user info
            data = jwt.decode(args['token'], consumer_secret, algorithms=["HS256"])
            user = UserModel.query.filter_by(temp_token=data['token']).first()
            
            if user:
                # Invalidate the token by generating a new one
                user.temp_token = generate_random_token()
                db.session.commit()
                
            return make_response(jsonify({'message': 'Logged out successfully'}), 200)
        except jwt.InvalidTokenError:
            return make_response(jsonify({'message': 'Invalid token'}), 400)
        except Exception as e:
            return make_response(jsonify({'message': f'Logout error: {str(e)}'}), 500)