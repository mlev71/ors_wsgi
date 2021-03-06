from unittest.mock import MagicMock, patch

from flask import Response

from nose.tools import assert_equal, assert_true, assert_is_not_none, assert_is_instance
from parameterized import parameterized

from app.components.identifier_objects import Ark, Identifier404



with open('app/test/ARK/nihdc.txt', 'r') as nihdc:
    nihdc_examples = nihdc.read().splitlines()

with open('app/test/ARK/erc.txt', 'r') as erc:
    erc_examples = erc.read().splitlines()

with open('app/test/ARK/datacite.txt', 'r') as datacite:
    datacite_examples = datacite.read().splitlines()

with open('app/test/ARK/empty.txt', 'r') as empty:
    empty_examples = empty.read().splitlines()


all_examples = erc_examples + datacite_examples + nihdc_examples + empty_examples

@parameterized(all_examples)
def test_ark_get(identifier):
    ''' Get the Metadata Back from EZID
    '''
    ark = Ark(guid=identifier) 
    assert_is_not_none(ark)
    try:
        ark.fetch()
        assert_is_not_none(ark.anvl)
        #print('\n')
        #print(ark.anvl)

    except Identifier404 as err:
        json_response = err.json_response()
        response_data = err.response_message
        
        assert_is_not_none(json_response)
        assert_is_instance(json_reponse, Response)
        assert_equal(json_response.status, 404)
        
        assert_is_not_none(response_data)
        assert_is_instance(response_data, dict)
        assert_true(identifier in response_data.get('@id'))
        #print('\n')
        #print(response_data)


@parameterized(erc_examples)
def test_ark_dev(identifier):
    ark = Ark(guid=identifier)
    
    assert_is_not_none(ark)
    ark.fetch()


    json_ld, profile = ark.to_json_ld()

    assert_is_not_none(json_ld)
    assert_is_instance(json_ld, dict)
    
    assert_true(profile in [None, 'erc', 'NIHdc', 'dc', 'datacite'])




