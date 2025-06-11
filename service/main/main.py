from flask_restful import (Resource)


class Login(Resource):
    def get(self):
        return {
            'status': 'success',
            'message': 'AGPB service'
        }, 200
