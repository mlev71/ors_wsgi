from unittest.mock import MagicMock, patch

from flask import Response

from nose.tools import assert_equal, assert_true, assert_is_not_none, assert_is_instance, assert_dict_equal
from parameterized import parameterized

from app.components.identifier_objects import Dataguid



examples = [
        # single file and checksums
        (
            {
            'form': 'object',
            'hashes': {'md5': '12345'},
            'urls': ['https://localhost/test.tsv'],
            'file_name': 'test.tsv',
            'size': 1000,
            'metadata': {}
                },

            {
            'identifier': [
                {'@type': 'PropertyValue', 'name': 'md5', 'value': '12345'}
                ],
            'contentSize': 1000,
            'contentUrl': ['https://localhost/test.tsv']

            }
            
        ),


        # multipule files and checksums
        (
            {
            'form': 'object',
            'hashes': {
                'md5': '12345',
                'sha-256': '1111',
                'etag': 'aaaa' 
                },
            'urls': [
                's3:/bucket/test.tsv',
                's3:/bucket/copy.tsv',
                's3:/bucket/backup.tsv'
                ],
            'file_name': 'test.tsv',
            'size': 1000,
            'metadata': {}
                },

            {
            'identifier': [
                {'@type': 'PropertyValue', 'name': 'md5', 'value': '12345'},
                {'@type': 'PropertyValue', 'name': 'sha-256', 'value': '1111'},
                {'@type': 'PropertyValue', 'name': 'etag', 'value': 'aaaa'}
                ],
            'contentSize': 1000,
            'contentUrl': [
                's3:/bucket/test.tsv',
                's3:/bucket/copy.tsv',
                's3:/bucket/backup.tsv'
                ]
            }
            
        ),

        # additional properties
        (
            {
            'form': 'object',
            'hashes': {'md5': '12345'},
            'urls': ['https://localhost/test.tsv'],
            'file_name': 'test.tsv',
            'size': 1000,
            'metadata': {},
            'urls_metadata': {'https://localhost/test.tsv': {}},
            'version': 'v1'
            },

            {
            'identifier': [
                {'@type': 'PropertyValue', 'name': 'md5', 'value': '12345'}
                ],
            'contentSize': 1000,
            'contentUrl': ['https://localhost/test.tsv'],
            'name': 'My Identifier Name',
            'version': 'v1'

            }
            
        ),
]




@parameterized(examples)
def test_to_dataguid(dg_json, schema_json):
    test_dg = Dataguid(schema_json=schema_json)

    test_dg.to_dataguid()

    # hashes
    assert_dict_equal(test_dg.dg_json.get('hashes'), dg_json.get('hashes'))

    # form
    assert_equal(test_dg.dg_json.get('form'), dg_json.get('form'))

    # file name
    assert_equal(test_dg.dg_json.get('file_name'), dg_json.get('file_name'))

    # urls
    assert_equal(test_dg.dg_json.get('urls'), dg_json.get('urls'))

    # size
    assert_equal(test_dg.dg_json.get('size'), dg_json.get('size'))


@parameterized(examples)
def test_to_schema(dg_json, schema_json):
    test_dg = Dataguid(dg_json=dg_json)

    test_dg.to_schema()

    # hashes

    cs = list(filter(lambda x: isinstance(x,dict), test_dg.schema_json.get('identifier')))

    assert_dict_equal(cs[0], schema_json.get('identifier')[0])

    # urls
    assert_equal(test_dg.schema_json.get('contentUrl'), schema_json.get('contentUrl'))

    # size
    assert_equal(test_dg.schema_json.get('contentSize'), schema_json.get('contentSize'))


