from flask import abort
from flask_restful import (Resource, reqparse,
                           fields, marshal_with)

from .utils import get_media_url_by_title

# Used for validateion
media_args = reqparse.RequestParser()

media_args.add_argument('titles', type=str, help="Please provide a file name")

# Used for serialization
mediaFields = {
    'title': fields.String,
    'url': fields.String
}


class CommonsFIleUrLPost(Resource):
    @marshal_with(mediaFields)
    def post(self, titles):
        args = media_args.parse_args()
        # TODO: Add arguments check
        if args['titles'] is not None or titles is not None:
            abort(400, f'Please provide required parameters {str(list(args.keys()))}')

        media_data = get_media_url_by_title(args['titles'])
        if type(media_data) is not list:
            abort(media_data['status_code'], media_data)

        return media_data, 200
