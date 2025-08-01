import io
import requests
from service.resources.wikidata.utils import make_api_request
from common import commons_url, consumer_key, consumer_secret
from service.resources.utils import generate_csrf_token


def get_media_url_by_title(file_titles):
    PARAMS = {
        "action": "query",
        "titles": file_titles,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    media_data = make_api_request(commons_url, PARAMS)

    if 'status_code' in list(media_data.keys()):
        return media_data

    media_pages = media_data["query"]["pages"]
    media_results = []

    for page in media_pages:
        media_object = {}
        media_id = list(media_data["query"]["pages"].keys())[0]
        media_title = media_pages[page]['title']

        if 'imageinfo' not in media_pages[media_id]:
            media_url = None
        else:
            media_url = media_pages[media_id]['imageinfo'][0]['url']

        media_object['title'] = media_title
        media_object['url'] = media_url if media_url else None
        media_results.append(media_object)
    
    return media_results


def upload_file(file_data, username, lang_label, auth, file_name):
    csrf_token, api_auth_token = generate_csrf_token(commons_url,
                                                    consumer_key,
                                                    consumer_secret,
                                                    auth['access_token'],
                                                    auth['access_secret'])
    params = {}
    params['action'] = 'upload'
    params['format'] = 'json'
    params['filename'] = file_name
    params['token'] = csrf_token
    params['text'] = "\n== {{int:license-header}} ==\n{{cc-by-sa-4.0}}\n\n[[Category:" +\
                     "AGPB-" + lang_label + "-Pronunciation]]"

    try:
        response = requests.post(commons_url,
                                data=params,
                                auth=api_auth_token,
                                files={'file': io.BytesIO(file_data)})
    except Exception as e:
        print('File upload response ', e)
    if response.status_code != 200:
        return False

    return response
