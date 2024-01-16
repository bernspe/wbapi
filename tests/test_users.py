import random

import pytest
import pandas as pd
import requests
import json
from datauri import DataURI

import users
from geodata.funcs import generate_random_germany_locations
from users.models import User
from wbapi.settings import BASE_DIR

NUMBER_OF_USERS = 3
USERTYPE='survey'
KEEP_USERS=True

base_url="https://static.94.87.140.128.clients.your-server.de/wbapi/"
#base_url = 'http://localhost:8000/'
def svg_encode(svg):
    # Ref: https://bl.ocks.org/jennyknuth/222825e315d45a738ed9d6e04c7a88d0
    # Encode an SVG string so it can be embedded into a data URL.
    enc_chars = '"%#{}<>' # Encode these to %hex
    enc_chars_maybe = '&|[]^`;?:@=' # Add to enc_chars on exception
    svg_enc = ''
    # Translate character by character
    for c in str(svg):
        if c in enc_chars:
            if c == '"':
                svg_enc += "'"
            else:
                svg_enc += '%' + format(ord(c), "x")
        else:
            svg_enc += c
    return ' '.join(svg_enc.split()) # Compact whitespace

def send_update_user(url,token, data):
    response = requests.patch(url, headers={'authorization': 'Bearer ' + token},
                             json=data)
    status = response.status_code
    return status

def generate_age_group():
    a = random.randint(0,len(User.AGE_GROUP_CHOICES)-1)
    return User.AGE_GROUP_CHOICES[a][0]

def generate_avatar():
    r = requests.get(
        'https://api.dicebear.com/7.x/lorelei/svg?seed=' + str(random.randint(1, 1000)) + '&glasses=variant01,variant02&glassesProbability=100')
    data = r.content
    data_s = str(DataURI.make(mimetype='image/svg+xml', charset='utf-8', base64=False, data=data))
    return data_s

@pytest.fixture(scope='module')
def load_users(request):
    df = pd.read_pickle('users.pkl')
    return df


@pytest.fixture(scope='module')
def update_user_sex(load_users, request):
    base_url = getattr(request.module, "base_url", 'http://localhost:8000/')
    df = load_users
    df['response_status']=df.apply(lambda x: send_update_user(base_url + 'users/'+x['username']+'/', x['token'],
                                                              {"sex": random.choice(['male','female'])}), axis=1)
    return df

@pytest.fixture(scope='module')
def update_user_agegroup(load_users, request):
    base_url = getattr(request.module, "base_url", 'http://localhost:8000/')
    df = load_users
    df['response_status']=df.apply(lambda x: send_update_user(base_url + 'users/'+x['username']+'/', x['token'],
                                                              {"age_group": generate_age_group()}), axis=1)
    return df

@pytest.fixture(scope='module')
def update_user_avatar(load_users, request):
    base_url = getattr(request.module, "base_url", 'http://localhost:8000/')
    df = load_users

    df['response_status']=df.apply(lambda x: send_update_user(base_url + 'users/'+x['username']+'/', x['token'],
                                                              {"avatar": {"svg":generate_avatar()}}), axis=1)
    return df

@pytest.fixture(scope='module')
def update_user_geolocation(load_users, request):
    base_url = getattr(request.module, "base_url", 'http://localhost:8000/')
    df = load_users
    lon,lat = generate_random_germany_locations(BASE_DIR,n=NUMBER_OF_USERS)
    df['lon']=pd.Series(lon)
    df['lat']=pd.Series(lat)
    df['response_status'] = df.apply(lambda x: send_update_user(base_url + 'users/' + x['username'] + '/', x['token'],
                                                                {"geolocation": {"longitude": str(x['lon']), "latitude": str(x['lat'])}}), axis=1)
    return df


class TestLogin:
    def test_register_users(self,valid_users):
        """
        Checks if the newly created users could be logged in
        :param valid_users:
        :return:
        """
        assert len(valid_users)==NUMBER_OF_USERS


    def test_update_sex_of_user(self, update_user_sex):
        df = update_user_sex
        if df['response_status'].apply(lambda x: ((x == 200) | (x == 201))).any():
            assert True
        else:
            assert False


    def test_update_age_group_of_user(self, update_user_agegroup):
        df = update_user_agegroup
        if df['response_status'].apply(lambda x: ((x == 200) | (x == 201))).any():
            assert True
        else:
            assert False

    def test_update_avatar_of_user(self, update_user_avatar):
        df = update_user_avatar
        if df['response_status'].apply(lambda x: ((x == 200) | (x == 201))).any():
            assert True
        else:
            assert False

    def test_update_geolocation_of_user(self, update_user_geolocation):
        df = update_user_geolocation
        if df['response_status'].apply(lambda x: ((x == 200) | (x == 201))).any():
            assert True
        else:
            assert False





