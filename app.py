from flask import redirect, session, render_template
from service import app, api, prefix
from swagger.swaggerConfig import SwaggerConfig
from service.resources.users.users import (UsersGet, UserPost, UserGet,
                                           UserPatch, UserDelete)
from service.resources.contributions.contribution import (ContributionsGet,
                                                          ContributionPost,
                                                          ContributionGet,
                                                          ContributionPatch,
                                                          ContributionDelete)
from service.resources.languages.languages import LanguageGet, LanguagesGet
from service.resources.wikidata.lexeme import (LexemesGet, LexemesTranslate,
                                               LexemeGlossesGet,
                                               LexemeFormsAudiosLackGet,
                                               LexemeAudioAdd,
                                               LexemesMissingAudioGet)

from service.resources.commons.commons import CommonsFIleUrLPost
from service.resources.auth.auth import AuthGet, AuthCallBackPost, AuthLogout

api.add_resource(SwaggerConfig, '/swagger-config')

api.add_resource(AuthGet, '/auth/login')
api.add_resource(AuthCallBackPost, '/oauth-callback')
api.add_resource(AuthLogout, '/auth/logout')

api.add_resource(UsersGet, '/users/')
api.add_resource(UserPost, '/users/')
api.add_resource(UserGet, '/users/<int:id>')
api.add_resource(UserPatch, '/users/<int:id>')
api.add_resource(UserDelete, '/users/<int:id>')

api.add_resource(ContributionsGet, '/contributions/')
api.add_resource(ContributionPost, '/contributions/')
api.add_resource(ContributionGet, '/contribution/<int:id>')
api.add_resource(ContributionPatch, '/contribution/<int:id>')
api.add_resource(ContributionDelete, '/contribution/<int:id>')

api.add_resource(LanguagesGet, '/languages/')
api.add_resource(LanguageGet, '/languages/<string:lang_code>')

api.add_resource(LexemesGet, '/lexemes/')
api.add_resource(LexemesTranslate, '/lexemes/translations/add')
api.add_resource(LexemeGlossesGet, '/lexemes/<string:id>')
api.add_resource(LexemeFormsAudiosLackGet, '/lexeme/language/forms')
api.add_resource(LexemeAudioAdd, '/lexeme/audio/add')
api.add_resource(LexemesMissingAudioGet, '/lexemes/missing/audio')


api.add_resource(CommonsFIleUrLPost, '/file/url/<string:titles>')


@app.route('/')
def redirect_to_prefix():
    return redirect(prefix)


if __name__ == '__main__':
    app.run(debug=True)
