from unittest.mock import MagicMock, patch

from flask import Response

from nose.tools import assert_equal, assert_true, assert_is_not_none, assert_is_instance
from parameterized import parameterized

from app.components.identifier_objects import Doi, Identifier404


with open('app/test/DOI/dois.txt', 'r') as gtex:
    full_dois = gtex.read().splitlines()
    gtex_examples = [ doi.replace('https://doi.org/','') for doi in full_dois]



@parameterized(gtex_examples)
def test_fetch_gtex(identifier):
    doi = Doi(guid=identifier)

    html_response = doi.fetch('text/html')

    assert_is_not_none(html_response)
    assert_equal(html_response.status_code, 200)
    assert_is_instance(html_response, Response)

    json_response = doi.fetch('application/json')

    assert_is_not_none(json_response)
    assert_equal(json_response.status_code, 200)
    assert_is_instance(json_response, Response)



