#!/usr/bin/env python3

# Author: Eugene Egbe
# Unit tests for the routes in the isa tool

import unittest
from service.resources.users.users import UsersGet, UserGet
from service import app, api

api.add_resource(UsersGet, '/users')
api.add_resource(UserGet, '/users/<int:id>')


class TestUser(unittest.TestCase):

    # setup and teardown #

    # executed prior to each test
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
        self.app = app.test_client()

    # executed after each test
    def tearDown(self):
        pass

    # tests #

    def test_get_users(self):
        response = self.app.get('/api/users', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_get_user(self):
        response = self.app.get('/api/users/1', follow_redirects=True)
        print('response', response.data)
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
