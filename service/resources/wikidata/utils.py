import json
import requests
from wikidata.client import Client
from common import (base_url, consumer_key,
                    consumer_secret, app_version)
from difflib import get_close_matches
from service.resources.utils import generate_csrf_token


def make_api_request(url, PARAMS):
    """ Makes request to an end point to get data

        Parameters:
            url (str): The Api url end point
            PARAMS (obj): The parameters to be used as arguments

        Returns:
            data (obj): Json object of the recieved data.
    """

    try:
        S = requests.Session()
        r = S.get(url=url, params=PARAMS)
        data = r.json()
    except Exception as e:
        return {
            'info': str(e),
            'status_code': 503
        }

    return data


def process_search_results(search_results, search, src_lang, ismatch_search):
    """
    """
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
    """
    """
    PARAMS = {
        "action": "wbsearchentities",
        "format": "json",
        "language": src_lang,
        "type": "lexeme",
        "uselang": src_lang,
        "search": search,
        "limit": 15
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


def process_lexeme_sense_data(senses_data, lang_1, lang_2):
    """
    """
    processed_data = {}
    lexeme = {
        'id': senses_data['id'],
        'lexicalCategoryId': senses_data['lexicalCategory'],
        'lexicalCategoryLabel': get_item_label(senses_data['lexicalCategory'])
    }
    processed_data['lexeme'] = lexeme
    processed_data['gloss'] = []

    for sense in senses_data['senses']:
        sense_base = {}
        sense_base['id'] = sense['id']
        sense_gloss = sense['glosses']
        if sense_gloss:
            for lang in [lang_1, lang_2]:
                if lang in sense_gloss:
                    processed_data['gloss'].append(sense_gloss[lang])

    return [processed_data]


def get_lexeme_sense_glosses(lexeme_id, src_lang, lang_1, lang_2):
    """
    Gloses for a particular lexeme
    """
    PARAMS = {
        "action": "wbgetentities",
        "format": "json",
        "languages": src_lang,
        "ids": lexeme_id
    }

    lexeme_senses_data = make_api_request(base_url, PARAMS)

    if 'status_code' in list(lexeme_senses_data.keys()):
        return lexeme_senses_data

    glosses_data = process_lexeme_sense_data(lexeme_senses_data['entities'][lexeme_id],
                                             lang_1, lang_2)
    return glosses_data


def process_lexeme_form_data(search_term, data, src_lang, lang_1, lang_2):
    processed_data = {}

    for form in data:
        form_audio_list = []

        for lang in [src_lang, lang_1, lang_2]:
            reps_match = {lang:{'language': lang, 'value': search_term}}
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

                # audio_object['audio'] = "File:" + best_match_audio[0] if \
                #     len(best_match_audio) > 1 else potential_match_audio[0]
                audio_object['audio'] = "File:" + best_match_audio[0]
                form_audio_list.append(audio_object)
            else:
                audio_object['audio'] = None
                form_audio_list.append(audio_object)
  
        processed_data[form['id']] = form_audio_list
    return [processed_data]


def get_lexeme_forms_audio(search_term, lexeme_id, src_lang, lang_1, lang_2):
    PARAMS = {
        "action": "wbgetentities",
        "format": "json",
        "languages": src_lang,
        "ids": lexeme_id
    }

    lexeme_data = make_api_request(base_url, PARAMS)

    if 'status_code' in list(lexeme_data.keys()):
        return lexeme_data

    form_data = process_lexeme_form_data(search_term,
                                         lexeme_data['entities'][lexeme_id]['forms'],
                                         src_lang, lang_1, lang_2)
    return form_data


def create_new_lexeme(language, value, categoryId, username, token):
    """
    Creates a new lexeme in Wikidata
    Parameters:
        language (str): The language of the lexeme
        value (str): The value of the lexeme
        categoryId (int): The ID of the lexical category
        username (str): The username of the person creating the lexeme
        token (str): The crsf token for the request   
    """

    lex_data = {
        'lemmas': {
            language: {
                'language': language,
                'value': value
            }
        },
        'lexicalCategory': {
            'entity-type': 'item',
            'numeric-id': categoryId
        }
    }
    
    params = {}
    params['new'] = 'lexeme'
    params['token'] = token
    params['action'] = 'wbeditentity'
    params['data'] = json.dumps(lex_data, ensure_ascii=False)
    params['summary'] = username + '@AGPB-' + app_version

    try:
        response = requests.post(base_url,
                                 data=params)

    except Exception as e:
        print('Error in creating lexeme', str(e))
        return {
            'info': 'Unable to edit. Please check credentials',
            'status_code': 503
        }

    revision_id = response.get('pageinfo').get('lastrevid', None)
    return {
        'revisionid': revision_id
    }
