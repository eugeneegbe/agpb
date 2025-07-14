from flask import abort
from flask_restful import (Resource, reqparse,
                           fields, marshal_with)
from service.utils.languages import getLanguages

lang_args = reqparse.RequestParser()


lang_args.add_argument('lang_code', type=str, help="Please provide a language code")

languageFields = {
    'lang_code': fields.String,
    'lang_label': fields.String,
    'lang_wd_id': fields.String
}

SinglelanguageFields = {
    'lang_code': fields.String,
    'lang_label': fields.String,
    'lang_wd_id': fields.String
}


class LanguagesGet(Resource):
    @marshal_with(languageFields)
    def map_languages(self, data):
        lang_data = []
        for lang in data:
            lang_pair = {
                'lang_code': lang[0],
                'lang_label': lang[1],
                'lang_wd_id': lang[2]
            }
            lang_data.append(lang_pair)
        return lang_data

    def get(self):
        languages = self.map_languages(getLanguages())
        return languages


class LanguageGet(Resource):
    @marshal_with(SinglelanguageFields)
    def post(self, lang_code):
        args = lang_args.parse_args()

        if not args['lang_code']:
            abort(400, "Language not supported")
        lang_pair = []
        for language in getLanguages():
            if language[0] == args['lang_code']:
                lang_pair.append(list(language))

        lang_pair = list(lang_pair)
        if not lang_pair:
            abort(400, "Language not supported")

        return {
            'lang_code': lang_pair[0][0],
            'lang_label': lang_pair[0][1],
            'lang_wd_id': lang_pair[0][2]
        }, 200
