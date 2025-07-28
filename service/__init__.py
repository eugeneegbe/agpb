import os

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, MethodNotAllowed, NotFound
from flask_swagger_ui import get_swaggerui_blueprint
from flask_login import LoginManager
from flask_cors import CORS

from common import (domain, port, prefix, build_swagger_config_json,
                    app_secret, is_dev)

app = Flask(__name__, template_folder='../templates')
CORS(app)
login_manager = LoginManager()

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.sqlite')
app.secret_key = app_secret
db = SQLAlchemy(app)
login_manager.init_app(app)
api = Api(app, prefix=prefix, catch_all_404s=True)

# Swagger
build_swagger_config_json()
swaggerui_blueprint = get_swaggerui_blueprint(
    prefix,
    f'http://{domain}:{port}{prefix}/swagger-config' if is_dev else \
        f'https://{domain}{prefix}/swagger-config' ,
    config={
        'app_name': "AGPB API",
        "layout": "BaseLayout",
        "docExpansion": "none"
    },
)

app.register_blueprint(swaggerui_blueprint, url_prefix=prefix)

@app.after_request
def after_request(response):
    response.headers.add(
        "Access-Control-Allow-Headers", "Content-Type,Authorization,true"
    )
    response.headers.add(
        "Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS"
    )
    return response


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

app.app_context().push()
