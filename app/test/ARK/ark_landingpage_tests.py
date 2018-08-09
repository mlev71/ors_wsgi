from unittest.mock import MagicMock, patch

import requests
import json
import string
from bs4 import BeautifulSoup

from nose.tools import assert_equal, assert_true, assert_is_not_none, assert_is_instance, assert_dict_equal
from parameterized import parameterized

from app.components.identifier_objects import Ark, Identifier404

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

with open('app/test/ARK/nihdc.txt', 'r') as nihdc:
    nihdc_examples = nihdc.read().splitlines()

with open('app/test/ARK/erc.txt', 'r') as erc:
    erc_examples = erc.read().splitlines()

with open('app/test/ARK/datacite.txt', 'r') as datacite:
    datacite_examples = datacite.read().splitlines()

with open('app/test/ARK/empty.txt', 'r') as empty:
    empty_examples = empty.read().splitlines()


all_examples = erc_examples  + nihdc_examples + empty_examples  + datacite_examples

@parameterized(all_examples)
def test_landingpage_local(identifier):
    landing_page_request = requests.get(
            url='https://localhost/'+identifier,
            headers = {'Accept':'text/html'},
            verify = False
            )

    assert_true(landing_page_request.status_code == 200)
    assert_is_not_none(landing_page_request.content)

    json_request = requests.get(
            url='https://localhost/'+identifier,
            headers = {'Accept':'application/json'},
            verify = False
            )

    assert_true(json_request.status_code == 200) 
    assert_is_not_none(json_request.content)

    # read json in 
    json_ld = json.loads(json_request.content.decode('utf-8'))

    assert_is_not_none(json_ld)
    assert_true(isinstance(json_ld, dict))
    # parse html 
    html = landing_page_request.content.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    # find the embedded json-ld in the html header
    html_json_ld = json.loads(soup.head.script.string)
    assert_dict_equal(json_ld,html_json_ld)
        
    # assert that all the components on the page are equivalent to the json components
    
    identifier_metadata = soup.find(id='identifier_container')

    html_metadata = {}
    for row in identifier_metadata.table.find_all('tr'):
        key_elem = row.find(class_='metadataKey')
        value_elem = row.find(class_='metadataVal')
        if key_elem != None:
            key = key_elem.string
        else:
            key = None

        if value_elem != None:
            value = value_elem.string
        else:
            value = None


        if value is not None and key is not None:
            formatted_key = key.lower().replace(' ', '')
            html_metadata.update({formatted_key: value})
             
    
    for key,value in json_ld.items():
        formatted_key = key.lower().replace('@', '')
        if isinstance(value, dict):
            value = value.get('@value')

        if formatted_key in html_metadata.keys():
            assert_true(html_metadata.get(formatted_key).lower().replace(' ', '') == value.lower().replace(' ', ''))




        


