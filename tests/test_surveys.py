import json
import random
import requests
import pytest
import pandas as pd

base_url="https://static.94.87.140.128.clients.your-server.de/wbapi/"
#base_url = 'http://localhost:8000/'

def whodas():
    with open('../icf_struct/whodas12_de.json') as fp:
        return json.load(fp)

def icf():
    with open('../icf_struct/icf_codes3.json') as fp:
        return json.load(fp)

@pytest.fixture(scope='module')
def load_users(request):
    df = pd.read_pickle('users.pkl')
    return df

def gen_art_survey(number_false_links=5,false_quote = 0.2):
    """
    Generates arteficial survey data
    :param number_false_links: how many additional faky links are provided to each whodas item
    :param false_quote: the quote of false answers
    :return: dataset with answers
    """
    s_data={}
    all_links = [k for k in icf().keys() if len(k) == 4]
    for k,v in whodas().items():
        true_links = v['l'].split(',')
        number_true_links=len(true_links)
        whodas_item={}
        l2 = all_links
        for l in true_links:
            if l in l2:
                l2.remove(l)
        false_links = random.sample(l2,k=number_false_links)
        #set correct answers
        for l in true_links:
            if len(l)>2:
                whodas_item[l]={
                        "belongs": True,
                        "selected": True,
                        "deselected": False
                    }
            else:
                true_links.remove(l)
                number_true_links-=1
        for l in false_links:
            whodas_item[l]={
                    "belongs": False,
                    "selected": False,
                    "deselected": True
                }
        # now flip for random elements to generate false answers
        flip_links = random.sample([*false_links,*true_links],k=int(false_quote*(number_true_links+number_false_links)))
        for l in flip_links:
            whodas_item[l]["selected"]= not whodas_item[l]['selected']
            whodas_item[l]["deselected"]= not whodas_item[l]['deselected']
        s_data[k]=whodas_item
    return s_data

def send_survey(url,token,false_quote):
    survey=gen_art_survey(false_quote=false_quote)
    response = requests.post(url, headers={'authorization': 'Bearer ' + token},
                             json={'type': 'WHODAS_ICF', 'data': survey})
    status = response.status_code
    if ((status == 200) | (status == 201)):
        score = json.loads(response.content)['score']
        return score
    else:
        print('Error during upload, Statuscode: '+str(status))
        return -1

@pytest.fixture(scope='module')
def post_survey(load_users, request):
    base_url = getattr(request.module, "base_url", 'http://localhost:8000/')
    df = load_users
    df['false_quote']=df.apply(lambda x: random.random(),axis=1)
    df['score']=df.apply(lambda x: send_survey(base_url + 'datastore/surveys/', x['token'], x['false_quote']), axis=1)
    return df



class TestSurvey:
    def test_random_survey(self, post_survey):
        """
        This test generates surveys with a random error rate. It checks that the recognized error rate stays below 10
        :param post_survey:
        :return:
        """
        df = post_survey
        if df['score'].apply(lambda x: x<0).any():
            assert False
        else:
            df['planned_score']=df.apply(lambda x: 100-(100*x['false_quote']), axis=1)
            df['error']=df['score']-df['planned_score']
            print('Errors: '+str(df['error'].tolist()))
            assert df['error'].apply(lambda x: abs(x)<10).all()

