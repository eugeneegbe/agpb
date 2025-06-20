from datetime import datetime, timedelta
import mwoauth
import json
import jwt
from flask import abort, jsonify

from flask_restful import (Resource, reqparse,
                           fields, marshal_with)
from service.models import UserModel
from service import db
from common import (auth_base_url, consumer_key, dev_fe_url, prod_fe_url,
                    consumer_secret, is_dev)
from flask import redirect, request, session, make_response, jsonify
from flask_login import current_user, login_user, logout_user
from .utils import generate_random_token


# Used for serialization
authFields = {
    'token': fields.String,
}
authGetFields = {
    'redirect_string': fields.String,
}


class AuthGet(Resource):
    @marshal_with(authGetFields)
    def get(self):
        if current_user.is_authenticated:
            user = UserModel.query.filter_by(username=current_user.username).first()
            token = jwt.encode({'token': user.temp_token,
                                'access_token': session.get('access_token', None),
                                'exp' : datetime.utcnow() + timedelta(minutes=45)},
                               consumer_secret, "HS256")

            redirect_base_url = dev_fe_url if is_dev else prod_fe_url
            return {
                "redirect_string": redirect_base_url + "oauth-callback?token=" + str(token)
            }, 302

        else:
            print('User is not authenticated, starting OAuth handshake')

            consumer_token = mwoauth.ConsumerToken(
                consumer_key, consumer_secret)
            try:
                redirect_string, request_token = mwoauth.initiate(
                    auth_base_url, consumer_token)
            except Exception as e:
                abort(400, 'mwoauth.initiate failed: ' + str(e))
            session['request_token'] = dict(zip(
                request_token._fields, request_token))
            print('redirect_string', redirect_string)
            return {
                "redirect_string": redirect_string
            }, 200


class AuthCallBackPost(Resource):
    @marshal_with(authFields)
    def get(self):
        if current_user.is_authenticated:
            token = jwt.encode({'token': current_user.temp_token,
                                'access_token': session.get('access_token', None),
                                'exp' : datetime.utcnow() + timedelta(minutes=45)},
                               consumer_secret, "HS256")

            return {
                'token': token
            }, 200

        if 'request_token' not in session.keys():
            return jsonify({
                'message': 'OAuth callback failed. Are cookies disabled?'
            }), 404

        consumer_token = mwoauth.ConsumerToken(
            consumer_key, consumer_secret)
        try:
            access_token = mwoauth.complete(
                auth_base_url,
                consumer_token,
                mwoauth.RequestToken(**session['request_token']),
                request.query_string)

            identity = mwoauth.identify(
                auth_base_url, consumer_token, access_token)

        except Exception as e:
            return jsonify({
                'message': 'OAuth callback failed. Are cookies disabled? ' + str(e)
            }), 404

        session['access_token'] = dict(zip(
            access_token._fields, access_token))
        session['username'] = identity['username']

        user = UserModel.query.filter_by(username=session.get('username')).first()
        if user:
            # User already exists, update the temp token
            user.temp_token = generate_random_token()
            db.session.commit()
            token = jwt.encode({'token': user.temp_token,
                                'access_token': session.get('access_token', None),
                                'exp' : datetime.utcnow() + timedelta(minutes=45)},
                                consumer_secret, "HS256")
            login_user(user)
            return {
                'token': token
            }, 200

        else:
            # User does not exist, create a new one
            user = UserModel(username=session.get('username'), pref_langs='de,en', temp_token=generate_random_token())
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return {
                    'message': f"Error creating user: {str(e)}"
                }, 400
            token = jwt.encode({'token': user.temp_token,
                                'access_token': session.get('access_token', None),
                                'exp' : datetime.utcnow() + timedelta(minutes=45)},
                                consumer_secret, "HS256")
            login_user(user)
            return {
                'token': token
            }, 200


class AuthLogout(Resource):
    def get(self):
        if current_user.is_authenticated:
            logout_user()
            session.clear()
            return make_response(jsonify({'message': 'Logged out successfully'}), 200)
        else:
            return make_response(jsonify({'message': 'User is not authenticated'}), 401)
