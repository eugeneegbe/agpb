import re
import json
import urllib.parse
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
from service.resources.utils import make_api_request, get_user_agent
from service.resources.commons.utils import upload_file
from service.resources.utils import generate_csrf_token
from SPARQLWrapper import SPARQLWrapper, JSON


def get_lexemes_lacking_audio(lang_qid, lang_code, page_size=15, page=1):
    offset = (page - 1) * page_size

    
    query = f"""
    SELECT DISTINCT ?l ?sense ?form ?formRepresentation ?category ?categoryLabel WHERE {{
    ?l dct:language wd:{lang_qid};
            ontolex:lexicalForm ?form;
            ontolex:sense ?sense;
            wikibase:lexicalCategory ?category.

    ?form ontolex:representation ?formRepresentation.

    MINUS {{
        ?form wdt:P443 ?audioFile.
    }}

    SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "{lang_code}".
        ?category rdfs:label ?categoryLabel.
    }}
    }}
    LIMIT {page_size}
    OFFSET {offset}
    """
    
    user_agent = "AGPB/%s.%s" % (sys.version_info[0], sys.version_info[1])
    sparql = SPARQLWrapper(sparql_endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    result = sparql.query().convert()
    final_results = []
    # TODO: Change key:lemma to form_rep
    if 'results' in result and 'bindings' in result['results']:
        for entry in result['results']['bindings']:
            final_results.append({
                "lexeme_id": entry['l']['value'].split('/')[-1],
                "sense_id": entry['sense']['value'].split('/')[-1],
                "lemma": entry['formRepresentation']['value'],
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


def process_search_results(search_results, search,
                           src_lang, ismatch_search, with_sense):
    '''
    '''
    print('with_sense', with_sense)
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
                res_item['sense_id'] = result['id'] + '-S1' if with_sense is True else None
                lexeme_result.append(res_item)

    else:
        for res in search_results:
            if res['display']['label']['language'] == src_lang:
                res_item = {}
                res_item['id'] = res['id']
                res_item['label'] = res['label']
                res_item['language'] = src_lang
                res_item['description'] = res['description']
                res_item['sense_id'] = res['id'] + '-S1' if with_sense is True else None
                lexeme_result.append(res_item)

    return lexeme_result


def lexemes_search(search, src_lang, ismatch, with_sense):
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

    wd_search_results = make_api_request(base_url, PARAMS, get_user_agent())
    if 'status_code' in list(wd_search_results.keys()):
        return wd_search_results

    if 'search' not in wd_search_results:
        return {'error': 'No search results found', 'status_code': 404}
    
    search_result_data = process_search_results(wd_search_results['search'],
                                                search, src_lang, bool(ismatch),
                                                bool(with_sense))
    return search_result_data


def get_language_label(languages, code):
    """
    Finds the language label from a list of tuples based on a given language code.

    Args:
        languages (list of tuples): A list of tuples, where each tuple contains
                                     (code, label, ID).
        code (str): The language code to match.

    Returns:
        str or None: The language label if a match is found, otherwise None.
    """
    for lang_code, label, _ in languages:
        if lang_code == code:
            return label
    return None


def get_item_label(id):
    client = Client()
    try:
        entity = client.get(id, load=True)
        if entity.label:
            return entity.label
    except Exception as e:
        print(str(e))
    return None


def get_image_url(file_name):
    '''
    Returns the image url from the image file name.
    '''
    return f'{wm_commons_image_base_url}{file_name}'


def get_default_gloss(lang):
    """
    Returns a default gloss dictionary for the specified language.
    """
    return {
        'language': lang,
        'value': None,
        'audio': None,
        'formId': None
    }


def get_wikimedia_commons_url(file_name, api_url):
    """
    Get the URL of an audio file in Wikimedia Commons given the file name.
    """
    params = {
        "action": "query",
        "titles": f"File:{file_name}",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }

    response = requests.get(api_url, params=params, headers=get_user_agent())
    data = response.json()

    pages = data.get("query", {}).get("pages", {})
    if pages:
        page_id = next(iter(pages))
        image_info = pages[page_id].get("imageinfo", [])
        if image_info:
            return image_info[0].get("url")
    return None


def get_matching_form_id(lexeme_value, src_lang, forms):
    """
    Returns the sense ID matching lexeme value in source language.
    Optimized for readability and efficiency using a generator expression.
    """
    return next((form['id'] for form in forms 
                 if form.get('representations', {}).get(src_lang, {}).get('value') == lexeme_value), None)


def get_matching_sense_id(src_lang, senses):
    """
    Returns the sense ID matching lexeme value in source language.
    Optimized for readability and efficiency using a generator expression.
    """
    return next((sense['id'] for sense in senses 
                 if sense.get('glosses', {}).get(src_lang)), None)


def process_lexeme_sense_data(lexeme_data, src_lang, lang_1, lang_2, image):
    """
    Processes lexeme and sense data, handling glosses and audio.
    This function has been refactored to be more efficient by using a dictionary
    for faster audio lookups and streamlining the main processing loop.
    """
    processed_data = {}
    media = get_image_url(image[0]['mainsnak']['datavalue']['value']) if image else None

    lemma_value = lexeme_data['lemmas'].get(src_lang, {}).get('value')
    if not lemma_value:
        language_name = next((name for code, name, _ in getLanguages() if code == src_lang), "Unknown Language")
        return {'error': f'Word not found in source language: {language_name}', 'status_code': 404}

    matched_sense_id = get_matching_sense_id(src_lang, lexeme_data.get('senses', []))
    matched_form_id = get_matching_form_id(lemma_value, src_lang, lexeme_data.get('forms', []))

    processed_data['lexeme'] = {
        'id': lexeme_data['id'],
        'lexicalCategoryId': lexeme_data['lexicalCategory'],
        'lexicalCategoryLabel': get_item_label(lexeme_data['lexicalCategory']),
        'image': media
    }

    processed_data['glosses'] = []
    processed_data['glosses'].append({
        'senseId': matched_sense_id,
        'gloss': {
            'language': src_lang,
            'value': lemma_value,
            'audio': None,
            'formId': matched_form_id
        }
    })

    # Use a dictionary for fast form-to-audio lookups
    form_audio_map = {}
    for form in lexeme_data.get('forms', []):
        claims = form.get('claims')
        if claims and 'P443' in claims:
            for audio_claim in claims['P443']:
                audio_value = audio_claim['mainsnak']['datavalue']['value']
                # The assumption is that one form has one audio file.
                form_audio_map[form['id']] = get_wikimedia_commons_url(audio_value, commons_url)
                break

    # Add other entries for senses
    senses = lexeme_data.get('senses', [])
    for lang in [lang_1, lang_2]:
        found_gloss = False
        for sense in senses:
            sense_gloss = sense.get('glosses', {}).get(lang)
            if sense_gloss:
                processed_data['glosses'].append({
                    'senseId': sense['id'],
                    'gloss': sense_gloss
                })
                found_gloss = True
                break
        if not found_gloss and senses:
            # If no gloss found for the language, add a default for the first sense
            processed_data['glosses'].append({
                'senseId': senses[0]['id'],
                'gloss': get_default_gloss(lang)
            })
            
    # Add audio to the glosses based on the pre-built map
    for sense_gloss in processed_data['glosses']:
        form_id = sense_gloss['gloss'].get('formId')
        audio_url = form_audio_map.get(form_id)
        if audio_url:
            sense_gloss['gloss']['audio'] = audio_url

    return processed_data


def process_lexeme_form_data(search_term, data, src_lang, lang_1, lang_2):
    """
    Processes lexeme form data to find audio URLs.
    Refactored to find the matching form once and then process its claims,
    avoiding redundant loops and using a more robust matching method.
    """
    processed_data = {}
    
    # Find the specific form that matches the search term in the source language
    matching_form = next((form for form in data 
                          if form.get('representations', {}).get(src_lang, {}).get('value') == search_term), None)

    if not matching_form:
        return []

    form_id = matching_form['id']
    form_claims = matching_form.get('claims', {})
    form_audio_list = []

    # Get a list of all potential audio file names from the claims
    potential_audios = [audio_claim['mainsnak']['datavalue']['value'] 
                        for audio_claim in form_claims.get('P443', [])]

    # Process each language
    for lang in [src_lang, lang_1, lang_2]:
        audio_object = {'language': lang, 'audio': None}
        reps_value = matching_form.get('representations', {}).get(lang, {}).get('value')
        
        if reps_value:
            # Look for an exact match for the language-prefixed filename
            audio_filename = f"{lang}-{reps_value}"
            best_match = next((audio for audio in potential_audios if audio_filename in audio), None)

            if best_match:
                audio_object['audio'] = get_wikimedia_commons_url(best_match, commons_url)

        form_audio_list.append(audio_object)
    
    processed_data[form_id] = form_audio_list
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

    lexeme_senses_data = make_api_request(base_url, PARAMS, get_user_agent())

    if 'status_code' in list(lexeme_senses_data.keys()):
        return lexeme_senses_data

    image = None
    if len(lexeme_senses_data['entities'][lexeme_id]['senses']) > 0:
        if 'P18' in lexeme_senses_data['entities'][lexeme_id]['senses'][0]['claims']:
            image = lexeme_senses_data['entities'][lexeme_id]['senses'][0]['claims']['P18']

    glosses_data = process_lexeme_sense_data(lexeme_senses_data['entities'][lexeme_id],
                                             src_lang, lang_1, lang_2, image)
    return glosses_data


def get_lexeme_forms_audio(search_term, lexeme_id, src_lang, lang_1, lang_2):
    PARAMS = {
        'action': 'wbgetentities',
        'format': 'json',
        'languages': src_lang,
        'strictlanguage': True,
        'ids': lexeme_id
    }

    lexeme_data = make_api_request(base_url, PARAMS, get_user_agent())

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


def describe_new_lexeme(description_data, username, auth_obj):
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
    for trans_data in description_data:
        return add_gloss_to_lexeme_sense(trans_data['lexeme_id'],
                                            trans_data['language'],
                                            trans_data['value'], username,
                                            csrf_token, auth, result_object)
    return {
        'error': 'No edit was made please check the data',
        'status_code': 503
    }


def add_gloss_to_lexeme_sense(lexeme_id, gloss_language, gloss_value,
                              username, csrf_token, auth, result_obj):
    """
    Adds a new gloss to an existing lexeme sense in Wikidata.

    This function correctly implements the logic for editing a lexeme.
    Adding a gloss is an *edit* to an existing lexeme, not the creation of a new one.
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
        'token': csrf_token,
        'baserevid': base_revid,
        'format': 'json'
    }

    try:
        # Step 5: Make the API call to edit the entity
        response = requests.post(base_url, data=post_params, auth=auth, headers=get_user_agent()).json()
        
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

        if 'upload' in upload_response.json():
            if 'warnings' in upload_response.json()['upload']:
                if 'duplicate' in upload_response.json()['upload']['warnings']:
                    file_name = upload_response.json()['upload']['warnings']['duplicate'][0]

        params = {}
        params['format'] = 'json'
        params['token'] = csrf_token
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
            claim_response = requests.post(base_url, data=params,
                                           auth=api_auth_token,
                                           headers=get_user_agent())
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


def add_translation_to_lexeme(username, auth_object, data):
    """
    Adds a translation to a lexeme senses in Wikidata.
    Parameters:
        username (str): The username of the person creating the lexeme
        auth_object (dict): The authentication object containing access tokens
        data (dict): The translation data containing:
                     - is_new (bool): Whether it's a new lexeme
                     - translation_language (str): The language code of the translation
                     - value (str): The value of the translation
                     - categoryId (int): The ID of the lexical category
                     - base_lexeme (str): The ID of the base lexeme to add the translation to
                     - translation_sense_id (str): The ID of the sense to which the translation is added
    Returns:
        dict: A dictionary containing the results of the operation
    """
    csrf_token, api_auth = generate_csrf_token(base_url,
                                               consumer_key,
                                               consumer_secret,
                                               auth_object['access_token'],
                                               auth_object['access_secret'])
    result_object = {}
    lastrev_id = None
    if bool(data['is_new']) is True:
    # New Lexeme needs to be created then returned
        _, _, lqid = get_language_qid(data['translation_language'])

        lexeme_entry = {
            'lemmas': {
                data['translation_language']: {
                    'language': data['translation_language'],
                    'value': data['value']
                }
            },
            'lexicalCategory': str(data['categoryId']),
            'language': lqid
        }

        data = {}
        data['action'] = 'wbeditentity'
        data['new'] = 'lexeme'

        data['token'] = csrf_token
        data['format'] = 'json'
        data['data'] = json.dumps(lexeme_entry)

        response = requests.post(base_url, data=data, auth=api_auth, headers=get_user_agent()).json()

        if 'error' in response:
            return {
                'info': 'Unable to edit. Please check credentials',
                'status_code': 503
            }
        lastrev_id = response['entity']['lastrevid']
        result_object[response['entity']['id']] = lastrev_id

    # Add the translation statement in either cases
    if lastrev_id or bool(data['is_new']) is False:
        
        value = {
            'entity-type': 'sense',
            'id': data['translation_sense_id']
        }
        params = {
            'format': 'json',
            'token': csrf_token,
            'action': 'wbcreateclaim',
            'entity': data['base_lexeme'],
            'property': 'P5972',
            'snaktype': 'value',
            'value': json.dumps(value)
        }

        try:
            claim_response = requests.post(base_url, data=params, auth=api_auth, headers=get_user_agent())
        except Exception as e:
            return {
                'error': 'Something went wrong!',
                'status_code': 401
            }

        if 'error' in claim_response.json().keys():
            return {
                'error': str(claim_response.json()['error']['code']
                            .capitalize() + ': ' + claim_response.json()['error']['info']
                            .capitalize())
            }

        results = []
        revision_id = claim_response.json().get('pageinfo').get('lastrevid', None)
        results.append({
            'lexeme_id': data['base_lexeme'].split('-')[0],
            'revisionid': revision_id
        })

        # Record contribution on tool
        contribution = ContributionModel(wd_item=data['base_lexeme'],
                                            username=username,
                                            lang_code=data['translation_language'],
                                            edit_type='translation',
                                            data=data['base_lexeme'] + '- P5927 -' + \
                                                data['translation_sense_id'] ,
                                            date=datetime.datetime.now())
        db.session.add(contribution)
        db.session.commit()

        return {'results': results}


def get_auth_object(consumer_key, consumer_secret, decoded_token):
    return {
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
        "access_token": decoded_token.get('access_token')['key'],
        "access_secret": decoded_token.get('access_token')['secret'],
    }


def validate_description_request_body(request_body, schema):
    try:
        validate(instance=request_body, schema=schema)
        return True
    except ValidationError as e:
        print(f"Validation error: {e.message}")
        return False


def check_exact_match_in_url(word, url):
    """
    Checks if a word is an exact match for the filename (minus the extension) in a URL.
    """
    decoded_url = urllib.parse.unquote(url)
    match = re.search(r'/([^/]+)\.[^/.]+$', decoded_url)
    if match:
        filename = match.group(1)
        filename_stripped = re.sub(r'^[a-zA-Z]{2,}-\w{2,}-|^[a-zA-Z]{2}-', '', filename)
        if re.fullmatch(word, filename_stripped, re.IGNORECASE):
            return True
    return False


def get_lexeme_translations(lexeme_id, src_lang, lang_1, lang_2):
    PARAMS = {
        'action': 'wbgetentities',
        'format': 'json',
        'languages': src_lang,
        'ids': lexeme_id
    }
    result = make_api_request(base_url, PARAMS, get_user_agent())
    if 'status_code' in list(result.keys()):
        return result

    lexeme_data = result.get('entities', {}).get(lexeme_id)
    matching_sense =  next((sense for sense in lexeme_data.get('senses', [])
                 if sense.get('glosses', {}).get(src_lang)), None)
    claims = matching_sense.get('claims', {}) if matching_sense else {}

    ids = None
    if 'P5972' in claims:
        ids = [entry['mainsnak']['datavalue']['value']['id'] for \
               entry in claims['P5972']]

    translation_data = get_multiple_lexemes_data(ids, src_lang,
                                                 lang_1, lang_2,
                                                 matching_sense['id'])
    return translation_data


def get_multiple_lexemes_data(lexemes_ids, src_lang,
                              lang_1, lang_2, matching_sense):
    final_results = []
    if lexemes_ids is None:
        for lang in [src_lang, lang_1, lang_2]:
            final_results.append({
                'base_lexeme': matching_sense,
                'lexeme_id': None,
                'trans_sense_id': None,
                'trans_language': lang,
                'value': None
            })
        return final_results

    PARAMS = {
        'action': 'wbgetentities',
        'format': 'json',
        'languages': ','.join([src_lang, lang_1, lang_2]),
        'ids': '|'.join([id.split('-')[0] for id in lexemes_ids])
    }

    result = make_api_request(base_url, PARAMS, get_user_agent())
    for lang in [src_lang, lang_1, lang_2]:
        match_struc = {}
        for id in lexemes_ids:
            lexeme_id = id.split('-')[0]
            lemmas = result['entities'][lexeme_id]['lemmas']
            if lang in lemmas.keys():
                match_struc['base_lexeme'] = matching_sense
                match_struc['trans_lexeme_id'] = lexeme_id
                match_struc['trans_sense_id'] = id
                match_struc['trans_language'] = lang
                match_struc['value'] = lemmas[lang]['value']
                final_results.append(match_struc)
                break
            else:
                final_results.append({
                    'base_lexeme': matching_sense,
                    'lexeme_id': None,
                    'trans_sense_id': None,
                    'trans_language': lang,
                    'value': None
                })

    return remove_duplicates_with_priority(final_results)


def remove_duplicates_with_priority(data):
    """
    Removes duplicate dictionaries from a list based on 'language',
    prioritizing entries where 'value' is not None.

    Args:
        data (list): A list of dictionaries with 'id', 'language', and 'value' keys.

    Returns:
        list: A new list with duplicate entries removed.
    """
    unique_entries = {}
    for item in data:
        key = (item['trans_language'])

        # Add the item if the key is new or if the current item has a value
        # and the stored one does not.
        if key not in unique_entries or (item['value'] is not None and unique_entries[key]['value'] is None):
            unique_entries[key] = item

    return list(unique_entries.values())
