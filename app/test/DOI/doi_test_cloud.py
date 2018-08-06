import requests
import re 
import json

from nose.tools import assert_equal, assert_true
from parameterized import parameterized

local_url = 'https://ors.datacite.org/doi:/'
access = '?code=AgVVJn6p3Nk0pXMgjzxkgO40oPl886k2djpjxxO9qd92EayjWNtbCrEoXQW6XDkPMBl2w14x0Q4MmvslxY1a4sV4ErsrD9dFK50M'


with open('dois.txt', 'r') as doi_list:
    doi_urls = doi_list.read().splitlines()
    dois = [ re.sub('https://doi.org/','', doi) for doi in doi_urls]


required_keys = ['@id', '@type', 'identifier', 'name', 'author','datePublished']

@parameterized(dois)
def test_get_json(doi):
    json_response = requests.get(
            url = local_url+doi+access,
            headers = {'Accept': 'application/ld+json'}
            )

    assert_equal(json_response.status_code, 200)

    json_doi = json.loads(json_response.content.decode('utf-8'))

    # assert all required keys are in the doi metadata
    assert_true(all([key in json_doi.keys() for key in required_keys]))

    # assert all required keys are not none
    assert_true(all([json_doi.get(key) is not None for key in required_keys]))
  

    # assert_true(json_doi.get('contentUrl') is not None)



@parameterized(dois)
def test_get_html(doi):
    html_response = requests.get(
            url = local_url+doi+access
            )

    assert_equal(html_response.status_code, 200)
    assert_true(html_response.content is not None)

