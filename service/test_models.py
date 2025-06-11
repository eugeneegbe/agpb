from datetime import datetime
from service import test_db


class UserModel(test_db.Model):
    __tablename__ = 'users'
    id = test_db.Column(test_db.Integer, primary_key=True)
    username = test_db.Column(test_db.String(80), unique=True, nullable=False)
    pref_langs = test_db.Column(test_db.String(25), nullable=False)

    def __repr__(self):
        return f"User(username= {self.username}, pref_langs= {self.pre_langs})"


class ContributionModel(test_db.Model):
    __tablename__ = 'contributions'
    id = test_db.Column(test_db.Integer, primary_key=True, index=True)
    wd_item = test_db.Column(test_db.String(150))
    username = test_db.Column(test_db.String(80))
    lang_code = test_db.Column(test_db.String(25))
    edit_type = test_db.Column(test_db.String(150))
    data = test_db.Column(test_db.Text)
    date = test_db.Column(test_db.Date, nullable=False,
                          default=datetime.now().strftime('%Y-%m-%d'))

    def __repr__(self):
        return "Contribution({}, {}, {}, {})".format(
               self.wd_item,
               self.username,
               self.lang_code,
               self.date)
