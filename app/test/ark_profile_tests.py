from unittest.mock import MagicMock, patch

from flask import Response

from nose.tools import assert_equal, assert_true, assert_is_not_none, assert_is_instance, assert_dict_equal
from parameterized import parameterized

from app.components.identifier_objects import Ark, Identifier404, UnknownProfile400


erc_tests = [
        # ERC element compressed
        (
        'ark:/9999/fktest', 
        '_target: http://example.org\n_profile: erc\nerc: who: Proust, Marcel%0Awhat: Remembrance of Things Past', 
        {
                '@id': 'http://n2t.net/ark:/9999/fktest', 
                'identifier':'http://n2t.net/ark:/9999/fktest', 
                '@context': 'https://schema.org',
                'url': 'http://example.org', 
                'who': {'@type': 'http://n2t.info/ark:/99152/h11', '@value': 'Proust, Marcel'},
                'what': {'@type': 'http://n2t.info/ark:/99152/h12' , '@value': 'Remembrance of Things Past'}
            }
        ),


        # ERC element expanded
        (
        'ark:/9999/fktest', 
        '_target: http://example.org\n_profile: erc\nerc.who: Proust, Marcel\nerc.what: Remembrance of Things Past', 
        {
                '@id': 'http://n2t.net/ark:/9999/fktest', 
                'identifier':'http://n2t.net/ark:/9999/fktest', 
                '@context': 'https://schema.org',
                'url': 'http://example.org', 
                'who': {'@type': 'http://n2t.info/ark:/99152/h11', '@value': 'Proust, Marcel'},
                'what': {'@type': 'http://n2t.info/ark:/99152/h12' , '@value': 'Remembrance of Things Past'}
            }
        ),


        # added invalid keys, want to ignore 
        ( 
        'ark:/9999/fktest', 
        '_target: http://example.org\n_profile: erc\nerc.who: Proust, Marcel\nerc.what: Remembrance of Things Past\nerc.NotAKey: Invalid', 
        {
                '@id': 'http://n2t.net/ark:/9999/fktest', 
                'identifier':'http://n2t.net/ark:/9999/fktest', 
                '@context': 'https://schema.org',
                'url': 'http://example.org', 
                'who': {'@type': 'http://n2t.info/ark:/99152/h11', '@value': 'Proust, Marcel'},
                'what': {'@type': 'http://n2t.info/ark:/99152/h12' , '@value': 'Remembrance of Things Past'}
            }
        ),
    
]


keys = ['@id', '@context', 'url']
dict_keys = ['who', 'what']

@parameterized(erc_tests)
def test_erc_conversion(identifier, anvl, json_ld):
    ark = Ark(guid=identifier) 
    ark.anvl = anvl

    json_response = ark.to_json_ld()

    for key in keys:
        assert_equal(json_response.get(key), json_ld.get(key))

    for key in dict_keys:
        assert_dict_equal(json_response.get(key), json_ld.get(key))
    
    assert_dict_equal(json_response, json_ld)

@parameterized(erc_landing)
def test_erc_landing_page(identifier, anvl, json_ld):


datacite_tests = [
    ( # multipule authors and alternateIdentifiers
            'ark:/85065/d76111zp', 
            '_target: http://example.org\n_profile: datacite\ndatacite: <?xml version="1.0"?>%0A<resource xmlns="http://datacite.org/schema/kernel-3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd"><identifier identifierType="ARK">85065/d76111zp</identifier><creators><creator><creatorName>Aneesh Subramanian</creatorName></creator><creator><creatorName>Caroline Ummenhofer</creatorName></creator></creators><titles><title>Translating process understanding to improve climate models. A US CLIVAR White Paper</title></titles><publisher>National Center for Atmospheric Research (NCAR)</publisher><publicationYear>2016</publicationYear><resourceType resourceTypeGeneral="Dataset">Dataset</resourceType><alternateIdentifiers><alternateIdentifier alternateIdentifierType="DOI">10.5065/D63X851Q</alternateIdentifier></alternateIdentifiers></resource>',
            {
                '@id': 'https://n2t.net/ark:/85065/d76111zp',
                'identifier': ['https://n2t.net/ark:/85065/d76111zp', 'https://doi.org/10.5065/D63X851Q'], 
                '@context': 'https://schema.org',
                '@type': 'Dataset',
                'url': 'http://example.org',
                'author': [
                    {'@type': 'Person', 'name': 'Aneesh Subramanian', 'givenName':'Aneesh', 'familyName': 'Subramanian'},
                    {'@type': 'Person', 'name': 'Caroline Ummenhofer', 'givenName': 'Caroline', 'familyName': 'Ummenhofer'}
                    ],
                'name': 'Translating process understanding to improve climate models. A US CLIVAR White Paper',
                'datePublished': '2016'
            }
    ),

    (# expanded into multipule elements
            'ark:/85065/d76111zp', 
            '_target: http://example.org\n_profile: datacite\ndatacite.identifier: ark:/85065/d76111zp\ndatacite.creator: Aneesh Subramanian;Caroline Ummenhofer\ndatacite.title: Translating process understanding to improve climate models. A US CLIVAR White Paper\ndatacite.publisher: National Center for Atmospheric Research (NCAR)\ndatacite.publicationYear: 2016\ndatacite.resourceType: Dataset\ndatacite.alternateIdentifiers: doi:/10.5065/D63X851Q',
            {
                '@id': 'https://n2t.net/ark:/85065/d76111zp',
                'identifier': ['https://n2t.net/ark:/85065/d76111zp', 'https://doi.org/10.5065/D63X851Q'], 
                '@context': 'https://schema.org',
                '@type': 'Dataset',
                'url': 'http://example.org',
                'author': [
                    {'@type': 'Person', 'name': 'Aneesh Subramanian', 'givenName':'Aneesh', 'familyName': 'Subramanian'},
                    {'@type': 'Person', 'name': 'Caroline Ummenhofer', 'givenName': 'Caroline', 'familyName': 'Ummenhofer'}
                    ],
                'name': 'Translating process understanding to improve climate models. A US CLIVAR White Paper',
                'datePublished': '2016'
            }
    ),



    (# expaned with organizational author
            'ark:/85065/d76111zp', 
            '_target: http://example.org\n_profile: datacite\ndatacite.identifier: ark:/85065/d76111zp\ndatacite.creator: NCAR\ndatacite.title: Translating process understanding to improve climate models. A US CLIVAR White Paper\ndatacite.publisher: National Center for Atmospheric Research (NCAR)\ndatacite.publicationYear: 2016\ndatacite.resourceType: Dataset\ndatacite.alternateIdentifiers: doi:/10.5065/D63X851Q',
            {
                '@id': 'https://n2t.net/ark:/85065/d76111zp',
                'identifier': ['https://n2t.net/ark:/85065/d76111zp', 'https://doi.org/10.5065/D63X851Q'], 
                '@context': 'https://schema.org',
                '@type': 'Dataset',
                'url': 'http://example.org',
                'author': {'@type': 'Organization', 'name': 'NCAR'},
                'name': 'Translating process understanding to improve climate models. A US CLIVAR White Paper',
                'datePublished': '2016'
            }
    )
]



schema_keys = ['@id', '@context', 'url', 'identifier', 'author', 'name', 'datePublished', '@type']

@parameterized(datacite_tests)
def test_json_conversion_datacite(identifier, anvl, json_ld):
    ark = Ark(guid=identifier)
    ark.anvl = anvl

    json = ark.to_json_ld()

    for key in schema_keys:
        assert_equal(json.get(key), json_ld.get(key))

    assert_dict_equal(json, json_ld)


dc_tests = [
            (
            'ark:/9999/fk4test',
            '_target: http://example.org\n_profile: dc\ndc.creator: Max Levinson\ndc.title: My Example\ndc.publisher: NIHdc\ndc.date: 2018\ndc.type: Dataset',
                {
                    '@id': 'https://n2t.net/ark:/9999/fk4test',
                    '@type': 'Dataset',
                    '@context': 'http://purl.org/dc/elements/1.1/',
                    'identifier': 'https://n2t.net/ark:/9999/fk4test',
                    'url': 'http://example.org',
                    'creator': 'Max Levinson',
                    'title': 'My Example',
                    'date': '2018',
                    'type': 'Dataset',
                    'publisher': 'NIHdc'
                }

            ),
        ]

dc_keys = ['@id', 'identifier', '@context', 'creator', 'title', 'date', 'type']

@parameterized(dc_tests)
def test_json_conversion_dublin_core(identifier, anvl, json_ld):
    ark = Ark(guid=identifier)
    ark.anvl = anvl

    json = ark.to_json_ld()

    for key in dc_keys:
        assert_equal(json.get(key), json_ld.get(key))

    assert_dict_equal(json, json_ld)


nihdc_tests = [
        (
            'ark:/9999/fk4test',
            '_target: http://example.org\n_profile: NIHdc\nNIHdc.author.type: Person\nNIHdc.author.firstName: Max\nNIHdc.author.lastName: Levinson\nNIHdc.author.name: Max Levinson\nNIHdc.name: My Example',
            {
                '@context':'https://schema.org',
                '@id': 'https://n2t.net/ark:/9999/fk4test',
                'identifier': 'https://n2t.net/ark:/9999/fk4test',
                'name': 'My Example',
                'url': 'http://example.org',
                'author': {
                    '@type': 'Person',
                    'firstName': 'Max',
                    'lastName': 'Levinson',
                    'name': 'Max Levinson'
                    }
                }

            ),
        (# multipule authors
            'ark:/9999/fk4test',
            '_target: http://example.org\n_profile: NIHdc\nNIHdc.author.type: Person;Person\nNIHdc.author.firstName: Max;Tim\nNIHdc.author.lastName: Levinson;Clark\nNIHdc.author.name: Max Levinson;Tim Clark\nNIHdc.name: My Example',
            {
                '@context':'https://schema.org',
                '@id': 'https://n2t.net/ark:/9999/fk4test',
                'identifier': 'https://n2t.net/ark:/9999/fk4test',
                'name': 'My Example',
                'url': 'http://example.org',
                'author': [
                    {
                    '@type': 'Person',
                    'firstName': 'Max',
                    'lastName': 'Levinson',
                    'name': 'Max Levinson'
                    },
                    {
                    '@type': 'Person',
                    'firstName': 'Tim',
                    'lastName': 'Clark',
                    'name': 'Tim Clark'
                        }
                    ]
                }

            ),

        (# checksum as identifier
            'ark:/9999/fk4test',
            '_target: http://example.org\n_profile: NIHdc\nNIHdc.identifier: https://n2t.net/ark:/9999/fk4test\nNIHdc.identifier.type: PropertyValue;PropertyValue\nNIHdc.identifier.name: md5;sha-256\nNIHdc.identifier.value: 1234;4321\nNIHdc.author.type: Person;Person\nNIHdc.author.firstName: Max;Tim\nNIHdc.author.lastName: Levinson;Clark\nNIHdc.author.name: Max Levinson;Tim Clark\nNIHdc.name: My Example',
            {
                '@context':'https://schema.org',
                '@id': 'https://n2t.net/ark:/9999/fk4test',
                'identifier': ['https://n2t.net/ark:/9999/fk4test', 
                    {
                        '@type': 'PropertyValue',
                        'name': 'md5',
                        '@value': '1234'
                        },
                    {
                        '@type': 'PropertyValue',
                        'name': 'sha-256',
                        '@value': '4321'
                        }
                   ], 
                'name': 'My Example',
                'url': 'http://example.org',
                'author': [
                    {
                    '@type': 'Person',
                    'firstName': 'Max',
                    'lastName': 'Levinson',
                    'name': 'Max Levinson'
                    },
                    {
                    '@type': 'Person',
                    'firstName': 'Tim',
                    'lastName': 'Clark',
                    'name': 'Tim Clark'
                        }
                    ]
                }

            )

            
]

@parameterized(nihdc_tests)
def test_json_conversion_nihdc(identifier, anvl, json_ld):
    ark = Ark(guid=identifier)
    ark.anvl = anvl

    json = ark.to_json_ld()

    print(json)
    for key in schema_keys:
        assert_equal(json.get(key), json_ld.get(key))

    assert_dict_equal(json, json_ld)

