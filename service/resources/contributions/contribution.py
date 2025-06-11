from flask import abort
from flask_restful import (Resource, reqparse,
                           fields, marshal_with)
from service.models import ContributionModel
from service import db

# Used for validateion
contrib_args = reqparse.RequestParser()
contrib_args.add_argument('username', type=str, help="Please provide a username")
contrib_args.add_argument('lang_code', type=str, help="Provide contribution language")
contrib_args.add_argument('edit_type', type=str, help="Please provide the type of edit")
contrib_args.add_argument('data', type=str, help="Please provide the edit data")


# Used for serialization
contributionFields = {
    'id': fields.Integer,
    'usename': fields.String,
    'lang_code': fields.String,
    'edit_type': fields.String,
    'data': fields.String
}


class ContributionsGet(Resource):
    @marshal_with(contributionFields)
    def get(self):
        contributions = ContributionModel.query.all()
        return contributions


class ContributionPost(Resource):
    @marshal_with(contributionFields)
    def post(self):
        args = contrib_args.parse_args()
        contribution = ContributionModel(username=args['username'],
                                         lang_code=args['lang_code'],
                                         edit_type=args['edit_type'],
                                         data=['data'])
        db.session.add(contribution)
        db.session.commit()
        contributions = ContributionModel.query.all()
        return contributions, 201


class ContributionGet(Resource):
    @marshal_with(contributionFields)
    def get(self, id):
        user = ContributionModel.query.filter_by(id=id).first()
        if not user:
            abort(400, "User not found")
        return user, 200


class ContributionPatch(Resource):
    @marshal_with(contributionFields)
    def patch(self, id):
        args = contrib_args.parse_args()
        contribution = ContributionModel.query.filter_by(id=id).first()
        if not contribution:
            abort(400, "Contribution not found")

        contribution.username = args["username"]
        contribution.lang_code = args["lang_code"]
        contribution.edit_type = args["edit_type"]  # for the same type no update
        contribution.data = args["data"]
        db.session.commit()
        return contribution, 200


class ContributionDelete(Resource):
    @marshal_with(contributionFields)
    def delete(self, id):
        contribution = ContributionModel.query.filter_by(id=id).first()
        if not contribution:
            abort(400, "User not found")
        db.session.delete(contribution)
        db.session.commit()
        contributions = ContributionModel.query.all()
        return contributions, 204
