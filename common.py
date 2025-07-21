import dotenv
import os
import json


class ENVIRONMENT:
    def __init__(self):
        dotenv.load_dotenv(os.path.dirname(__file__) + '/.venv')

        self.port = os.getenv("PORT")
        self.prefix = os.getenv("PREFIX")
        self.domain = os.getenv("DOMAIN")
        self.base_url = os.getenv("BASE_URL")
        self.commons_url = os.getenv("WM_COMMONS_URL")
        self.consumer_key = os.getenv("CONSUMER_KEY")
        self.consumer_secret = os.getenv("COMSUMER_SECRET")
        self.app_version = os.getenv("APP_VERSION")
        self.app_secret = os.getenv("APP_SECRET")
        self.is_dev = os.getenv("IS_DEV")
        self.dev_fe_url = os.getenv("DEV_FE_URL")
        self.auth_base_url = os.getenv("OAUTH_BASE_URL")
        self.prod_fe_url = os.getenv("PROD_FE_URL")
        self.commons_image_base_url = os.getenv("WM_COMMONS_IMAGE_BASE_URL")
        self.wm_commons_audio_base_url = os.getenv("WM_COMMONS_AUDIO_BASE_URL")
        self.sparql_endpoint_url = os.getenv("SPARQL_ENDPOINT_URL")

    def get_instance(self):
        if not hasattr(self, "_instance"):
            self._instance = ENVIRONMENT()
        return self._instance

    def getDomain(self):
        return self.domain

    def getPort(self):
        return self.port

    def getPrefix(self):
        return self.prefix

    def getBaseUrl(self):
        return self.base_url
    
    def getCommonsAPIUrl(self):
        return self.commons_url

    def getConsumerKey(self):
        return self.consumer_key

    def getConsumerSecret(self):
        return self.consumer_secret
    
    def getAppSecret(self):
        return self.app_secret

    def getAppVersion(self):
        return self.app_version

    def getIsDev(self):
        return bool(self.is_dev)
    
    def getDevFEUrl(self):
        return self.dev_fe_url

    def getProdFEUrl(self):
        return self.prod_fe_url
    
    def getAuthBaseUrl(self):
        return self.auth_base_url
    
    def getCommonsImageBaseUrl(self):
        return self.commons_image_base_url
    
    def getCommonsAudioBaseUrl(self):
        return self.wm_commons_audio_base_url
    
    def getSparqlEndpointUrl(self):
        return self.sparql_endpoint_url


domain = ENVIRONMENT().get_instance().getDomain()
port = ENVIRONMENT().get_instance().getPort()
prefix = ENVIRONMENT().get_instance().getPrefix()
base_url = ENVIRONMENT().get_instance().getBaseUrl()
commons_url = ENVIRONMENT().get_instance().getCommonsAPIUrl()
consumer_key = ENVIRONMENT().get_instance().getConsumerKey()
consumer_secret = ENVIRONMENT().get_instance().getConsumerSecret()
app_version = ENVIRONMENT().get_instance().getAppVersion()
app_secret = ENVIRONMENT().get_instance().getAppSecret()
is_dev = ENVIRONMENT().get_instance().getIsDev()
dev_fe_url = ENVIRONMENT().get_instance().getDevFEUrl()
prod_fe_url = ENVIRONMENT().get_instance().getProdFEUrl()
auth_base_url = ENVIRONMENT().get_instance().getAuthBaseUrl()
wm_commons_image_base_url = ENVIRONMENT().get_instance().getCommonsImageBaseUrl()
wm_commons_audio_base_url = ENVIRONMENT().get_instance().getCommonsAudioBaseUrl()
sparql_endpoint_url = ENVIRONMENT().get_instance().getSparqlEndpointUrl()


def build_swagger_config_json():
    config_file_path = os.path.dirname(__file__) + '/swagger/config.json'

    with open(config_file_path, 'r') as file:
        config_data = json.load(file)

    config_data['servers'] = [
        {"url": f"http://localhost:{port}{prefix}"},
        {"url": f"http://{domain}:{port}{prefix}"}
    ]

    new_config_file_path = os.path.dirname(__file__) + '/swagger/config.json'

    with open(new_config_file_path, 'w') as new_file:
        json.dump(config_data, new_file, indent=2)
