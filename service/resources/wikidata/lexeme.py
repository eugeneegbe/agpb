from flask import abort, jsonify
from flask_restful import (Resource, reqparse,
                           fields, marshal_with)

from .utils import (lexemes_search, get_lexeme_sense_glosses,
                    get_lexeme_forms_audio, create_new_lexeme)


# Used for validateion
lexeme_args = reqparse.RequestParser()
form_audio_args = reqparse.RequestParser()
lexeme_create_args = reqparse.RequestParser()

lexeme_args.add_argument('search', type=str, help="Please provide a search term")
lexeme_args.add_argument('src_lang', type=str, help="Source language is required")
lexeme_args.add_argument('id', type=str, help="Lexeme ID is required")
lexeme_args.add_argument('property', type=str, help="Provide a property to fetch")
lexeme_args.add_argument('lang_1', type=str, help="Provide the first language")
lexeme_args.add_argument('lang_2', type=str, help="Provide the second language")
lexeme_args.add_argument('ismatch', type=str, help="Match lexeme in language")

lexeme_create_args.add_argument('value', type=str, help="Lexeme value text")
lexeme_create_args.add_argument('token', type=str, help="User csrf toeken")
lexeme_create_args.add_argument('username', type=str, help="User Name of editor")
lexeme_create_args.add_argument('language', type=str, help="Lexeme language")
lexeme_create_args.add_argument('categoryId', type=str, help="Lexeme Category")


form_audio_args.add_argument('search_term', type=str, help="Provide a search term")
form_audio_args.add_argument('id', type=str, help="Lexeme ID is required")
form_audio_args.add_argument('src_lang', type=str, help="Source language is required")
form_audio_args.add_argument('lang_1', type=str, help="Provide the first language")
form_audio_args.add_argument('lang_2', type=str, help="Provide the second language")


lexeme_response_fields = {
    'lexeme': fields.Nested({
        'id': fields.String,
        'lexicalCategoryId': fields.String,
        'lexicalCategoryLabel': fields.String,
        'image': fields.String,
    }),
    'gloss': fields.List(fields.Nested({
        'language': fields.String,
        'value': fields.String,
        'audio': fields.String,
        'formId': fields.String,
    })),
}

# Used for serialization
lexemeSearcFields = {
    'id': fields.String,
    'label': fields.String,
    'language': fields.String,
    'description': fields.String,
}


lexemeCreateFields = {
    'revisionid': fields.Integer
}


class LexemesGet(Resource):
    @marshal_with(lexemeSearcFields)
    def post(self):
        args = lexeme_args.parse_args()
        # TODO: Add arguments check
        if not args['search'] or not args['src_lang']:
            abort(400, f'Please provide required parameters {str(list(args.keys()))}')

        lexemes = lexemes_search(args['search'], args['src_lang'],
                                 ismatch=int(args['ismatch']))
        if type(lexemes) is not list:
            abort(lexemes['status_code'], lexemes)

        return lexemes, 200


class LexemesCreate(Resource):
    def post(self):
        args = lexeme_create_args.parse_args()

        # TODO: Add arguments check
        if args['language'] is None or args['value'] is None or \
           args['categoryId'] is None or \
           args['token'] is None or args['username'] is None:
            abort(400, f'Please provide required parameters {str(list(args.keys()))}')

        result = create_new_lexeme(args['language'], args['value'],
                                   args['categoryId'], args['username'], args['token'])

        if result['status_code'] == 503:
            return result, result['status_code']

        return result, 200


class LexemeGlossesGet(Resource):
    @marshal_with(lexeme_response_fields)
    def post(self, id):
        args = lexeme_args.parse_args()
        if not id or not args['lang_1'] or not args['lang_2'] or not args['src_lang']:
            abort(400, f'Please provide required parameters {str(list(args.keys()))}')

        lexeme_glosses = get_lexeme_sense_glosses(args['id'], args['src_lang'],
                                                  args['lang_1'], args['lang_2'])

        if type(lexeme_glosses) is not list:
            abort(lexeme_glosses['status_code'], lexeme_glosses)

        return lexeme_glosses, 200


class LexemeFormAudioGet(Resource):
    def post(self, id):
        args = form_audio_args.parse_args()
        if args['search_term'] is None or args['lang_1'] is None or \
           args['lang_2'] is None or args['id'] is None or \
           args['src_lang'] is None or id is None:
            abort(400, f'Check required title parameters {str(list(args.keys()))}')

        lexeme_audios = get_lexeme_forms_audio(args['search_term'], args['id'],
                                               args['src_lang'], args['lang_1'],
                                               args['lang_2'])
        if type(lexeme_audios) is not list:
            abort(lexeme_audios['status_code'], lexeme_audios)

        return lexeme_audios
