from flask import abort, request
from flask_login import current_user
import jwt
from service import db
from flask_restful import (Resource, reqparse,
                           fields, marshal_with)
from service.require_token import token_required
from .utils import (lexemes_search, get_lexeme_sense_glosses,
                    translate_new_lexeme, get_lexemes_lacking_audio,
                    add_audio_to_lexeme, get_auth_object,
                    add_gloss_to_lexeme_sense, validate_translation_request_body)
from common import consumer_key, consumer_secret, prod_fe_url


# Used for validateion
lexeme_args = reqparse.RequestParser()
form_audio_args = reqparse.RequestParser()
lexeme_translate_args = reqparse.RequestParser()
lex_form_without_audio_args = reqparse.RequestParser()
lex_audio_add_args = reqparse.RequestParser()
lexeme_gloss_add_args = reqparse.RequestParser()
lexeme_missing_audio_args = reqparse.RequestParser()
lexeme_gloss_args = reqparse.RequestParser()

lexeme_gloss_args.add_argument('src_lang', type=str, help="Source language is required")
lexeme_gloss_args.add_argument('id', type=str, help="Lexeme ID is required")
lexeme_gloss_args.add_argument('lang_1', type=str, help="Provide the first language")
lexeme_gloss_args.add_argument('lang_2', type=str, help="Provide the second language")

lexeme_args.add_argument('search', type=str, help="Please provide a search term")
lexeme_args.add_argument('src_lang', type=str, help="Source language is required")
lexeme_args.add_argument('id', type=str, help="Lexeme ID is required")
lexeme_args.add_argument('property', type=str, help="Provide a property to fetch")
lexeme_args.add_argument('lang_1', type=str, help="Provide the first language")
lexeme_args.add_argument('lang_2', type=str, help="Provide the second language")
lexeme_args.add_argument('ismatch', type=str, help="Match lexeme in language")

translation_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "translation_language": {
                "type": "string",
                "example": "ig"
            },
            "translation_value": {
                "type": "string",
                "example": "mother"
            },
            "categoryId": {
                "type": "string",
                "example": "Q1084"
            },
            "lexeme_id": {
                "type": "string",
                "example": "L3625"
            },
            "is_new": {
                "type": "boolean",
                "example": True
            },
            "lexeme_sense_id": {
                "type": "string",
                "example": "L3625-S1"
            }
        },
        "required": ["translation_language", "translation_value", "categoryId", "lexeme_id", "is_new", "lexeme_sense_id"]
    }
}

add_audio_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "lang_wdqid": {
                "type": "string",
                "example": "Q188"
            },
            "lang_label": {
                "type": "string",
                "example": "German"
            },
            "formid": {
                "type": "string",
                "example": "L3625-F1"
            },
            "filename": {
                "type": "string",
                "example": "L3625-de-Mutter.ogg"
            },
            "file_content": {
                "type": "string",
                "example": "T2dnUwA"
            }
        },
        "required": ["lang_wdqid", "lang_label", "formid", "file_content"]
    }
}

form_audio_args.add_argument('search_term', type=str, help="Provide a search term")
form_audio_args.add_argument('id', type=str, help="Lexeme ID is required")
form_audio_args.add_argument('src_lang', type=str, help="Source language is required")
form_audio_args.add_argument('lang_1', type=str, help="Provide the first language")
form_audio_args.add_argument('lang_2', type=str, help="Provide the second language")

lex_form_without_audio_args.add_argument('lang_wdqid', type=str, help="Wikidata language Qid")
lex_form_without_audio_args.add_argument('limit', type=int, help="Query result limit")
lex_form_without_audio_args.add_argument('offset', type=int, help="Query result offset for pagination")

lex_audio_add_args.add_argument('lang_wdqid', type=str, help="Wikidata language Qid")
lex_audio_add_args.add_argument('lang_label', type=str, help="Language label")
lex_audio_add_args.add_argument('file_content', type=str, help="Audio data in bytes")
lex_audio_add_args.add_argument('formid', type=str, help="Lexeme Form Id")
lex_audio_add_args.add_argument('filename', type=str, help="Composed file name f the uploaded file")

lexeme_gloss_add_args.add_argument('lexeme_id', type=str, help="Lexeme ID is required")
lexeme_gloss_add_args.add_argument('sense_id', type=str, help="Sense ID is required")
lexeme_gloss_add_args.add_argument('gloss_language', type=str, help="Gloss language is required")
lexeme_gloss_add_args.add_argument('gloss_value', type=str, help="Gloss value is required")
lexeme_gloss_add_args.add_argument('username', type=str, help="User Name of editor")

lexeme_missing_audio_args.add_argument('lang_wdqid', type=str, help="Wikidata language Qid")
lexeme_missing_audio_args.add_argument('lang_code', type=str, help="The language code is required")
lexeme_missing_audio_args.add_argument('page_size', type=int, help="You may need to provide a page size")
lexeme_missing_audio_args.add_argument('page', type=int, help="You may need to provide a page number")


lexeme_response_fields = {
    'lexeme': fields.Nested({
        'id': fields.String,
        'lexicalCategoryId': fields.String,
        'lexicalCategoryLabel': fields.String,
        'image': fields.String,
    }),
    'glosses': fields.List(fields.Nested({
        'gloss': fields.Nested({
            'language': fields.String,
            'value': fields.String,
            'audio': fields.String,
            'formId': fields.String,
        }),
        'senseId': fields.String
    })),
}

# Used for serialization
lexemeSearcFields = {
    'id': fields.String,
    'label': fields.String,
    'language': fields.String,
    'description': fields.String,
}

LexemeGlossAddFields = {
    'revisionid': fields.Integer
}

lexemetranslateFields = {
    'revisionid': fields.Integer
}

LexemeAudioAddFields = {
    'results': fields.List(fields.Nested({
        'revisionid': fields.Integer,
        'lexeme_id': fields.String
    }))
}

lexeMissingAudioFields = {
    "lexeme_id": fields.String,
    "sense_id": fields.String,
    "lemma": fields.String,
    "categoryId": fields.String,
    "categoryLabel": fields.String,
    "formId": fields.String
}

lexemeNoAudioFields = {
    'forms': fields.List(fields.Nested({
        'lemma': fields.String,
        'lexeme': fields.String,
        'formid': fields.String
    }))
}


class LexemesGet(Resource):
    @marshal_with(lexemeSearcFields)
    def post(self):
        args = lexeme_args.parse_args()
        # TODO: Add arguments check
        if args['search'] is None or args['src_lang'] is None:
            abort(400, f'Please provide required parameters {str(list(args.keys()))}')

        lexemes = lexemes_search(args['search'], args['src_lang'],
                                 ismatch=int(args['ismatch']))
        if type(lexemes) is not list:
            abort(lexemes['status_code'], lexemes)

        return lexemes, 200


class LexemesTranslate(Resource):
    @token_required
    def post(self, data):
        if request.base_url != prod_fe_url:
            abort(403, 'Invalid request URL. Please contribute from production.')

        request_body = request.get_json()
        if not request_body:
            abort(400, 'Request body is empty')

        if not validate_translation_request_body(request_body, translation_schema):
            abort(400, 'Invalid request body')

        # get request header token_required info
        token = request.headers.get('x-access-tokens')

        decoded_token = jwt.decode(token, consumer_secret, algorithms=["HS256"])
        if 'access_token' not in decoded_token:
            return {
                'message': 'Access token is missing in the decoded token'
            }, 400
        auth_obj = get_auth_object(consumer_key, consumer_secret, decoded_token)
        result = translate_new_lexeme(request_body, current_user.username, auth_obj)

        if 'status_code' in result and result['status_code'] == 503:
            return result, result['status_code']

        return result, 200


class LexemeGlossesGet(Resource):
    @marshal_with(lexeme_response_fields)
    def post(self, id):
        print('were are here')
        args = lexeme_gloss_args.parse_args()
        if args['lang_1'] == args['lang_2']:
            abort(401, f'Target languages should not be the same')
        if id is None or (args['lang_1'] is None and args['lang_2'] is None) or \
            args['src_lang'] is None:
            keys = ', '.join(list(args.keys()))
            abort(400, f'Please provide required parameters: {keys}')

        lexeme_glosses = get_lexeme_sense_glosses(args['id'], args['src_lang'],
                                                  args['lang_1'], args['lang_2'])

        if 'error' in lexeme_glosses:
            abort(lexeme_glosses['status_code'], lexeme_glosses)

        return lexeme_glosses, 200


class LexemeFormsAudiosLackGet(Resource):
    @marshal_with(lexemeNoAudioFields)
    def post(self):
        args = lex_form_without_audio_args.parse_args()
        if args['lang_wdqid'] is None or args['limit'] is None or args['offset'] is None:
            abort(400, f'Please provide required parameters {str(list(args.keys()))}')

        results = get_lexemes_lacking_audio(args['lang_wdqid'], args['limit'],
                                            args['offset'])

        if 'error' in results:
            abort(results['status_code'], results)

        return results, 200


class LexemeAudioAdd(Resource):
    @marshal_with(LexemeAudioAddFields)
    def post(self):
        if request.base_url != prod_fe_url:
            abort(403, 'Invalid request URL. Please contribute from production.')

        request_body = request.get_json()
        if not request_body:
            abort(400, 'Request body is empty')

        if not validate_translation_request_body(request_body, add_audio_schema):
            abort(400, 'Invalid request body')

        # get request header token_required info
        token = request.headers.get('x-access-tokens')

        try:
            decoded_token = jwt.decode(token, consumer_secret, algorithms=["HS256"])
            if 'access_token' not in decoded_token:
                return {
                    'message': 'Access token is missing in the decoded token'
                }, 400
            
        except Exception as e:
            abort(401, 'User may not be authenticated')

        auth_obj = get_auth_object(consumer_key, consumer_secret, decoded_token)
        results = add_audio_to_lexeme(current_user.username, auth_obj, request_body)

        if 'error' in results:
            abort(503, results)

        return results, 200


class LexemeGlossAdd(Resource):
    @token_required
    @marshal_with(LexemeGlossAddFields)
    def post(self, data):
        args = lexeme_gloss_add_args.parse_args()

        if args['lexeme_id'] is None or args['sense_id'] is None or \
           args['gloss_language'] is None or args['gloss_value'] is None:
            abort(400, f'Please provide required parameters {str(list(args.keys()))}')

        # get request header token_required info
        token = request.headers.get('x-access-tokens')

        decoded_token = jwt.decode(token, consumer_secret, algorithms=["HS256"])
        if 'access_token' not in decoded_token:
            return {
                'message': 'Access token is missing in the decoded token'
            }, 400

        auth_obj = get_auth_object(consumer_key, consumer_secret, decoded_token)
        results = add_gloss_to_lexeme_sense(args['lexeme_id'], args['sense_id'],
                                            args['gloss_language'],
                                            args['gloss_value'], auth_obj)
        if 'error' in results:
            abort(results['status_code'], results)
        return results, 200


class LexemesMissingAudioGet(Resource):
    @marshal_with(lexeMissingAudioFields)
    def post(self):
        args = lexeme_missing_audio_args.parse_args()
        # TODO: Add arguments check
        if args['lang_wdqid'] is None or args['lang_code'] is None:
            abort(400, f'Please provide required parameters {str(list(args.keys()))}')

        results = get_lexemes_lacking_audio(args['lang_wdqid'], args['lang_code'],
                                            args['page_size'], args['page'])
        if 'error' in results:
            abort(results['status_code'], results)

        return results, 200
