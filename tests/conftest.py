import json
from random import randint

import pytest
import requests
import pandas as pd


CLIENT_ID = "11ypSpQrEcxAutnbPmuhJuDnYBzle1hcByyfrH5N"
CLIENT_SECRET = "zfp1RoZADyhynxaRpridJoVzh6bwgoqHUcA2NF6F0LF8CL7Ky8p2xEONqf48fLfQSGhfT54eK4f0PTNawkbAHiH0ptliBtauAXowmOfmIQGYXZz3yJ4HWMVxJfqzJ5Mx"

@pytest.fixture(scope='class')
def user_account(request):
    """
    tries to register a new user
    :return: user token and user data from name_generator
    """
    user_data=[]
    base_url = getattr(request.module, "base_url", 'http://localhost:8000/')
    def _user_account(data):
        response = requests.post(base_url + 'register/', data=data)
        d=json.loads(response.content)
        assert response.status_code==200
        if response.status_code==200:
            token = d['access_token']
            username = d['username']
            record= {'token':token,'username':username, **data}
            user_data.append(record)
            return record, response.status_code

    yield _user_account
    KEEP_USERS=getattr(request.module,'KEEP_USERS',False)
    if not KEEP_USERS:
        for d in user_data:
            requests.delete(base_url + 'users/' + d['username'] + '/', headers={'authorization': 'Bearer ' + d['token']})


@pytest.fixture(scope='class')
def valid_users(user_account, request):
    users=[]
    NUMBER_OF_USERS = getattr(request.module, "NUMBER_OF_USERS", 3)
    usertype = getattr(request.module,'USERTYPE','survey')
    base_url = getattr(request.module, "base_url", 'http://localhost:8000/')
    for n in register_request_generator(n=NUMBER_OF_USERS, type=usertype):
        user,status=user_account(n)
        assert status==200
        checktoken(user['token'], base_url)
        print('User of type ',usertype,' created.  Username: ',user['username'])
        users.append(user)

    KEEP_USERS = getattr(request.module, 'KEEP_USERS', False)
    if KEEP_USERS:
        df = pd.DataFrame(users)
        df.to_pickle('users.pkl')
        df.drop(columns=['client_id', 'client_secret', 'grant_type', 'scope']).to_json('users.json',
                                                                                   orient='records')
    return users

def checktoken(token, base_url):
    response=requests.get(base_url+'userinfo/', headers={'authorization': 'Bearer ' + token})
    assert response.status_code==200


def register_request_generator(n=1, type='survey'):
    for i in range(n):
        if (type=='survey'):
            password='password'
        if (type=='patient'):
            password='12.12.2000'
        data = {'client_id':CLIENT_ID,'client_secret':CLIENT_SECRET,'grant_type':'password','scope':'write',
                'password': password, 'testuser':''}
        yield data

