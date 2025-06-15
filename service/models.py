from datetime import datetime
from service import db
from flask_login import UserMixin
from service import login_manager


@login_manager.user_loader
def load_user(id):
    return UserModel.objects(pk=id).first()


class UserModel(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    pref_langs = db.Column(db.String(25), nullable=False)
    temp_token = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"User(username= {self.username}, pref_langs={self.pre_langs})"


class ContributionModel(db.Model):
    __tablename__ = 'contributions'
    id = db.Column(db.Integer, primary_key=True, index=True)
    wd_item = db.Column(db.String(150))
    username = db.Column(db.String(80))
    lang_code = db.Column(db.String(25))
    edit_type = db.Column(db.String(150))
    data = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False,
                     default=datetime.now().strftime('%Y-%m-%d'))

    def __repr__(self):
        return "Contribution({}, {}, {}, {})".format(
               self.wd_item,
               self.username,
               self.lang_code,
               self.date)
