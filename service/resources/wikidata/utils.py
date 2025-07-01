import json
import requests
from wikidata.client import Client
from common import (base_url, consumer_key, wm_commons_image_base_url,
                    consumer_secret, app_version, wm_commons_audio_base_url)
from difflib import get_close_matches
from service.utils.languages import getLanguages
from service.resources.utils import make_api_request
from service.resources.commons.utils import upload_file
from service.resources.utils import generate_csrf_token


def get_lexemes_lacking_audio(lang_qid, limit=50, offset=0):
    """
    All english forms missing an audio pronounciation
    affixes excluded
    TODO: Should be modified to find forms without audios
    """
    sparql_endpoint = "https://query.wikidata.org/sparql"
    query = f"""
    SELECT DISTINCT ?lexeme ?lemma ?audio WHERE {{
      ?lexeme dct:language wd:{lang_qid};
         wikibase:lemma ?lemma;
         ontolex:lexicalForm ?form .
      ?form ontolex:representation ?lemma .
      MINUS {{ ?form wdt:P443 ?audio. }}
      # Exclude affixes
      MINUS {{ ?lexeme wikibase:lexicalCategory wd:Q62155. }}
    }}
    LIMIT {limit}
    OFFSET {offset}
    """
    headers = {
        "Accept": "application/json"
    }
    response = requests.get(sparql_endpoint, params={"query": query}, headers=headers)
    if response.status_code == 200:
        audio_result = {}
        data = response.json().get("results", {}).get("bindings", [])

        form_entries = []
        for form in data:
            form_entries.append({
                'lexeme': form['lexeme']['value'].split('/')[-1],
                'formId': form['form']['value'].splilt('/')[-1],
                'lemma': form['lemma']['value']
            })
        audio_result['forms'] = form_entries
        return audio_result
    else:
        return {
            "error": f"SPARQL query failed with status code {response.status_code}",
            "details": response.text
        }


def process_search_results(search_results, search, src_lang, ismatch_search):
    '''
    '''
    src_match = {'type': 'label', 'language': src_lang, 'text': search}
    lexeme_result = []
    if ismatch_search:
        for result in search_results:
            res_item = {}
            if result['match'] == src_match:
                res_item['id'] = result['id']
                res_item['label'] = result['label']
                res_item['language'] = src_lang
                res_item['description'] = result['description']
                lexeme_result.append(res_item)

    else:
        for res in search_results:
            res_item = {}
            res_item['id'] = res['id']
            res_item['label'] = res['label']
            res_item['language'] = src_lang
            res_item['description'] = res['description']
            lexeme_result.append(res_item)

    return lexeme_result


def lexemes_search(search, src_lang, ismatch):
    '''
    '''
    PARAMS = {
        'action': 'wbsearchentities',
        'format': 'json',
        'language': src_lang,
        'type': 'lexeme',
        'uselang': src_lang,
        'search': search,
        'limit': 15
    }

    wd_search_results = make_api_request(base_url, PARAMS)

    if 'status_code' in list(wd_search_results.keys()):
        return wd_search_results

    search_result_data = process_search_results(wd_search_results['search'],
                                                search, src_lang, bool(ismatch))

    return search_result_data


def get_item_label(id):
    client = Client()
    entity = client.get(id, load=True)
    if entity.label:
        return entity.label
    return None


def get_image_url(file_name):
    '''
    Returns the image url from the image file name.
    '''
    return f'{wm_commons_image_base_url}{file_name}'


def process_lexeme_sense_data(lexeme_data, src_lang, lang_1, lang_2, image):
    '''
    '''
    processed_data = {}
    lexeme = {
        'id': lexeme_data['id'],
        'lexicalCategoryId': lexeme_data['lexicalCategory'],
        'lexicalCategoryLabel': get_item_label(lexeme_data['lexicalCategory']),
        'image': get_image_url(image[0]['mainsnak']['datavalue']['value'])
    }

    processed_data['lexeme'] = lexeme
    processed_data['glosses'] = []

    for sense in lexeme_data['senses']:
        sense_base = {}
        sense_gloss = sense['glosses']
        if sense_gloss:
            temp_sense_gloss = sense_gloss.copy()
            for lang in [src_lang, lang_1, lang_2]:
                if lang in sense_gloss:
                    sense_base['senseId'] = sense['id']
                    sense_base['gloss'] = temp_sense_gloss[lang]
                    processed_data['glosses'].append(sense_base)

    #  TODO: Add audio data
    for sense_gloss in processed_data['glosses']:
        for form in lexeme_data['forms']:
            sense_gloss['gloss']['formId'] = form['id']
            if sense_gloss['gloss']['language'] in form['representations']:
                if form['claims'] and 'P443' in form['claims']:
                    audio = form['claims']['P443'][0]['mainsnak']['datavalue']['value']
                    sense_gloss['gloss']['audio'] = wm_commons_audio_base_url + audio
            else:
                sense_gloss['gloss']['audio'] = None
    return [processed_data]


def get_lexeme_sense_glosses(lexeme_id, src_lang, lang_1, lang_2):
    '''
    Gloses for a particular lexeme
    '''
    PARAMS = {
        'action': 'wbgetentities',
        'format': 'json',
        'languages': src_lang,
        'ids': lexeme_id
    }

    lexeme_senses_data = make_api_request(base_url, PARAMS)

    if 'status_code' in list(lexeme_senses_data.keys()):
        return lexeme_senses_data

    if 'P18' in lexeme_senses_data['entities'][lexeme_id]['senses'][0]['claims']:
        image = lexeme_senses_data['entities'][lexeme_id]['senses'][0]['claims']['P18']
    else:
        image = None
    glosses_data = process_lexeme_sense_data(lexeme_senses_data['entities'][lexeme_id],
                                             src_lang, lang_1, lang_2, image)
    return glosses_data


def process_lexeme_form_data(search_term, data, src_lang, lang_1, lang_2):
    processed_data = {}

    for form in data:
        form_audio_list = []

        for lang in [src_lang, lang_1, lang_2]:
            reps_match = {lang: {'language': lang, 'value': search_term}}
            audio_object = {}
            audio_object['language'] = lang
            if form['representations'] == reps_match and form['claims']:
 
                form_claims_audios = form['claims']['P443']

                potential_match_audio = []
                for audio_claim in form_claims_audios:
                    # TODO: Find a way to best match serach term to audio
                    value = audio_claim['mainsnak']['datavalue']['value']
                    potential_match_audio.append(value)

                best_match_audio = get_close_matches(lang + '-' + search_term,
                                                     potential_match_audio)

                # audio_object['audio'] = 'File:' + best_match_audio[0] if \
                #     len(best_match_audio) > 1 else potential_match_audio[0]
                audio_object['audio'] = 'File:' + best_match_audio[0]
                form_audio_list.append(audio_object)
            else:
                audio_object['audio'] = None
                form_audio_list.append(audio_object)
  
        processed_data[form['id']] = form_audio_list
    return [processed_data]


def get_lexeme_forms_audio(search_term, lexeme_id, src_lang, lang_1, lang_2):
    PARAMS = {
        'action': 'wbgetentities',
        'format': 'json',
        'languages': src_lang,
        'ids': lexeme_id
    }

    lexeme_data = make_api_request(base_url, PARAMS)

    if 'status_code' in list(lexeme_data.keys()):
        return lexeme_data

    form_data = process_lexeme_form_data(search_term,
                                         lexeme_data['entities'][lexeme_id]['forms'],
                                         src_lang, lang_1, lang_2)
    return form_data


def get_language_qid(lang_code):
    languages = getLanguages()
    for code, name, qid in languages:
        if code == lang_code:
            return code, name, qid
    return None


def create_new_lexeme(language, value, categoryId, username, auth_obj):
    '''
    Creates a new lexeme in Wikidata
    Parameters:
        language (str): The language of the lexeme
        value (str): The value of the lexeme
        categoryId (int): The ID of the lexical category
        username (str): The username of the person creating the lexeme
        token (str): The crsf token for the request
    '''
    csrf_token, auth = generate_csrf_token(base_url, consumer_key,
                                           consumer_secret,
                                           auth_obj['access_token'],
                                           auth_obj['access_secret'])
    _, _, lqid = get_language_qid(language)

    lexeme_entry = {
        'lemmas': {
            language: {
                'language': language,
                'value': value
            }
        },
        'lexicalCategory': str(categoryId),
        'language': lqid
    }

    data = {}
    data['action'] = 'wbeditentity'
    data['new'] = 'lexeme'
    data['summary'] = username + '@AGPB-' + app_version
    data['token'] = csrf_token
    data['format'] = 'json'
    data['data'] = json.dumps(lexeme_entry)

    response = requests.post(base_url, data=data, auth=auth).json()
    print('response', response)
    
    if 'error' in response:
        return {
            'info': 'Unable to edit. Please check credentials',
            'status_code': 503
        }

    return {
        'revisionid': response['entity']['lastrevid']
    }


def add_audio_to_lexeme(username, language_qid, lang_label,
                        data, form_id, auth_object, file_name):

    csrf_token, api_auth_token = generate_csrf_token(base_url,
                                                     consumer_key,
                                                     consumer_secret,
                                                     auth_object['access_token'],
                                                     auth_object['access_secret'])
    params = {}
    params['format'] = 'json'
    params['token'] = csrf_token
    params['summary'] = username + '@AGPB-v' + app_version
    params['action'] = 'wbcreateclaim'
    params['entity'] = form_id
    params['property'] = 'P443'
    params['snaktype'] = 'value'
    params['value'] = '"' + file_name + '"'

    revision_id = None

    upload_response = upload_file(data, username, lang_label, auth_object, file_name)

    if upload_response is False:
        return {
            'error': 'Upload failed'
        }

    claim_response = requests.post(base_url, data=params, auth=api_auth_token)

    if 'error' in claim_response.json().keys():
        return {
            'error': str(claim_response.json()['error']['code']
                         .capitalize() + ': ' + claim_response.json()['error']['info']
                         .capitalize())
        }

    claim_result = claim_response.json()

    # get language item here from lang_code
    qualifier_value = language_qid
    qualifier_params = {}
    qualifier_params['claim'] = claim_result['claim']['id']
    qualifier_params['action'] = 'wbsetqualifier'
    qualifier_params['property'] = 'P407'
    qualifier_params['snaktype'] = 'value'
    qualifier_params['value'] = json.dumps({'entity-type': 'item', 'id': qualifier_value})
    qualifier_params['format'] = 'json'
    qualifier_params['token'] = csrf_token
    qualifier_params['summary'] = username + '@AGPB-v' + app_version

    qual_response = requests.post(base_url, data=qualifier_params,
                                  auth=api_auth_token)

    qualifier_params = qual_response.json()

    if qual_response.status_code != 200:
        {'error': 'Qualifier could not be added'}
    if 'success' in qualifier_params.keys():
        revision_id = qualifier_params.get('pageinfo').get('lastrevid', None)
        return {'revisionid': revision_id}
    else:
        return {
            'error': "Error: " + str(qual_response.json()['error']['info'].capitalize())
        }
