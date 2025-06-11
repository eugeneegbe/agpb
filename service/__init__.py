import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, MethodNotAllowed, NotFound
from flask_swagger_ui import get_swaggerui_blueprint

from common import domain, port, prefix, build_swagger_config_json

app = Flask(__name__, template_folder='../templates')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.sqlite')

db = SQLAlchemy(app)
api = Api(app, prefix=prefix, catch_all_404s=True)

# Swagger
build_swagger_config_json()
swaggerui_blueprint = get_swaggerui_blueprint(
    prefix,
    f'http://{domain}:{port}{prefix}/swagger-config',
    config={
        'app_name': "AGPB API",
        "layout": "BaseLayout",
        "docExpansion": "none"
    },
)

app.register_blueprint(swaggerui_blueprint, url_prefix=prefix)


# Errors
@app.errorhandler(NotFound)
def handle_method_not_found(e):
    response = jsonify({"message": str(e)})
    response.status_code = 404
    return response


@app.errorhandler(MethodNotAllowed)
def handle_method_not_allowed_error(e):
    response = jsonify({"message": str(e)})
    response.status_code = 405
    return response
