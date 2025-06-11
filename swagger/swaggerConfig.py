import os
from flask_restful import Resource
from flask import jsonify
import json


class SwaggerConfig(Resource):
    def get(self):
        with open(os.path.dirname(__file__) + '/' + 'config.json', 'r') as config_file:
            config_data = json.load(config_file)
        return jsonify(config_data)
