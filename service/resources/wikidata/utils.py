import json
import sys
import base64
import datetime
import requests
from wikidata.client import Client
from common import (base_url, consumer_key, wm_commons_image_base_url,
                    consumer_secret, app_version, wm_commons_audio_base_url,
                    sparql_endpoint_url, commons_url)
from difflib import get_close_matches
from jsonschema import validate, ValidationError
from service import db
from service.models import ContributionModel
from service.utils.languages import getLanguages
from service.resources.utils import make_api_request
from service.resources.commons.utils import upload_file
from service.resources.utils import generate_csrf_token
from SPARQLWrapper import SPARQLWrapper, JSON


def get_lexemes_lacking_audio(lang_qid, lang_code, page_size=15, page=1):
    offset = (page - 1) * page_size
    query = f"""
    SELECT ?l ?sense ?lemma ?category ?categoryLabel ?form WHERE {{
        ?l   ontolex:sense ?sense;
            dct:language wd:{lang_qid};
            wikibase:lemma ?lemma;
            ontolex:lexicalForm ?form;
            wikibase:lexicalCategory ?category.
        ?category rdfs:label ?categoryLabel.
        FILTER(lang(?categoryLabel) = "{lang_code}")
        FILTER(NOT EXISTS {{ ?form wikibase:P443 ?audioFile. }})
    }}
    ORDER BY ?l
    LIMIT {page_size}
    OFFSET {offset}
    """

    user_agent = "AGPB/%s.%s" % (sys.version_info[0], sys.version_info[1])
    sparql = SPARQLWrapper(sparql_endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    result = sparql.query().convert()
    final_results = []
    if 'results' in result and 'bindings' in result['results']:
        for entry in result['results']['bindings']:
            final_results.append({
                "lexeme_id": entry['l']['value'].split('/')[-1],
                "sense_id": entry['sense']['value'].split('/')[-1],
                "lemma": entry['lemma']['value'],
                "categoryId": entry['category']['value'].split('/')[-1],
                "categoryLabel": entry['categoryLabel']['value'],
                "formId": entry['form']['value'].split('/')[-1]
            })
        return final_results
    else:
        return {
            "error": f"SPARQL query failed with status code {result.status_code}",
            "details": result.text
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


def get_default_gloss(lang):
    """
    Returns a default gloss dictionary for the specified language.

    Args:
        lang (str): The language code for the gloss.

    Returns:
        dict: A dictionary with the following keys:
            - 'language': The provided language code.
            - 'value': None (default value).
            - 'audio': None (default value).
            - 'formId': None (default value).
    """
    return {
        'language': lang,
        'value': None,
        'audio': None,
        'formId': None
    }


def process_lexeme_sense_data(lexeme_data, src_lang, lang_1, lang_2, image):
    '''
    '''
    processed_data = {}
    media = None
    if image is not None:
        media = get_image_url(image[0]['mainsnak']['datavalue']['value'])

    lexeme = {
        'id': lexeme_data['id'],
        'lexicalCategoryId': lexeme_data['lexicalCategory'],
        'lexicalCategoryLabel': get_item_label(lexeme_data['lexicalCategory']),
        'image': media
    }

    processed_data['lexeme'] = lexeme
    processed_data['glosses'] = []

    for lang in [src_lang, lang_1, lang_2]:
        for sense in lexeme_data['senses']:
            sense_base = {}
            sense_gloss = sense['glosses']

            if sense_gloss and lang in sense_gloss:
                temp_sense_gloss = sense_gloss.copy()
                sense_base['senseId'] = sense['id']
                sense_base['gloss'] = temp_sense_gloss[lang]
                processed_data['glosses'].append(sense_base)

            else:
                if lang not in list(s['gloss']['language'] for s in processed_data['glosses']):
                    sense_base = {}
                    sense_base['senseId'] = sense['id']
                    sense_base['gloss'] = get_default_gloss(lang)
                    processed_data['glosses'].append(sense_base)

    for sense_gloss in processed_data['glosses']:
        for form in lexeme_data['forms']:
            sense_gloss['gloss']['formId'] = form['id'] if sense_gloss['gloss']['value'] else None
            if sense_gloss['gloss']['language'] in form['representations']:
                if form['claims'] and 'P443' in form['claims']:
                    audio = form['claims']['P443'][0]['mainsnak']['datavalue']['value']
                    sense_gloss['gloss']['audio'] = wm_commons_audio_base_url + audio
            else:
                sense_gloss['gloss']['audio'] = None
    return processed_data


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


def translate_new_lexeme(translation_data, username, auth_obj):
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
    result_object = {}
    for trans_data in translation_data:

        lastrev_id = None
        if trans_data['is_new'] is True:
        # New Lexeme needs to be created then returned
            _, _, lqid = get_language_qid(trans_data['translation_language'])

            lexeme_entry = {
                'lemmas': {
                    trans_data['translation_language']: {
                        'language': trans_data['translation_language'],
                        'value': trans_data['translation_value']
                    }
                },
                'lexicalCategory': str(trans_data['categoryId']),
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

            if 'error' in response:
                return {
                    'info': 'Unable to edit. Please check credentials',
                    'status_code': 503
                }
            lastrev_id = response['entity']['lastrevid']
            result_object[response['entity']['id']] = lastrev_id

        if lastrev_id or bool(trans_data['is_new']) is False:
            # Just add the gloss here
            return add_gloss_to_lexeme_sense(trans_data['lexeme_id'],
                                             trans_data['lexeme_sense_id'],
                                             trans_data['translation_language'],
                                             trans_data['translation_value'], username,
                                             csrf_token, auth, result_object)
    return {
        'error': 'No edit was made please check the data',
        'status_code': 503
    }


def add_gloss_to_lexeme_sense(lexeme_id, sense_id, gloss_language,
                              gloss_value, username, csrf_token, auth, result_obj):
    """
    Adds a new gloss to an existing lexeme sense in Wikidata.

    This function correctly implements the logic for editing a lexeme.
    Adding a gloss is an *edit* to an existing lexeme, not the creation of a new one.

    Parameters:
        lexeme_id (str): The ID of the lexeme to modify (e.g., "L123").
        sense_id (str): The ID of the sense to add the gloss to (e.g., "L123-S1").
        gloss_language (str): The language code for the new gloss (e.g., "fr").
        gloss_value (str): The text of the new gloss.
        username (str): The username of the editor for the summary.
        auth_obj (dict): The authentication object with access_token and access_secret.
    """
    # We get the current lexeme
    # Then get its avoid edit conflicts
    get_params = {
        'action': 'wbgetentities',
        'ids': lexeme_id,
        'format': 'json'
    }
    get_response = requests.get(base_url, params=get_params)
    
    if get_response.status_code != 200:
        return {
            'info': f'Failed to fetch lexeme {lexeme_id}. Status: {get_response.status_code}',
            'status_code': get_response.status_code
        }

    lexeme_data = get_response.json()

    if 'error' in lexeme_data or lexeme_id not in lexeme_data.get('entities', {}):
        return {'info': f'Could not find lexeme {lexeme_id} in API response.', 'status_code': 404}

    entity = lexeme_data['entities'][lexeme_id]
    base_revid = entity.get('lastrevid')
    senses = entity.get('senses', [])

    if not base_revid:
        return {'info': f'Could not find base revision ID for lexeme {lexeme_id}.', 'status_code': 404}

    # Step 3: Find the target sense and add/update the gloss.
    # We must submit the entire 'senses' array back, so we modify it in place.
    sense_found = False
    for sense in senses:
        if sense['id'] == sense_id:
            # Add the new gloss to the existing glosses dictionary
            if 'glosses' not in sense:
                sense['glosses'] = {}
            sense['glosses'][gloss_language] = {
                'language': gloss_language,
                'value': gloss_value
            }
            sense_found = True
            break

    if not sense_found:
        return {'info': f'Sense {sense_id} not found in lexeme {lexeme_id}', 'status_code': 404}

    # Step 4: Prepare the data for the wbeditentity API call.
    # The 'data' payload contains the modified 'senses' array.
    edit_payload = {
        'senses': senses
    }

    post_params = {
        'action': 'wbeditentity',
        'id': lexeme_id,
        'data': json.dumps(edit_payload),
        'summary': f"Adding '{gloss_language}' gloss for sense {sense_id} via AGPB-v{app_version}",
        'token': csrf_token,
        'baserevid': base_revid,
        'format': 'json'
    }

    try:
        # Step 5: Make the API call to edit the entity
        response = requests.post(base_url, data=post_params, auth=auth).json()
        
        if 'error' in response:
            error_info = response['error'].get('info', 'Unknown error')
            return {
                'error': f'Unable to edit. Wikidata API error: {error_info}',
                'status_code': 503
            }
        contribution = ContributionModel(wd_item=lexeme_id,
                                                username=username,
                                                lang_code=gloss_language,
                                                edit_type='audio',
                                                data="Added: " + gloss_value,
                                                date=datetime.datetime.now())
        db.session.add(contribution)
        db.session.commit()

    except Exception as e:
        return {'error': 'Qualifier could not be added: ' + str(e)}

    # Record contribtion
    result_obj[lexeme_id] = response.get('entity', {}).get('lastrevid')
    return result_obj


def add_audio_to_lexeme(username, auth_object, audio_data):

    csrf_token, api_auth_token = generate_csrf_token(base_url,
                                                     consumer_key,
                                                     consumer_secret,
                                                     auth_object['access_token'],
                                                     auth_object['access_secret'])
    results = []
    for data in audio_data:  
        revision_id = None
        upload_response = upload_file(base64.b64decode(data['file_content']), username,
                                    data['lang_label'], auth_object, data['filename'])
        
        file_name = data['filename']
        if 'duplicate' in upload_response.json()['upload']['warnings']:
            file_name = upload_response.json()['upload']['warnings']['duplicate'][0]

        params = {}
        params['format'] = 'json'
        params['token'] = csrf_token
        params['summary'] = username + '@AGPB-v' + app_version
        params['action'] = 'wbcreateclaim'
        params['entity'] = data['formid']
        params['property'] = 'P443'
        params['snaktype'] = 'value'
        params['value'] = '"' + file_name + '"'

        if upload_response is False:
            return {
                'error': 'Upload failed'
            }

        try:
            claim_response = requests.post(base_url, data=params, auth=api_auth_token)
        except Exception as e:
            return {
                'error': 'Upload failed' + str(e)
            }

        if 'error' in claim_response.json().keys():
            return {
                'error': str(claim_response.json()['error']['code']
                            .capitalize() + ': ' + claim_response.json()['error']['info']
                            .capitalize())
            }

        claim_result = claim_response.json()

        # get language item here from lang_code
        qualifier_value = data['lang_wdqid']
        qualifier_params = {}
        qualifier_params['claim'] = claim_result['claim']['id']
        qualifier_params['action'] = 'wbsetqualifier'
        qualifier_params['property'] = 'P407'
        qualifier_params['snaktype'] = 'value'
        qualifier_params['value'] = json.dumps({'entity-type': 'item', 'id': qualifier_value})
        qualifier_params['format'] = 'json'
        qualifier_params['token'] = csrf_token
        qualifier_params['summary'] = username + '@AGPB-v' + app_version

        try:
            qual_response = requests.post(base_url, data=qualifier_params,
                                        auth=api_auth_token)

            qualifier_params = qual_response.json()

            if qual_response.status_code != 200:
                return {'error': 'Qualifier could not be added'}
        
            revision_id = qualifier_params.get('pageinfo').get('lastrevid', None)
            results.append({
                'lexeme_id': data['formid'].split('-')[0],
                'revisionid': revision_id
            })

            # Record contribution on tool
            contribution = ContributionModel(wd_item=data['formid'].split('-')[0],
                                             username=username,
                                             lang_code=data['lang_label'],
                                             edit_type='audio',
                                             data=data['formid'] + '-' + file_name,
                                             date=datetime.datetime.now())
            db.session.add(contribution)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            return {'error': 'Qualifier could not be added: ' + str(e)}

    return {'results': results}

def get_auth_object(consumer_key, consumer_secret, decoded_token):
    return {
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
        "access_token": decoded_token.get('access_token')['key'],
        "access_secret": decoded_token.get('access_token')['secret'],
    }


def validate_translation_request_body(request_body, schema):
    try:
        validate(instance=request_body, schema=schema)
        return True
    except ValidationError as e:
        print(f"Validation error: {e.message}")
        return False
