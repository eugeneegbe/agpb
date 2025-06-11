from flask import abort
from flask_restful import (Resource, reqparse,
                           fields, marshal_with)
from service.models import UserModel
from service import db

# Used for validateion
user_args = reqparse.RequestParser()
user_args.add_argument('username', type=str, help="Please provide a username")
user_args.add_argument('pref_langs', type=str, help="Provide a preffered language")

# Used for serialization
userFields = {
    'id': fields.Integer,
    'username': fields.String,
    'pre_langs': fields.String
}


class UsersGet(Resource):
    @marshal_with(userFields)
    def get(self):
        users = UserModel.query.all()
        return users


class UserPost(Resource):
    @marshal_with(userFields)
    def post(self):
        args = user_args.parse_args()
        user = UserModel(username=args['username'], pre_langs=args['pre_langs'])
        db.session.add(user)
        db.session.commit()
        users = UserModel.query.all()
        return users, 201


class UserGet(Resource):
    @marshal_with(userFields)
    def get(self, id):
        user = UserModel.query.filter_by(id=id).first()
        if not user:
            abort(400, "User not found")
        return user, 200


class UserPatch(Resource):
    @marshal_with(userFields)
    def patch(self, id):
        args = user_args.parse_args()
        user = UserModel.query.filter_by(id=id).first()
        if not user:
            abort(400, "User not found")
        user.username = args["username"]
        user.pre_langs = args["pre_langs"]
        db.session.commit()
        return user, 200


class UserDelete(Resource):
    @marshal_with(userFields)
    def delete(self, id):
        user = UserModel.query.filter_by(id=id).first()
        if not user:
            abort(400, "User not found")
        db.session.delete(user)
        db.session.commit()
        users = UserModel.query.all()
        return users, 204
